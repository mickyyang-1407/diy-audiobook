#!/usr/bin/env python3
"""Check music beds before you use them.

Usage:
  music.py check FILE|FOLDER …    find frozen "held chord" stretches (exit 1 if any); needs numpy
  music.py info  FILE|FOLDER …    duration and loudness of each track
  music.py make  OUT.wav [--minutes 4] [--seed 1] [--key C]
                                  generate a free, original music-box lullaby bed (needs numpy) — a
                                  zero-setup fallback; Suno or your own music sounds better (references/music.md)

AI music generators (Suno included) sometimes hang on one chord for one to six minutes. In a 3-minute
preview you won't notice; at minute 30 of a sleep story it is maddening. `check` measures, per second, how
similar the spectrum is to the spectrum 20 s earlier (30 s moving average). Frozen stretches score 0.92–0.98;
real music — strings, piano, ambient pads included — stayed under 0.82 on the beds we calibrated on.
Flagged: score > 0.85 for at least 20 s. Cut those parts out (any audio editor) and check again.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import die, duration, loudness, need, ts  # noqa: E402

AUDIO = (".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".aiff", ".aif")
SR, LAG, AVG, TH, MIN_S = 8000, 20, 30, 0.85, 20


def files(args):
    out = []
    for a in args:
        p = Path(a).expanduser()
        if p.is_dir():
            out += sorted(q for q in p.iterdir() if q.suffix.lower() in AUDIO)
        elif p.exists():
            out.append(p)
        else:
            die(f"{p} not found")
    return out


def held(path):
    try:
        import numpy as np
    except ImportError:
        die("music.py check needs numpy: pip install numpy")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    n, win = len(x) // SR, np.hanning(SR)
    if n < LAG + AVG:
        return [], 0.0
    S = []
    for i in range(n):
        m = np.abs(np.fft.rfft(x[i * SR:(i + 1) * SR] * win))[40:2000]
        S.append(m / (np.linalg.norm(m) + 1e-9))
    S = np.array(S)
    s = np.zeros(n)
    s[LAG:] = (S[LAG:] * S[:-LAG]).sum(1)
    s = np.convolve(s, np.ones(AVG) / AVG, "same")
    out, i = [], 0
    while i < n:
        if s[i] > TH:
            j = i
            while j < n and s[j] > TH:
                j += 1
            if j - i >= MIN_S:
                out.append((max(0, i - LAG), j, float(s[i:j].max())))
            i = j
        else:
            i += 1
    return out, float(np.median(s[LAG:]))


NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def make(out, minutes=4.0, seed=1, key="C"):
    """Slow 3/4 music-box arpeggios over I–vi–IV–V with a soft pad. Deterministic for a given seed."""
    try:
        import numpy as np
    except ImportError:
        die("music.py make needs numpy: pip install numpy")
    import wave
    rng = np.random.default_rng(seed)
    sr, beat = 44100, 60 / 66                       # 66 bpm, three beats per chord bar, two bars per chord
    root = 60 + NOTE[key.upper()[0]]
    prog = [(0, 4, 7), (9, 12, 16), (5, 9, 12), (7, 11, 14)]       # I vi IV V (semitones above the tonic)
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    n = int(minutes * 60 * sr)
    y = np.zeros(n + sr * 6)
    t_note = np.arange(int(sr * 3.5)) / sr
    env = np.exp(-t_note * 1.6) * (1 - np.exp(-t_note * 400))

    def box(m, at, amp):
        f = hz(m)
        tone = np.sin(2 * np.pi * f * t_note) + 0.25 * np.sin(2 * np.pi * 2 * f * t_note) \
            + 0.08 * np.sin(2 * np.pi * 3.01 * f * t_note)
        i = int(at * sr)
        seg = (tone * env * amp)[:len(y) - i]
        y[i:i + len(seg)] += seg

    t, bar = 0.0, 0
    while t < minutes * 60:
        chord = prog[(bar // 2) % 4]
        # pad: the chord an octave down, slow swell over the two bars
        L = int(beat * 6 * sr)
        tp = np.arange(L) / sr
        swell = np.sin(np.pi * np.clip(tp / (beat * 6), 0, 1)) ** 2
        pad = sum(np.sin(2 * np.pi * hz(root - 12 + c) * tp) for c in chord) * swell * 0.035
        i = int(t * sr)
        y[i:i + L] += pad[:len(y) - i]
        for b in range(2):                          # two bars of arpeggio per chord
            pattern = [chord[0], chord[1], chord[2], chord[1] + 12 if rng.random() < .5 else chord[2] + 12,
                       chord[2], chord[1]]
            for k, m in enumerate(pattern):
                if rng.random() < 0.12:             # an occasional rest keeps it from ticking like a clock
                    continue
                box(root + 12 + m, t + (b * 3 + k * 0.5) * beat, 0.16 if k % 2 == 0 else 0.11)
        t += beat * 6
        bar += 2
    y = y[:n]
    fade = int(sr * 4)
    y[:fade] *= np.linspace(0, 1, fade)
    y[-fade:] *= np.linspace(1, 0, fade)
    # soft room: a few decaying echoes
    wet = np.zeros_like(y)
    for d, g in ((0.11, .35), (0.23, .25), (0.37, .18), (0.53, .12)):
        k = int(d * sr)
        wet[k:] += y[:-k] * g
    y = y + wet
    y = y / (np.abs(y).max() + 1e-9) * 0.5
    pcm = (y * 32767).astype("<i2")
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "make":
        a = sys.argv
        opt = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d
        out = Path(a[2])
        make(out, opt("--minutes", 4.0), opt("--seed", 1), opt("--key", "C"))
        i, _ = loudness(out)
        print(f"{out}: {ts(duration(out), srt=False)}, {i:.1f} LUFS — original generated music, free to use")
        return
    if len(sys.argv) < 3 or sys.argv[1] not in ("check", "info"):
        print(__doc__); sys.exit(2)
    need("ffmpeg")
    bad = 0
    for f in files(sys.argv[2:]):
        if sys.argv[1] == "info":
            i, tp = loudness(f)
            print(f"{f.name}: {ts(duration(f), srt=False)}, {i:.1f} LUFS, peak {tp:.1f} dBTP")
            continue
        runs, med = held(f)
        if runs:
            bad += 1
            print(f"✗ {f.name}: held chord " + ", ".join(f"{ts(a, srt=False)}–{ts(b, srt=False)} ({sc:.2f})"
                                                        for a, b, sc in runs))
        else:
            print(f"✓ {f.name}: no held chords (median {med:.2f})")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
