# 🎧 有聲書自己做DIY Audiobook

**跟Claude Code說一句話，就做出有聲書、兒童故事或睡前廣播劇——每個角色不同聲音，還有配樂和插圖。**

> 「把〈獅子與老鼠〉做成給孩子聽的有聲書，要有插圖和輕音樂。」

<p align="center"><img src="examples/lion-and-mouse/cover-small.jpg" width="520" alt="〈獅子與老鼠〉封面——由這個repo自動產生"></p>

<p align="center"><b><a href="https://mickyyang-1407.github.io/diy-audiobook/?lang=zh">🌐 網站與示範</a></b></p>

你會拿到一集完整的成品：為「用聽的」改寫好的故事、每個角色不同的聲音、講話時自動壓低的輕音樂、跟著劇情換場的插圖、影片、封面、字幕、章節、上架文案。
**免費語音和免費配樂內建就能用**——不用註冊、不用API key。想要更好，再接MiniMax、OpenAI、Suno或你自己電腦上的ComfyUI。

[English](README.md) · [繁體中文](README.zh-TW.md)

🎬 **看看成品**（全部由這個repo產生）：
[兒童故事〈獅子與老鼠〉影片](docs/assets/lion-and-mouse.mp4) ·
[睡前廣播劇〈紅髮會〉](docs/assets/red-headed-league-90s.m4a) ·
[English *The Speckled Band*](docs/assets/speckled-band-90s.m4a) ·
或到[網站](https://mickyyang-1407.github.io/diy-audiobook/?lang=zh)一次看完

它原本是YouTube頻道 **[枕邊偵探社](https://youtube.com/@PillowMysteries)** 背後的量產線：福爾摩斯、江戶川亂步、布朗神父等經典推理，做成睡前廣播劇，已經做了將近200集。這裡的每個預設值（語速、停頓、響度、配樂要多小聲）都是在這些集數裡一集一集用耳朵調出來的。

---

## 五分鐘開始

**需要：**[Claude Code](https://claude.com/claude-code)、Python 3.9以上、ffmpeg。

```bash
git clone https://github.com/mickyyang-1407/diy-audiobook ~/.claude/skills/diy-audiobook
pip install -r ~/.claude/skills/diy-audiobook/requirements.txt   # 免費語音、配樂檢查、封面
brew install ffmpeg                                              # 或 apt install ffmpeg／winget install ffmpeg
python3 ~/.claude/skills/diy-audiobook/scripts/doctor.py         # 看看你的電腦現在能做什麼
```

然後直接跟Claude Code說：

> 把〈小紅帽〉做成給孩子聽的有聲書，要有插圖和輕音樂。

> 把〈龜兔賽跑〉做成十分鐘的英文兒童故事，要有插圖。

> 把〈紅髮會〉做成睡前廣播劇，慢一點、輕一點。

> 把〈花斑帶〉做成有聲書，每個角色不同聲音，不要配樂。

## 可以選什麼

| | 免費、不用設定 | 要帳號或key | 自己的 |
|---|---|---|---|
| **語音** | 微軟Edge語音 | MiniMax（中文最自然）、OpenAI | — |
| **配樂** | 自動生成的音樂盒搖籃曲 | **Suno**（有一步一步教學＋提示詞範本） | 任何音檔 |
| **插圖** | — | OpenAI、MiniMax·或**自己電腦的ComfyUI**（免費） | 任何圖、任何app畫的 |
| **風格** | `kids`兒童·`bedtime`睡前·`audiobook`有聲書 | | |

教學：[付費語音／API key](docs/API.zh-TW.md)·[配樂與Suno](references/music.md)·[插圖：本機或雲端](references/images.md)

## 產出

| 檔案 | |
|---|---|
| `build/<slug>.m4a` | 成品，−14 LUFS、≤ −1 dBTP，可直接上YouTube／Spotify／Apple；也可另出無配樂版 |
| `build/<slug>.mp4` | 1080p影片：插圖跟著劇情換、淡入淡出 |
| `build/cover.jpg` | 1280×720封面，標題＋一句鉤子 |
| `build/subtitles.srt` | 逐句字幕，時間取自實際音檔 |
| `build/description.md` | 標題、依場景自動產生的章節、版權註記 |

## 怎麼運作

**Claude做語言模型擅長的事**：把故事改寫成適合用聽的、判斷誰在說話、選角、寫插圖和配樂的提示詞。
**程式做語言模型不擅長的事**：數引號、對齊段落、量響度、修剪靜音、壓配樂、對齊插圖時間、抓錯誤。
`check.py`沒過，任何要花錢的服務都不會被呼叫。

## 為什麼預設值是這樣

完整版在[references/lessons.md](references/lessons.md)：

- **TTS每段前後都會墊約0.4秒靜音**，不修掉的話，一句對白和後面的「他說」會隔整整一秒。
- **不同TTS聲音的音量最多差9 dB**，每個聲音都會自動對齊旁白。
- **有配樂的混音絕對不能跑動態響度正規化**——它會在每個停頓把配樂拉上來。人聲先做到目標響度，再墊配樂（低16.5 LU，有人說話時再3:1壓下去）。
- **AI配樂有時會卡在同一個和弦好幾分鐘**，`music.py check`會在聽眾發現之前先抓出來。
- **畫圖模型每張圖之間沒有記憶**，同一個角色每次都要用一模一樣的文字描述。
- **模型自我檢查會漏掉整段沒翻的段落**，程式檢查不會。

## 版權

只用**在你發布的地區**已進入公有領域的作品（作者過世滿70年大多數地方都適用，有些地區是50年）或你自己寫的故事，並且**從原文翻譯**——現成的譯本有它自己的著作權。配樂和插圖必須是你自己的、在允許你用途的條款下生成的，或有授權。範例用的是柯南·道爾（1891–92，[Project Gutenberg](https://www.gutenberg.org/ebooks/1661)）和為這個repo改寫的伊索寓言。

## 歡迎貢獻

更多語言的聲音池、更多語音／畫圖後端、更好的品質檢查都歡迎。原則只有兩條：**花錢之前先驗證**、**用量的，不要用猜的**。

MIT © Micky Yang
