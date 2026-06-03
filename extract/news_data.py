"""
extract/news_data.py
--------------------
Extracts recent Indonesian financial-market news from RSS feeds (Kontan,
CNBC Indonesia, Detik Finance, Tempo Bisnis — see ``config/news_sources.py``).

This replaces the previous global-English NewsAPI source: the rebuild needs
*Indonesian* market context for the AI analyst. Each feed is fetched
independently so one bad feed doesn't block the others.

Returns a DataFrame with columns (unchanged from the old extractor, so the
``bq_news_articles`` asset is untouched):
    date, title, description, source, url, published_at
"""

import calendar
import html
import re
from datetime import datetime, timezone

import feedparser
import pandas as pd

from config.news_sources import FEEDS, MAX_PER_FEED

_COLUMNS = ["date", "title", "description", "source", "url", "published_at"]
_UA = "Mozilla/5.0 (compatible; FinanceDataBot/1.0; +https://github.com/Jakesinakal)"
_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(raw: str) -> str:
    """Strip HTML tags/entities that RSS summaries often carry."""
    if not raw:
        return ""
    return html.unescape(_TAG_RE.sub("", raw)).strip()


def _published(entry) -> tuple[str, str]:
    """Return (published_at_iso, date_yyyy_mm_dd) from a feed entry.

    feedparser's ``*_parsed`` struct_time is in UTC — use ``calendar.timegm``
    (not ``time.mktime``, which would assume local time) to convert correctly.
    """
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        dt = datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
        return dt.isoformat(), dt.strftime("%Y-%m-%d")
    raw = entry.get("published") or entry.get("updated") or ""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return raw, (raw[:10] if len(raw) >= 10 else today)


def extract_news(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Fetch the latest market-news headlines from the configured RSS feeds.

    ``start_date`` / ``end_date`` are accepted for interface consistency with
    the other extract assets but are not used — RSS feeds only expose their
    current window of recent items.

    Returns:
        DataFrame with columns: date, title, description, source, url, published_at
    """
    records: list[dict] = []

    for feed in FEEDS:
        try:
            print(f"[News] Fetching {feed.source} — {feed.url}")
            parsed = feedparser.parse(feed.url, request_headers={"User-Agent": _UA})
            entries = parsed.entries[:MAX_PER_FEED]
            kept = 0
            for entry in entries:
                url = (entry.get("link") or "").strip()
                title = _clean_text(entry.get("title", ""))
                if not url or not title:
                    continue
                published_at, date = _published(entry)
                records.append({
                    "date":         date,
                    "title":        title,
                    "description":  _clean_text(entry.get("summary", "")),
                    "source":       feed.source,
                    "url":          url,
                    "published_at": published_at,
                })
                kept += 1
            print(f"[News] {feed.source}: {kept} articles")
        except Exception as e:  # one bad feed must not block the rest
            print(f"[News] ERROR fetching {feed.source}: {e}")

    if not records:
        print("[News] WARNING: No articles returned from any feed.")
        return pd.DataFrame(columns=_COLUMNS)

    df = (
        pd.DataFrame(records, columns=_COLUMNS)
        .drop_duplicates(subset=["url"])
        .sort_values("published_at", ascending=False)
        .reset_index(drop=True)
    )
    print(f"[News] Total cleaned articles across {len(FEEDS)} feeds: {len(df)} rows")
    return df
