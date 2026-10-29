# Music · 配樂

Music is optional. A soft bed under a bedtime story or a children's tale helps a lot; a straight audiobook
usually sounds better without. You never set volumes by hand: `mix.py` puts the music 16.5 LU under the voice
and pushes it down further whenever someone speaks.

## Four ways to get music

| | effort | cost | sounds |
|---|---|---|---|
| **A. Generated lullaby** — `music.py make` | none | free | simple music box; fine for kids, a placeholder for the rest |
| **B. Suno** (AI music) | 10 minutes | Suno plan | the best match to each story |
| **C. Your own music** | — | — | yours |
| **D. Royalty-free library** | search | free / paid | read the licence: it must allow your use (e.g. monetised YouTube) |

Whatever you use, put the files in the episode's `music/` folder and set `"music": "music"` in `episode.json`.
Several files are fine — they are levelled to each other and chained with 4-second crossfades, repeating
until the episode is covered. Then **always run the check** (see below).

## A. Generated lullaby (zero setup)

```bash
python3 scripts/music.py make episodes/<ep>/music/lullaby.wav --minutes 4 --key F
```
Original music made on your computer — you own it, no licence questions. Different `--seed` = different melody.

## B. Suno, step by step

1. Sign up at **suno.com**.
   ⚠️ **Rights**: Suno's terms decide whether you may use the music commercially (for example on a
   monetised YouTube channel). Historically only songs made on a **paid** plan could be used commercially —
   check Suno's current terms before you publish.
2. Click **Create** → switch to **Custom** → turn **Instrumental** on (no singing under a story).
3. Paste the **Style** prompt (Claude writes one for each story into `music/SUNO-PROMPT.md`; templates below)
   and the **Exclude** list if your plan shows that field.
4. Press **Create**. Suno makes two versions, a few minutes each. Listen to both; keep the calm ones.
   Make 3–6 tracks for a 30–60 minute episode so it doesn't repeat too often.
5. Download (WAV if your plan offers it, otherwise MP3) into the episode's `music/` folder.
6. Check them:
   ```bash
   python3 scripts/music.py check episodes/<ep>/music
   ```
   `✗ held chord 9:46–15:49` means the track freezes on one chord there. Cut that part out in any audio
   editor (Audacity is free), or just don't use that track. Then check again.

### Suno prompt rules (what actually works)
- **Tags only, comma-separated, ≤ ~150 characters.** No sentences, no durations, no chord names, no
  "builds to a climax", no "like <composer>" — Suno ignores them.
- Always end with `instrumental, no vocals`.
- For sleep: slow tempo words (`60bpm`, `adagio`), `no drums`, `soft`, `sparse`.

### Templates

| story | Style | Exclude |
|---|---|---|
| bedtime mystery | `ambient chamber music, warm strings, soft piano, 60bpm, D minor, mysterious, calm, sparse, no drums, instrumental, no vocals` | `drums, percussion, bass drop, choir, bright, upbeat` |
| children's story | `gentle lullaby, music box, celesta, soft harp, 70bpm, F major, warm, playful, tender, instrumental, no vocals` | `drums, electric guitar, synth lead, loud, dark` |
| fairy tale | `whimsical orchestral, pizzicato strings, flute, glockenspiel, 80bpm, G major, magical, light, instrumental, no vocals` | `drums, heavy, epic, choir, dark` |
| audiobook (if any) | `minimal ambient, soft piano, warm pad, 65bpm, C major, neutral, unobtrusive, instrumental, no vocals` | `drums, melody lead, vocals, strong rhythm` |
| sea / adventure, softly | `cinematic ambient, solo cello, low strings, ocean texture, 62bpm, A minor, wistful, calm, no drums, instrumental, no vocals` | `drums, brass, epic, percussion` |

## Things learned the hard way
- **Held chords** are the #1 defect in AI music beds (see above). Check every track, every time.
- Avoid tracks with drums, a strong lead melody or vocals — they fight the voice.
- Rotate a few tracks across episodes of a series so every night doesn't sound identical.
- Make a no-music version too (`mix.py --nomusic`): some listeners can't sleep with music.
