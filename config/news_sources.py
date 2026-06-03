"""
config/news_sources.py
-----------------------
RSS feeds for the Indonesian financial press, consumed by
``extract/news_data.py``. Edit this list to add/remove sources — it's the
single place that defines where market news comes from.

⚠️  Source note (probed 2026-06-03): the originally-planned Bisnis.com and
    Investor.id do **not** expose a working public RSS feed at any standard
    path, so Detik Finance and Tempo Bisnis (both verified, market-focused)
    stand in for them. Swap them back here if a working feed is found.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Feed:
    source: str   # human-readable source name stored on each article
    url: str      # RSS/Atom feed URL


# Verified working market/finance feeds.
FEEDS: list[Feed] = [
    Feed("Kontan", "https://investasi.kontan.co.id/rss"),
    Feed("CNBC Indonesia", "https://www.cnbcindonesia.com/market/rss"),
    Feed("Detik Finance", "https://finance.detik.com/rss"),
    Feed("Tempo Bisnis", "https://rss.tempo.co/bisnis"),
]

# Cap per feed so the table (and the later per-article AI sentiment pass)
# stays bounded; feeds are ordered newest-first.
MAX_PER_FEED = 25
