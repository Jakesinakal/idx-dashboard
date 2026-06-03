# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

```bash
source venv/bin/activate
```

Required `.env` variables (see `.env` for non-secret values):
- `GCP_PROJECT_ID`, `GCP_BUCKET_NAME`, `BQ_DATASET`
- `FRED_API_KEY` (FRED macro data); `GEMINI_API_KEY` (Fase 2 AI — free tier). `NEWS_API_KEY` is **no longer used** (news moved to Indonesian RSS) — harmless if still present.
- `GOOGLE_APPLICATION_CREDENTIALS` (defaults to `credentials/gcp-credentials.json`)

## Commands

```bash
# Launch the Dagster UI (asset catalog + manual runs)
dagster dev

# Materialize all assets from the CLI (no UI)
dagster asset materialize --select '*' -m dagster_pipeline

# Materialize a single asset
dagster asset materialize --select bq_macro_economic_daily -m dagster_pipeline

# Run with a custom date range (overrides the 2-year default)
dagster job execute -m dagster_pipeline -j finance_etl_job \
  --config '{"ops": {"extract_ihsg": {"config": {"start_date": "2024-01-01", "end_date": "2024-12-31"}}}}'

# dbt commands — always run from the project root (not from dbt/)
dbt deps --project-dir dbt --profiles-dir dbt          # install packages (first time or after packages.yml changes)
dbt build --project-dir dbt --profiles-dir dbt         # run + test all models
dbt run --select fct_daily_market --project-dir dbt --profiles-dir dbt
dbt test --project-dir dbt --profiles-dir dbt

# Migrate BigQuery tables to date-partitioned (one-time, run carefully)
python scripts/migrate_to_partitioned.py
```

There are no Python unit tests in this project. Data quality is covered by Dagster asset checks (`dagster_pipeline/asset_checks.py`) and dbt tests (`dbt test`).

## Backend

The `backend/` directory contains a **FastAPI** app that serves data from BigQuery for a dashboard frontend.

```bash
# Install backend dependencies (separate from root requirements.txt)
pip install -r backend/requirements.txt

# Run from backend/ directory
cd backend
uvicorn main:app --reload --port 8000
```

`backend/database.py` exports `get_client()` (creates a `bigquery.Client`), `PROJECT_ID`, `DATASET`, and `TABLE_PREFIX` (`` `project.dataset` `` formatted for use directly in SQL f-strings). All routers import from here.

CORS allows `http://localhost:3000`, `http://localhost:3001`, and `https://financial-data-dashboard-vz.vercel.app` (the production Vercel deployment) by default; override with `ALLOWED_ORIGINS` (comma-separated) in the environment. All routes are read-only (`GET`). The app creates a new `bigquery.Client` per request (no connection pooling).

**Deployment**: the backend is containerized via `backend/Dockerfile` and runs on Google Cloud Run (listens on `$PORT`, default 8080); the live instance is in `asia-southeast1` (its URL is the `NEXT_PUBLIC_API_URL` in the root `.env`). The frontend deploys to Vercel (`financial-data-dashboard-vz.vercel.app`).

**Endpoints** (all prefixed `/api`):
- `GET /api/snapshot` — latest row from `macro_economic_daily` (IHSG close, return %, USD/IDR, fed rate, CPI) plus market `breadth` (advancers / decliners / unchanged across the tracked stock universe) and news `sentiment` (market mood = avg AI sentiment score + positive/negative/neutral counts)
- `GET /api/stocks/today` — latest stock prices for all IDX tickers with `return_pct` and `vs_ihsg` (outperform / underperform / neutral) classification
- `GET /api/currency/trend?days=30` — currency rates (USD/IDR, EUR/IDR, JPY/IDR) for the last N days from `currency_rates` table (7–365)
- `GET /api/ihsg/comparison` — IHSG close at today, 30d, 60d, 90d ago with `change_pct`
- `GET /api/ihsg/history?days=90` — IHSG close series for the last N days (7–730), relative to the latest data point, for the trend chart
- `GET /api/screener?universe=LQ45&signal=&sort=return&order=desc` — per-ticker technical-signal snapshot from `stock_signals`: price, 1-day return, RSI, MA trend, momentum, 52w high/low, and a BUY/HOLD/SELL/OVERBOUGHT signal. Filters by `universe` (LQ45 / JII70 / ALL) and `signal`; sortable. Uses parameterized BigQuery queries (user input)
- `GET /api/movers?universe=LQ45&limit=5` — top gainers and losers by 1-day return within the universe
- `GET /api/news?limit=20&source=` — latest Indonesian market headlines from `news_articles` with per-article `sentiment_label` / `sentiment_score` (optional `source` filter)
- `GET /api/briefing` — the latest daily AI market briefing (`narrative` + `ihsg_return_pct` + `news_mood`) from `daily_briefing`
- `GET /health` — health check

## Frontend

The `frontend/` directory is a **Next.js 16 + React 19** dashboard that consumes the FastAPI backend.

```bash
# From the frontend/ directory
cd frontend
npm install        # first time
npm run dev        # dev server on http://localhost:3000
npm run build      # production build
npm run lint       # ESLint
```

> **Next.js version warning** (`frontend/AGENTS.md`): This is Next.js 16 — APIs and file conventions differ from earlier versions in training data. Read `node_modules/next/dist/docs/` before writing any code that touches routing, data fetching, or config.

Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` to override the default backend URL (`http://localhost:8000`).

**Structure** (`frontend/src/`):
- `app/` — Next.js App Router pages (`page.tsx`, `layout.tsx`)
- `components/` — four chart/card components: `MarketSnapshot`, `StockPerformance`, `CurrencyTrend`, `IHSGComparison`
- `lib/api.ts` — typed fetch helpers (`fetchSnapshot`, `fetchStocks`, `fetchCurrencyTrend`, `fetchIHSGComparison`) and formatters (`fmtNumber`, `fmtPct`, `returnColor`). All fetches use `cache: "no-store"`.

Styling is Tailwind CSS v4. Charts use Recharts.

## Architecture

This is a **Python ELT pipeline** orchestrated by Dagster. The asset graph has two parallel output paths from each extract — one to GCS (bronze Parquet) and one into the transform/BQ layer:

```
extract_ihsg ──────┬─► raw_ihsg_gcs (GCS)
                   ├─► transformed_data ─► bq_macro_economic_daily
                   └─► bq_stock_performance ─► bq_stock_signals  (direct; signals snapshot)

extract_fred ──────┬─► raw_fred_gcs (GCS)
                   └─► transformed_data

extract_currency ──┬─► raw_currency_gcs (GCS)
                   ├─► transformed_data
                   └─► bq_currency_rates    (direct, own table)

extract_news ──────┬─► raw_news_gcs (GCS)
                   └─► bq_news_articles ─► bq_news_sentiment  (LLM sentiment)

bq_daily_briefing ◄── macro_economic_daily + stock_signals + news_sentiment  (AI narrative)
```

**Extract** (`extract/`): Four independent modules pull raw data:
- `ihsg_data.py` — IHSG index (`^JKSE`) + the tracked IDX stock universe (**LQ45**, ~45 stocks) via `yfinance` (long format: date, ticker, name, close, volume). Each ticker downloaded individually so one failure doesn't block others. The ticker list is **not** hardcoded here — it comes from `config/universe.py` (single source of truth; see below).
- `fred_data.py` — CPIAUCSL, FEDFUNDS, DEXINUS from the FRED REST API (monthly series, outer-merged)
- `currency_data.py` — IDR/USD, EUR/IDR, JPY/IDR via `yfinance`
- `news_data.py` — Recent Indonesian financial-market headlines from **RSS feeds** (Kontan, CNBC Indonesia, Detik Finance, Tempo Bisnis — configured in `config/news_sources.py`, capped at 25/feed) via `feedparser`. Each feed fetched independently so one failure doesn't block the others. `start_date`/`end_date` accepted for interface consistency but **not used** (RSS only exposes recent items). Replaced the old global-English NewsAPI source — Bisnis.com & Investor.id were dropped (no working public RSS)

**Stock universe config** (`config/universe.py`): the single source of truth for which IDX stocks the pipeline tracks. Each `Stock` is tagged with the index/indices it belongs to (`indices`, e.g. `LQ45`), so a new universe like `JII70` is added by editing this one file. Helpers: `extract_ticker_names()` (used by `extract/ihsg_data.py` to build `TICKERS` = benchmark + all stocks), `tickers_for(index)`, `stocks_for(index)`, and `expected_stock_count(index)` (used by the `ticker_count_per_day` asset check). LQ45 membership is revised by IDX every Feb/Aug — the list is a snapshot to review periodically.

**Load** (`load/`):
- `gcs_loader.py` — uploads DataFrames as Parquet to `gs://{GCP_BUCKET_NAME}/raw/{folder}/{folder}_{YYYYMMDD}.parquet`
- `bigquery_loader.py` — supports three write modes: `append`, `truncate`, and `merge`. The `merge` mode uses a staging table + BigQuery `MERGE` statement (upsert); on first run it promotes staging directly since the target table doesn't exist yet. Schema is auto-detected from the DataFrame.

**Transform** (`transform/data_transform.py`): Joins IHSG, FRED, and currency data on `date` using `^JKSE` as the base. Monthly FRED values are forward-filled across daily trading dates. Drops rows where `ihsg_close` or `usd_idr` is null. Adds `year`, `month`, `week`.

**Technical indicators** (`transform/indicators.py`): pure, side-effect-free functions computing per-ticker MA20/50/200, Wilder RSI(14), 20-day average volume, 20-day momentum, and 52-week high/low, plus a transparent BUY/HOLD/SELL/OVERBOUGHT rule set (`classify_signal`). Unit-testable without BigQuery; consumed by the `bq_stock_signals` asset.

**AI layer** (`ai/`): provider-agnostic LLM access in `ai/llm.py` — an abstract `LLMProvider` with a `GeminiProvider` (Gemini free tier; sets `thinking_budget=0` so a small token budget isn't eaten by reasoning, plus retry/backoff on transient 429/503). Swapping to Claude later is one new class. `ai/sentiment.py` batch-scores headlines (JSON mode, defensive fallback to `netral`); `ai/briefing.py` builds the daily narrative from a context dict. Wired by two assets: **`bq_news_sentiment`** writes `sentiment_label`/`sentiment_score` back onto `news_articles`, scoring only un-scored rows (incremental & idempotent across daily runs); **`bq_daily_briefing`** gathers macro + breadth/movers + news sentiment → narrative → `daily_briefing` (merge on `date`). Default model `gemini-2.5-flash-lite` (override via `GEMINI_MODEL`). Requires `GEMINI_API_KEY`.

**BigQuery asset quirk** — `bq_macro_economic_daily` recalculates `ihsg_return_pct` post-merge via a BigQuery `LAG()` UPDATE statement so that every incremental run produces correct values across the full table, not just within the batch window. `bq_stock_performance` filters out the `^JKSE` row — it contains only individual stock tickers. `bq_stock_signals` reads the **full** `stock_performance` history from BigQuery (not an in-memory input — MA200 needs the long window), computes the indicator/signal snapshot, and writes one row per ticker to `stock_signals` (write mode: truncate/replace each run); it depends on `bq_stock_performance` via `deps=[...]` and enriches each row with `index_membership` from `config.universe` for the universe filter.

**Dagster pipeline** (`dagster_pipeline/`):
- `assets.py` — defines all SDAs with group names: `extract`, `raw_gcs`, `transform`, `bigquery`. The `DateRangeConfig` on extract assets defaults to a 2-year lookback; the schedule overrides it with a 2-day window. All extract assets have a `RetryPolicy(max_retries=3, delay=60, backoff=EXPONENTIAL)`. **Holiday/non-trading day pattern**: on days with no market data, extract assets return an empty DataFrame instead of raising `Failure`; every downstream asset checks `if df.empty` and returns `MaterializeResult(metadata={"skipped": True})` rather than attempting a no-op write. Any new downstream asset must follow this same guard.
- `schedules.py` — `weekday_finance_schedule` (Python variable; Dagster-registered name: `weekday_8am_wib_schedule`) runs every weekday at 08:00 WIB (01:00 UTC), incrementally fetching the last 2 days.
- `asset_checks.py` — Dagster asset checks that query BigQuery directly. ERROR checks are blocking; WARN checks are not. Covers: positive close prices, non-negative volume, unique (date, ticker) pairs, IDX circuit-breaker return range (±35%), ticker count per day (compared against `config.universe.expected_stock_count()`, scoped to the last 14 days so backfilled pre-IPO dates don't generate noise), IHSG close not null, USD/IDR in plausible range, no weekend dates, no large date gaps (>14 days — threshold sized to clear the multi-day Lebaran/Eid market closure without false positives), and FRED null warmup check. For `bq_stock_signals`: RSI within [0, 100] (ERROR), signal label in the valid set (ERROR), and ticker coverage == `config.universe.expected_stock_count()` (WARN). For the AI layer: `bq_news_sentiment` — sentiment label in {positif, negatif, netral} (ERROR); `bq_daily_briefing` — narrative not empty (ERROR).
- `sensors.py` — `etl_failure_sensor` logs run failures with run ID, job name, failed asset keys, and truncated error message. Runs automatically (RUNNING status by default).
- `workspace.yaml` — points Dagster at the `dagster_pipeline` Python module.

**BigQuery tables** (dataset `financial_data`, location `US`):
- `macro_economic_daily` — joined ^JKSE + FRED + currency (one row per trading day), merge key: `date`
- `stock_performance` — individual IDX stock rows from `extract_ihsg`, partitioned by date, clustered by ticker, merge key: `(date, ticker)`
- `currency_rates` — IDR/USD, EUR/IDR, JPY/IDR daily rates from `extract_currency`, merge key: `date`
- `news_articles` — Indonesian market headlines from RSS (`extract_news`), merge key: `url`; columns: date, title, description, source, url, published_at, plus `sentiment_label` / `sentiment_score` (added by `bq_news_sentiment`). The old NewsAPI data was renamed to `news_articles_newsapi_backup` (drop after verification)
- `daily_briefing` — one AI market-briefing narrative per day (`date`, `narrative`, `ihsg_return_pct`, `news_mood`, `generated_at`), merge key: `date`
- `stock_signals` — latest per-ticker technical-indicator + signal snapshot (one row per tracked stock), recomputed from `stock_performance` each run (write mode: **truncate**). Carries `index_membership` for the universe filter; powers the screener / movers endpoints

**Scripts** (`scripts/`):
- `migrate_to_partitioned.py` — one-time migration to add `PARTITION BY DATE(date)` (and `CLUSTER BY ticker` for `stock_performance`) to existing tables. Creates a `_backup` copy before swapping; backup must be dropped manually after verification.

The `dbt/` directory contains a full dbt project with models in three layers:
- **Staging** (`models/staging/`): `stg_stock_performance`, `stg_macro_economic` — reads from BigQuery sources (views)
- **Intermediate** (`models/intermediate/`): `int_stock_with_returns`, `int_macro_with_indicators` — ephemeral enrichment
- **Marts** (`models/marts/`): `fct_daily_market`, `mart_monthly_performance`, `dim_ticker` — materialized tables

dbt assets are defined in `dagster_pipeline/dbt_assets.py` (`finance_dbt_assets`). **They are not yet imported in `dagster_pipeline/__init__.py`** — to register them, add `from dagster_pipeline import dbt_assets` and include `dbt_assets` in the `load_assets_from_modules` call and pass `dbt_resource` to `Definitions`. They depend on `bq_macro_economic_daily` and `bq_stock_performance` (wired via `meta.dagster.asset_key` in `dbt/models/staging/sources.yml`). `DbtProject.prepare_if_dev()` in `dbt_assets.py` automatically runs `dbt deps` and `dbt parse` when `dagster dev` starts. `dbt_assets.py` also converts `GOOGLE_APPLICATION_CREDENTIALS` from a relative path to absolute at import time — dbt runs as a subprocess with `dbt/` as its CWD, so a relative credentials path would fail to resolve without this fix.

dbt packages used (installed via `dbt deps`):
- `metaplane/dbt_expectations` `>=0.10.0,<0.11.0` — data quality tests
- `dbt-labs/dbt_utils` `>=1.0.0,<2.0.0` — macro utilities

**Column note**: `macro_economic_daily` contains a `usd_idr_fred` column (USD/IDR from FRED, different scale than yfinance). The staging model `stg_macro_economic` intentionally excludes it; use `usd_idr` (from yfinance) instead.

