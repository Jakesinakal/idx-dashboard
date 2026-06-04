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
# Each stock is tagged with the index/indices it belongs to. A stock can be in
# more than one (e.g. LQ45 *and* JII70). Adding/removing a tag here is the only
# edit needed — extract, screener filter, and asset checks all derive from this.
#
# JII70 = Jakarta Islamic Index 70 constituents (period Des 2025 – Mei 2026,
# per IDX). 30 of them also sit in LQ45 (tagged with both); the remaining 40
# are JII70-only.
STOCKS: list[Stock] = [
    # --- LQ45 (45 constituents; 30 also in JII70) ---
    Stock("ACES.JK", "Aspirasi Hidup Indonesia (Ace Hardware)", (LQ45, JII70)),
    Stock("ADMR.JK", "Adaro Minerals Indonesia", (LQ45, JII70)),
    Stock("ADRO.JK", "Alamtri Resources (Adaro Energy)", (LQ45, JII70)),
    Stock("AKRA.JK", "AKR Corporindo", (LQ45, JII70)),
    Stock("AMMN.JK", "Amman Mineral Internasional", (LQ45,)),
    Stock("AMRT.JK", "Sumber Alfaria Trijaya (Alfamart)", (LQ45,)),
    Stock("ANTM.JK", "Aneka Tambang", (LQ45, JII70)),
    Stock("ARTO.JK", "Bank Jago", (LQ45,)),
    Stock("ASII.JK", "Astra International", (LQ45,)),
    Stock("BBCA.JK", "Bank Central Asia", (LQ45,)),
    Stock("BBNI.JK", "Bank Negara Indonesia", (LQ45,)),
    Stock("BBRI.JK", "Bank Rakyat Indonesia", (LQ45,)),
    Stock("BBTN.JK", "Bank Tabungan Negara", (LQ45,)),
    Stock("BMRI.JK", "Bank Mandiri", (LQ45,)),
    Stock("BRIS.JK", "Bank Syariah Indonesia", (LQ45, JII70)),
    Stock("BRPT.JK", "Barito Pacific", (LQ45,)),
    Stock("CPIN.JK", "Charoen Pokphand Indonesia", (LQ45, JII70)),
    Stock("CTRA.JK", "Ciputra Development", (LQ45, JII70)),
    Stock("ESSA.JK", "ESSA Industries Indonesia", (LQ45, JII70)),
    Stock("EXCL.JK", "XL Axiata", (LQ45, JII70)),
    Stock("GOTO.JK", "GoTo Gojek Tokopedia", (LQ45,)),
    Stock("ICBP.JK", "Indofood CBP Sukses Makmur", (LQ45, JII70)),
    Stock("INCO.JK", "Vale Indonesia", (LQ45,)),
    Stock("INDF.JK", "Indofood Sukses Makmur", (LQ45, JII70)),
    Stock("INKP.JK", "Indah Kiat Pulp & Paper", (LQ45, JII70)),
    Stock("INTP.JK", "Indocement Tunggal Prakarsa", (LQ45, JII70)),
    Stock("ISAT.JK", "Indosat Ooredoo Hutchison", (LQ45, JII70)),
    Stock("ITMG.JK", "Indo Tambangraya Megah", (LQ45, JII70)),
    Stock("JSMR.JK", "Jasa Marga", (LQ45, JII70)),
    Stock("KLBF.JK", "Kalbe Farma", (LQ45, JII70)),
    Stock("MAPA.JK", "Map Aktif Adiperkasa", (LQ45, JII70)),
    Stock("MAPI.JK", "Mitra Adiperkasa", (LQ45, JII70)),
    Stock("MBMA.JK", "Merdeka Battery Materials", (LQ45, JII70)),
    Stock("MDKA.JK", "Merdeka Copper Gold", (LQ45, JII70)),
    Stock("MEDC.JK", "Medco Energi Internasional", (LQ45, JII70)),
    Stock("PANI.JK", "Pantai Indah Kapuk Dua", (LQ45,)),
    Stock("PGAS.JK", "Perusahaan Gas Negara", (LQ45, JII70)),
    Stock("PGEO.JK", "Pertamina Geothermal Energy", (LQ45,)),
    Stock("PTBA.JK", "Bukit Asam", (LQ45, JII70)),
    Stock("SIDO.JK", "Industri Jamu & Farmasi Sido Muncul", (LQ45, JII70)),
    Stock("SMGR.JK", "Semen Indonesia", (LQ45, JII70)),
    Stock("TLKM.JK", "Telkom Indonesia", (LQ45, JII70)),
    Stock("TOWR.JK", "Sarana Menara Nusantara", (LQ45,)),
    Stock("UNTR.JK", "United Tractors", (LQ45, JII70)),
    Stock("UNVR.JK", "Unilever Indonesia", (LQ45, JII70)),

    # --- JII70-only (40 constituents not in LQ45) ---
    Stock("AADI.JK", "Adaro Andalan Indonesia", (JII70,)),
    Stock("ARCI.JK", "Archi Indonesia", (JII70,)),
    Stock("AVIA.JK", "Avia Avian", (JII70,)),
    Stock("BKSL.JK", "Sentul City", (JII70,)),
    Stock("BRMS.JK", "Bumi Resources Minerals", (JII70,)),
    Stock("BSDE.JK", "Bumi Serpong Damai", (JII70,)),
    Stock("BTPS.JK", "Bank BTPN Syariah", (JII70,)),
    Stock("BUMI.JK", "Bumi Resources", (JII70,)),
    Stock("CMRY.JK", "Cisarua Mountain Dairy", (JII70,)),
    Stock("DEWA.JK", "Darma Henwa", (JII70,)),
    Stock("DKFT.JK", "Central Omega Resources", (JII70,)),
    Stock("DSNG.JK", "Dharma Satya Nusantara", (JII70,)),
    Stock("ELSA.JK", "Elnusa", (JII70,)),
    Stock("ENRG.JK", "Energi Mega Persada", (JII70,)),
    Stock("ERAA.JK", "Erajaya Swasembada", (JII70,)),
    Stock("HEAL.JK", "Medikaloka Hermina", (JII70,)),
    Stock("HRTA.JK", "Hartadinata Abadi", (JII70,)),
    Stock("HRUM.JK", "Harum Energy", (JII70,)),
    Stock("IMPC.JK", "Impack Pratama Industri", (JII70,)),
    Stock("INDY.JK", "Indika Energy", (JII70,)),
    Stock("JPFA.JK", "Japfa Comfeed Indonesia", (JII70,)),
    Stock("KIJA.JK", "Kawasan Industri Jababeka", (JII70,)),
    Stock("KPIG.JK", "MNC Tourism Indonesia", (JII70,)),
    Stock("LSIP.JK", "PP London Sumatra Indonesia", (JII70,)),
    Stock("MARK.JK", "Mark Dynamics Indonesia", (JII70,)),
    Stock("MIKA.JK", "Mitra Keluarga Karyasehat", (JII70,)),
    Stock("MTEL.JK", "Dayamitra Telekomunikasi", (JII70,)),
    Stock("MYOR.JK", "Mayora Indah", (JII70,)),
    Stock("RAJA.JK", "Rukun Raharja", (JII70,)),
    Stock("RATU.JK", "Raharja Energi Cepu", (JII70,)),
    Stock("SMRA.JK", "Summarecon Agung", (JII70,)),
    Stock("SRTG.JK", "Saratoga Investama Sedaya", (JII70,)),
    Stock("SSIA.JK", "Surya Semesta Internusa", (JII70,)),
    Stock("TAPG.JK", "Triputra Agro Persada", (JII70,)),
    Stock("TCPI.JK", "Transcoal Pacific", (JII70,)),
    Stock("TINS.JK", "Timah", (JII70,)),
    Stock("TKIM.JK", "Pabrik Kertas Tjiwi Kimia", (JII70,)),
    Stock("TOBA.JK", "TBS Energi Utama", (JII70,)),
    Stock("TPIA.JK", "Chandra Asri Pacific", (JII70,)),
    Stock("WIFI.JK", "Solusi Sinergi Digital", (JII70,)),
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