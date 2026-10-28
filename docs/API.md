# Using paid voices (APIs), step by step

**You don't need an API.** The default `edge` voices are free and need no sign-up. Switch to a paid
backend when you want more natural acting (especially in Mandarin).

| backend | good for | sign up |
|---|---|---|
| `edge` (default) | trying it out, English, many languages | nothing to sign up for |
| `minimax` | the most natural Mandarin, the most character voices | https://www.minimax.io (mainland accounts: https://www.minimaxi.com) |
| `openai` | any language; direct the acting in plain words | https://platform.openai.com |

**What does it cost?** All of them bill per character and prices change — check the provider's pricing page.
`check.py` prints the episode's character count (`… characters`); multiply by the price.
Every synthesized line is cached, so re-running after a fix only pays for the lines you changed.

## 1. Get a key

**MiniMax**: account → API Keys → create → copy.
**OpenAI**: platform.openai.com → API keys → Create new secret key → copy (shown only once).

> 🔒 Treat a key like a credit-card number. Never paste it into a file, a chat, a screenshot or GitHub.
> If it leaks, delete it on the same page and create a new one.

## 2. Tell your shell about it (once)

```bash
echo 'export MINIMAX_API_KEY="your-key"' >> ~/.zshrc          # bash users: ~/.bashrc
echo 'export MINIMAX_API_HOST="https://api.minimaxi.com"' >> ~/.zshrc   # only for mainland-China accounts
echo 'export OPENAI_API_KEY="your-key"' >> ~/.zshrc
```
Open a new terminal (or `source ~/.zshrc`). Restart Claude Code too, so it sees the key.

## 3. Test one sentence

```bash
python3 ~/.claude/skills/diy-audiobook/scripts/try_voice.py minimax "Chinese (Mandarin)_Gentleman" "晚安，今晚的故事開始了。"
python3 ~/.claude/skills/diy-audiobook/scripts/try_voice.py openai onyx "Good night. Tonight's story begins."
```
`✓ … works` = done; listen to the file it wrote. `✗` tells you what's wrong (no key, bad key, out of quota…).

## 4. Use it

**In Claude Code**: "use MiniMax voices for this episode".
**By hand**: set `"backend": "minimax"` (or `"openai"`) in the episode's `episode.json`.

Voices and pools: `voices/minimax.json`, `voices/openai.json`. Pick a voice for a role in `cast.json`:
`{"holmes": {"voice": "onyx", "instructions": "A sharp, quiet Victorian gentleman."}}`.

| backend | options per voice |
|---|---|
| edge | `rate` ("-10%"), `pitch` ("-4Hz"), `volume` |
| minimax | `speed` (0.85), `emotion` ("calm"), `pitch`, `model` |
| openai | `instructions`, `speed`, `model` |

## Troubleshooting

- **`… is not set`** — open a new terminal / restart Claude Code after step 2.
- **MiniMax `1002` / `1039`** — per-minute limits; the script waits and retries on its own.
- **MiniMax `2067`** — your plan's quota is used up; retrying won't help.
- **OpenAI `HTTP 401`** — wrong or deleted key. `HTTP 429` — too fast or no credit; retried automatically.
- **Another TTS provider?** Add one function to `scripts/backends.py` (text + voice settings in, audio file
  out). `OPENAI_BASE_URL` also lets the `openai` backend talk to any OpenAI-compatible speech endpoint.
  Pull requests welcome.
