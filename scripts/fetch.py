#!/usr/bin/env python3
"""Create an episode folder from a public-domain text.

Usage:
  fetch.py <episode_dir> --gutenberg 1661 [--start "THE RED-HEADED LEAGUE"] [--end "A CASE OF IDENTITY"]
  fetch.py <episode_dir> --url https://…/story.txt [--start …] [--end …]
  fetch.py <episode_dir> --file story.txt
  options: --title "…" --author "…" --language zh-TW --max-paragraphs 40

Writes episode.json (edit it afterwards) and source/source.json = [{"id": "P001", "text": "…"}, …].
--start / --end are literal lines that bracket the story inside a collection (end line excluded).
"""
import argparse
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import die, load, save  # noqa: E402

GUTENBERG = "https://www.gutenberg.org/cache/epub/{n}/pg{n}.txt"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "pillow-detective/1.0 (+https://github.com/mickyyang-1407/pillow-detective)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8-sig", errors="replace")


def strip_gutenberg(text):
    a = re.search(r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", text)
    b = re.search(r"\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG", text)
    return text[a.end() if a else 0:b.start() if b else len(text)]


def cut(text, start, end):
    if start:
        # skip a table-of-contents hit: take the last occurrence that is followed by real prose
        hits = [m.start() for m in re.finditer(re.escape(start), text)]
        if not hits:
            die(f"--start {start!r} not found")
        text = text[hits[-1] if len(hits) > 1 else hits[0]:]
        text = text.split("\n", 1)[1] if "\n" in text else ""
    if end:
        k = text.find(end)
        if k < 0:
            die(f"--end {end!r} not found after the start")
        text = text[:k]
    return text


def paragraphs(text):
    text = text.replace("\r\n", "\n")
    out = []
    for block in re.split(r"\n\s*\n", text):
        p = re.sub(r"\s*\n\s*", " ", block).strip()
        p = re.sub(r"_([^_]+)_", r"\1", p)          # Gutenberg italics
        if not p or re.fullmatch(r"[\W\dIVXLC.]+", p):  # rules, chapter numerals
            continue
        out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--gutenberg", type=int)
    src.add_argument("--url")
    src.add_argument("--file")
    ap.add_argument("--start"); ap.add_argument("--end")
    ap.add_argument("--title", default=""); ap.add_argument("--author", default="")
    ap.add_argument("--language", default="zh-TW", help="language of the finished drama (BCP-47)")
    ap.add_argument("--max-paragraphs", type=int, default=0, help="keep only the first N (for a short demo)")
    a = ap.parse_args()

    if a.gutenberg:
        url = GUTENBERG.format(n=a.gutenberg); raw = get(url)
    elif a.url:
        url = a.url; raw = get(url)
    else:
        url = str(Path(a.file).resolve()); raw = Path(a.file).read_text(encoding="utf-8-sig")
    paras = paragraphs(cut(strip_gutenberg(raw), a.start, a.end))
    if a.max_paragraphs:
        paras = paras[:a.max_paragraphs]
    if not paras:
        die("no paragraphs found — check --start/--end")

    ep = Path(a.episode).expanduser()
    rows = [{"id": f"P{i:03d}", "text": p} for i, p in enumerate(paras, 1)]
    save(ep / "source/source.json", rows)
    cfg_path = ep / "episode.json"
    cfg = load(cfg_path, {}) if cfg_path.exists() else {}
    template = load(Path(__file__).resolve().parent.parent / "templates/episode.json")
    cfg = {**template, **cfg, "source_url": url, "language": cfg.get("language", a.language)}
    if a.title:
        cfg["title"] = a.title
    if a.author:
        cfg["author"] = a.author
    save(cfg_path, cfg)
    words = sum(len(p.split()) for p in paras)
    print(f"{ep}: {len(rows)} paragraphs, ~{words} words → source/source.json; edit episode.json next")


if __name__ == "__main__":
    main()
