# 〈獅子與老鼠〉配樂 · Suno 提示詞

這集已經用 `music.py make` 生成的音樂盒搖籃曲墊好了。想換成 Suno 的音樂，照下面做：

1. 到 suno.com → **Create** → 切到 **Custom** → 打開 **Instrumental**
2. **Style** 欄貼上：
   ```
   gentle lullaby, music box, celesta, soft harp, warm strings, 68bpm, F major, tender, playful, cozy, instrumental, no vocals
   ```
3. **Exclude** 欄（有的話）貼上：
   ```
   drums, percussion, electric guitar, synth lead, loud, dark, choir
   ```
4. **Title** 隨意（例如 Lion and Mouse Lullaby）→ **Create**，挑一首最安靜的，下載放進這個 `music/` 資料夾
5. 跟 Claude 說「配樂換好了」，或自己跑：
   ```bash
   python3 scripts/music.py check episodes/lion-and-mouse/music   # 有 ✗ 的那首不要用
   python3 scripts/mix.py episodes/lion-and-mouse && python3 scripts/video.py episodes/lion-and-mouse
   ```
⚠️ 要放上有營利的頻道，先確認你的 Suno 方案允許商用。
