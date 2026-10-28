# 用付費語音（API）——一步一步來

**先講結論：不用 API 也能做。** 預設的 `edge` 語音免費、不用申請任何東西。
想要更像真人演出（尤其中文），再換成付費語音。

| 後端 | 適合 | 去哪申請 |
|---|---|---|
| `edge`（預設） | 試做、英文、多語言 | 不用申請 |
| `minimax` | 中文演出最自然，角色聲音最多 | 國際站 https://www.minimax.io ／ 中國站 https://www.minimaxi.com |
| `openai` | 任何語言；可以用一句話指示演技 | https://platform.openai.com |

**會花多少錢？** 每家都按字數計費，價格常常變動，請以官網為準。
`check.py` 會印出這一集共多少字（`… characters`），乘上官網單價就是這一集的語音費。
同一句話合成過就會存起來，之後重跑不會再收一次錢。

---

## 1. 拿到 API key

**MiniMax**：登入後台，找到「API Keys」頁面 → 建立新的 key → 複製。
**OpenAI**：登入 platform.openai.com → API keys → Create new secret key → 複製（只會顯示一次）。

> 🔒 API key 就跟信用卡號一樣。**不要**貼進任何檔案、聊天、截圖、或 GitHub。
> 外流了就立刻到同一個頁面把它刪掉，再建一把新的。

## 2. 告訴電腦你的 key（只做一次）

打開「終端機」，把下面這行的 `你的key` 換掉後貼上（Mac 預設是 zsh）：

```bash
# MiniMax（國際站）
echo 'export MINIMAX_API_KEY="你的key"' >> ~/.zshrc
# MiniMax 中國站帳號要多加這一行
echo 'export MINIMAX_API_HOST="https://api.minimaxi.com"' >> ~/.zshrc

# OpenAI
echo 'export OPENAI_API_KEY="你的key"' >> ~/.zshrc
```

然後**關掉終端機再重開**（或執行 `source ~/.zshrc`）。如果有開 Claude Code，也要重開，它才讀得到。

## 3. 試一句話，確定 key 能用

```bash
python3 ~/.claude/skills/diy-audiobook/scripts/try_voice.py minimax "Chinese (Mandarin)_Gentleman" "晚安，今晚的故事開始了。"
python3 ~/.claude/skills/diy-audiobook/scripts/try_voice.py openai onyx "Good night. Tonight's story begins."
```

看到 `✓ … works` 就成功了，打開產生的 `try-minimax.wav` 聽聽看。
看到 `✗` 會直接告訴你哪裡不對（沒設 key、key 錯、額度用完……）。

## 4. 叫它用付費語音

**用 Claude Code**：直接說「這集用 MiniMax 的聲音」。
**自己改**：把那一集 `episode.json` 裡的 `"backend": "edge"` 改成 `"minimax"` 或 `"openai"`。

能用的聲音與分組在 `voices/minimax.json`、`voices/openai.json`；
要指定某個角色的聲音，就在 `cast.json` 寫 `{"holmes": {"voice": "Chinese (Mandarin)_Reliable_Executive"}}`。

| 後端 | 可以調的參數 |
|---|---|
| edge | `rate`（"-10%"）、`pitch`（"-4Hz"）、`volume` |
| minimax | `speed`（0.85）、`emotion`（"calm"）、`pitch`、`model` |
| openai | `instructions`（"像老紳士一樣，慢慢地、輕聲地說"）、`speed`、`model` |

## 常見問題

- **`MINIMAX_API_KEY is not set`**：第 2 步做完沒有重開終端機／Claude Code。
- **MiniMax 回 `1002` 或 `1039`**：每分鐘的次數上限，程式會自己等一下再重試，不用管它。
- **MiniMax 回 `2067`**：方案的總額度用完了，重試沒有用，等額度重置或升級方案。
- **OpenAI 回 `HTTP 401`**：key 錯了或被刪了。`HTTP 429`：太快或沒餘額，程式會自動重試幾次。
- **想用其他家的語音**：在 `scripts/backends.py` 加一個函式（收文字和聲音設定、寫出音檔），歡迎發 Pull Request。
