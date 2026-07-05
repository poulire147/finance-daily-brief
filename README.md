# 每日財經晨報自動化系統

每天台北時間 06:30 由 GitHub Actions 雲端自動執行（電腦不需開機）：
抓取 14 條中英文財經 RSS → Gemini 整併事件、評重要性、翻譯摘要 →
產出一頁晨報發布到 GitHub Pages → Telegram 推播當日 Top 5 必讀。

## 架構

```
config.yaml            ← 來源、關鍵字、模型、門檻（最常改這裡）
prompt.txt             ← AI 判斷準則（想調排序邏輯改這裡）
src/
  fetch.py             ← RSS 抓取、Google News 中繼、去重
  analyze.py           ← Gemini 呼叫、JSON 解析、失敗降級
  render.py            ← HTML 晨報版面
  notify.py            ← Telegram 推播
  main.py              ← 主流程
validate_feeds.py      ← 來源健檢（部署前先跑一次）
.github/workflows/daily.yml  ← 每日排程
docs/                  ← GitHub Pages 輸出（index.html + 每日 archive）
```

## 部署步驟（一次性，約 20 分鐘）

### 1. 申請 Gemini API key
到 https://aistudio.google.com/apikey ，**建立新專案**（不要沿用報銷 OCR
的專案，額度才會獨立）→ 產生 API key。

### 2. 建立 Telegram Bot
1. Telegram 搜尋 `@BotFather` → 傳 `/newbot` → 取名 → 得到 **bot token**
2. 對你的新 bot 傳一句任意訊息
3. 瀏覽器開 `https://api.telegram.org/bot<token>/getUpdates`，
   在回傳 JSON 找 `"chat":{"id": 數字}`，那個數字就是 **chat id**

### 3. 建立 GitHub repo 並上傳
```bash
cd finance-daily-brief
git init && git add . && git commit -m "init"
# 到 GitHub 建立新 repo（公開私人皆可），然後：
git remote add origin https://github.com/<你的帳號>/<repo>.git
git push -u origin main
```

### 4. 設定 Secrets
Repo → Settings → Secrets and variables → Actions → New repository secret，
新增三個：

| 名稱 | 內容 |
|---|---|
| `GEMINI_API_KEY` | 步驟 1 的 key |
| `TELEGRAM_BOT_TOKEN` | 步驟 2 的 token |
| `TELEGRAM_CHAT_ID` | 步驟 2 的 chat id |

### 5. 開啟 GitHub Pages
Repo → Settings → Pages → Source 選 **Deploy from a branch** →
Branch 選 `main`、資料夾選 `/docs` → Save。
網址會是 `https://<帳號>.github.io/<repo>/`，
把它填回 `config.yaml` 的 `site_url` 並 push（推播訊息才會附連結）。

### 6. 手動測試一次
Repo → Actions → Daily Finance Brief → **Run workflow**。
跑完後手機應收到 Telegram、Pages 網址應看得到晨報。

## 部署前建議：先在家跑來源健檢
```bash
pip install -r requirements.txt
python validate_feeds.py
```
❌ 的來源代表 feed 網址失效，到 `config.yaml` 換掉即可（RSS 網址
偶爾會被媒體改動，這支腳本隨時可重跑）。

## 日常調整（不用碰程式碼）

| 想做的事 | 改哪裡 |
|---|---|
| 加／換新聞來源 | `config.yaml` → `sources` |
| 加關注個股關鍵字 | `config.yaml` → `must_read_keywords` |
| 調整「幾家報導算大事」 | `config.yaml` → `hot_source_threshold` |
| 改 AI 排序邏輯、摘要風格 | `prompt.txt` |
| 升級 AI 模型 | `config.yaml` → `model` |
| 改推播則數 | `config.yaml` → `telegram_top_n` |
| 改執行時間 | `daily.yml` → `cron`（注意是 UTC，台北 -8 小時） |

## 降級機制
Gemini 呼叫失敗（限速、服務中斷）時不會開天窗：自動改用本地規則
（關鍵字命中 + 跨來源熱度）排序產出晨報，僅英文不翻譯，並在導讀
標示當日為降級模式。

## 費用
全部落在免費額度：GitHub Actions（每日一次約 3–5 分鐘）、GitHub
Pages、Gemini 免費層（每日 1–3 個 request）、Telegram Bot。
