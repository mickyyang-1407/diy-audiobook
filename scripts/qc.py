#!/usr/bin/env python3
"""Automatic checks on a finished episode. Exit 0 = nothing red.

Usage: qc.py <episode_dir>

Red:    master loudness off target by > 0.5 LU, AAC true peak above -1.0 dBTP, a clip that is far too long or
        far too short for its text (TTS glitches: repeated phrases, swallowed sentences), dead air > 12 s.
Yellow: clips whose pace is unusual, an intro/outro more than 1.3× slower than the story (a chain of short
        sentences — sounds halting), roles levelled by more than 9 dB (a voice that is very quiet or loud raw).
Ears are still the final check: listen to the first minute, one scene change, and every yellow clip.
"""
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Episode, load, ts  # noqa: E402


def units(text):
    cjk = len(re.findall(r"[぀-ヿ㐀-鿿]", text))
    return cjk + len(re.findall(r"[A-Za-z0-9']+", text)) * 1.6 or 1


def main():
    ep = Episode(sys.argv[1])
    red, yellow = [], []
    tl = load(ep.build / "timeline.json")
    pace = [(c, (c["end"] - c["start"]) / units(c["text"])) for c in tl if units(c["text"]) >= 6]
    if len(pace) >= 5:
        med = statistics.median(p for _, p in pace)
        for c, p in pace:
            where = f"{ts(c['start'], srt=False)} {c['para']} {c['role']}: {c['text'][:30]}"
            if c["para"] in ("INTRO", "OUTRO") and p > 1.3 * med:
                # 10-29: 「嗨，小朋友，晚安。故事時間到囉。」 measured 1.39× and sounded halting — every 。 is a
                # ~1 s stop on edge voices; the greeting a listener liked measured 1.29×
                yellow.append(f"{c['para'].lower()} is {p / med:.2f}× slower than the story — it will sound halting. "
                              f"Join the short sentences with commas into one or two flowing sentences")
            if p > 2.2 * med or p < 0.45 * med:
                red.append(f"clip pace {p / med:.1f}× normal — {where}")
            elif p > 1.6 * med or p < 0.62 * med:
                yellow.append(f"clip pace {p / med:.1f}× normal — {where}")
    for a, b in zip(tl, tl[1:]):
        if b["start"] - a["end"] > 12:
            red.append(f"{b['start'] - a['end']:.1f} s of silence before {ts(b['start'], srt=False)}")
    lv = load(ep.build / "levels.json", {})
    for role, db in lv.get("offset_db", {}).items():
        if abs(db) > 9:
            yellow.append(f"{role} needed {db:+.1f} dB to match the narrator — listen to that voice")
    for name in ("mix-report.json", "mix-report-nomusic.json"):
        p = ep.build / name
        if not p.exists():
            continue
        m = json.loads(p.read_text())["master"]
        if abs(m["lufs"] - m["target"]) > 0.5:
            red.append(f"{m['file']}: {m['lufs']:.1f} LUFS, target {m['target']}")
        if m["true_peak"] > -1.0:
            red.append(f"{m['file']}: true peak {m['true_peak']:.1f} dBTP > -1.0")
        print(f"{m['file']}: {m['lufs']:.1f} LUFS, {m['true_peak']:.1f} dBTP")
    if not any((ep.build / n).exists() for n in ("mix-report.json", "mix-report-nomusic.json")):
        yellow.append("no mix report yet — run mix.py")
    print(f"{len(tl)} clips, {ts(tl[-1]['end'], srt=False)} of speech")
    for y in yellow:
        print(f"yellow: {y}")
    for r in red:
        print(f"RED: {r}")
    save_to = ep.build / "qc.json"
    save_to.write_text(json.dumps({"red": red, "yellow": yellow}, ensure_ascii=False, indent=1))
    print("QC OK" if not red else f"QC FAILED ({len(red)} red)")
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
