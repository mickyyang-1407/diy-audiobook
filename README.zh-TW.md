# 🎧 有聲書自己做 DIY Audiobook

**一句話，把任何公版書做成多角色有聲書或睡前廣播劇。給 Claude Code 用的 skill。**

> 「把〈紅髮會〉做成繁體中文有聲書，每個角色不同聲音。」

你會拿到一集做好的成品：需要的話先翻譯、每個角色有自己的聲音、可選講話時自動壓低的輕音樂、串流平台標準響度、字幕、章節、上架文案。
內建免費語音就能做；想要更像真人演出，再接 MiniMax 或 OpenAI 的付費語音。

[English](README.md) · [繁體中文](README.zh-TW.md)

🎧 **先聽聽看**（全部由這個 repo 產生，用免費語音、不需要任何 API key）：[繁體中文〈紅髮會〉](examples/red-headed-league/demo-first-90s.m4a)·[English *The Speckled Band*](examples/speckled-band/demo-first-90s.m4a)

它原本是 YouTube 頻道 **[枕邊偵探社](https://youtube.com/@PillowMysteries)** 背後的量產線：福爾摩斯、江戶川亂步、布朗神父等經典推理，做成睡前廣播劇，已經做了將近 200 集。這裡的每個預設值（語速、停頓、響度、配樂要多小聲）都是在這些集數裡一集一集用耳朵調出來的。

---

## 怎麼運作

```
 公版原文 ──▶ fetch.py ──▶ Claude 翻譯／改寫 ──▶ Claude 標誰在說話、選角
                         （逐段對齊原文）                    │
   上架文案 ◀── package.py ◀── qc.py ◀── mix.py ◀── synth.py ◀── check.py ◀┘
   章節、版權註記     響度、異常    配樂、−14 LUFS  每個角色一個聲音  花錢合成前先擋掉錯誤
```

**Claude 做語言模型擅長的事**：翻譯、為耳朵改寫、判斷誰在說話、選角。
**程式做語言模型不擅長的事**：數引號、對齊段落、量響度、修剪靜音、壓配樂。`check.py` 沒過，一個字都不會送去合成。

## 快速開始

**需要：**[Claude Code](https://claude.com/claude-code)、Python 3.9 以上、ffmpeg。

```bash
git clone https://github.com/mickyyang-1407/diy-audiobook ~/.claude/skills/diy-audiobook
pip install edge-tts            # 免費語音、不用 key
brew install ffmpeg             # 或 apt install ffmpeg
```

然後在 Claude Code 裡說：

> 把〈藍寶石〉做成繁體中文有聲書，每個角色不同聲音。

> 把〈藍寶石〉做成睡前廣播劇，慢一點、輕一點、加配樂。

> 把安徒生〈賣火柴的小女孩〉做成給小朋友聽的十分鐘睡前故事。

> Make a bedtime radio drama of "The Speckled Band" in English.

## 產出

| 檔案 | |
|---|---|
| `build/<slug>.m4a` | 成品，−14 LUFS、≤ −1 dBTP，可直接上 YouTube／Spotify／Apple |
| `build/<slug>.mp4` | 有設封面圖時，輸出靜態畫面影片 |
| `build/subtitles.srt` | 逐句字幕，時間取自實際音檔 |
| `build/description.md` | 標題、依場景自動產生的章節、版權註記 |
| `build/timeline.json` | 每一句：誰說的、幾分幾秒、說了什麼 |

## 語音

| 後端 | 費用 | 適合 | 設定 |
|---|---|---|---|
| `edge`（預設） | 免費 | 試用、英文、多語言 | `pip install edge-tts` |
| `minimax` | 付費 | 最自然的中文演出 | `export MINIMAX_API_KEY=…` |
| `openai` | 付費 | 任何語言，可用文字指示演技 | `export OPENAI_API_KEY=…` |

**沒用過 API？**一步一步的教學：[docs/API.zh-TW.md](docs/API.zh-TW.md)（[English](docs/API.md)）。
一行測試你的 key 能不能用：`python3 scripts/try_voice.py minimax "Chinese (Mandarin)_Gentleman" "你好"`

**兩種風格**：`bedtime`（預設，慢、停頓長、輕聲）或 `audiobook`（正常語速）。
`fetch.py … --style audiobook`，或直接跟 Claude 說你要哪一種。

角色可以從**聲音池**（`man_old` 老紳士、`woman_young` 年輕小姐、`boy` 男孩……）自動分配，也可以手選。每個聲音都會自動對齊旁白音量，半夜一點不會有人需要去調音量。

## 為什麼預設值是這樣

幾個用血淚換來的教訓，完整版在 [references/lessons.md](references/lessons.md)：

- **TTS 每段前後都會墊約 0.4 秒靜音。** 不修掉的話，一句對白和後面的「他說」會隔整整一秒。所以先修剪，再插入精確的停頓（0.35／1.5／3.5 秒）。
- **不同 TTS 聲音的音量最多差 9 dB。** 每個聲音用它全部的台詞量響度，對齊旁白。
- **有配樂的混音絕對不能跑動態響度正規化**——它會在每個停頓把配樂拉上來。正確順序：人聲先做到目標響度，再墊配樂（比人聲低 16.5 LU，有人說話時再 3:1 壓下去）。
- **AAC 編碼會讓真峰值多衝 1 dB**，所以峰值要量編碼後的檔案，不是 WAV。
- **模型自我檢查會漏掉整段沒翻的段落**；程式檢查不會。

## 版權

只用**在你發布的地區**已進入公有領域的作品（作者過世滿 70 年大多數地方都適用，有些地區是 50 年），並且**從原文翻譯**——現成的譯本有它自己的著作權。示範用的是柯南·道爾〈紅髮會〉（1891），原文來自 [Project Gutenberg](https://www.gutenberg.org/ebooks/1661)。配樂必須是你自己的或有授權的。

## 歡迎貢獻

更多語言的聲音池、更多 TTS 後端、更好的 QC 檢查都歡迎。原則只有兩條：**花錢之前先驗證**、**用量的，不要用猜的**。

MIT © Micky Yang
