# 🌙 Pillow Detective

**Turn any public-domain story into a multi-voice bedtime radio drama — with one sentence to Claude Code.**

> "Make tonight's episode: *The Red-Headed League*, in Traditional Chinese."

…and you get a finished episode: translated, every character in their own voice, a soft music bed that ducks
under the dialogue, mastered to streaming loudness, with subtitles, chapters and upload text.

[English](README.md) · [繁體中文](README.zh-TW.md)

🎧 **Listen:** [90-second demo](examples/red-headed-league/demo-first-90s.m4a) — made entirely by this repo
with free voices, no API key.

This is the production line behind **[枕邊偵探社 (Pillow Detective Agency)](https://youtube.com/@PillowMysteries)**,
a YouTube channel of Sherlock Holmes and other classic mysteries as bedtime radio dramas — nearly 200 episodes produced.
Every default here (pacing, gaps, loudness, how loud the music sits) was tuned by ear over those episodes.

---

## How it works

```
 public-domain text ──▶ fetch.py ──▶ Claude translates & adapts ──▶ Claude tags who speaks
                                           (paragraph-aligned)        + casts the voices
                                                                             │
   upload text ◀── package.py ◀── qc.py ◀── mix.py ◀── synth.py ◀── check.py ◀┘
   chapters, credits       loudness,   music bed,   one voice     blocks every mistake
                           glitches    −14 LUFS     per character before a paid TTS call
```

**Claude does what language models are good at** — translation, adaptation for the ear, deciding who is
speaking, casting. **Scripts do what models are bad at** — counting quotes, aligning paragraphs, measuring
loudness, trimming silence, ducking music. Nothing reaches the TTS engine until `check.py` passes.

## Quick start

**Requirements:** [Claude Code](https://claude.com/claude-code), Python 3.9+, ffmpeg.

```bash
git clone https://github.com/mickyyang-1407/pillow-detective ~/.claude/skills/pillow-detective
pip install edge-tts            # free voices, no key
brew install ffmpeg             # or: apt install ffmpeg
```

Then in Claude Code:

> Make a bedtime radio drama of "The Speckled Band" in English.

> 用枕邊偵探社的流程，把〈藍寶石〉做成一集繁體中文睡前廣播劇。

> Turn Andersen's "The Little Match Girl" into a 10-minute bedtime story for kids, Japanese.

### Without Claude Code

Every step is a plain script; the files Claude writes are simple JSON you can write yourself.

```bash
python3 scripts/check.py examples/red-headed-league
python3 scripts/synth.py examples/red-headed-league
python3 scripts/mix.py   examples/red-headed-league --nomusic
python3 scripts/qc.py    examples/red-headed-league
```

## What you get

| file | |
|---|---|
| `build/<slug>.m4a` | the episode, −14 LUFS, ≤ −1 dBTP (YouTube / Spotify / Apple ready) |
| `build/<slug>.mp4` | still-image video, if you set a cover image |
| `build/subtitles.srt` | sentence-level captions, timed from the actual audio |
| `build/description.md` | title, chapters from the scene breaks, credits |
| `build/timeline.json` | every line: who, when, what |

## Voices

| backend | cost | best for | setup |
|---|---|---|---|
| `edge` (default) | free | trying it out, English, many languages | `pip install edge-tts` |
| `minimax` | paid | the most natural Mandarin acting | `export MINIMAX_API_KEY=…` |
| `openai` | paid | any language; acting via text instructions | `export OPENAI_API_KEY=…` |

Characters get voices from **pools** (`man_old`, `woman_young`, `boy`…) or you hand-pick them.
Every voice is automatically levelled to the narrator, so nobody reaches for the volume knob at 1 a.m.

## Why the defaults sound the way they do

A few things learned the hard way — full list in [references/lessons.md](references/lessons.md):

- **TTS pads ~0.4 s of silence on both ends of every clip.** Untrimmed, a line of dialogue and the
  "he said" after it sit a full second apart. Clips are trimmed, then exact gaps inserted (0.35 s / 1.5 s / 3.5 s).
- **Different TTS voices differ by up to 9 dB.** Each voice is measured over all its lines and matched to the narrator.
- **Never run dynamic loudness normalisation on a mix with music** — it pumps the music up in every pause.
  The voice is mastered first; music goes in afterwards, 16.5 LU under, ducked 3:1 while someone speaks.
- **AAC encoding overshoots true peak by up to 1 dB**, so peaks are verified on the encoded file, not the WAV.
- **Model self-checks miss whole untranslated paragraphs.** Deterministic checks don't.

## Copyright

Use texts that are public domain **where you publish** (author dead 70+ years covers most countries; some use 50),
and translate from the original — existing translations have their own copyright. The example uses
Arthur Conan Doyle's *The Red-Headed League* (1891) from [Project Gutenberg](https://www.gutenberg.org/ebooks/1661).
Music you add must be yours or licensed for it.

## Repo layout

```
SKILL.md              the instructions Claude Code follows
scripts/              fetch · check · synth · mix · qc · package (stdlib + ffmpeg; edge-tts for free voices)
voices/               voice pools per backend and language
references/           translation guide · speaker tagging rules · lessons from nearly 200 episodes
examples/             a complete episode folder you can run as-is
```

## Contributing

Voice pools for more languages, more TTS backends, and better QC checks are all welcome. Please keep the
principle: **validate before you spend**, and **measure, don't guess**.

MIT © Micky Yang
