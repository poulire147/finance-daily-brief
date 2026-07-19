# -*- coding: utf-8 -*-
"""AI 分析模組：呼叫 Gemini 做事件整併、重要性評分、翻譯摘要。"""
import json
import os
import re
import time

import requests

API_URL = ("https://generativelanguage.googleapis.com/v1beta/"
           "models/{model}:generateContent")


def _build_prompt(prompt_text: str, cfg: dict, items: list[dict]) -> str:
    terms = "\n".join(f"- {t}" for t in cfg.get("terminology", []))
    kws = "、".join(cfg.get("must_read_keywords", []))
    payload = [{
        "source": it["source"], "lang": it["lang"], "title": it["title"],
        "summary": it["summary"], "url": it["url"],
        "keyword_hits": it.get("keyword_hits", []),
        "reported_by": it.get("dup_sources", [it["source"]]),
    } for it in items]
    return (
        f"{prompt_text}\n\n"
        f"## 使用者關鍵字清單\n{kws}\n\n"
        f"## 用語規範\n{terms}\n\n"
        f"## 跨來源熱度門檻\n{cfg.get('hot_source_threshold', 3)} 家\n\n"
        f"## 新聞清單\n{json.dumps(payload, ensure_ascii=False)}"
    )


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(),
                  flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def analyze(items: list[dict], cfg: dict, prompt_text: str) -> dict:
    """成功回傳 AI 分析結果；失敗丟出例外，由 main 降級處理。"""
    api_key = os.environ["GEMINI_API_KEY"]
    model = cfg.get("model", "gemini-2.5-flash")
    limit = cfg.get("max_items_to_ai", 120)
    prompt = _build_prompt(prompt_text, cfg, items[:limit])

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 65536,
            "responseMimeType": "application/json",
        },
    }

    last_err = None
    for attempt in range(3):
        try:
            resp = requests.post(
                API_URL.format(model=model),
                params={"key": api_key}, json=body, timeout=180)
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            result = _extract_json(text)
            if "events" in result:
                return result
            raise ValueError("回傳 JSON 缺少 events 欄位")
        except Exception as exc:
            last_err = exc
            time.sleep(15 * (attempt + 1))   # 免費層限速時退避重試
    raise RuntimeError(f"Gemini 分析失敗（重試 3 次）：{last_err}")


def fallback_result(items: list[dict], cfg: dict) -> dict:
    """AI 失敗時的降級輸出：靠本地關鍵字與跨來源熱度排序，不翻譯。"""
    threshold = cfg.get("hot_source_threshold", 3)
    events = []
    for it in items:
        hits = it.get("keyword_hits", [])
        n_src = len(it.get("dup_sources", []))
        if hits:
            level, reason = "must_read", f"命中關鍵字：{'、'.join(hits)}"
        elif n_src >= threshold:
            level, reason = "must_read", f"{n_src} 家來源報導"
        else:
            level, reason = "skim", "未分析（AI 服務暫時無法使用）"
        events.append({
            "title_zh": it["title"], "summary_zh": it["summary"][:150],
            "importance": level, "reason": reason, "keyword_hits": hits,
            "source_count": n_src,
            "links": [{"source": it["source"], "url": it["url"],
                       "lang": it["lang"]}],
        })
    order = {"must_read": 0, "watch": 1, "skim": 2}
    events.sort(key=lambda e: order[e["importance"]])
    return {"overview": "⚠️ 今日 AI 分析暫時無法使用，以下為關鍵字與熱度規則的降級排序，"
                        "英文新聞未翻譯。", "events": events[:60]}
