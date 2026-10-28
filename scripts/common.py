"""Shared helpers: episode paths, quote splitting, ffmpeg I/O. Standard library only."""
import json
import re
import shutil
import subprocess
import sys
from array import array
from pathlib import Path

SR = 44100
ROOT = Path(__file__).resolve().parent.parent

# Opening → closing quote marks that count as "someone is speaking".
# Top-level only: 『』 inside 「」 (a quote within a quote) stays with the outer speaker.
OPEN = {"「": "」", "“": "”"}
CLOSE = {v: k for k, v in OPEN.items()}


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def need(tool):
    if not shutil.which(tool):
        die(f"{tool} not found — install it first (macOS: brew install ffmpeg; Debian/Ubuntu: apt install ffmpeg)")


def load(path, default=None):
    p = Path(path)
    if not p.exists():
        if default is not None:
            return default
        die(f"missing {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def save(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(p)


class Episode:
    def __init__(self, path):
        self.dir = Path(path).expanduser().resolve()
        if not (self.dir / "episode.json").exists():
            die(f"{self.dir} has no episode.json — run fetch.py first or point at an episode folder")
        self.cfg = load(self.dir / "episode.json")

    def __getattr__(self, name):
        return self.dir / {"source": "source/source.json", "script": "script/script.json",
                           "speakers": "script/speakers.json", "cast": "cast.json",
                           "build": "build"}[name]

    @property
    def slug(self):
        return self.dir.name


def runs(text, open_quote_carry=False):
    """Split a paragraph into [("N", narration) | ("Q", quoted speech)] at top-level quotes.

    Handles 「」, “” and straight ASCII double quotes. The quote marks themselves are dropped from what is
    spoken. English (and translated) fiction often has one speaker run across several paragraphs: each paragraph
    opens a quote and only the last one closes it — an unclosed tail is still speech, not narration.
    `open_quote_carry=True` means the paragraph starts inside a quote left open by the previous one.
    """
    out, buf, depth, ascii_open = [], [], 1 if open_quote_carry else 0, False
    mode = "Q" if open_quote_carry else "N"

    def flush():
        s = "".join(buf).strip()
        if s:
            if out and out[-1][0] == mode:
                out[-1] = (mode, out[-1][1] + s)
            else:
                out.append((mode, s))
        buf.clear()

    for ch in text:
        if ch == '"':
            if not ascii_open and depth == 0:
                flush(); ascii_open = True; mode = "Q"; continue
            if ascii_open:
                flush(); ascii_open = False; mode = "N"; continue
        if ch in OPEN and not ascii_open:
            if depth == 0:
                flush(); mode = "Q"; depth = 1; continue
            depth += 1
        elif ch in CLOSE and not ascii_open and depth > 0:
            depth -= 1
            if depth == 0:
                flush(); mode = "N"; continue
        buf.append(ch)
    flush()
    return out


def leaves_quote_open(text, carried=False):
    """True if the paragraph ends inside a top-level quote (multi-paragraph speech convention)."""
    depth, ascii_open = 1 if carried else 0, False
    for ch in text:
        if ch == '"':
            ascii_open = not ascii_open if depth == 0 else ascii_open
        elif ch in OPEN and not ascii_open:
            depth += 1
        elif ch in CLOSE and not ascii_open and depth > 0:
            depth -= 1
    return depth > 0 or ascii_open


def paragraph_runs(rows):
    """{paragraph id: runs} for a whole script, carrying open quotes across paragraphs."""
    # Convention: every paragraph of a long speech re-opens the quote mark, so a paragraph that starts with
    # its own opening quote begins fresh; one that doesn't is still inside the previous speech.
    out, open_tail = {}, False
    for r in rows:
        carried = open_tail and not _reopens(r["text"])
        out[r["id"]] = runs(r["text"], carried)
        open_tail = leaves_quote_open(r["text"], carried)
    return out


def _reopens(text):
    s = text.lstrip()
    return bool(s) and (s[0] in OPEN or s[0] == '"')


def speakers_for(tag, n_quotes):
    """Normalise a speakers.json value to one speaker (or None = narrator) per quote."""
    if tag is None:
        return [None] * n_quotes
    if isinstance(tag, str):
        return [tag] * n_quotes
    return list(tag)


# ---------- audio ----------

def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        die(f"{cmd[0]} failed:\n{r.stderr[-2000:]}")
    return r


def decode(path, gain_db=0.0):
    """Any audio file → mono 44.1 kHz int16 samples (optionally with a gain, applied by ffmpeg)."""
    af = ["-af", f"volume={gain_db:.2f}dB"] if gain_db else []
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), *af, "-ac", "1", "-ar", str(SR),
                        "-f", "s16le", "-"], capture_output=True)
    if r.returncode:
        die(f"cannot decode {path}: {r.stderr.decode()[-500:]}")
    a = array("h")
    a.frombytes(r.stdout)
    if sys.byteorder == "big":
        a.byteswap()
    return a


def write_wav(path, samples):
    import wave
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    data = samples
    if sys.byteorder == "big":
        data = array("h", samples); data.byteswap()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())


def trim(samples, thresh=300, keep_ms=40):
    """Strip the silence TTS engines pad at both ends (often 0.3–0.5 s each side), so the gaps we insert are
    the gaps you hear — otherwise a quote and the 'he said' after it end up a full second apart."""
    n = len(samples)
    i = 0
    while i < n and abs(samples[i]) < thresh:
        i += 1
    j = n
    while j > i and abs(samples[j - 1]) < thresh:
        j -= 1
    pad = SR * keep_ms // 1000
    return samples[max(0, i - pad):min(n, j + pad)]


def silence(seconds):
    return array("h", bytes(2 * int(SR * seconds)))



def loudness(path):
    """Integrated loudness (LUFS) and true peak (dBTP) via ffmpeg ebur128."""
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = r.stderr[r.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", s)
    tp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", s)
    f = lambda m: float("-inf") if not m or m.group(1) == "-inf" else float(m.group(1))
    return f(i), f(tp)


def duration(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(r.stdout.strip())


def ts(sec, srt=True):
    h, rem = divmod(max(0.0, sec), 3600)
    m, s = divmod(rem, 60)
    if srt:
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}"
    return f"{int(h)}:{int(m):02d}:{int(s):02d}" if h else f"{int(m)}:{int(s):02d}"
