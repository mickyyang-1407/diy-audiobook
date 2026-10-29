#!/usr/bin/env python3
"""Render the episode video: the illustrations, each on screen from its paragraph onwards, with soft crossfades.

Usage: video.py <episode_dir> [--nomusic] [--fit|--fill]

Pictures: art/prompts.json + art/<id>.* (see draw.py). Without them, the single episode.json "image" is used.
Audio: build/<slug>.m4a (or -nomusic.m4a) from mix.py. Writes build/<slug>.mp4 (1920×1080, H.264, AAC copied).
--fill (default) crops pictures to fill the frame; --fit letterboxes them instead.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Episode, die, duration, load, need, run  # noqa: E402

W, H, FPS, XF = 1920, 1080, 12, 1.5
EXTS = (".png", ".jpg", ".jpeg", ".webp")


def picture(adir, iid):
    for e in EXTS:
        p = adir / f"{iid}{e}"
        if p.exists():
            return p
    return None


def main():
    need("ffmpeg")
    ep = Episode(sys.argv[1])
    nomusic = "--nomusic" in sys.argv
    audio = ep.build / f"{ep.slug}{'-nomusic' if nomusic else ''}.m4a"
    if not audio.exists():
        die(f"{audio.name} missing — run mix.py{' --nomusic' if nomusic else ''} first")
    total = duration(audio)
    tl = load(ep.build / "timeline.json")
    first_at = {}
    for c in tl:
        first_at.setdefault(c["para"], c["start"])

    shots = []                                   # (start seconds, picture)
    spec_path = ep.dir / "art/prompts.json"
    if spec_path.exists():
        rows = load(ep.script)
        scene_starts = [r["id"] for r in rows if r.get("scene")] or [rows[0]["id"]]
        for k, img in enumerate(load(spec_path)["images"]):
            p = picture(ep.dir / "art", img["id"])
            if not p:
                die(f"art/{img['id']}.png missing — run draw.py")
            at = img.get("at") or scene_starts[min(k, len(scene_starts) - 1)]
            if at not in first_at:
                die(f"image {img['id']}: paragraph {at} is not in the timeline")
            shots.append((0.0 if k == 0 else first_at[at], p))
    elif ep.cfg.get("image"):
        p = Path(ep.cfg["image"]).expanduser()
        shots = [(0.0, p if p.is_absolute() else ep.dir / p)]
    else:
        die("no pictures: add art/prompts.json + draw.py, or set \"image\" in episode.json")
    shots.sort(key=lambda s: s[0])
    shots[0] = (0.0, shots[0][1])

    fit = "--fit" in sys.argv
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2" if fit else
          f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}")
    cmd, chains = ["ffmpeg", "-y", "-v", "error"], []
    n = len(shots)
    for i, (t, p) in enumerate(shots):
        end = shots[i + 1][0] if i + 1 < n else total
        dur = max(0.5, end - t) + XF
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(p)]
        chains.append(f"[{i}:v]{vf},setsar=1,format=yuv420p,fps={FPS}[v{i}]")
    last = "v0"
    for i in range(1, n):
        # offset = when the next picture starts, minus the overlap
        off = shots[i][0] - XF / 2
        chains.append(f"[{last}][v{i}]xfade=transition=fade:duration={XF}:offset={max(0.0, off):.3f}[x{i}]")
        last = f"x{i}"
    cmd += ["-i", str(audio), "-filter_complex", ";".join(chains), "-map", f"[{last}]", "-map", f"{n}:a",
            "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium", "-crf", "20", "-c:a", "copy",
            "-t", f"{total:.3f}", "-movflags", "+faststart", str(audio.with_suffix(".mp4"))]
    run(cmd)
    print(f"{audio.with_suffix('.mp4').name}: {n} picture{'s' if n > 1 else ''}, {total / 60:.1f} min")


if __name__ == "__main__":
    main()
