  📦 IDX Intelligence — Dokumentasi Lengkap Project

  1. Visi & Latar Belakang

  Awalnya project ini cuma data viewer biasa (dashboard nampilin 4 saham + data makro). Pada 2 Jun 2026 dirasa "useless" — cuma
  nge-duplikat tools gratis, nggak ada decision support, berita dikumpulin tapi nyaris nggak dipakai, nggak ada "so what?".

  Pivot: jadi alat intelijen saham Indonesia personal, gabungan:
  1. AI Market Analyst — AI jelasin kenapa pasar gerak + skor sentimen berita (ini pembeda utama vs tools gratis).
  2. Screener & Signals — banyak saham IDX + indikator teknikal + screener.
  
  Tujuan ganda: (a) dipakai Jake sendiri harian, (b) portfolio showcase buat recruiter → standar desain & kualitas kode
  dinaikin.

  2. Keputusan Terkunci

  - Tetap GCP (BigQuery, GCS, Cloud Run)
  - AI: Gemini free tier, dibikin provider-agnostic (ai/llm.py) biar gampang upgrade ke Claude
  - TANPA Telegram bot
  - Dashboard dibikin baru, tapi pertahankan skeleton Next.js 16 + Tailwind v4 + Recharts
  - Saham: mulai LQ45; daftar saham = config bertag-indeks (JII70 gampang ditambah)
  - Semua GRATIS ($0)
  - Berita: ganti NewsAPI global → RSS keuangan Indonesia

  3. Wireframe & Arah Desain (terkunci)

  - Multi-halaman: Beranda /, Screener /screener, Detail /stock/[ticker]
  - Briefing AI = hero di Beranda (paling menonjol — differentiator)
  - Filter universe (LQ45/JII70/Semua) di header
  - Visual: "Elegant Dark Minimal" — hitam-zinc, garis tipis (bukan kartu tebal), angka monospace, aksen violet, lapang. Ala
  Vercel/Linear-dark.
  - Teknis frontend: hand-roll komponen Tailwind v4 + Recharts (bukan library)

  4. Rencana Berfase & Status

  ┌────────┬──────────────────────────────────────────────────────────┬────────────┐
  │  Fase  │                           Isi                            │         Status         │
  ├────────┼──────────────────────────────────────────────────────────┼────────────────────────┤
  │ Fase 0 │ Ekspansi 4 saham → LQ45 (config bertag)                  │ ✅ Selesai             │
  ├────────┼──────────────────────────────────────────────────────────┼────────────────────────┤
  │ Fase 1 │ Indikator teknikal + tabel signals + screener + endpoint │ ✅ Selesai             │
  ├────────┼──────────────────────────────────────────────────────────┼────────────────────────┤
  │ Fase 2 │ AI (Gemini): sentimen berita + briefing harian + RSS     │ ✅ Selesai             │
  ├────────┼──────────────────────────────────────────────────────────┼────────────────────────┤
  │ Fase 3 │ Dashboard frontend baru                                  │ ⬜ Belum (tinggal ini) │
  └────────┴──────────────────────────────────────────────────────────┴────────────────────────┘

  Urutan kerja yang disepakati: wireframe dulu → bangun workflow (Fase 0→2) → poles UI. Jangan bangun UI penuh di atas data
  mock.

  ---
  5. Detail yang Sudah Dikerjakan

  Fase 0 — LQ45 ✅

  - config/universe.py (baru) — sumber kebenaran tunggal: 45 saham LQ45, tiap saham di-tag indeks (Stock dataclass + helper
  extract_ticker_names/tickers_for/stocks_for/expected_stock_count/name_map/index_membership_map).
  - extract/ihsg_data.py — TICKERS diambil dari config (bukan hardcode).
  - asset_checks.py — ticker_count_per_day pakai expected_stock_count() (bukan != 4), di-scope 14 hari terakhir biar tanggal
  pre-IPO pas backfill nggak bikin warning palsu.
  - BigQuery stock_performance di-backfill ke 45 ticker × ~2 tahun (21.626 baris). Semua asset check hijau.

  Fase 1 — Screener & Signals ✅

  - transform/indicators.py — logika indikator murni: MA20/50/200, Wilder RSI(14), vol_avg20, momentum_20d, 52-week high/low +
  aturan sinyal transparan classify_signal (BUY/HOLD/SELL/OVERBOUGHT).
  - Asset bq_stock_signals (deps=[bq_stock_performance]) → tabel stock_signals (45 baris snapshot, truncate tiap run, bawa
  index_membership buat filter universe).
  - Asset checks: rsi_in_range, signal_in_valid_set (ERROR), ticker_coverage (WARN) — hijau.
  - Endpoint (dites TestClient): /api/screener, /api/movers, /api/ihsg/history, /api/snapshot (+breadth). Pakai parameterized 
  query (anti SQL-injection).

  Fase 2 — Lapisan AI ✅

  - Sumber berita: NewsAPI global → RSS Indonesia (config/news_sources.py + extract/news_data.py via feedparser). Sumber final:
  Kontan, CNBC Indonesia, Detik Finance, Tempo Bisnis.
  - ai/llm.py — provider-agnostic (LLMProvider + GeminiProvider); default gemini-2.5-flash-lite, thinking_budget=0,
  retry+backoff.
  - ai/sentiment.py + asset bq_news_sentiment → skor sentimen (batched JSON) ditulis balik ke news_articles
  (sentiment_label/sentiment_score), incremental & idempotent.
  - ai/briefing.py + asset bq_daily_briefing → narasi briefing harian → tabel daily_briefing.
  - Asset checks: sentiment_label_valid, briefing_not_empty (ERROR) — hijau.
  - Endpoint: /api/news (+sentimen), /api/briefing, /api/snapshot (+mood).
  - macro & currency di-sync ke terkini.

  ---
  6. Kontrak Endpoint (semua LIVE & tested)

  ┌──────────────────────────────────────────────────┬──────────────────────────────────────────────────────┐
  │                     Endpoint                     │                         Isi                          │
  ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ GET /api/snapshot                                │ IHSG, USD/IDR, fed, CPI + breadth + sentiment (mood) │
  ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ GET /api/ihsg/history?days=                      │ seri IHSG buat chart                                 │
  ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ GET /api/movers?universe=&limit=                                 │ top gainers/losers                                   │
  ├──────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ GET /api/screener?universe=&signal=&sort=&order=                 │ tabel 45 saham + sinyal                              │
  ├──────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ GET /api/news?limit=&source=                                     │ berita + sentimen per artikel                        │
  ├──────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ GET /api/briefing                                                │ narasi briefing AI harian                            │
  ├──────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ GET /api/stocks/today, /api/currency/trend, /api/ihsg/comparison │ (lama, masih ada)                                    │
  └──────────────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────┘

  ---
  7. Keputusan Teknis & Alasannya

  - Config universe terpisah → JII70 tinggal nambah tag, zero code change.
  - Check ticker scoped 14 hari → banyak saham LQ45 IPO baru, tanggal lama wajar < 45, biar nggak noise.
  - Kolom date itu STRING di BQ → check pakai DATE(date) (sempat bug, udah fix).
  - stock_signals simpan latest-only → cukup buat screener; chart detail (Fase 3) butuh history MA → extend nanti.
  - Gemini flash-lite + thinking_budget=0 + retry → 2.0-flash kena 429 (kuota), 2.5-flash kadang 503; model 2.5 "thinking" jadi
  token kemakan kalau budget kecil.
  - Bisnis.com & Investor.id di-drop → nggak punya RSS publik yang jalan (di-probe). Diganti Detik + Tempo (config, gampang
  dibalikin).
  - Tabel NewsAPI lama di-rename jadi news_articles_newsapi_backup (bukan dihapus) → reversible.
  - Parameterized query di endpoint yang nerima input user → keamanan + portfolio-grade.

  ---
  8. Status Git

  - Repo: github.com/Jakesinakal/finance-data-platform (root tunggal)
  - Branch kerja: feat/lq45-universe (belum di-merge ke main)
  - Commit: baseline acadbc4 udah di-push; Fase 0, 1, 2 di-commit bertahap (batch Fase 2 AI terakhir mungkin masih perlu di-push
  — cek git status)
  - Repo lama finance-dashboard = arsip → jangan dihapus dulu sampai Vercel di-repoint ke repo baru
  - Aturan: kerjaan fitur di branch, jangan langsung di main

  9. Follow-up Tertunda (nggak blocking)

  - dbt/models/marts/dim_ticker.sql masih hardcode 4 saham → regenerate buat LQ45 (idealnya dari config). dbt juga belum di-wire
  ke Dagster.
  - Halaman detail /stock/[ticker] butuh history MA per hari → stock_signals cuma simpan snapshot terakhir, extend nanti.
  - news_articles_newsapi_backup bisa dihapus kalau udah yakin.

  10. Catatan Cara Kerja (preferensi Jake)

  - Respon pakai bahasa Indonesia santai.
  - Kasih tau scope sebelum bertindak; tapi sekali rencana disepakati, boleh jalan otonom sampai selesai — akurat > cepat.
  - Jangan tambahin trailer Co-Authored-By/AI di commit.