# -*- coding: utf-8 -*-
"""HTML 產生模組：把分析結果排成一頁晨報。"""
import html
from datetime import datetime

LEVELS = [
    ("must_read", "必讀", "lv-must"),
    ("watch", "關注", "lv-watch"),
    ("skim", "掃過", "lv-skim"),
]

CSS = """
:root{
  --bg:#F3F6F8; --card:#FFFFFF; --ink:#1B2733; --sub:#5A6B7A;
  --line:#DCE4EA; --must:#BE3B47; --watch:#B07A2A; --skim:#8595A3;
  --link:#2B5F8A;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;
  line-height:1.65;-webkit-font-smoothing:antialiased}
.wrap{max-width:760px;margin:0 auto;padding:0 16px 64px}
header{padding:28px 0 14px;border-bottom:3px double var(--ink)}
.masthead{font-family:"Noto Serif TC","PMingLiU",serif;font-weight:900;
  font-size:clamp(26px,6vw,38px);letter-spacing:.12em;margin:0}
.dateline{color:var(--sub);font-size:13px;letter-spacing:.18em;margin-top:6px}
.overview{background:var(--card);border-left:4px solid var(--ink);
  padding:16px 18px;margin:20px 0 8px;font-size:15.5px}
.overview b{letter-spacing:.1em}
h2.sec{display:flex;align-items:center;gap:10px;margin:30px 0 12px;
  font-size:17px;letter-spacing:.2em}
h2.sec .dot{width:10px;height:10px;border-radius:50%}
.lv-must h2 .dot, .dot.must{background:var(--must)}
.dot.watch{background:var(--watch)} .dot.skim{background:var(--skim)}
.count{color:var(--sub);font-size:13px;font-weight:400;letter-spacing:0}
.item{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:14px 16px;margin-bottom:10px}
.item.must{border-left:4px solid var(--must)}
.item.watch{border-left:4px solid var(--watch)}
.item.skim{border-left:4px solid var(--skim);opacity:.92}
.title{font-weight:700;font-size:16.5px;margin:0 0 6px}
.summary{margin:0 0 10px;font-size:14.5px;color:#33424F}
.meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.chip{font-size:12px;padding:2px 9px;border-radius:999px;
  background:#EEF3F6;color:var(--sub);border:1px solid var(--line)}
.chip.why{background:#FBF1F2;color:var(--must);border-color:#EED4D7}
.chip.kw{background:#FDF6EC;color:var(--watch);border-color:#EFE0C8}
.links{margin-top:8px;font-size:13px}
.links a{color:var(--link);text-decoration:none;margin-right:12px}
.links a:hover{text-decoration:underline}
.links .en::after{content:" EN";font-size:10px;color:var(--sub);
  vertical-align:super}
footer{margin-top:40px;color:var(--sub);font-size:12.5px;
  border-top:1px solid var(--line);padding-top:14px}
details.status{margin-top:8px} details.status summary{cursor:pointer}
@media (max-width:480px){.item{padding:12px 13px}}
"""


def _chip(text: str, cls: str = "") -> str:
    return f'<span class="chip {cls}">{html.escape(text)}</span>'


def _event_html(ev: dict, level_cls: str) -> str:
    chips = [_chip(f"為什麼在這：{ev.get('reason','')}", "why")]
    for kw in ev.get("keyword_hits", []) or []:
        chips.append(_chip(f"關鍵字 {kw}", "kw"))
    if ev.get("source_count", 1) and ev["source_count"] >= 2:
        chips.append(_chip(f"{ev['source_count']} 家來源"))
    links = "".join(
        f'<a class="{("en" if l.get("lang") == "en" else "zh")}" '
        f'href="{html.escape(l.get("url", "#"))}" target="_blank" '
        f'rel="noopener">{html.escape(l.get("source", "來源"))}</a>'
        for l in ev.get("links", [])[:5])
    return (
        f'<div class="item {level_cls}">'
        f'<p class="title">{html.escape(ev.get("title_zh", ""))}</p>'
        f'<p class="summary">{html.escape(ev.get("summary_zh", ""))}</p>'
        f'<div class="meta">{"".join(chips)}</div>'
        f'<div class="links">{links}</div></div>')


def render(result: dict, feed_status: list[dict],
           generated_at: datetime) -> str:
    date_str = generated_at.strftime("%Y 年 %m 月 %d 日")
    weekday = "一二三四五六日"[generated_at.weekday()]

    sections = []
    for key, label, _ in LEVELS:
        evs = [e for e in result.get("events", [])
               if e.get("importance") == key]
        if not evs:
            continue
        cls = key.split("_")[0] if key != "must_read" else "must"
        cls = {"must_read": "must", "watch": "watch", "skim": "skim"}[key]
        body = "".join(_event_html(e, cls) for e in evs)
        sections.append(
            f'<h2 class="sec"><span class="dot {cls}"></span>{label}'
            f'<span class="count">{len(evs)} 則</span></h2>{body}')

    ok = [s for s in feed_status if s.get("ok")]
    bad = [s for s in feed_status if not s.get("ok")]
    status_lines = "".join(
        f"<li>❌ {html.escape(s['source'])}：{html.escape(s.get('error','無資料'))}</li>"
        for s in bad) or "<li>全部來源正常</li>"

    overview = html.escape(result.get("overview", ""))

    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>每日財經晨報 {date_str}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@900&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="wrap">
<header>
  <h1 class="masthead">每日財經晨報</h1>
  <div class="dateline">{date_str}（{weekday}）｜{generated_at.strftime("%H:%M")} 產製</div>
</header>
<div class="overview"><b>今日導讀</b>　{overview}</div>
{"".join(sections)}
<footer>來源正常 {len(ok)} 個{f"，異常 {len(bad)} 個" if bad else ""}。
本頁由自動化系統產製，內容為新聞摘要，不構成投資建議。
<details class="status"><summary>來源狀態</summary><ul>{status_lines}</ul></details>
</footer>
</div></body></html>"""
