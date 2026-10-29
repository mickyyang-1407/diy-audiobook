# 🎧 DIY Audiobook · 有聲書自己做

**Make your own audiobook, children's story or bedtime radio drama — every character with their own voice,
with music and pictures — by saying one sentence to Claude Code.**

> "Make a children's story of *The Lion and the Mouse* in Traditional Chinese, with pictures and gentle music."

<p align="center"><img src="examples/lion-and-mouse/cover-small.jpg" width="520" alt="The Lion and the Mouse — cover made by this repo"></p>

<p align="center"><b><a href="https://mickyyang-1407.github.io/diy-audiobook/">🌐 Website & demos</a></b></p>

…and you get a finished episode: the story adapted for listening, a different voice for every character,
soft music that ducks under the dialogue, illustrations timed to the story, a video, a cover, subtitles,
chapters and upload text. **Free voices and free music out of the box** — no account, no API key.
Plug in MiniMax, OpenAI, Suno or your own ComfyUI when you want more.

[English](README.md) · [繁體中文](README.zh-TW.md)

🎬 **Watch / listen** — every file made by this repo:
[Kids · 〈獅子與老鼠〉 video](docs/assets/lion-and-mouse.mp4) ·
[English · *The Speckled Band*](docs/assets/speckled-band-90s.m4a) ·
[繁體中文 · 〈紅髮會〉](docs/assets/red-headed-league-90s.m4a) ·
or watch them all on the [website](https://mickyyang-1407.github.io/diy-audiobook/)

It started as the production line behind **[枕邊偵探社 (Pillow Detective Agency)](https://youtube.com/@PillowMysteries)**,
a YouTube channel of Sherlock Holmes and other classic mysteries as bedtime radio dramas — nearly 200 episodes produced.
Every default here (pacing, gaps, loudness, how loud the music sits) was tuned by ear over those episodes.

---

## Quick start (5 minutes)

**You need:** [Claude Code](https://claude.com/claude-code), Python 3.9+, ffmpeg.

```bash
git clone https://github.com/mickyyang-1407/diy-audiobook ~/.claude/skills/diy-audiobook
pip install -r ~/.claude/skills/diy-audiobook/requirements.txt   # free voices, music check, covers
brew install ffmpeg                                              # or: apt install ffmpeg / winget install ffmpeg
python3 ~/.claude/skills/diy-audiobook/scripts/doctor.py         # shows what your computer can do
```

Then just ask Claude Code:

> Make a 10-minute children's story of "The Tortoise and the Hare" in English, with pictures.

> 把〈小紅帽〉做成給孩子聽的有聲書，要有插圖和輕音樂。

> Make an audiobook of "The Speckled Band" — one voice per character, no music.

> 把〈紅髮會〉做成睡前廣播劇，慢一點、輕一點。

## What you can choose

| | free, zero setup | with an account / key | your own |
|---|---|---|---|
| **Voices** | Microsoft Edge voices | MiniMax (best Mandarin), OpenAI | — |
| **Music** | generated music-box lullaby | **Suno** (step-by-step guide + prompts) | any audio file |
| **Pictures** | — | OpenAI, MiniMax · or **local ComfyUI** (free) | any picture, any app |
| **Style** | `kids` · `bedtime` · `audiobook` | | |

Guides: [paid voices / API keys](docs/API.md) ([中文](docs/API.zh-TW.md)) ·
[music & Suno](references/music.md) · [pictures: local or cloud](references/images.md)

## What you get

| file | |
|---|---|
| `build/<slug>.m4a` | the episode, −14 LUFS, ≤ −1 dBTP (YouTube / Spotify / Apple ready); `--nomusic` version too |
| `build/<slug>.mp4` | 1080p video: the pictures timed to the story, soft crossfades |
| `build/cover.jpg` | 1280×720 thumbnail with the title and a hook |
| `build/subtitles.srt` | sentence-level captions, timed from the actual audio |
| `build/description.md` | title, chapters from the scene breaks, credits |

## How it works

```
 story ──▶ fetch ──▶ Claude adapts ──▶ Claude casts ──▶ check ──▶ synth ──▶ mix ──▶ video ──▶ qc ──▶ package
 (book,    (Gutenberg,  for the ear      voices,           (gate)    voices    + music  + pictures
  file)     URL, file)                    pictures, music                                  + cover
```

**Claude does what language models are good at** — adapting a story for the ear, deciding who speaks,
casting voices, writing picture and music prompts. **Scripts do what models are bad at** — counting quotes,
aligning paragraphs, measuring loudness, trimming silence, ducking music, timing pictures, catching
glitches. Nothing reaches a paid service until `check.py` passes.

### Without Claude Code
Every step is a plain script, every file Claude writes is simple JSON:
```bash
python3 scripts/check.py examples/red-headed-league && python3 scripts/synth.py examples/red-headed-league
python3 scripts/mix.py examples/red-headed-league --nomusic && python3 scripts/qc.py examples/red-headed-league
python3 scripts/selftest.py         # offline self-test
```

## Why the defaults sound the way they do

Full list in [references/lessons.md](references/lessons.md):

- **TTS pads ~0.4 s of silence on both ends of every clip.** Untrimmed, a line of dialogue and the "he said"
  after it sit a full second apart. Clips are trimmed, then exact gaps inserted.
- **Different TTS voices differ by up to 9 dB.** Each voice is measured over all its lines and matched to the narrator.
- **Never run dynamic loudness normalisation on a mix with music** — it pumps the music up in every pause.
  The voice is mastered first; music goes in afterwards, 16.5 LU under, ducked 3:1 while someone speaks.
- **AI music sometimes freezes on one chord for minutes.** `music.py check` finds those stretches before your
  listeners do.
- **Image models have no memory between pictures** — recurring characters are described identically every time.
- **Model self-checks miss whole untranslated paragraphs.** Deterministic checks don't.

## Copyright

Use texts that are public domain **where you publish** (author dead 70+ years covers most countries; some use
50) or your own, and translate from the original — existing translations have their own copyright.
Music and pictures must be yours, generated under terms that allow your use, or licensed. Examples:
Conan Doyle (1891–92, [Project Gutenberg](https://www.gutenberg.org/ebooks/1661)) and an Aesop fable retold for
this repo.

## Repo layout

```
SKILL.md       the instructions Claude Code follows (the whole flow, step by step)
scripts/       doctor · fetch · check · synth · music · draw · mix · video · cover · qc · package · try_voice · selftest
voices/        voice pools per backend, language and style
workflows/     ComfyUI workflow template (bring your own, too)
references/    translation · speaker tagging · music & Suno · pictures · lessons from nearly 200 episodes
docs/          API key guides (English, 中文) + the website (GitHub Pages)
examples/      three complete episodes: kids (中文), bedtime (中文), English
```

## Contributing

Voice pools for more languages, more TTS / image backends and better QC checks are all welcome.
Keep the two principles: **validate before you spend**, and **measure, don't guess**.

MIT © Micky Yang
