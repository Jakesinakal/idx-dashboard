"""
ai/briefing.py
--------------
Generate the daily market briefing — the dashboard's hero feature: a short,
plain-Indonesian narrative explaining *why* the market moved today, grounded
strictly in the numbers we pass in (no hallucinated data).

`build_briefing(context)` takes a plain dict assembled by the
`bq_daily_briefing` asset and returns the narrative string.
"""

from __future__ import annotations

from ai.llm import LLMProvider, get_llm

_SYSTEM = (
    "Kamu analis pasar saham Indonesia yang menulis briefing harian untuk "
    "investor ritel. Tulis 3-4 kalimat, bahasa Indonesia yang jelas dan objektif. "
    "Sebutkan angka kunci yang relevan (IHSG, rupiah, breadth, sentimen). "
    "Jelaskan KENAPA pasar bergerak, kaitkan dengan sentimen berita bila relevan. "
    "JANGAN mengarang angka atau fakta di luar data yang diberikan. "
    "Jangan pakai bullet point — tulis sebagai paragraf mengalir."
)


def _fmt_movers(movers: list[dict]) -> str:
    return ", ".join(f"{m['ticker']} {m['return_pct']:+.1f}%" for m in movers) or "-"


def _build_prompt(d: dict) -> str:
    ihsg_ret = d.get("ihsg_return_pct")
    ihsg_ret_s = f"{ihsg_ret:+.2f}%" if ihsg_ret is not None else "tidak tersedia"
    headlines = "\n".join(
        f"- [{h['sentiment_label']}] {h['title']}" for h in d.get("top_headlines", [])
    ) or "- (tidak ada)"

    return f"""Data pasar IDX per {d.get('date')}:
- IHSG close: {d.get('ihsg_close')} ({ihsg_ret_s})
- USD/IDR: {d.get('usd_idr')}
- Breadth saham {d.get('universe', 'LQ45')}: {d.get('advancers')} naik / {d.get('decliners')} turun
- Top gainers: {_fmt_movers(d.get('top_gainers', []))}
- Top losers: {_fmt_movers(d.get('top_losers', []))}
- Sentimen berita (mood {d.get('news_mood')}): {d.get('pos')} positif / {d.get('neg')} negatif / {d.get('neu')} netral
- Headline utama:
{headlines}

Tulis briefing harian berdasarkan data di atas."""


def build_briefing(context: dict, llm: LLMProvider | None = None) -> str:
    """Return the daily briefing narrative for the given context dict."""
    llm = llm or get_llm()
    return llm.generate(
        _build_prompt(context), system=_SYSTEM, temperature=0.4, max_tokens=500,
    )
