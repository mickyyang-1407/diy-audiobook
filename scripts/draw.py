#!/usr/bin/env python3
"""Draw the illustrations listed in art/prompts.json.

Usage: draw.py <episode_dir> [--redo 01 03] [--backend comfyui|openai|minimax|manual]

art/prompts.json (written by Claude, see references/images.md):
  {"style": "soft watercolour children's picture book, warm light, …",
   "negative": "text, letters, watermark, …",           # optional, used by local models
   "images": [{"id": "01", "at": "P001", "prompt": "…"}, …]}
  `at` = the paragraph where the picture appears in the video (default: one picture per scene).

Backends (episode.json → "art": {"backend": …}):
  comfyui  local, free. Needs ComfyUI running (COMFYUI_URL, default http://127.0.0.1:8188) and a checkpoint:
           art.checkpoint or COMFYUI_CHECKPOINT. Any workflow works: art.workflow = an API-format graph with
           {{PROMPT}} {{NEGATIVE}} {{SEED}} {{WIDTH}} {{HEIGHT}} {{CHECKPOINT}} placeholders.
  openai   cloud, OPENAI_API_KEY (same key as the voices). Model art.model, default gpt-image-1.
  minimax  cloud, MINIMAX_API_KEY (same key as the voices). Model image-01.
  manual   you supply the pictures: put art/01.png, art/02.jpg … in place (any tool — ChatGPT, Gemini,
           Midjourney, your own drawings, public-domain illustrations). draw.py only checks they are there.
Writes art/<id>.png and art/CREDITS.md. Existing pictures are kept unless --redo lists them.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, Episode, die, load, save  # noqa: E402

DEFAULT_NEG = ("text, letters, words, caption, watermark, signature, logo, blood, gore, weapon, nudity, "
               "deformed hands, extra fingers, blurry")


class ArtError(Exception):
    pass


def _req(url, body=None, headers=None, timeout=300, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read()
    except urllib.error.HTTPError as e:
        raise ArtError(f"HTTP {e.code} from {url.split('?')[0]}: {e.read()[:400].decode(errors='replace')}") from None
    except urllib.error.URLError as e:
        raise ArtError(f"cannot reach {url.split('?')[0]} ({e.reason})") from None
    return b if raw else json.loads(b)


def _key(name):
    k = os.environ.get(name)
    if not k:
        raise ArtError(f"{name} is not set — see docs/API.md")
    return k


def size_of(art):
    w, h = (int(x) for x in str(art.get("size", "1344x768")).lower().split("x"))
    return w, h


# ---------------- comfyui ----------------

def comfyui(prompt, neg, seed, art, out):
    base = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    ckpt = art.get("checkpoint") or os.environ.get("COMFYUI_CHECKPOINT", "")
    wf_path = Path(art.get("workflow") or ROOT / "workflows/comfyui-sdxl.json")
    if not wf_path.is_absolute():
        wf_path = ROOT / wf_path if (ROOT / wf_path).exists() else wf_path
    text = wf_path.read_text(encoding="utf-8")
    if "{{CHECKPOINT}}" in text and not ckpt:
        try:
            names = _req(f"{base}/object_info/CheckpointLoaderSimple", timeout=20)[
                "CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        except (ArtError, KeyError):
            names = []
        raise ArtError("no checkpoint chosen — set \"checkpoint\" in episode.json art (or COMFYUI_CHECKPOINT). "
                       + (f"Installed: {', '.join(names[:12])}" if names else "Is ComfyUI running?"))
    w, h = size_of(art)
    graph = json.loads(text)
    graph.pop("_doc", None)

    def fill(v):
        if isinstance(v, dict):
            return {k: fill(x) for k, x in v.items()}
        if isinstance(v, list):
            return [fill(x) for x in v]
        if isinstance(v, str):
            num = {"{{SEED}}": seed, "{{WIDTH}}": w, "{{HEIGHT}}": h}
            if v in num:
                return num[v]
            return (v.replace("{{PROMPT}}", prompt).replace("{{NEGATIVE}}", neg)
                    .replace("{{CHECKPOINT}}", ckpt))
        return v

    graph = fill(graph)
    pid = _req(f"{base}/prompt", {"prompt": graph, "client_id": "diy-audiobook"}, timeout=60)["prompt_id"]
    deadline = time.time() + int(art.get("timeout_s", 1800))
    while time.time() < deadline:
        time.sleep(3)
        h_ = _req(f"{base}/history/{pid}", timeout=30).get(pid)
        if not h_:
            continue
        st = h_.get("status", {})
        if st.get("status_str") == "error":
            raise ArtError(f"ComfyUI error: {json.dumps(st.get('messages', ''))[-500:]}")
        for node in h_.get("outputs", {}).values():
            for img in node.get("images", []):
                q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""),
                                            "type": img.get("type", "output")})
                out.write_bytes(_req(f"{base}/view?{q}", raw=True, timeout=120))
                return
    raise ArtError(f"ComfyUI took longer than {art.get('timeout_s', 1800)} s (prompt {pid})")


# ---------------- openai ----------------

def openai(prompt, neg, seed, art, out):
    w, h = size_of(art)
    size = "1536x1024" if w > h else "1024x1536" if h > w else "1024x1024"
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    body = {"model": art.get("model", "gpt-image-1"), "prompt": f"{prompt}\nAvoid: {neg}.", "size": size, "n": 1}
    if art.get("quality"):
        body["quality"] = art["quality"]
    r = _req(f"{base}/images/generations", body, {"Authorization": f"Bearer {_key('OPENAI_API_KEY')}"})
    d = (r.get("data") or [{}])[0]
    if d.get("b64_json"):
        out.write_bytes(base64.b64decode(d["b64_json"]))
    elif d.get("url"):
        out.write_bytes(_req(d["url"], raw=True))
    else:
        raise ArtError(f"OpenAI returned no image: {str(r)[:300]}")


# ---------------- minimax ----------------

def minimax(prompt, neg, seed, art, out):
    w, h = size_of(art)
    host = os.environ.get("MINIMAX_API_HOST", "https://api.minimax.io").rstrip("/")
    ratio = "16:9" if w > h * 1.5 else "4:3" if w > h else "9:16" if h > w * 1.5 else "3:4" if h > w else "1:1"
    body = {"model": art.get("model", "image-01"), "prompt": f"{prompt} Avoid: {neg}.", "aspect_ratio": ratio,
            "response_format": "base64", "n": 1}
    r = _req(f"{host}/v1/image_generation", body, {"Authorization": f"Bearer {_key('MINIMAX_API_KEY')}"})
    code = (r.get("base_resp") or {}).get("status_code")
    imgs = (r.get("data") or {}).get("image_base64") or []
    if code not in (0, None) or not imgs:
        raise ArtError(f"MiniMax image: {r.get('base_resp') or str(r)[:300]}")
    out.write_bytes(base64.b64decode(imgs[0]))


BACKENDS = {"comfyui": comfyui, "openai": openai, "minimax": minimax}
CREDIT = {"comfyui": "generated locally with ComfyUI", "openai": "generated with OpenAI image models",
          "minimax": "generated with MiniMax image-01", "manual": "supplied by the producer"}


def main():
    ep = Episode(sys.argv[1])
    art = ep.cfg.get("art") or {}
    backend = sys.argv[sys.argv.index("--backend") + 1] if "--backend" in sys.argv else art.get("backend", "manual")
    redo = set()
    if "--redo" in sys.argv:
        redo = {a for a in sys.argv[sys.argv.index("--redo") + 1:] if not a.startswith("--")}
    spec = load(ep.dir / "art/prompts.json")
    style, neg = spec.get("style", ""), spec.get("negative", DEFAULT_NEG)
    rows = {r["id"] for r in load(ep.script)}
    adir = ep.dir / "art"
    missing, made = [], 0
    for k, img in enumerate(spec["images"], 1):
        if img.get("at") and img["at"] not in rows:
            die(f"art/prompts.json image {img['id']}: paragraph {img['at']} does not exist")
        have = [p for p in adir.glob(f"{img['id']}.*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
        if have and img["id"] not in redo:
            continue
        if backend == "manual":
            missing.append(img["id"]); continue
        if backend not in BACKENDS:
            die(f"unknown art backend {backend!r}; choose comfyui, openai, minimax or manual")
        out = adir / f"{img['id']}.png"
        seed = int(art.get("seed", 1000)) + k + (500 if img["id"] in redo else 0)
        t0 = time.time()
        try:
            BACKENDS[backend](f"{style} {img['prompt']}".strip(), neg, seed, art, out)
        except ArtError as e:
            die(f"{img['id']}: {e}\n(pictures already drawn are kept — fix and run draw.py again)")
        made += 1
        print(f"  {img['id']} drawn in {time.time() - t0:.0f}s: {img['prompt'][:70]}", flush=True)
    if missing:
        die("put these pictures in art/ (any of .png .jpg .webp): " + ", ".join(f"{m}.png" for m in missing)
            + "\n  prompts to paste into ChatGPT / Gemini / Midjourney are in art/prompts.json")
    (adir / "CREDITS.md").write_text(f"# Illustrations\n\n{len(spec['images'])} pictures, {CREDIT.get(backend, backend)}."
                                     f"\nPrompts: art/prompts.json\n", encoding="utf-8")
    meta = load(ep.dir / "episode.json")
    meta.setdefault("art", {})["credit"] = CREDIT.get(backend, backend)
    save(ep.dir / "episode.json", meta)
    print(f"{len(spec['images'])} pictures ready ({made} new) in art/")


if __name__ == "__main__":
    main()
