"""
ai/sentiment.py
---------------
LLM-based news sentiment scoring for the AI analyst layer.

Headlines are scored in *batches* (one LLM call per ~20 articles, JSON mode)
so a full day's news costs only a handful of calls — important on the Gemini
free tier. Scoring is defensive: any malformed/short response falls back to
``netral`` per-article rather than crashing the pipeline.

Each article gets:
- ``sentiment_label`` : "positif" | "negatif" | "netral" (investor's view)
- ``sentiment_score`` : +1.0 / 0.0 / -1.0  (averaged elsewhere into a market mood)
"""

from __future__ import annotations

from ai.llm import LLMProvider, get_llm

LABEL_SCORE = {"positif": 1.0, "netral": 0.0, "negatif": -1.0}

_SYSTEM = (
    "Kamu analis pasar saham Indonesia (IHSG/IDX). Nilai sentimen tiap headline "
    "berita dari sudut pandang investor: 'positif' bila cenderung mengangkat "
    "harga saham/pasar, 'negatif' bila menekan, 'netral' bila dampaknya tidak "
    "jelas atau tidak relevan ke pasar."
)


def _build_prompt(batch: list[dict]) -> str:
    headlines = "\n".join(f'{i}. "{art.get("title", "")}"' for i, art in enumerate(batch))
    return (
        "Klasifikasi sentimen tiap headline di bawah.\n"
        'Balas HANYA JSON array, satu objek per headline: '
        '{"i": <index>, "label": "positif" | "negatif" | "netral"}.\n\n'
        f"{headlines}"
    )


def _chunks(items: list, n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def _score_batch(batch: list[dict], llm: LLMProvider) -> list[str]:
    """Return one label per article in ``batch`` ('netral' on any problem)."""
    labels = ["netral"] * len(batch)
    try:
        arr = llm.generate_json(
            _build_prompt(batch), system=_SYSTEM, max_tokens=40 * len(batch) + 100,
        )
    except Exception:
        return labels
    if not isinstance(arr, list):
        return labels
    for obj in arr:
        try:
            i = int(obj["i"])
            label = str(obj["label"]).strip().lower()
        except (KeyError, ValueError, TypeError):
            continue
        if 0 <= i < len(batch) and label in LABEL_SCORE:
            labels[i] = label
    return labels


def score_headlines(
    items: list[dict], llm: LLMProvider | None = None, batch_size: int = 20,
) -> list[dict]:
    """Score a list of ``{"url", "title", ...}`` dicts.

    Returns ``[{"url", "sentiment_label", "sentiment_score"}, ...]`` aligned to input.
    """
    llm = llm or get_llm()
    out: list[dict] = []
    for batch in _chunks(items, batch_size):
        labels = _score_batch(batch, llm)
        for art, label in zip(batch, labels):
            out.append({
                "url": art["url"],
                "sentiment_label": label,
                "sentiment_score": LABEL_SCORE[label],
            })
    return out
