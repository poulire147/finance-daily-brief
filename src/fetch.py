# -*- coding: utf-8 -*-
"""RSS 抓取模組：直抓 RSS 與 Google News 中繼，含去重與時間過濾。"""
import re
import time
import html
import urllib.parse
from datetime import datetime, timedelta, timezone

import feedparser

GNEWS_TEMPLATE = (
    "https://news.google.com/rss/search?q={query}"
    "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
)

UA = "Mozilla/5.0 (compatible; DailyBriefBot/1.0)"


def _source_url(src: dict) -> str:
    if src.get("type") == "gnews":
        q = urllib.parse.quote(src["query"])
        return GNEWS_TEMPLATE.format(query=q)
    return src["url"]


def _entry_time(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
    return None


def _clean(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)          # 去 HTML tag
    return re.sub(r"\s+", " ", text).strip()


def _norm_title(title: str) -> str:
    """去重用的標題正規化：小寫、去符號空白、砍 Google News 的「 - 媒體名」尾巴。"""
    t = re.sub(r"\s+-\s+[^-]{2,40}$", "", title)
    return re.sub(r"[\W_]+", "", t.lower())


def fetch_all(sources: list[dict], hours_lookback: int = 26) -> list[dict]:
    """回傳統一格式的新聞條目，並附上每個來源的抓取狀態。"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)
    items, status = [], []

    for src in sources:
        url = _source_url(src)
        try:
            feed = feedparser.parse(url, agent=UA)
            entries = feed.entries or []
            kept = 0
            for e in entries:
                ts = _entry_time(e)
                if ts is not None and ts < cutoff:
                    continue
                title = _clean(e.get("title", ""))
                if not title:
                    continue
                items.append({
                    "source": src["name"],
                    "lang": src.get("lang", "en"),
                    "title": title,
                    "summary": _clean(e.get("summary", ""))[:400],
                    "url": e.get("link", ""),
                    "published": ts.isoformat() if ts else "",
                })
                kept += 1
            status.append({"source": src["name"], "ok": bool(entries),
                           "total": len(entries), "kept": kept})
        except Exception as exc:  # 單一來源失敗不影響整體
            status.append({"source": src["name"], "ok": False,
                           "error": str(exc)[:120]})

    # 去重：同標題（正規化後）保留第一則，但記錄重複來源供熱度計算
    seen: dict[str, dict] = {}
    for it in items:
        key = _norm_title(it["title"])
        if key in seen:
            dup = seen[key]
            if it["source"] not in dup["dup_sources"]:
                dup["dup_sources"].append(it["source"])
        else:
            it["dup_sources"] = [it["source"]]
            seen[key] = it

    deduped = sorted(seen.values(), key=lambda x: x["published"], reverse=True)
    return deduped, status


def mark_keywords(items: list[dict], keywords: list[str]) -> None:
    """本地關鍵字命中標記（第一層，不靠 AI）。"""
    for it in items:
        text = f"{it['title']} {it['summary']}".lower()
        it["keyword_hits"] = [kw for kw in keywords if kw.lower() in text]
