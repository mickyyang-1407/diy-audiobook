#!/usr/bin/env python3
"""Synthesize the multi-voice narration track of an episode.

Usage: synth.py <episode_dir> [--workers N] [--only-clips]

Reads   episode.json, script/script.json, script/speakers.json, script/cast.resolved.json (run check.py first)
Writes  build/clips/<hash>.*      one cached TTS call per (voice settings, text) — re-runs only pay for changes
        build/narration.wav       mono 44.1 kHz, every voice levelled to the narrator, gaps inserted
        build/timeline.json       [{start, end, role, para, scene, text}]
        build/subtitles.srt

Every paragraph is cut at its top-level quotes; each piece goes to its speaker's voice and adjacent pieces of the
same speaker are merged into one request. The silence TTS engines pad at both ends of a clip is trimmed so the
gaps you hear are the gaps in episode.json.
"""
import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backends  # noqa: E402
from common import (SR, Episode, decode, die, load, loudness, need, paragraph_runs, save, silence,  # noqa: E402
                    speakers_for, trim, ts, write_wav)

WORKERS = {"edge": 4, "minimax": 2, "openai": 3}
MAX_LEVEL_DB = 12.0


def plan(ep, rows, speakers):
    """Ordered pieces: {role, text, para, scene, gap_before}."""
    g = ep.cfg["gaps"]
    pr = paragraph_runs(rows)
    out, scene = [], 0
    if ep.cfg.get("intro"):
        out.append({"role": "narrator", "text": ep.cfg["intro"], "para": "INTRO", "scene": None,
                    "gap_before": g.get("lead_in", 1.0)})
    first = True
    for r in rows:
        if r.get("scene") and not first:
            scene += 1
        rs = pr[r["id"]]
        who = iter(speakers_for(speakers.get(r["id"]), sum(1 for k, _ in rs if k == "Q")))
        pieces = []
        for k, t in rs:
            role = (next(who, None) or "narrator") if k == "Q" else "narrator"
            if pieces and pieces[-1]["role"] == role:
                prev = pieces[-1]["text"]
                sep = " " if re.match(r"[\w‘“\"']", t) and re.search(r"[\w.,;:!?’”\"'—]$", prev) \
                    and not re.search(r"[\u3040-\u30ff\u3400-\u9fff]$", prev) else ""
                pieces[-1]["text"] = prev + sep + t
            else:
                pieces.append({"role": role, "text": t})
        for i, p in enumerate(pieces):
            if i:
                gap = g["quote"]
            elif first:
                gap = g["after_intro"] if out else g.get("lead_in", 1.0)
            elif r.get("scene"):
                gap = g["scene"]
            else:
                gap = g["paragraph"]
            out.append({**p, "para": r["id"], "scene": scene, "gap_before": gap})
        first = False
    if ep.cfg.get("outro"):
        out.append({"role": "narrator", "text": ep.cfg["outro"], "para": "OUTRO", "scene": None,
                    "gap_before": g["before_outro"]})
    return [p for p in out if re.search(r"\w", p["text"])]  # a quote that is only "……" becomes silence


def key(backend, voice, text):
    blob = json.dumps([backend, voice, text], ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:20]


def split_cues(text, t0, t1, cjk):
    """Sentence-level subtitle cues with time shared out by length."""
    limit = 28 if cjk else 84
    parts = [s for s in re.split(r"(?<=[。！？!?…；;])\s*|(?<=[.])\s+", text) if s.strip()]
    cues = []
    for s in parts:
        while len(s) > limit:
            cut = max((s.rfind(c, 0, limit) for c in "，,、：: "), default=-1)
            cut = cut + 1 if cut > limit // 3 else limit
            cues.append(s[:cut]); s = s[cut:]
        if s.strip():
            cues.append(s)
    total = sum(len(c) for c in cues) or 1
    out, t = [], t0
    for c in cues:
        d = (t1 - t0) * len(c) / total
        out.append((t, t + d, c.strip()))
        t += d
    return out


def main():
    need("ffmpeg")
    ep = Episode(sys.argv[1])
    resolved = ep.dir / "script/cast.resolved.json"
    if not resolved.exists() or resolved.stat().st_mtime < max(
            p.stat().st_mtime for p in (ep.script, ep.dir / "episode.json") if p.exists()):
        die("run check.py first (cast.resolved.json is missing or older than the script)")
    voices = load(resolved)
    rows = load(ep.script)
    speakers = load(ep.speakers, {})
    backend = ep.cfg["backend"]
    fn, ext = backends.get(backend)
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else WORKERS[backend]

    pieces = plan(ep, rows, speakers)
    clips = ep.build / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    for p in pieces:
        p["clip"] = clips / (key(backend, voices[p["role"]], p["text"]) + ext)
    todo = {}
    for p in pieces:
        if not p["clip"].exists():
            todo[p["clip"]] = p
    print(f"{len(pieces)} pieces, {len(todo)} to synthesize with {backend} ({workers} at a time)", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {}
        for path, p in todo.items():
            tmp = path.with_suffix(".part" + ext)
            futs[pool.submit(fn, p["text"], voices[p["role"]], tmp)] = (path, tmp)
        for f in as_completed(futs):
            path, tmp = futs[f]
            try:
                f.result()
            except backends.TTSError as e:
                pool.shutdown(cancel_futures=True)
                die(f"{e}\n(clips made so far are cached — fix the problem and run synth.py again)")
            tmp.replace(path)
            done += 1
            if done % 10 == 0 or done == len(todo):
                print(f"  {done}/{len(todo)}", flush=True)
    if "--only-clips" in sys.argv:
        return

    # Level every voice to the narrator: TTS voices differ by several dB, and a bedtime listener should never
    # reach for the volume. Measured per role over all its clips, not per clip (short clips measure badly).
    audio = {}
    for p in pieces:
        if p["clip"] not in audio:
            audio[p["clip"]] = trim(decode(p["clip"]))
    # grouped by voice, not role: a role that shares the narrator's voice ("same:narrator") must get the same gain
    vkey = {role: json.dumps(v, sort_keys=True) for role, v in voices.items()}
    names = {}
    for role in sorted(vkey, key=lambda r: (r != "narrator", r)):
        names.setdefault(vkey[role], role)
    level_dir = ep.build / "level"
    lufs = {}
    for k in sorted({vkey[p["role"]] for p in pieces}):
        buf = silence(0)
        for p in pieces:
            if vkey[p["role"]] == k:
                buf.extend(audio[p["clip"]])
        tmp = level_dir / f"{names[k]}.wav"
        write_wav(tmp, buf)
        lufs[names[k]] = loudness(tmp)[0]
    ref = lufs.get("narrator", max(lufs.values()))
    offsets = {}
    for name, v in lufs.items():
        offsets[name] = 0.0 if v == float("-inf") else max(-MAX_LEVEL_DB, min(MAX_LEVEL_DB, ref - v))
    for name, db in offsets.items():
        if abs(db) >= 0.5:
            print(f"  level {name}: {db:+.1f} dB")
    leveled = {}
    for p in pieces:
        k = (p["clip"], p["role"])
        if k not in leveled:
            db = offsets[names[vkey[p["role"]]]]
            leveled[k] = audio[p["clip"]] if abs(db) < 0.5 else trim(decode(p["clip"], gain_db=db))

    g = ep.cfg["gaps"]
    track = silence(0)
    timeline, cues = [], []
    cjk = ep.cfg.get("language", "").startswith(("zh", "ja", "ko"))
    for p in pieces:
        track.extend(silence(p["gap_before"]))
        t0 = len(track) / SR
        track.extend(leveled[(p["clip"], p["role"])])
        t1 = len(track) / SR
        timeline.append({"start": round(t0, 3), "end": round(t1, 3), "role": p["role"], "para": p["para"],
                         "scene": p["scene"], "text": p["text"]})
        cues += split_cues(p["text"], t0, t1, cjk)
    track.extend(silence(g.get("tail", 5.0)))
    write_wav(ep.build / "narration.wav", track)
    save(ep.build / "timeline.json", timeline)
    (ep.build / "subtitles.srt").write_text(
        "".join(f"{i}\n{ts(a)} --> {ts(b)}\n{t}\n\n" for i, (a, b, t) in enumerate(cues, 1)), encoding="utf-8")
    save(ep.build / "levels.json", {"lufs": lufs, "offset_db": offsets})
    print(f"narration {ts(len(track) / SR, srt=False)} → build/narration.wav, timeline.json, subtitles.srt")


if __name__ == "__main__":
    main()
