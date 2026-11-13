# zh-tw-writing

讓 Claude 寫出台灣人讀起來順的繁體中文。

這是一份 [Agent Skill](https://agentskills.io)。裝好之後，請 Claude 寫或改中文時會自動載入。[Claude Code](https://code.claude.com/docs/en/skills) 可以直接用，其他讀得懂 `SKILL.md` 格式的工具也可以。

## 它在處理什麼

模型寫中文常出三種問題。來源不同，所以分開處理。

- AI 腔。句型有套路，讀兩段就猜得到下一句。例如「不是 X，而是 Y」、三連排比、段尾金句、「值得注意的是」。
- 翻譯腔。腦子裡先有英文句子，再逐字換成中文。例如硬翻的慣用語、句句補主詞、「進行」「作為」滿天飛，還有中國用語。
- 壓太乾。整理逐字稿或訪談時，把一段有起因、有笑點、有數字的故事縮成一句結論。

## 改寫前後

下面是測試題裡的一段，產品是虛構的。原文是用 AI 寫的更新說明：

> 在當今快速發展的 AI 時代，知識管理扮演著至關重要的角色。作為一個致力於賦能團隊的平台，我們很高興地宣布 NoteFlow 3.0 的正式發布——這不僅僅是一次更新，更是一次思維方式的革新。
>
> 在這個版本中，我們對搜索功能進行了全面的優化。用戶現在可以通過自然語言進行查詢，系統將會在 0.8 秒內返回結果，相比上一版本的 3.5 秒有了顯著的提升。

載入這份 skill 之後，Claude 改出來的：

> NoteFlow 3.0 正式發布了。
>
> 這一版全面改善了搜尋功能。現在可以用自然語言查詢，0.8 秒內就有結果，上一版要 3.5 秒。

版本、功能、兩個秒數都還在，拿掉的是開場的鋪陳和口號。

## 安裝

Claude Code：

```bash
git clone https://github.com/ncchen99/zh-tw-writing.git ~/.claude/skills/zh-tw-writing
```

只想在某個專案裡用，就改放到那個專案的 `.claude/skills/zh-tw-writing`。之後要更新：

```bash
git -C ~/.claude/skills/zh-tw-writing pull
```

其他工具的話，把整個資料夾放到它讀 skill 的位置。

## 使用

裝好後不用特別做什麼。請 Claude 寫筆記、文章、講稿、信件、README，或是把英文內容翻成中文、把逐字稿整理成筆記，它會自己載入。也可以直接講：

- 「這段幫我去 AI 味」
- 「讀起來像翻譯的，改順一點」
- 「改成台灣用語」
- 在 Claude Code 裡輸入 `/zh-tw-writing`

## 單獨用掃描程式

`scripts/zh_lint.py` 不靠 Claude 也能跑，只用 Python 3 的標準函式庫。

```bash
python3 scripts/zh_lint.py 文章.md
```

拿上面那段原文去掃，會列出這樣的結果（節錄）：

```text
【破折號】1 處（要改）
  L1    …Flow 3.0 的正式發布——這不僅僅是一次更新，更是一次…
        改成逗號、句號，或另起一句

【中國用語】4 處（要改）
  L3    …對搜索功能進行了全面的優化。用戶現在可以通過自然語言進行查詢…
        → 使用者

【鋪陳再推翻、自問自答、分裂句】2 處（看一下）
  L5    …？因為我們相信，真正的生產力不是做更多的事，而是把注意力留給真正重要的事。我…
        不是 X 而是 Y：直接講 Y
```

| 選項 | 作用 |
|---|---|
| `--text "一段文字"` | 直接掃一段文字。檔名寫 `-` 則從標準輸入讀 |
| `--all` | 每一類列出全部命中，預設每類最多 8 筆 |
| `--loose` | 連要看上下文的詞也列出來，例如質量、項目、搜索、落地 |
| `--allow 詞,詞` | 不檢查這些詞 |
| `--json` | 輸出 JSON |
| `--strict` | 有「要改」等級的命中時，結束碼為 1，可以放進 CI |

列出來的是候選。引句、專有名詞、內容確實有三項的清單都可以留。硬翻的句子、抽象主詞、壓太乾的段落，程式抓不到，還是要自己讀一遍。

## 資料夾裡有什麼

| 路徑 | 內容 |
|---|---|
| `SKILL.md` | 十二條寫作規則，每條附原因和對照例子，另有交稿前的檢查步驟 |
| `references/ai-tells.md` | AI 腔的句型和詞，每一類都有改法 |
| `references/translationese.md` | 翻譯腔的句法、硬翻的慣用語、哪些詞該留英文 |
| `references/tw-terms.md` | 中國用語和台灣用語對照，分科技、商業、一般用語，另有語氣詞 |
| `references/transcript-notes.md` | 把逐字稿、訪談、演講整理成筆記的做法 |
| `scripts/zh_lint.py` | 掃描程式 |
| `evals/` | 三個測試題 |

## 改成自己的習慣

- 自稱的方式。規則預設省略主詞，偶爾用「我」。習慣用名字自稱的人，在 `CLAUDE.md` 寫一句「替我寫第一人稱的文字時，需要主詞就用『小安』」就可以。
- 用詞。`references/tw-terms.md` 和 `zh_lint.py` 開頭的詞表都可以自己增刪。臨時不想檢查某些詞，用 `--allow`。
- 適用範圍。這些規則是從科技、新創類的筆記和講稿改出來的，用詞表也偏這個領域。公文、法律文件、文學創作沒有特別考慮。

## 測試

`evals/` 的三個測試題分別考整理逐字稿、改寫 AI 腔的稿子、寫講稿，格式是 skill-creator 用的那一種。題目的提示故意用簡體字寫，模擬語音輸入轉出來的文字。

目前這三題的自動檢查鑑別力不夠。作者自己跑的時候，有沒有載入 skill 兩邊都全過，差別要讀輸出才看得出來。歡迎補更難的題目。

## 來源

AI 腔的部分參考了兩份英文準則，把裡面的句型對應到中文，再加上中文模型特有的毛病：

- [stop-slop](https://github.com/hardikpandya/stop-slop)（MIT）
- [avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing)（MIT）

翻譯腔、台灣用詞、逐字稿整理這三部分，是實際改稿時被讀者挑出來的毛病累積成的。

## 授權

[MIT](LICENSE)。歡迎開 issue 或 PR 補詞表和例子。

## English

An Agent Skill that helps Claude write natural Traditional Chinese as used in Taiwan. It targets three failure modes: formulaic AI-sounding patterns, translationese carried over from English, and over-compressed summaries of transcripts. It ships with a dependency-free linter (`scripts/zh_lint.py`). The skill itself is written in Chinese.
