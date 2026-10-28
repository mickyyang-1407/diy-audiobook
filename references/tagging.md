# Speaker tagging

`script/speakers.json` says who speaks each paragraph's top-level quotes. Always decide from the **original
text** (`said Holmes`, context, turn-taking), not from the translation alone — alternating two-person
dialogue without attributions is where guesses go wrong.

```json
{"P005": "holmes", "P050": ["king", "holmes"], "P242": ["holmes", null]}
```

- **string** — every top-level quote in the paragraph is this character
- **list** — one speaker per top-level quote, in order; `null` = the narrator reads that quote.
  The list length must equal the number of quotes (`check.py` blocks otherwise)
- **not listed** — the narrator reads the whole paragraph

## Rules

1. **First-person narrator** (Watson, Hastings…): tag their lines with their own key (`watson`) and cast it
   as `"same:narrator"`. Same voice, but the tag documents who is speaking.
2. **Leave to the narrator**: quoted words, titles, signs, newspaper text, advertisements, inscriptions,
   sound effects (「噹」). **Letters and telegrams** read aloud within the story → tag the writer.
3. **Speech inside speech**: a client telling their story and quoting someone else in `『』` — the whole
   top-level quote stays the client's.
4. **A speech spanning paragraphs** — tag every paragraph with the same speaker.
5. **Disguises**: a character in disguise gets the disguise's own voice until the reveal — the voice must
   not give the twist away.
6. **Crowds / several voices at once**: `crowd`.
7. **Keys**: lowercase English, underscores (`holmes`, `mrs_hudson`, `client`, `inspector`). One character
   keeps one key for the whole episode — and across a series if they recur.
8. Unsure who speaks: pick the most likely, and list those paragraph ids in your report to the human.

## Casting

`cast.json` gives every key a voice:

| value | meaning |
|---|---|
| `{"voice": "…", "rate": "-10%", "pitch": "-4Hz"}` | a specific voice (options depend on the backend) |
| `"pool:man_old"` | first free voice of that pool in `voices/<backend>.json` |
| `"same:narrator"` | share another role's voice |

- Hand-pick voices for the narrator and leads; pools are for one-scene roles.
- Choose the pool from the original: age, sex, temperament (old gentleman → `man_old`, sailor or thug →
  `man_rough`, young lady → `woman_young`, housekeeper → `woman_old`, police inspector → `man_mid`).
- Two roles never share a voice identity unless you say `same:` — listeners tell characters apart by voice.
- Side characters get no "emotion" setting (MiniMax): it over-acts in a bedtime context.
- In a series, recurring characters keep their voice forever. Keep the lead's voice out of the pools.
