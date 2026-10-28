---
name: diy-audiobook
description: Make a finished multi-voice audiobook or bedtime radio drama from a public-domain book (Sherlock Holmes, fairy tales, classics — any language) — translated or adapted, every character with their own voice, optional music bed, mastered loudness, subtitles, chapters and upload text. Free voices by default; MiniMax or OpenAI voices with an API key. Use when the user asks for an audiobook, bedtime story, sleep story, audio drama, radio play, 有聲書, 睡前故事, 廣播劇, or "make an episode" of a story channel.
---

# DIY Audiobook · 有聲書自己做

You (the agent) are the translator, script editor and casting director; the scripts in `scripts/` do the
deterministic work (download, validation, TTS, mixing, loudness, QC). This split came out of producing nearly 200
episodes: models are good at language and judgment, bad at counting quotes and measuring LUFS — so the
scripts check everything you write before any paid TTS call is made.

`SKILL_DIR` below = the folder this file is in. Run scripts with the Python that has `edge-tts` installed.

## 0. Setup (once)

```bash
ffmpeg -version >/dev/null && python3 -c "import edge_tts" || pip install edge-tts   # ffmpeg: brew/apt install ffmpeg
```
Backends: `edge` (free, default), `minimax` (`MINIMAX_API_KEY`, best Mandarin acting), `openai`
(`OPENAI_API_KEY`). Keys only ever come from the environment — never write them into episode files, and never
ask the user to paste a key into the chat. If they want a paid backend and the key is missing, point them to
`docs/API.zh-TW.md` / `docs/API.md` and have them run `scripts/try_voice.py` themselves.

## 1. Pick a story — copyright first

- Must be public domain **where the user publishes**. Author died > 70 years ago covers most countries; some
  (Taiwan, Japan before 2018…) use 50. Check the specific author/year and tell the user what you checked.
- **Translate from the original yourself.** Existing translations have their own copyright even when the
  original is free.
- Pick something with dialogue — two to five speaking characters is the sweet spot.

## 2. Fetch

```bash
python3 $SKILL_DIR/scripts/fetch.py episodes/01-red-headed-league --gutenberg 1661 \
  --start "II. THE RED-HEADED LEAGUE" --end "III. A CASE OF IDENTITY" \
  --title "紅髮會" --author "柯南·道爾" --language zh-TW
```
Also `--url` or `--file`. `--style audiobook` = natural pace and shorter pauses; the default `bedtime` is slow
and soft — pick from what the user asked for ("audiobook" vs "bedtime story / sleep / radio drama").
Then fill `episode.json`: `intro` / `outro` (a fixed greeting makes it a show —
e.g. 「晚安，歡迎來到枕邊偵探社……」), `show`, `backend`, optional `music` and `image` paths.

## 3. Translate / adapt → `script/script.json`

`[{"id": "P001", "text": "…", "scene": true, "scene_title": "不速之客"}, …]` — **one entry per source
paragraph, same ids, same order.** Rules: [references/translation.md](references/translation.md). Work in
chunks of ~40 paragraphs, then do a separate review pass against the source (most errors are caught there:
dropped sentences, flipped negations, inconsistent names). Mark scene changes with `"scene": true`.

## 4. Tag speakers → `script/speakers.json`, cast → `cast.json`

```json
{"P002": "holmes", "P008": ["holmes", "holmes"], "P050": ["king", null]}
```
String = every top-level quote in that paragraph is this character; list = one per quote, `null` = narrator
reads that one; untagged paragraphs = narrator. Full rules: [references/tagging.md](references/tagging.md).

```json
{"narrator": {"voice": "zh-CN-YunyangNeural", "rate": "-12%"}, "watson": "same:narrator",
 "holmes": {"voice": "zh-CN-YunxiNeural", "pitch": "-4Hz"}, "wilson": "pool:man_old"}
```
`pool:<kind>` picks a free voice from `voices/<backend>.json` (`man_mid man_young man_old man_rough
woman_young woman_mid woman_old boy girl`). Lead characters deserve a hand-picked voice; one-scene roles use pools.

## 5. Gate — must pass before any TTS call

```bash
python3 $SKILL_DIR/scripts/check.py <episode>
```
Fix every `ERROR`. Read every `warn` (a length-ratio warning almost always means a skipped sentence).

## 6. Produce

```bash
python3 $SKILL_DIR/scripts/synth.py <episode>             # cached per clip — re-runs only pay for changed text
python3 $SKILL_DIR/scripts/mix.py <episode>               # with music (if set); add --nomusic for a voice-only version
python3 $SKILL_DIR/scripts/qc.py <episode>                # exit 1 = something red
python3 $SKILL_DIR/scripts/package.py <episode>           # build/description.md with chapters + credits
```
Outputs in `<episode>/build/`: `<slug>.m4a`, `<slug>.mp4` (if `image`), `subtitles.srt`, `description.md`.
For a fix after listening: edit the text in `script.json`, re-run synth → mix (only changed clips are re-made).

## 7. Hand-off to the human

Report: duration, loudness/true peak from the mix report, cast table, every QC yellow with its timestamp.
Ask them to listen to: the first minute, one scene change, and each yellow clip. Uploading is theirs.
Never claim it "sounds good" — you cannot hear it; say what was measured.

## Defaults that are already decided (don't re-ask)

Bedtime pacing (`rate -10%…-12%` / MiniMax `speed 0.85`), gaps quote 0.35 s · paragraph 1.5 s · scene 3.5 s,
every voice levelled to the narrator, music 16.5 LU under the voice with 3:1 ducking while speaking,
master −14 LUFS / ≤ −1.0 dBTP after AAC. Why each number is what it is: [references/lessons.md](references/lessons.md).
