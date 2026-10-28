#!/usr/bin/env python3
"""Validate an episode before spending any TTS calls. Exit 0 = ready to synthesize.

Usage: check.py <episode_dir> [--show-untagged]

Blocks on: script paragraphs that don't line up with the source, paragraphs left untranslated or half
translated, speaker lists whose length doesn't match the number of quotes, roles without a voice, two roles
sharing one voice. Writes script/cast.resolved.json.
"""
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Episode, load, paragraph_runs, save, speakers_for  # noqa: E402
from castlib import CastError, resolve  # noqa: E402


def size(text):
    """Comparable 'amount of content': CJK characters count one each, other scripts count words."""
    cjk = len(re.findall(r"[぀-ヿ㐀-鿿]", text))
    words = len(re.findall(r"[A-Za-z0-9À-ÿ']+", text))
    return cjk + words


def main():
    ep = Episode(sys.argv[1])
    errors, warns = [], []
    src = load(ep.source)
    rows = load(ep.script)
    speakers = load(ep.speakers, {})
    cast = load(ep.cast, {})

    sid = [r["id"] for r in src]
    tid = [r["id"] for r in rows]
    missing = [i for i in sid if i not in set(tid)]
    extra = [i for i in tid if i not in set(sid)]
    if missing:
        errors.append(f"not in script.json (dropped paragraphs?): {missing[:15]}{' …' if len(missing) > 15 else ''}")
    if extra:
        errors.append(f"script ids that are not in the source: {extra[:15]}")
    if tid != [i for i in sid if i in set(tid)]:
        errors.append("script.json paragraphs are out of source order")
    empty = [r["id"] for r in rows if not r.get("text", "").strip()]
    if empty:
        errors.append(f"empty paragraphs: {empty}")

    # Untranslated / truncated paragraphs: an LLM translator sometimes returns a paragraph unchanged or drops
    # half of it. Compare each paragraph's size ratio against the episode median.
    lang = ep.cfg.get("language", "")
    by_src = {r["id"]: r["text"] for r in src}
    ratios = {r["id"]: size(r["text"]) / max(1, size(by_src.get(r["id"], ""))) for r in rows if r["id"] in by_src}
    if len(ratios) >= 5:
        med = statistics.median(ratios.values())
        allowed = {r["id"] for r in rows if r.get("allow_short")}
        for pid, k in ratios.items():
            if size(by_src[pid]) < 25:
                continue
            if k < 0.3 * med and pid not in allowed:
                errors.append(f"{pid}: only {k / med:.0%} of the usual length — a passage is missing (if the cut "
                              f"is deliberate, add \"allow_short\": true to that paragraph)")
            elif k < 0.45 * med or k > 2.6 * med:
                warns.append(f"{pid}: length ratio {k:.2f} vs median {med:.2f} — check for a missing or padded passage")
    if lang.startswith(("zh", "ja")):
        for r in rows:
            latin = len(re.findall(r"[A-Za-z]", r["text"]))
            if latin > 12 and latin > 0.25 * len(r["text"]):
                errors.append(f"{r['id']}: looks untranslated ({latin} Latin letters)")

    pr = paragraph_runs(rows)
    ids = set(tid)
    for pid, tag in speakers.items():
        if pid not in ids:
            errors.append(f"speakers.json: {pid} is not a paragraph id"); continue
        nq = sum(1 for k, _ in pr[pid] if k == "Q")
        if nq == 0:
            errors.append(f"speakers.json: {pid} is tagged but has no quoted speech")
        elif isinstance(tag, list) and len(tag) != nq:
            errors.append(f"speakers.json: {pid} lists {len(tag)} speakers for {nq} quotes")
    untagged = [pid for pid, rs in pr.items() if any(k == "Q" for k, _ in rs) and pid not in speakers]

    try:
        voices = resolve(ep.cfg, speakers, cast)
    except CastError as e:
        errors.append(f"cast: {e}")
        voices = {}

    clips, chars = 0, 0
    for r in rows:
        rs = pr[r["id"]]
        who = iter(speakers_for(speakers.get(r["id"]), sum(1 for k, _ in rs if k == "Q")))
        prev = object()
        for k, t in rs:
            role = (next(who, None) or "narrator") if k == "Q" else "narrator"
            clips += role != prev
            prev = role
            chars += len(t)

    print(f"{ep.slug}: {len(rows)} paragraphs, {sum(1 for r in rows if r.get('scene'))} scene breaks, "
          f"~{clips} clips, {chars} characters, backend {ep.cfg['backend']}")
    for role, v in sorted(voices.items()):
        n = sum(1 for t in speakers.values() for s in (t if isinstance(t, list) else [t]) if s == role)
        extra_v = " ".join(f"{k}={v[k]}" for k in ("pitch", "rate", "speed", "emotion") if v.get(k))
        print(f"  {role:<14} {v['voice']:<40} {extra_v}  ({n} tagged)")
    if untagged:
        print(f"  {len(untagged)} paragraphs with quotes read by the narrator (fine for signs, letters, titles): "
              + (", ".join(untagged) if "--show-untagged" in sys.argv else f"{', '.join(untagged[:12])}"
                 + (" … (--show-untagged)" if len(untagged) > 12 else "")))
    if not ep.cfg.get("intro") or not ep.cfg.get("outro"):
        warns.append("episode.json intro/outro is empty — the show's fixed greeting makes it feel like a series")
    for w in warns:
        print(f"warn: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        sys.exit(1)
    save(ep.dir / "script/cast.resolved.json", voices)
    print("OK — ready for synth.py")


if __name__ == "__main__":
    main()
