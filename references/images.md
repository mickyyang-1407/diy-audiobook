# Pictures · 插圖

Pictures are optional — audio-only is a complete audiobook. Add them when you publish to YouTube, or for
children, who love to look while they listen. One picture per scene (every 2–5 minutes) is plenty.

## Four ways to get pictures

| backend | effort | cost | set in `episode.json` → `"art"` |
|---|---|---|---|
| **manual** — any app you like | copy, paste, save | free–paid | `{"backend": "manual"}` |
| **openai** (cloud) | API key | per picture | `{"backend": "openai"}` |
| **minimax** (cloud) | API key | per picture | `{"backend": "minimax"}` |
| **comfyui** (local) | install once | free | `{"backend": "comfyui", "checkpoint": "…"}` |

The same OpenAI / MiniMax key works for voices **and** pictures — see [docs/API.md](../docs/API.md).
Run `python3 scripts/doctor.py` to see what your computer can use right now.

### Manual — easiest for beginners
1. Claude writes `art/prompts.json` (one prompt per picture).
2. Paste each prompt into ChatGPT, Gemini, Midjourney… — or draw it yourself.
3. Save the results as `art/01.png`, `art/02.png` … (`.jpg` / `.webp` also fine).
4. `python3 scripts/draw.py <ep>` checks they're all there.

### Cloud (OpenAI / MiniMax)
Set the key once (docs/API.md), set the backend, run `python3 scripts/draw.py <ep>`. Wide pictures by default
(`"size": "1344x768"`).

### Local (ComfyUI) — free, private
- Install ComfyUI (https://github.com/comfyanonymous/ComfyUI or the desktop app) and one image model.
  Apple-Silicon Macs and NVIDIA GPUs both work.
- Start ComfyUI, then `"art": {"backend": "comfyui", "checkpoint": "<model file name>"}`.
  `doctor.py` lists the models it can see. Default workflow: `workflows/comfyui-sdxl.json` (any SDXL/SD1.5 model).
  Also included: `workflows/comfyui-qwen-image-2.1.json` — best results for picture books (the example's pictures).
- **Any other workflow** (Flux, Qwen-Image, your favourite LoRA setup): in ComfyUI, *Export (API)*, replace
  the prompt text with `{{PROMPT}}` (and optionally `{{NEGATIVE}}` `{{SEED}}` `{{WIDTH}}` `{{HEIGHT}}`
  `{{CHECKPOINT}}`), save it, and set `"workflow": "path/to/it.json"`.
- Models that understand plain English sentences (Flux, Qwen-Image) follow scene descriptions far better
  than anime-tag models — we tried: an anime SDXL model drew "storybook art" as a literal open book.
- `COMFYUI_URL` if ComfyUI runs elsewhere than `http://127.0.0.1:8188`.

### Public-domain illustrations
Classic books often have original illustrations that are now public domain (e.g. Sidney Paget's Sherlock
Holmes drawings on Wikimedia Commons). Check the artist's death date, save them as `art/NN.png`, use manual.

## `art/prompts.json` — how Claude writes it

```json
{"style": "A full-page children's picture book illustration (the whole frame is the scene, no book or page visible): soft watercolor …",
 "negative": "text, letters, watermark, scary, blood …",
 "images": [{"id": "01", "at": "P001", "prompt": "a big friendly lion with a fluffy golden mane … sleeping under a big shady tree"}]}
```
- **One style line for the whole book/series**, prepended to every prompt. A series that changes style
  every episode looks like a different channel.
- **Describe recurring characters identically in every prompt** ("a big friendly lion with a fluffy golden mane
  and kind amber eyes") — models have no memory between pictures.
- `at` = the paragraph where the picture appears. One per scene; never more often than every ~30 s.
- **No text in pictures** (models misspell). Titles go on the cover via `cover.py`.
- **Don't draw the twist** of a mystery. For children: nothing scary, no weapons, no blood.
- Picture-book style words can backfire: say "the whole frame is the scene, no book visible".
- Some models ignore the negative prompt (Qwen-Image at cfg 1 does). Put the exclusions *in* the prompt:
  "the lion alone, no other animals" — our first lion picture got two uninvited friends.
- Look at every picture before rendering the video. Redraw one: `draw.py <ep> --redo 03`.

## Video and cover
```bash
python3 scripts/video.py <ep>                 # pictures timed to the story, soft crossfades → build/<slug>.mp4
python3 scripts/cover.py <ep> --line2 "再小也能幫大忙"   # 1280×720 thumbnail → build/cover.jpg
```
Cover text: the title plus one hook of ≤ ~7 characters / 4 words. Curiosity, not fear.
YouTube asks creators to disclose realistic AI-generated content; `package.py` writes the picture credit into
the description.
