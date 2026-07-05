# -*- coding: utf-8 -*-
"""主流程：抓取 → 關鍵字標記 → AI 分析（失敗降級）→ 產頁 → 推播。"""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import fetch as F          # noqa: E402
import analyze as A        # noqa: E402
import render as R         # noqa: E402
import notify as N         # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TAIPEI = timezone(timedelta(hours=8))


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    prompt_text = (ROOT / "prompt.txt").read_text(encoding="utf-8")

    print("=== 1/4 抓取 RSS ===")
    items, status = F.fetch_all(cfg["sources"], cfg.get("hours_lookback", 26))
    F.mark_keywords(items, cfg.get("must_read_keywords", []))
    print(f"共 {len(items)} 則（去重後）")
    for s in status:
        flag = "✅" if s.get("ok") else "❌"
        print(f"  {flag} {s['source']}: {s.get('kept', s.get('error'))}")

    print("=== 2/4 AI 分析 ===")
    try:
        result = A.analyze(items, cfg, prompt_text)
        print(f"AI 整併為 {len(result['events'])} 個事件")
    except Exception as exc:
        print(f"⚠️ {exc}，改用降級模式")
        result = A.fallback_result(items, cfg)

    print("=== 3/4 產生 HTML ===")
    now = datetime.now(TAIPEI)
    page = R.render(result, status, now)
    docs = ROOT / "docs"
    (docs / "archive").mkdir(parents=True, exist_ok=True)
    (docs / "index.html").write_text(page, encoding="utf-8")
    (docs / "archive" / f"{now:%Y-%m-%d}.html").write_text(
        page, encoding="utf-8")
    print(f"已寫入 docs/index.html 與 archive/{now:%Y-%m-%d}.html")

    print("=== 4/4 Telegram 推播 ===")
    N.send_telegram(result, cfg.get("telegram_top_n", 5),
                    cfg.get("site_url", ""))
    print("完成")


if __name__ == "__main__":
    main()
