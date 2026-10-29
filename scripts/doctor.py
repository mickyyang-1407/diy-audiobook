#!/usr/bin/env python3
"""What can this computer do right now? Checks tools, Python packages, API keys (only whether they are set —
never their values) and a local ComfyUI, then says which voice / picture / music options are ready.

Usage: doctor.py
"""
import importlib.util
import json
import os
import shutil
import sys
import urllib.request

OK, NO, OPT = "✓", "✗", "·"


def has(mod):
    return importlib.util.find_spec(mod) is not None


def comfy():
    url = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    try:
        with urllib.request.urlopen(f"{url}/object_info/CheckpointLoaderSimple", timeout=3) as r:
            d = json.load(r)
        return url, d["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    except Exception:
        return url, None


def main():
    rows, ready = [], {"voices": [], "pictures": ["manual (your own pictures)"], "music": ["none"]}
    py = sys.version_info >= (3, 9)
    rows.append((OK if py else NO, f"Python {sys.version.split()[0]}", "" if py else "need 3.9 or newer"))
    ff = shutil.which("ffmpeg") and shutil.which("ffprobe")
    rows.append((OK if ff else NO, "ffmpeg", "" if ff else "install: brew install ffmpeg  /  apt install ffmpeg  /  winget install ffmpeg"))
    for mod, why, pip in (("edge_tts", "free voices", "edge-tts"), ("numpy", "music check + free lullaby music", "numpy"),
                          ("PIL", "cover images", "pillow")):
        rows.append((OK if has(mod) else NO, f"{pip} ({why})", "" if has(mod) else f"pip install {pip}"))
    if has("edge_tts"):
        ready["voices"].append("edge (free)")
    if has("numpy"):
        ready["music"].append("generated lullaby (free): music.py make")
    ready["music"].append("your own / Suno files: put them in the episode's music/ folder")
    for key, what in (("MINIMAX_API_KEY", "MiniMax voices + pictures"), ("OPENAI_API_KEY", "OpenAI voices + pictures")):
        on = bool(os.environ.get(key))
        rows.append((OK if on else OPT, f"{key} ({what})", "set" if on else "not set — optional, see docs/API.md"))
        if on:
            name = key.split("_")[0].lower()
            ready["voices"].append(name)
            ready["pictures"].append(f"{name} (cloud)")
    url, ckpts = comfy()
    if ckpts is None:
        rows.append((OPT, "ComfyUI (local pictures)", f"not reachable at {url} — optional, see references/images.md"))
    else:
        rows.append((OK, "ComfyUI (local pictures)", f"{url}, {len(ckpts)} checkpoints"))
        ready["pictures"].append("comfyui (local, free)")
    for mark, name, note in rows:
        print(f" {mark} {name:<46} {note}")
    print()
    for k, v in ready.items():
        print(f" {k:<9} {', '.join(v) if v else '— none yet'}")
    essential = py and ff and ready["voices"]
    print("\nReady to make an episode." if essential else "\nFix the ✗ lines above first.")
    sys.exit(0 if essential else 1)


if __name__ == "__main__":
    main()
