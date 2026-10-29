# Why the numbers are what they are

Everything here was learned producing the 枕邊偵探社 channel — nearly 200 episodes of Sherlock Holmes, Edogawa
Rampo, G. K. Chesterton and other public-domain mysteries as Mandarin bedtime radio dramas.

## Sound

| setting | value | why |
|---|---|---|
| pace | edge `rate -10…-12%`, MiniMax `speed 0.85` | normal TTS speed is a news read; sleepy listeners lose the plot |
| gap between a quote and "he said" | 0.35 s | TTS engines pad 0.3–0.5 s of silence on both ends of a clip; untrimmed, a quote and its attribution end up a full second apart and sound broken. `synth.py` trims and inserts exact gaps |
| greeting (intro / outro) | one or two flowing sentences, commas not full stops | a listener heard the kids' greeting 「嗨，小朋友，晚安。故事時間到囉。」 as "weird at the start": measured 1.39× slower than the story, with two ~1 s stops inside 9 s. Rewritten as one comma-joined sentence: 1.03×, pauses ≤ 0.34 s. `qc.py` flags greetings > 1.3× |
| paragraph / scene gap | 1.5 s / 3.5 s | a scene change needs to be *heard* — there's no visual break |
| voice levelling | every voice matched to the narrator (integrated LUFS over all its clips) | raw TTS voices differ by up to 9 dB, and it is the first thing a listener notices. Measuring per clip is unreliable (short clips) — measure per voice |
| music bed + ducking | 16.5 LU under the voice; sidechain 3:1, attack 200 ms, release 1.8 s | tested by ear in three rounds: −15 LU / 2:1 was too loud, −18 LU / 4:1 too quiet, the middle stuck. Measured result: music ~19.7 dB under the voice while someone talks, ~15 dB in the pauses |
| order of mastering | voice to target first, then add music, then linear gain + limiter | loudnorm in dynamic mode acts like an AGC: run it on the mix and it lifts the music in every pause |
| master | −14 LUFS integrated, ≤ −1.0 dBTP measured **after** AAC encoding | AAC overshoots the PCM true peak by 0.3–1 dB; `mix.py` re-encodes with a lower ceiling until the delivered file passes |
| loudnorm accuracy | re-aim until within 0.3 LU | speech peaks sit ~19 dB above its loudness, so loudnorm can't run linear and lands 0.4–0.7 LU low |
| two versions | with and without music | some listeners can't sleep with music, some can't without it |
| no rain / ambience | — | an early version had rain; it was dropped — the voice and one quiet music bed are enough |

### Music beds
- Use music you own or that is licensed for it. Loop-friendly, no drums, no vocals, no sudden swells.
- Check AI-generated music for **held notes**: some generators freeze a chord for minutes. Unnoticeable in a
  preview, maddening at minute 30 of a sleep story. Listen to the whole bed before using it.
- Rotate a few beds across episodes so the channel doesn't sound identical every night.

## Pipeline

- **Validate before paying.** Every check in `check.py` exists because the mistake reached TTS at least once:
  untranslated paragraphs, speaker lists one short, a pool name used as a voice id, two roles sharing a voice.
- **Cache every TTS call** by (backend, voice settings, text). Fixing one sentence then costs one call.
- **Model self-checks miss things.** A translator model that skipped 48 paragraphs reported "no problems".
  Deterministic checks (length ratios, script detection, quote counts) catch what self-review doesn't.
- **Rate limits**: MiniMax answers a per-minute limit with HTTP 200 and `status_code` 1002 (requests) or 1039
  (tokens) — back off and retry. Code 2067 is a plan quota: retrying doesn't help.
- **Speech-to-text QC** (optional, e.g. Whisper) hallucinates in the last 30-second window ("please like and
  subscribe") and writes digits for spoken numbers — normalise before comparing, cut at the known ending.

## Channel

- A fixed opening line and closing line turn single videos into a show.
- Thumbnails: a dark, warm public-domain illustration (e.g. Sidney Paget's Strand drawings for Holmes) with
  two short lines of text — curiosity, not fear. People are about to sleep.
- Shorts/teasers: one mystery per clip, never spoil the solution, link the full episode.
- Publish on a fixed schedule (same time every night). Bedtime listeners build a habit.
