#!/usr/bin/env python3
"""Mix narration with an optional music bed, master the loudness, and render audio (+ video if an image is set).

Usage: mix.py <episode_dir> [--nomusic]

Reads   build/narration.wav, episode.json (music, music_below_lu, duck_ratio, image, target_lufs, true_peak)
Writes  build/<slug>.m4a           (always)
        build/<slug>.mp4           (when episode.json "image" points at a picture)
        build/mix-report.json

Music sits `music_below_lu` LU under the voice (16.5 by default) and is pushed down a further few dB while
someone is speaking (sidechain, `duck_ratio`:1), so the pauses breathe but words are never masked.
The master is two-pass EBU R128 to `target_lufs` with true-peak headroom for the AAC encoder.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Episode, die, duration, loudness, need, run, save  # noqa: E402

AAC_TP_LIMIT = -1.0      # delivered AAC must stay under this true peak (YouTube/Apple/Spotify all accept it)


def last_json(stderr):
    return json.loads(stderr[stderr.rfind("{"):stderr.rfind("}") + 1])


def resolve(ep, value):
    if not value:
        return None
    p = Path(value).expanduser()
    p = p if p.is_absolute() else ep.dir / p
    if not p.exists():
        die(f"{p} does not exist (episode.json)")
    return p


def main():
    need("ffmpeg")
    ep = Episode(sys.argv[1])
    cfg = ep.cfg
    narr = ep.build / "narration.wav"
    if not narr.exists():
        die("build/narration.wav missing — run synth.py first")
    nomusic = "--nomusic" in sys.argv
    music = None if nomusic else resolve(ep, cfg.get("music"))
    image = resolve(ep, cfg.get("image"))
    total = duration(narr)
    n_lufs, _ = loudness(narr)
    report = {"narration_lufs": n_lufs, "duration_s": round(total, 2)}

    target, tp = cfg.get("target_lufs", -14.0), cfg.get("true_peak", -1.5)
    out_a = ep.build / f"{ep.slug}{'-nomusic' if nomusic else ''}.m4a"

    # 1) Voice alone to target. Speech peaks sit ~19 dB above its loudness, so loudnorm usually runs in dynamic
    #    mode and lands a few tenths under target — measure and nudge the aim until it is within 0.3 LU.
    #    The music must NOT go through this step: dynamic loudnorm behaves like an AGC and would pull the bed up
    #    in every pause.
    pre, voice = ep.build / "voice-pre.wav", ep.build / "voice.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(narr), "-af", "aresample=48000,aformat=channel_layouts=stereo",
         "-c:a", "pcm_s24le", str(pre)])
    aim = target
    for passes in range(1, 6):
        r = subprocess.run(["ffmpeg", "-nostats", "-i", str(pre), "-af",
                            f"loudnorm=I={aim:.2f}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True)
        m = last_json(r.stderr)
        ln = (f"loudnorm=I={aim:.2f}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
              f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
              f"linear=true")
        run(["ffmpeg", "-y", "-v", "error", "-i", str(pre), "-af", f"{ln},aresample=48000", "-c:a", "pcm_s24le",
             str(voice)])
        v_lufs, _ = loudness(voice)
        if abs(v_lufs - target) <= 0.3:
            break
        aim = max(-30.0, min(-5.0, aim + target - v_lufs))
    pre.unlink(missing_ok=True)
    report["voice"] = {"lufs": v_lufs, "passes": passes}

    # 2) Music bed `music_below_lu` under the finished voice, ducked a few dB more while someone speaks.
    mixed = voice
    if music:
        mixed = ep.build / "mixed.wav"
        m_lufs, _ = loudness(music)
        gain = v_lufs - cfg.get("music_below_lu", 16.5) - m_lufs
        fade_out = max(0.0, total - 10)
        fc = (f"[1:a]aresample=48000,aformat=channel_layouts=stereo,volume={gain:.2f}dB,"
              f"afade=t=in:d=8,afade=t=out:st={fade_out:.2f}:d=10,atrim=0:{total:.3f}[m];"
              f"[0:a]asplit=2[n][key];"
              f"[m][key]sidechaincompress=threshold=0.06:ratio={cfg.get('duck_ratio', 3)}:attack=200:"
              f"release=1800:knee=6[md];[n][md]amix=inputs=2:normalize=0:duration=first[out]")
        run(["ffmpeg", "-y", "-v", "error", "-i", str(voice), "-stream_loop", "-1", "-i", str(music),
             "-filter_complex", fc, "-map", "[out]", "-c:a", "pcm_s24le", str(mixed)])
        report["music"] = {"file": music.name, "music_lufs": m_lufs, "gain_db": round(gain, 2),
                           "below_lu": cfg.get("music_below_lu", 16.5), "duck_ratio": cfg.get("duck_ratio", 3)}

    # 3) Linear trim + peak limiter, encode, verify. AAC overshoots the PCM peak by 0.3–1 dB, so if the encoded
    #    file crosses -1.0 dBTP, lower the limiter and encode again.
    trim_db = target - loudness(mixed)[0]
    ceiling = tp
    for attempt in range(4):
        lim = 10 ** (ceiling / 20)
        run(["ffmpeg", "-y", "-v", "error", "-i", str(mixed), "-af",
             f"volume={trim_db:.2f}dB,alimiter=limit={lim:.4f}:level=false:attack=5:release=60,aresample=48000",
             "-c:a", "aac", "-b:a", "192k", str(out_a)])
        i, peak = loudness(out_a)
        if peak <= AAC_TP_LIMIT:
            break
        ceiling -= 0.5
    if mixed != voice:
        mixed.unlink(missing_ok=True)
    report.update(master={"file": out_a.name, "lufs": i, "true_peak": peak, "target": target,
                          "limiter_ceiling": ceiling, "encode_passes": attempt + 1})
    if image:
        out_v = out_a.with_suffix(".mp4")
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "1", "-i", str(image), "-i", str(out_a),
             "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
                    "format=yuv420p", "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium",
             "-r", "1", "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out_v)])
        report["video"] = out_v.name
    save(ep.build / f"mix-report{'-nomusic' if nomusic else ''}.json", report)
    print(f"{out_a.name}: {i:.1f} LUFS, true peak {peak:.1f} dBTP"
          + (f"; music {report['music']['gain_db']:+.1f} dB" if music else "")
          + (f"; video {report['video']}" if image else ""))
    if abs(i - target) > 0.5:
        print(f"warn: integrated loudness {i:.1f} is more than 0.5 LU off target {target} — "
              f"very dynamic narration; check build/mix-report.json")


if __name__ == "__main__":
    main()
