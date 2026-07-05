# -*- coding: utf-8 -*-
"""來源健檢：逐一測試 config.yaml 的每個 feed，列出可用性與最新文章時間。
用法：python validate_feeds.py
"""
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent / "src"))
import fetch as F

cfg = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
items, status = F.fetch_all(cfg["sources"], hours_lookback=72)

print(f"{'來源':<28}{'狀態':<6}{'72h內':<8}")
print("-" * 46)
for s in status:
    if s.get("ok"):
        print(f"{s['source']:<28}{'✅':<6}{s['kept']:<8}")
    else:
        print(f"{s['source']:<28}{'❌':<6}{s.get('error','')[:40]}")
print(f"\n去重後合計 {len(items)} 則")
