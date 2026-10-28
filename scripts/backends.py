"""Text-to-speech backends. Each one turns (text, voice settings) into an audio file.

  edge     — Microsoft Edge online voices via the `edge-tts` package. Free, no key. Default.
  minimax  — MiniMax T2A (best Mandarin drama voices). Needs MINIMAX_API_KEY.
             MINIMAX_API_HOST defaults to https://api.minimax.io (mainland accounts: https://api.minimaxi.com).
  openai   — OpenAI gpt-4o-mini-tts. Needs OPENAI_API_KEY (OPENAI_BASE_URL for a compatible endpoint).

A voice setting is what cast.json gives a role: {"voice": "…", plus backend options}.
  edge:    rate ("-10%"), pitch ("+0Hz"), volume ("+0%")
  minimax: speed (0.85), emotion ("calm" | null), pitch (0), model ("speech-2.8-hd")
  openai:  instructions ("Speak slowly and softly…"), model ("gpt-4o-mini-tts"), speed
"""
import asyncio
import json
import os
import time
import urllib.error
import urllib.request


class TTSError(Exception):
    pass


def _post(url, body, headers, timeout=240):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raise TTSError(f"HTTP {e.code}: {e.read()[:500].decode(errors='replace')}") from None


def _key(name):
    k = os.environ.get(name)
    if not k:
        raise TTSError(f"{name} is not set — export it in your shell (never write keys into the episode files)")
    return k


# ---------------- edge ----------------

def edge(text, v, out):
    try:
        import edge_tts
    except ImportError:
        raise TTSError("edge backend needs the edge-tts package: pip install edge-tts") from None

    async def go():
        c = edge_tts.Communicate(text, v["voice"], rate=v.get("rate", "+0%"), pitch=v.get("pitch", "+0Hz"),
                                 volume=v.get("volume", "+0%"))
        await c.save(str(out))

    for attempt in range(5):
        try:
            asyncio.run(go())
            if out.exists() and out.stat().st_size > 0:
                return out
        except Exception as e:  # network hiccups and 'No audio was received' are transient
            err = e
        time.sleep(2 * (attempt + 1))
    raise TTSError(f"edge-tts failed for voice {v['voice']}: {err}")


# ---------------- minimax ----------------

def minimax(text, v, out):
    host = os.environ.get("MINIMAX_API_HOST", "https://api.minimax.io").rstrip("/")
    body = {"model": v.get("model", os.environ.get("MINIMAX_TTS_MODEL", "speech-2.8-hd")), "text": text,
            "stream": False, "output_format": "hex", "language_boost": v.get("language_boost", "auto"),
            "voice_setting": {"voice_id": v["voice"], "speed": v.get("speed", 0.85), "vol": 1,
                              "pitch": v.get("pitch", 0)},
            "audio_setting": {"sample_rate": 44100, "format": "wav", "channel": 1}}
    if v.get("emotion"):
        body["voice_setting"]["emotion"] = v["emotion"]
    for attempt in range(8):
        raw, _ = _post(f"{host}/v1/t2a_v2", body, {"Authorization": f"Bearer {_key('MINIMAX_API_KEY')}"})
        r = json.loads(raw)
        code = (r.get("base_resp") or {}).get("status_code")
        # per-minute limits come back as HTTP 200 with these codes: 1002 = requests/min, 1039 = tokens/min
        if code in (1002, 1039):
            time.sleep(min(60, 5 * 2 ** attempt)); continue
        if code != 0 or not (r.get("data") or {}).get("audio"):
            raise TTSError(f"MiniMax: {r.get('base_resp')}")
        out.write_bytes(bytes.fromhex(r["data"]["audio"]))
        return out
    raise TTSError("MiniMax: still rate-limited after 8 retries")


# ---------------- openai ----------------

def openai(text, v, out):
    body = {"model": v.get("model", "gpt-4o-mini-tts"), "voice": v["voice"], "input": text,
            "response_format": "wav"}
    if v.get("instructions"):
        body["instructions"] = v["instructions"]
    if v.get("speed"):
        body["speed"] = v["speed"]
    for attempt in range(6):
        try:
            base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            raw, _ = _post(f"{base}/audio/speech", body,
                           {"Authorization": f"Bearer {_key('OPENAI_API_KEY')}"})
            out.write_bytes(raw)
            return out
        except TTSError as e:
            if "HTTP 429" not in str(e) and "HTTP 5" not in str(e):
                raise
            time.sleep(min(60, 5 * 2 ** attempt))
    raise TTSError("OpenAI: still failing after 6 retries")


BACKENDS = {"edge": (edge, ".mp3"), "minimax": (minimax, ".wav"), "openai": (openai, ".wav")}


def get(name):
    if name not in BACKENDS:
        raise TTSError(f"unknown backend {name!r}; choose one of {', '.join(BACKENDS)}")
    return BACKENDS[name]
