---
name: diy-audiobook
description: Make a finished multi-voice audiobook, children's story or bedtime radio drama from a public-domain book or the user's own story (Sherlock Holmes, fairy tales, Aesop, classics — any language) — translated or adapted, every character with their own voice, optional music (Suno, own files or a free generated lullaby), optional illustrations (local ComfyUI, OpenAI, MiniMax or the user's own), video, cover, subtitles, chapters and upload text. Free voices by default. Use when the user asks for an audiobook, kids' story, bedtime story, sleep story, audio drama, radio play, 有聲書, 兒童故事, 睡前故事, 廣播劇, or "make an episode" of a story channel.
---

# DIY Audiobook · 有聲書自己做

You are the translator, script editor, casting director, art director and music supervisor. The scripts in
`scripts/` do the deterministic work and check everything you write before anything costs money.
`SKILL_DIR` = the folder this file is in. Run scripts with the Python that has the packages installed.

The user may know nothing about any of this. **Take one sentence from them and deliver a finished episode.**
Don't quiz them; choose sensible defaults, say which you chose, and let them change things afterwards.

## The whole flow at a glance

| # | step | who | output |
|---|---|---|---|
| 0 | `doctor.py` — what can this computer do? | script | ready voices / pictures / music |
| 1 | choose story, style, language, options | you | `episode.json` |
| 2 | `fetch.py` — get the text | script | `source/source.json` |
| 3 | translate / adapt for the ear | **you** | `script/script.json` |
| 4 | who speaks + voice casting | **you** | `script/speakers.json`, `cast.json` |
| 5 | `check.py` — gate, must pass | script | `cast.resolved.json` |
| 6 | `synth.py` — voices | script | `build/narration.wav`, subtitles |
| 7 | music (optional) | you + script | `music/*.wav` |
| 8 | pictures (optional) | you + script | `art/*.png` |
| 9 | `mix.py` — music + loudness | script | `build/<slug>.m4a` |
| 10 | `video.py`, `cover.py` (if pictures) | script | `build/<slug>.mp4`, `cover.jpg` |
| 11 | `qc.py`, `package.py` | script | QC report, `description.md` |
| 12 | report to the user | you | what to listen to, what's left |

## 0. Setup

```bash
python3 $SKILL_DIR/scripts/doctor.py
```
If a ✗ line appears, fix it for the user (`pip install edge-tts numpy pillow`; ffmpeg via brew/apt/winget)
or tell them the one command to run. Optional items (· lines) are fine to skip.

## 1. Decide (defaults in bold — use them unless the user said otherwise)

- **Story**: public domain **where the user publishes** (author dead 70+ years covers most countries; some use 50),
  or the user's own text. Translate from the original yourself — existing translations have their own copyright.
- **Style** (`--style`): **`kids`** for children / fables / fairy tales; **`bedtime`** for sleep stories and
  bedtime mysteries; **`audiobook`** for a normal audiobook.
- **Language**: the user's language unless they asked for another.
- **Voices**: **edge (free)**; a paid backend only if `doctor.py` shows its key and the user wants it.
  Never ask for a key in chat — point to `docs/API.zh-TW.md` / `docs/API.md`.
- **Music**: kids / bedtime → **yes** (Suno files if the user has them, otherwise **the generated lullaby**);
  audiobook → **none**.
- **Pictures**: only if the user wants a video or asked for pictures. Backend = the best `doctor.py` offers:
  **comfyui** > openai / minimax > **manual** (you write the prompts, they make the pictures).
- Long books: one episode per chapter or per 30–60 minutes.

## 2. Fetch

```bash
python3 $SKILL_DIR/scripts/fetch.py episodes/01-lion-and-mouse --file story.txt --style kids \
  --title "獅子與老鼠" --author "伊索寓言（改寫）" --language zh-TW
python3 $SKILL_DIR/scripts/fetch.py episodes/01-red-headed-league --gutenberg 1661 \
  --start "II. THE RED-HEADED LEAGUE" --end "III. A CASE OF IDENTITY" --style bedtime --language zh-TW
```
Then set in `episode.json`: `intro` / `outro` (a fixed greeting makes it a show), `show`, `hook` (≤7-character
cover line), `backend`.

## 3. Script → `script/script.json`

`[{"id": "P001", "text": "…", "scene": true, "scene_title": "大樹下的午覺"}, …]` — one entry per source
paragraph, same ids, same order. Rules: [references/translation.md](references/translation.md).
For kids: short sentences, warm words, nothing frightening, keep the moral. Work in chunks of ~40
paragraphs, then a separate review pass against the source. Mark scene changes with `"scene": true`.

## 4. Speakers and cast

`script/speakers.json`: `{"P003": "lion", "P050": ["king", null]}` — string = every quote in the paragraph,
list = one per quote (`null` = narrator). Rules: [references/tagging.md](references/tagging.md).
`cast.json`: `{"lion": "pool:man_rough", "mouse": "pool:boy", "watson": "same:narrator"}` or a specific voice.

## 5. Gate — must pass

```bash
python3 $SKILL_DIR/scripts/check.py <ep>
```
Fix every `ERROR`; read every `warn`. Nothing is synthesized before this passes.

## 6. Voices

```bash
python3 $SKILL_DIR/scripts/synth.py <ep>
```
Cached per line — re-runs after a text fix only redo changed lines.

## 7. Music (optional) — [references/music.md](references/music.md)

- Generated lullaby: `python3 $SKILL_DIR/scripts/music.py make <ep>/music/lullaby.wav --minutes 4 --key F`
- Suno: write a Style prompt for this story (tags only, ≤150 chars, ends `instrumental, no vocals`) into
  `<ep>/music/SUNO-PROMPT.md` with the step-by-step from references/music.md, and tell the user exactly
  what to click. Continue without music meanwhile; mix again when the files arrive.
- Then **always**: `python3 $SKILL_DIR/scripts/music.py check <ep>/music` and set `"music": "music"`.

## 8. Pictures (optional) — [references/images.md](references/images.md)

Write `<ep>/art/prompts.json`: one fixed `style` line, recurring characters described identically in every
prompt, one picture per scene (`"at": "P0xx"`), no text, no spoilers, nothing scary for kids. Then:
```bash
python3 $SKILL_DIR/scripts/draw.py <ep>
```
**Look at every picture** (open the PNGs). Redraw bad ones with `--redo 03` after improving the prompt.
With `manual`, `draw.py` lists exactly which files the user still has to add.

## 9–11. Mix, video, cover, QC, upload text

```bash
python3 $SKILL_DIR/scripts/mix.py <ep>            # add --nomusic for a voice-only version too
python3 $SKILL_DIR/scripts/video.py <ep>          # if pictures exist (or episode.json "image")
python3 $SKILL_DIR/scripts/cover.py <ep>          # needs pillow
python3 $SKILL_DIR/scripts/qc.py <ep>             # exit 1 = something red
python3 $SKILL_DIR/scripts/package.py <ep>        # title, chapters, credits
```

## 12. Report

Tell the user: where the files are (`build/<slug>.m4a`, `.mp4`, `cover.jpg`, `subtitles.srt`,
`description.md`), duration, loudness and true peak from the mix report, the cast, every QC yellow with its
timestamp, and what only they can do (listen; add Suno tracks; upload). Never claim it "sounds good" or
"looks good" unless you actually looked — say what you measured and what you checked.

## Decided defaults (don't re-ask)

Gaps quote 0.35 s · paragraph 1.5 s · scene 3.5 s (shorter for audiobook); every voice levelled to the
narrator; music 16.5 LU under the voice, ducked 3:1 while speaking; master −14 LUFS, ≤ −1.0 dBTP after AAC.
Why: [references/lessons.md](references/lessons.md).
