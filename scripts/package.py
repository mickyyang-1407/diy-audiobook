#!/usr/bin/env python3
"""Write the upload text: title, description with chapters, credits.

Usage: package.py <episode_dir>
Writes build/description.md (paste into YouTube / podcast host; upload build/subtitles.srt as captions).

Chapters come from the scene breaks in script.json; a scene may carry "scene_title". YouTube only shows
chapters when the first is at 0:00, there are at least three, and each is at least 10 seconds long.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Episode, load, ts  # noqa: E402

CREDIT = {"edge": "Microsoft Edge neural voices", "minimax": "MiniMax speech", "openai": "OpenAI text-to-speech"}


def main():
    ep = Episode(sys.argv[1])
    cfg = ep.cfg
    rows = {r["id"]: r for r in load(ep.script)}
    tl = load(ep.build / "timeline.json")
    zh = cfg.get("language", "").startswith("zh")
    chapters, seen = [(0.0, "開場" if zh else "Opening")], set()
    for c in tl:
        s = c["scene"]
        if s is None or s in seen:
            continue
        seen.add(s)
        r = rows.get(c["para"], {})
        title = r.get("scene_title") or (f"第 {s + 1} 幕" if zh else f"Part {s + 1}")
        if c["start"] - chapters[-1][0] >= 10:
            chapters.append((c["start"], title))
        elif len(chapters) == 1:
            chapters[0] = (0.0, title)
    ok = len(chapters) >= 3
    show = cfg.get("show", "")
    title = f"{cfg.get('title', ep.slug)}｜{show}" if show else cfg.get("title", ep.slug)
    lines = [f"# {title}", ""]
    if zh:
        lines += [f"{cfg.get('author', '')}〈{cfg.get('title', '')}〉，多角色睡前廣播劇。關燈、躺好，聽完再睡。", ""]
    else:
        lines += [f"{cfg.get('title', '')} by {cfg.get('author', '')}, as a multi-voice bedtime radio drama.", ""]
    if ok:
        lines += [f"{ts(t, srt=False)} {name}" for t, name in chapters] + [""]
    src = cfg.get("source_url", "")
    lines += ["原著為公有領域作品" + (f"：{src}" if src.startswith("http") else "") if zh
              else "Original text in the public domain" + (f": {src}" if src.startswith("http") else ""),
              ("語音：" if zh else "Voices: ") + CREDIT.get(cfg["backend"], cfg["backend"]),
              ("製作流程：" if zh else "Made with ") + "pillow-detective (Claude Code skill)"]
    out = ep.build / "description.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{out}" + ("" if ok else "  (fewer than 3 usable chapters — YouTube will not show chapters)"))


if __name__ == "__main__":
    main()
