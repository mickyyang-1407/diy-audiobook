# Translating for the ear

The listener is lying in the dark, half asleep. They can't re-read a sentence. Everything below serves that.

## Hard rules

1. **One script paragraph per source paragraph, same id.** Never merge, split, or skip — `check.py` aligns
   them, and a reviewer (human or model) needs side-by-side paragraphs to catch mistakes.
2. **Translate everything.** No summarising, no "…and so on". Bedtime softening is allowed (slow down a
   violent moment, drop gore adjectives) — cutting plot is not.
3. **Quotes are structural.** Only real speech goes inside top-level quotes (`「」` for Chinese, `“ ”` for
   English). Nested speech uses `『』` / `‘ ’`. A long speech over several paragraphs: open the quote at the
   start of every paragraph, close it only at the end of the last one — exactly like the original.
4. **Keep the punctuation of feeling.** A question stays a question (`？」`, not `。」`). Exclamation marks
   become full stops for bedtime unless it's a gasp the plot needs.
5. **One name, one spelling, the whole series.** Keep a glossary (`names.json` next to the script is a good
   habit): 華生, 雷斯垂德, 哈德森太太… A name that changes halfway loses a listener who can't scroll back.

## Review pass (do it — this is where most errors are caught)

After translating, re-read source and translation paragraph by paragraph. The error types that actually
happened across nearly 200 episodes (quote structure went wrong in almost every one):

- **Quote structure**: a speech closed early, an outer quote never closed (every following paragraph becomes
  "speech"), narration wrapped in quotes, ASCII `'` used as a quote.
- **Meaning flipped**: "bet on the horse to lose" → "to win"; "she would never let me marry anyone else" →
  the opposite; "he misses me" → "I miss him". Check every negation and every direction of an action.
- **Wrong person**: I/we/he/she swapped, especially in reported speech.
- **Forms of address taken as subjects**: "This gentleman, Mr. Wilson, has been…" is said *to* Wilson.
- **Period details**: Victoria (the colony) vs Victorian (the era); sovereign = gold pound; half a crown;
  "I'll swing for it" = "I'll hang for it / take the blame".
- **Whole paragraphs left untranslated** — a model's self-check often reports "no problems" anyway.
  `check.py` catches Latin-heavy paragraphs and abnormal length ratios; trust it over the self-check.
- **Wrong script variant** (simplified characters leaking into Traditional Chinese). If you run OpenCC to
  check, diff and read every changed character — don't blindly apply it to finished Traditional text
  (it "corrects" correct regional words).
- **Puns and letter games**: rewrite them for the ear ("a rat" / "Ballarat") and add a half-sentence
  explanation inside the narration if the plot depends on it. Codes and ciphers: spell them out the way they
  should be *heard*.

## Writing for TTS

- Numbers and dates as words when the reading is ambiguous (1895 → 一八九五年; 221B → 二二一B).
- Short sentences beat long ones; commas are breathing points for the voice.
- A quote that is only `……` (silence) becomes a pause, which is fine.
- Avoid characters a TTS engine reads in two ways when a synonym exists (行, 長, 重…), or test the line.
