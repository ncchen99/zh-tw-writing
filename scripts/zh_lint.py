#!/usr/bin/env python3
"""zh_lint.py：掃描中文（台灣繁體）文字裡常見的 AI 腔、翻譯腔、中國用語和標點問題。

用法：
  python3 zh_lint.py 檔案 [檔案 ...]
  python3 zh_lint.py --text "一段文字"
  cat 檔案 | python3 zh_lint.py -

選項：
  --all       每一類列出全部命中（預設每類最多 8 筆）
  --loose     連「看上下文」的詞也列出來（質量、項目、落地、打造…）
  --allow 詞  不檢查這些詞，逗號分隔（例如 --allow 洞見,其實）
  --json      輸出 JSON，給其他程式用
  --strict    有「要改」等級的命中時，結束碼為 1

列出來的是候選，不是判決。引句、專有名詞、內容確實有三項的清單都可以留。
只用 Python 標準函式庫。
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ───────────────────────── 詞表 ─────────────────────────

# 中國用語 → 台灣用語。左邊是正規表示式。
CN_TERMS = [
    (r"用戶", "使用者"), (r"軟件", "軟體"), (r"硬件", "硬體"), (r"網絡", "網路"),
    (r"互聯網", "網際網路／網路"), (r"信息", "資訊／訊息"), (r"數據庫", "資料庫"),
    (r"視頻", "影片／視訊"), (r"音頻", "音訊"), (r"屏幕", "螢幕"), (r"鼠標", "滑鼠"),
    (r"內存", "記憶體"), (r"硬盤", "硬碟"), (r"服務器", "伺服器"), (r"芯片", "晶片"),
    (r"人工智能", "人工智慧"), (r"智能體", "agent"), (r"智能(?!障礙)", "智慧"),
    (r"(?<!演)算法", "演算法"), (r"代碼", "程式碼"), (r"編程", "寫程式／程式設計"),
    (r"默認", "預設"), (r"創建", "建立"), (r"獲取", "取得"), (r"調用", "呼叫"),
    (r"接口", "介面／API"), (r"界面", "介面"), (r"文檔", "文件"), (r"文件夾", "資料夾"),
    (r"鏈接", "連結"), (r"模塊", "模組"), (r"插件", "外掛"), (r"線程", "執行緒"),
    (r"集成", "整合"), (r"兼容", "相容"), (r"實時", "即時"), (r"在線(?!上)", "線上"),
    (r"激活", "啟用"), (r"打印", "列印"), (r"博客", "部落格"), (r"短信", "簡訊"),
    (r"移動端|移動設備", "手機／行動裝置"), (r"高清", "高畫質"), (r"交互", "互動"),
    (r"反饋", "回饋／意見"), (r"回調", "回呼／callback"),
    (r"創始人", "創辦人"), (r"初創", "新創"), (r"風投", "創投"),
    (r"基礎設施", "基礎建設"), (r"招人|招聘", "請人／找人／徵才"), (r"營銷", "行銷"),
    (r"渠道", "通路／管道"), (r"賽道", "領域／市場"), (r"抓手", "著力點"),
    (r"閉環", "講清楚哪個流程接起來了"), (r"拉通", "串起來／協調"), (r"給到", "給"),
    (r"內卷", "惡性競爭"), (r"性價比", "CP 值"), (r"立馬", "馬上"), (r"靠譜", "可靠"),
    (r"牛逼", "厲害"), (r"硅谷", "矽谷"), (r"悉尼", "雪梨"), (r"新西蘭", "紐西蘭"),
    (r"意大利", "義大利"), (r"沙特", "沙烏地"), (r"土豆", "馬鈴薯"),
    (r"出租車", "計程車"), (r"公交", "公車"), (r"塑料", "塑膠"), (r"本科", "大學部"),
]

# 兩邊都有人用、要看上下文的詞。加 --loose 才列。
CN_TERMS_LOOSE = [
    (r"質量", "品質（物理的質量不用改）"), (r"項目", "專案（清單裡的一項不用改）"),
    (r"水平", "水準／程度"), (r"設置", "設定"), (r"運行", "執行／跑"), (r"添加", "新增／加上"),
    (r"搜索", "搜尋"), (r"登錄", "登入"), (r"組件", "元件"), (r"進程", "行程"),
    (r"融資", "募資（借錢的融資不用改）"), (r"創業公司", "新創"), (r"頭部", "龍頭／領先的"),
    (r"打法", "做法／策略"), (r"對齊", "對一下／同步"), (r"落地", "做出來／導入"),
    (r"出海", "做海外市場"), (r"大模型", "模型／大型語言模型"), (r"提示詞", "prompt"),
    (r"打造", "做／建立（行銷味重，偶爾用可以）"), (r"底層邏輯", "講清楚是什麼道理"),
    (r"護城河", "別人追不上的地方"), (r"痛點", "困擾／卡住的地方"),
    (r"解鎖", "打開／做得到（unlock 的直譯）"),
]

# AI 腔的詞句。
AI_PHRASES = [
    r"值得注意的是", r"需要指出的是", r"值得一提的是", r"不可否認", r"毋庸置疑",
    r"眾所周知", r"總而言之", r"綜上所述", r"總的來說", r"歸根結[柢底]", r"歸根究[柢底]",
    r"讓我們一起", r"讓我們來看看", r"接下來[，,]?我們將", r"扮演[^，。]{0,8}角色",
    r"至關重要", r"不可或缺", r"舉足輕重", r"深遠的(?:影響|意義)", r"在[^，。]{1,12}的浪潮",
    r"隨著[^，。]{1,15}的(?:快速|蓬勃|不斷|高速)?發展", r"在當今", r"新的篇章",
    r"邁出[^，。]{0,4}重要的一步", r"奠定[^，。]{0,4}基礎", r"賦能", r"助力", r"深耕",
    r"佈局", r"布局", r"攜手", r"共創", r"致力於", r"旨在", r"無縫", r"全方位", r"一站式",
    r"顛覆性", r"革命性", r"深入探討", r"一探究竟", r"揭開[^，。]{0,6}面紗", r"全面解析",
    r"意義所在", r"未來可期", r"拭目以待", r"時間會證明", r"老實說", r"坦白[講說]",
    r"(?:^|(?<=[，。！？「\n]))說真的", r"不得不說", r"不瞞你說", r"最有意思的是", r"令人驚訝的是", r"出乎意料的是",
    r"重點來了", r"一文看懂", r"終極指南", r"你需要知道的", r"重新定義",
]

# 聊天機器人的殘留。
CHATBOT = [
    r"好的[，,]以下是", r"當然可以[！!]?", r"希望(?:這|以上)[^。]{0,10}(?:幫助|有用)",
    r"如果(?:你|您)?(?:還)?需要[^。]{0,12}(?:調整|修改|協助|補充)", r"作為一個 ?AI", r"截至我的",
]

# 鋪陳再推翻、自問自答、分裂句。
STRUCTURES = [
    (r"不是[^。！？\n]{1,25}?[，,、]?\s*而是", "不是 X 而是 Y：直接講 Y"),
    (r"不只是[^。！？\n]{1,25}?[，,]?\s*更是", "不只是 X 更是 Y：講具體改變了什麼"),
    (r"不僅[^。！？\n]{1,25}?[，,]?\s*(?:更|還|而且)", "不僅 X 更 Y：兩件事分開講或只留重要的"),
    (r"與其說[^。！？\n]{1,25}不如說", "與其說 X 不如說 Y：直接講 Y"),
    (r"看似[^。！？\n]{1,15}[，,]?\s*(?:其實|實則|卻)", "看似 X 其實 Y：講具體差在哪"),
    (r"問題不在[^。！？\n]{1,15}[，,]?\s*而在", "問題不在 X 而在 Y：直接講 Y"),
    (r"(?:^|[。！？\n])\s*(?:為什麼|結果呢|然後呢|怎麼說|答案是什麼)？", "自問自答：刪掉問句，直接講答案"),
    (r"的背後[，,]\s*是", "X 的背後，是 Y：改成有人做事的句子"),
    (r"(?:讓|使)[^。！？\n，]{2,20}的[，,]\s*是", "分裂句：改成「因為…所以…」或直接講"),
]

# 翻譯腔的句法。
TRANSLATIONESE = [
    (r"(?:作為|身為)一[個名位]", "作為一個…：省掉，或改「…出身」"),
    (r"進行(?:了)?[^\s，。]{0,2}(?:討論|分析|訪談|溝通|測試|研究|調整|修改|評估|合作|交流|探討|說明|處理|改善|開發|驗證)", "進行＋名詞：直接用動詞"),
    (r"(?:做出|作出)(?:了)?[^，。]{0,4}(?:決定|選擇|判斷|改變|回應|調整)", "做出＋名詞：直接用動詞"),
    (r"加以", "加以…：直接用動詞"),
    (r"(?:創辦人|使用者|開發者|工程師|投資人|客戶|讀者|觀眾|講者|員工|夥伴|用戶|學生)們", "…們：中文複數通常不用標"),
    (r"(?<!分)之一(?=[，。、！？])", "…之一：多半可以改成「很…」或直接講"),
    (r"當[^，。！？\n]{2,25}的時候", "當…的時候：改「…時」或省略"),
    (r"這(?:使得|意味著)", "這使得／這意味著：改「所以」或併句"),
    (r"擁有", "擁有：多半寫「有」"),
    (r"將會", "將會：寫「會」"),
    (r"有(?:很高的|極大的|一定的)?可能性", "有可能性：寫「很可能」「可能」"),
    (r"的[^，。、；：！？\s「」（）]{1,8}的[^，。、；：！？\s「」（）]{1,8}的", "的…的…的：拆成兩句"),
]

# 硬翻的慣用語和翻譯腔名詞。
IDIOMS = [
    (r"兔子洞", "一頭栽進去／越挖越深"), (r"把[^，。]{0,8}午餐吃掉", "搶生意"),
    (r"下巴(?:都)?掉", "看傻眼"), (r"低垂的果實", "最容易做的那幾件"),
    (r"房間裡的大象", "大家都知道卻沒人提的事"), (r"房間裡的(?:每個|所有)?人", "在場的人"),
    (r"在一天結束", "說到底"), (r"移動指針", "有明顯的效果"), (r"在同一頁", "想法一致"),
    (r"一粒鹽", "聽聽就好"), (r"閃亮的(?:東西|物件|新玩意)", "看起來值得一試的新東西"),
    (r"不公平的優勢", "別人很難追上的優勢"), (r"上檔", "能得到的好處"),
    (r"皮膚在遊戲", "自己也有風險"), (r"桌邊的位子", "說得上話"),
    (r"學習迴圈", "learning loop"), (r"洞見|洞察", "發現／看法"),
    (r"心智模型", "想法／理解方式"), (r"顆粒度", "細到什麼程度"),
]

FILLERS = ["其實", "真的", "真正", "非常", "十分", "相當", "基本上", "某種程度上",
           "可以說", "事實上", "實際上", "顯然", "無疑", "簡單來說", "換句話說"]

CONNECTORS = ["並且", "以及", "然而", "此外", "因此", "與此同時", "另一方面", "總之"]

HEADING_TROPES = [
    (r"[，,]\s*和", "「X，和 Y」式小標"), (r"的藝術", "「X 的藝術」"),
    (r"當[^，。]{1,10}遇上", "「當 X 遇上 Y」"), (r"重新定義", "「重新定義 X」"),
]

CJK = r"一-鿿㐀-䶿"
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")

# ───────────────────────── 工具 ─────────────────────────


def strip_code(text):
    """把程式碼區塊、行內程式碼、網址換成等長的空白，行號才不會跑掉。"""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"```.*?```", blank, text, flags=re.S)
    text = re.sub(r"`[^`\n]+`", blank, text)
    text = re.sub(r"https?://\S+", blank, text)
    return text


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def excerpt(text, start, end, pad=14):
    s = max(0, start - pad)
    e = min(len(text), end + pad)
    out = text[s:e].replace("\n", " ")
    return ("…" if s > 0 else "") + out + ("…" if e < len(text) else "")


def find_all(text, pattern, hint=""):
    hits = []
    for m in re.finditer(pattern, text, flags=re.M):
        hits.append({"line": line_of(text, m.start()), "match": m.group(0).strip(),
                     "context": excerpt(text, m.start(), m.end()), "hint": hint})
    return hits


def sentences(text):
    for s in re.split(r"[。！？!?\n]+", text):
        s = re.sub(r"^[\s\-\*•·\d\.、「『（(#>'\"|`]+", "", s)
        if len(re.findall(f"[{CJK}]", s)) >= 4:
            yield s


def paragraphs(text):
    for p in re.split(r"\n\s*\n|\n", text):
        p = p.strip()
        if len(re.findall(f"[{CJK}]", p)) >= 30:
            yield p

# ───────────────────────── 檢查 ─────────────────────────


def lint(raw, loose=False, allow=()):
    text = strip_code(raw)
    n_cjk = len(re.findall(f"[{CJK}]", text))
    per_k = lambda n: (n * 1000 / n_cjk) if n_cjk else 0
    allowed = lambda s: any(a and a in s for a in allow)
    groups = []

    def add(title, level, hits, note=""):
        hits = [h for h in hits if not allowed(h["match"])]
        if hits:
            groups.append({"title": title, "level": level, "count": len(hits), "note": note, "hits": hits})

    # 標點
    add("分號", "看一下", find_all(text, r"；", "用句號斷開，或用逗號接"))
    add("破折號", "要改", find_all(text, f"——|—|[{CJK}]\\s*–|–\\s*[{CJK}]", "改成逗號、句號，或另起一句"))
    multi_colon = [h for h in find_all(text, r"^.*：.*：.*$", "一句裡兩個以上的冒號，拆開")
                   if not re.match(r"\s*[\{\[\"']", h["match"])]
    add("冒號串句", "看一下", multi_colon)
    add("半形標點貼著中文", "要改",
        find_all(text, f"[{CJK}][,;:!?](?=[{CJK}\\s]|$)|[,;:!?][{CJK}]", "改全形"))
    seen, spacing = set(), []
    for h in find_all(text, f"[{CJK}][A-Za-z0-9]|[A-Za-z0-9][{CJK}]", "中文和英文、數字之間空一格"):
        if h["line"] not in seen:
            seen.add(h["line"])
            spacing.append(h)
    add("中英文之間沒空格", "看一下", spacing, "一行只列一次")
    add("emoji", "要改", [{"line": line_of(text, m.start()), "match": m.group(0),
                          "context": excerpt(text, m.start(), m.end()), "hint": "拿掉"}
                         for m in EMOJI.finditer(text)])

    # 用語
    hits = []
    for pat, sug in CN_TERMS:
        hits += find_all(text, pat, "→ " + sug)
    add("中國用語", "要改", sorted(hits, key=lambda h: h["line"]))
    if loose:
        hits = []
        for pat, sug in CN_TERMS_LOOSE:
            hits += find_all(text, pat, "→ " + sug)
        add("看上下文的詞", "看一下", sorted(hits, key=lambda h: h["line"]))

    # AI 腔
    hits = []
    for pat in AI_PHRASES:
        hits += find_all(text, pat, "刪掉，或換成具體的事")
    add("AI 腔詞句", "要改", sorted(hits, key=lambda h: h["line"]))
    hits = []
    for pat in CHATBOT:
        hits += find_all(text, pat, "交付的文字裡不該有")
    add("聊天機器人的殘留", "要改", sorted(hits, key=lambda h: h["line"]))
    hits = []
    for pat, hint in STRUCTURES:
        hits += find_all(text, pat, hint)
    add("鋪陳再推翻、自問自答、分裂句", "看一下", sorted(hits, key=lambda h: h["line"]))

    # 翻譯腔
    hits = []
    for pat, sug in IDIOMS:
        hits += find_all(text, pat, "→ " + sug)
    add("硬翻的慣用語、翻譯腔名詞", "要改", sorted(hits, key=lambda h: h["line"]))
    hits = []
    for pat, hint in TRANSLATIONESE:
        hits += find_all(text, pat, hint)
    add("翻譯腔句法", "看一下", sorted(hits, key=lambda h: h["line"]))

    # 小標
    hits = []
    for m in re.finditer(r"^(#{1,6}\s+.*|\s*h\d?:\s*'.*)$", text, flags=re.M):
        for pat, hint in HEADING_TROPES:
            if re.search(pat, m.group(0)):
                hits.append({"line": line_of(text, m.start()), "match": m.group(0).strip()[:40],
                             "context": m.group(0).strip()[:60], "hint": hint})
    add("小標套路", "看一下", hits)

    # 密度類：只在偏多時才報
    stats = {"中文字數": n_cjk}
    filler_hits = []
    for w in FILLERS:
        filler_hits += find_all(text, re.escape(w), "刪掉試試，意思沒變就不要放回去")
    stats["虛詞每千字"] = round(per_k(len(filler_hits)), 1)
    if len(filler_hits) >= 3 and per_k(len(filler_hits)) > 4:
        add("虛詞偏多", "看一下", sorted(filler_hits, key=lambda h: h["line"]),
            f"每千字 {stats['虛詞每千字']} 個")

    conn_hits = []
    for w in CONNECTORS:
        conn_hits += find_all(text, re.escape(w), "先刪掉試試，讀不通再放回去")
    stats["連接詞每千字"] = round(per_k(len(conn_hits)), 1)
    if n_cjk and per_k(len(conn_hits)) > 5:
        add("連接詞偏多", "看一下", sorted(conn_hits, key=lambda h: h["line"]),
            f"每千字 {stats['連接詞每千字']} 個")

    for word, limit, hint in [("被", 6, "改主動，或把做事的人寫出來"),
                              ("一個", 9, "「他是一個醫生」寫「他是醫生」"),
                              ("它", 3, "省略，或把名詞再講一次")]:
        hs = find_all(text, f"(?<![其])它(?:們)?" if word == "它" else re.escape(word), hint)
        stats[f"「{word}」每千字"] = round(per_k(len(hs)), 1)
        if n_cjk >= 200 and per_k(len(hs)) > limit:
            add(f"「{word}」偏多", "看一下", hs, f"每千字 {round(per_k(len(hs)), 1)} 個")

    sents = list(sentences(text))
    first = [s for s in sents if re.match(r"(?:我們|我)(?![們]?的?名字)", s)]
    stats["句數"] = len(sents)
    stats["「我」開頭的句子"] = len(first)
    if len(first) >= 3 and len(first) / max(1, len(sents)) >= 0.2:
        add("「我」開頭的句子偏多", "看一下",
            [{"line": 0, "match": "我", "context": s[:28] + "…", "hint": "省略主詞，或換成名字、「自己」"} for s in first],
            f"{len(first)}／{len(sents)} 句")

    # 連續三句同一個開頭
    runs, run = [], []
    for s in sents:
        head = s[:2]
        if run and run[-1][:2] == head:
            run.append(s)
        else:
            if len(run) >= 3:
                runs.append(run)
            run = [s]
    if len(run) >= 3:
        runs.append(run)
    add("連續幾句同一個開頭", "看一下",
        [{"line": 0, "match": r[0][:2], "context": f"「{r[0][:2]}…」連續 {len(r)} 句", "hint": "省掉開頭，或換個說法"} for r in runs])

    # 段尾短句
    paras = list(paragraphs(text))
    punch = []
    for p in paras:
        ss = [s for s in re.split(r"(?<=[。！？])", p) if s.strip()]
        if len(ss) >= 3:
            last = re.sub(r"[^" + CJK + "]", "", ss[-1])
            if 0 < len(last) <= 10:
                punch.append({"line": 0, "match": ss[-1].strip(), "context": ss[-1].strip(),
                              "hint": "段尾短句。每段都這樣收就是公式"})
    stats["段落數"] = len(paras)
    if len(punch) >= 3 and len(punch) / max(1, len(paras)) >= 0.25:
        add("段尾金句偏多", "看一下", punch, f"{len(punch)}／{len(paras)} 段")

    # 粗體標籤清單
    labels = find_all(text, r"^\s*(?:[-*•]|\d+\.)?\s*\*\*[^*\n]{1,20}\*\*\s*[：:]", "能寫成段落就寫成段落")
    if len(labels) >= 5:
        add("「粗體標籤：說明」排到底", "看一下", labels)

    return {"stats": stats, "groups": groups}

# ───────────────────────── 輸出 ─────────────────────────


def report(name, result, show_all=False):
    out = [f"zh_lint：{name}（中文 {result['stats']['中文字數']:,} 字）"]
    if not result["groups"]:
        out.append("  沒有掃到候選。還是要自己從頭讀一遍，硬翻的句子和抽象主詞程式抓不到。")
        return "\n".join(out)
    total = 0
    for g in result["groups"]:
        total += g["count"]
        note = f"，{g['note']}" if g["note"] else ""
        out.append(f"\n【{g['title']}】{g['count']} 處（{g['level']}{note}）")
        shown = g["hits"] if show_all else g["hits"][:8]
        for h in shown:
            loc = f"L{h['line']:<4}" if h["line"] else "     "
            out.append(f"  {loc} {h['context']}")
            if h["hint"]:
                out.append(f"        {h['hint']}")
        if len(g["hits"]) > len(shown):
            out.append(f"  …還有 {len(g['hits']) - len(shown)} 處，加 --all 列出全部")
    must = sum(g["count"] for g in result["groups"] if g["level"] == "要改")
    out.append(f"\n合計 {total} 處候選，其中「要改」{must} 處。這些是候選，不是判決。")
    out.append("引句、專有名詞、內容確實有三項的清單可以留。程式抓不到硬翻的句子、抽象主詞和壓太乾的段落，還是要自己讀一遍。")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="掃描中文文字裡的 AI 腔、翻譯腔、中國用語和標點問題")
    ap.add_argument("files", nargs="*", help="要掃的檔案，- 代表標準輸入")
    ap.add_argument("--text", help="直接給一段文字")
    ap.add_argument("--all", action="store_true", help="列出全部命中")
    ap.add_argument("--loose", action="store_true", help="連要看上下文的詞也列")
    ap.add_argument("--allow", default="", help="不檢查的詞，逗號分隔")
    ap.add_argument("--json", action="store_true", help="輸出 JSON")
    ap.add_argument("--strict", action="store_true", help="有「要改」的命中時結束碼為 1")
    a = ap.parse_args()

    allow = tuple(x.strip() for x in a.allow.split(",") if x.strip())
    inputs = []
    if a.text is not None:
        inputs.append(("（文字）", a.text))
    for f in a.files:
        if f == "-":
            inputs.append(("（標準輸入）", sys.stdin.read()))
        else:
            inputs.append((f, Path(f).read_text(encoding="utf-8")))
    if not inputs:
        if sys.stdin.isatty():
            ap.print_help()
            return 2
        inputs.append(("（標準輸入）", sys.stdin.read()))

    results, must = {}, 0
    for name, raw in inputs:
        r = lint(raw, loose=a.loose, allow=allow)
        results[name] = r
        must += sum(g["count"] for g in r["groups"] if g["level"] == "要改")
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("\n\n".join(report(n, r, a.all) for n, r in results.items()))
    return 1 if (a.strict and must) else 0


if __name__ == "__main__":
    sys.exit(main())
