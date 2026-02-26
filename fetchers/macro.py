"""Macro data fetchers — DXY (yfinance) and yield curve (FRED API)."""
import os
import requests
import yfinance as yf

FRED_BASE = "https://api.stlouisfed.org/fred"


def _fred_latest(series_id: str) -> float | None:
    """Fetch the most recent non-missing value for a FRED data series."""
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY not set")

    url = f"{FRED_BASE}/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "sort_order": "desc",
        "limit": 10,
        "file_type": "json",
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()

    for obs in resp.json().get("observations", []):
        val = obs.get("value", ".")
        if val != ".":
            return float(val)
    return None


def get_dxy() -> dict:
    """Fetch US Dollar Index — level, 1d/5d change, trend, and intraday move detection."""
    daily = yf.Ticker("DX-Y.NYB").history(period="10d", interval="1d")
    if daily.empty or len(daily) < 2:
        raise ValueError("No DXY data")

    current = float(daily["Close"].iloc[-1])
    prev    = float(daily["Close"].iloc[-2])
    start   = float(daily["Close"].iloc[0])

    change_1d = (current - prev)  / prev  * 100
    change_5d = (current - start) / start * 100

    if change_5d > 0.5:
        trend = "RISING"
    elif change_5d < -0.5:
        trend = "FALLING"
    else:
        trend = "FLAT"

    # Intraday move — detect post-release spikes (>0.3% from today's open)
    intraday_change = None
    significant_intraday = False
    try:
        intra = yf.Ticker("DX-Y.NYB").history(period="1d", interval="1h")
        if not intra.empty and len(intra) >= 2:
            day_open     = float(intra["Open"].iloc[0])
            intraday_change     = round((current - day_open) / day_open * 100, 3)
            significant_intraday = abs(intraday_change) > 0.3
    except Exception:
        pass

    return {
        "level":                round(current,  3),
        "change_1d_pct":        round(change_1d, 3),
        "change_5d_pct":        round(change_5d, 3),
        "trend":                trend,
        "intraday_change_pct":  intraday_change,
        "significant_intraday": significant_intraday,
    }


def get_yield_curve() -> dict:
    """Fetch 2yr and 10yr Treasury yields from FRED. Returns spread and curve status."""
    y2  = _fred_latest("DGS2")
    y10 = _fred_latest("DGS10")

    if y2 is None or y10 is None:
        raise ValueError("FRED yield data unavailable")

    spread = round(y10 - y2, 3)

    if spread < -0.5:
        status = "DEEPLY_INVERTED"
    elif spread < 0:
        status = "INVERTED"
    elif spread < 0.25:
        status = "FLAT"
    else:
        status = "NORMAL"

    return {
        "yield_2yr":    round(y2,  3),
        "yield_10yr":   round(y10, 3),
        "spread_10y_2y": spread,
        "curve_status": status,
    }
