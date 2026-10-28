#!/usr/bin/env python3
"""Check a TTS backend and your API key with one short sentence (costs a few characters).

Usage:
  try_voice.py edge    zh-TW-HsiaoChenNeural  "晚安，今晚的故事開始了。"
  try_voice.py minimax "Chinese (Mandarin)_Gentleman" "晚安，今晚的故事開始了。"
  try_voice.py openai  onyx "Good night. Tonight's story begins."
Writes try-<backend>.<ext> in the current folder and prints how long it is.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backends  # noqa: E402
from common import SR, decode, need  # noqa: E402


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    need("ffmpeg")
    name, voice = sys.argv[1], sys.argv[2]
    text = sys.argv[3] if len(sys.argv) > 3 else "晚安，今晚的故事開始了。"
    try:
        fn, ext = backends.get(name)
        out = Path(f"try-{name}{ext}")
        fn(text, {"voice": voice}, out)
    except backends.TTSError as e:
        print(f"✗ {e}")
        sys.exit(1)
    secs = len(decode(out)) / SR
    print(f"✓ {name} works — {out} ({secs:.1f} s). Open it and listen.")


if __name__ == "__main__":
    main()
