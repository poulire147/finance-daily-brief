# -*- coding: utf-8 -*-
"""Telegram 推播模組：推送當日 Top N 必讀。"""
import os
import requests


def send_telegram(result: dict, top_n: int, site_url: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("[notify] 未設定 Telegram，略過推播")
        return False

    musts = [e for e in result.get("events", [])
             if e.get("importance") == "must_read"][:top_n]
    lines = ["📰 <b>每日財經晨報</b>", ""]
    for i, ev in enumerate(musts, 1):
        lines.append(f"{i}. {ev.get('title_zh', '')}")
        lines.append(f"    <i>{ev.get('reason', '')}</i>")
    if site_url:
        lines += ["", f'完整晨報：{site_url}']

    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": "\n".join(lines),
              "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=30)
    print(f"[notify] Telegram 回應 {resp.status_code}")
    return resp.ok
