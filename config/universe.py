"""
config/universe.py
------------------
Single source of truth for the IDX stock universe the pipeline tracks.

Every stock is tagged with the index/indices it belongs to (``indices``), so a
new index universe (e.g. JII70 — the Jakarta Islamic Index) can be added later
by editing *this file only*: tag the relevant stocks with ``JII70`` and the
extract, asset checks, and (later) the backend ``universe=`` filter pick it up
with zero code changes elsewhere.

⚠️  LQ45 membership is revised by IDX twice a year (every February and August).
    The list below is a snapshot — review it against the latest IDX revision
    when refreshing the universe. Adding/removing a stock here is the only edit
    needed; downstream counts (e.g. the ``ticker_count_per_day`` asset check)
    derive from ``expected_stock_count()``.

Tickers use the Yahoo Finance ``.JK`` suffix (the symbols ``yfinance`` expects).
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Index universe identifiers -------------------------------------------
LQ45 = "LQ45"
JII70 = "JII70"  # reserved — tag stocks with this when the JII70 set is added

# --- The benchmark index itself -------------------------------------------
# Not a tradeable stock: it is fetched alongside the stocks (it anchors the
# macro_economic_daily join) but is excluded from the screener and from the
# per-day ticker count.
BENCHMARK_TICKER = "^JKSE"
BENCHMARK_NAME = "IHSG"


@dataclass(frozen=True)
class Stock:
    """A single tracked IDX stock and the indices it belongs to."""

    ticker: str           # yfinance symbol, e.g. "BBCA.JK"
    name: str
    indices: tuple[str, ...] = ()

    def in_index(self, index: str) -> bool:
        return index.upper() in self.indices


# --- The tracked universe --------------------------------------------------
# Snapshot of LQ45 constituents. Each stock is tagged ``LQ45``; add ``JII70``
# (or other tags) to the tuple as new universes are introduced.
STOCKS: list[Stock] = [
    Stock("ACES.JK", "Aspirasi Hidup Indonesia (Ace Hardware)", (LQ45,)),
    Stock("ADMR.JK", "Adaro Minerals Indonesia", (LQ45,)),
    Stock("ADRO.JK", "Alamtri Resources (Adaro Energy)", (LQ45,)),
    Stock("AKRA.JK", "AKR Corporindo", (LQ45,)),
    Stock("AMMN.JK", "Amman Mineral Internasional", (LQ45,)),
    Stock("AMRT.JK", "Sumber Alfaria Trijaya (Alfamart)", (LQ45,)),
    Stock("ANTM.JK", "Aneka Tambang", (LQ45,)),
    Stock("ARTO.JK", "Bank Jago", (LQ45,)),
    Stock("ASII.JK", "Astra International", (LQ45,)),
    Stock("BBCA.JK", "Bank Central Asia", (LQ45,)),
    Stock("BBNI.JK", "Bank Negara Indonesia", (LQ45,)),
    Stock("BBRI.JK", "Bank Rakyat Indonesia", (LQ45,)),
    Stock("BBTN.JK", "Bank Tabungan Negara", (LQ45,)),
    Stock("BMRI.JK", "Bank Mandiri", (LQ45,)),
    Stock("BRIS.JK", "Bank Syariah Indonesia", (LQ45,)),
    Stock("BRPT.JK", "Barito Pacific", (LQ45,)),
    Stock("CPIN.JK", "Charoen Pokphand Indonesia", (LQ45,)),
    Stock("CTRA.JK", "Ciputra Development", (LQ45,)),
    Stock("ESSA.JK", "ESSA Industries Indonesia", (LQ45,)),
    Stock("EXCL.JK", "XL Axiata", (LQ45,)),
    Stock("GOTO.JK", "GoTo Gojek Tokopedia", (LQ45,)),
    Stock("ICBP.JK", "Indofood CBP Sukses Makmur", (LQ45,)),
    Stock("INCO.JK", "Vale Indonesia", (LQ45,)),
    Stock("INDF.JK", "Indofood Sukses Makmur", (LQ45,)),
    Stock("INKP.JK", "Indah Kiat Pulp & Paper", (LQ45,)),
    Stock("INTP.JK", "Indocement Tunggal Prakarsa", (LQ45,)),
    Stock("ISAT.JK", "Indosat Ooredoo Hutchison", (LQ45,)),
    Stock("ITMG.JK", "Indo Tambangraya Megah", (LQ45,)),
    Stock("JSMR.JK", "Jasa Marga", (LQ45,)),
    Stock("KLBF.JK", "Kalbe Farma", (LQ45,)),
    Stock("MAPA.JK", "Map Aktif Adiperkasa", (LQ45,)),
    Stock("MAPI.JK", "Mitra Adiperkasa", (LQ45,)),
    Stock("MBMA.JK", "Merdeka Battery Materials", (LQ45,)),
    Stock("MDKA.JK", "Merdeka Copper Gold", (LQ45,)),
    Stock("MEDC.JK", "Medco Energi Internasional", (LQ45,)),
    Stock("PANI.JK", "Pantai Indah Kapuk Dua", (LQ45,)),
    Stock("PGAS.JK", "Perusahaan Gas Negara", (LQ45,)),
    Stock("PGEO.JK", "Pertamina Geothermal Energy", (LQ45,)),
    Stock("PTBA.JK", "Bukit Asam", (LQ45,)),
    Stock("SIDO.JK", "Industri Jamu & Farmasi Sido Muncul", (LQ45,)),
    Stock("SMGR.JK", "Semen Indonesia", (LQ45,)),
    Stock("TLKM.JK", "Telkom Indonesia", (LQ45,)),
    Stock("TOWR.JK", "Sarana Menara Nusantara", (LQ45,)),
    Stock("UNTR.JK", "United Tractors", (LQ45,)),
    Stock("UNVR.JK", "Unilever Indonesia", (LQ45,)),
]


# --- Helpers ---------------------------------------------------------------
def stocks_for(index: str | None = None) -> list[Stock]:
    """Stocks in ``index`` (e.g. "LQ45", "JII70"). ``None`` / "ALL" -> every tracked stock."""
    if index is None or index.upper() == "ALL":
        return list(STOCKS)
    idx = index.upper()
    return [s for s in STOCKS if idx in s.indices]


def tickers_for(index: str | None = None) -> list[str]:
    """yfinance ticker symbols for ``index`` (excludes the benchmark)."""
    return [s.ticker for s in stocks_for(index)]


def expected_stock_count(index: str | None = None) -> int:
    """Number of distinct stock tickers expected per day (excludes the benchmark).

    Used by the ``ticker_count_per_day`` asset check so the expectation tracks
    the universe automatically as stocks are added or removed above.
    """
    return len(stocks_for(index))


def extract_ticker_names() -> dict[str, str]:
    """``{ticker: name}`` for the extract step: the benchmark plus every tracked stock."""
    return {BENCHMARK_TICKER: BENCHMARK_NAME, **{s.ticker: s.name for s in STOCKS}}


def name_map() -> dict[str, str]:
    """``{ticker: name}`` for the tracked stocks (excludes the benchmark)."""
    return {s.ticker: s.name for s in STOCKS}


def index_membership_map() -> dict[str, str]:
    """``{ticker: comma-joined index tags}`` e.g. ``{"BBCA.JK": "LQ45"}``.

    Stored on each ``stock_signals`` row so the screener can filter by universe
    (``WHERE index_membership LIKE '%LQ45%'``) without importing this config.
    """
    return {s.ticker: ",".join(s.indices) for s in STOCKS}


def available_indices() -> list[str]:
    """All index tags currently in use across the universe (sorted)."""
    return sorted({idx for s in STOCKS for idx in s.indices})