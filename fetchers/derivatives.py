"""Crypto derivatives data — Binance Futures (funding rate, OI, basis) + Deribit (put/call ratio).
All endpoints are public and require no API keys.
"""
import requests

BINANCE_FUTURES = "https://fapi.binance.com/fapi/v1"
BINANCE_SPOT    = "https://api.binance.com/api/v3"
DERIBIT         = "https://www.deribit.com/api/v2/public"

SYMBOLS = ["BTC", "ETH"]


def _funding_rate(symbol: str) -> float | None:
    """Latest funding rate as a percentage (e.g. 0.01 = 0.01%)."""
    resp = requests.get(
        f"{BINANCE_FUTURES}/fundingRate",
        params={"symbol": f"{symbol}USDT", "limit": 1},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data:
        return round(float(data[-1].get("fundingRate", 0)) * 100, 4)
    return None


def _open_interest(symbol: str) -> float | None:
    """Current open interest in contracts (base asset units)."""
    resp = requests.get(
        f"{BINANCE_FUTURES}/openInterest",
        params={"symbol": f"{symbol}USDT"},
        timeout=10,
    )
    resp.raise_for_status()
    return float(resp.json().get("openInterest", 0))


def _basis(symbol: str) -> float | None:
    """Basis = (futures mark price - spot price) / spot price * 100."""
    spot_r = requests.get(
        f"{BINANCE_SPOT}/ticker/price",
        params={"symbol": f"{symbol}USDT"},
        timeout=10,
    )
    fut_r = requests.get(
        f"{BINANCE_FUTURES}/ticker/price",
        params={"symbol": f"{symbol}USDT"},
        timeout=10,
    )
    spot_r.raise_for_status()
    fut_r.raise_for_status()

    spot = float(spot_r.json()["price"])
    fut  = float(fut_r.json()["price"])
    return round((fut - spot) / spot * 100, 4)


def _btc_put_call_ratio() -> float | None:
    """BTC options put/call ratio by open interest from Deribit.
    > 1.0  → more puts (hedging / bearish tilt)
    < 0.7  → more calls (bullish sentiment)
    """
    resp = requests.get(
        f"{DERIBIT}/get_book_summary_by_currency",
        params={"currency": "BTC", "kind": "option"},
        timeout=20,
    )
    resp.raise_for_status()
    instruments = resp.json().get("result", [])

    put_oi  = 0.0
    call_oi = 0.0
    for inst in instruments:
        name = inst.get("instrument_name", "")
        oi   = inst.get("open_interest") or 0
        if name.endswith("-P"):
            put_oi  += oi
        elif name.endswith("-C"):
            call_oi += oi

    if call_oi == 0:
        return None
    return round(put_oi / call_oi, 3)


def get_crypto_derivatives() -> dict:
    """Return funding rates, open interest, basis for BTC+ETH and BTC put/call ratio."""
    result = {}

    for sym in SYMBOLS:
        data = {}

        try:
            data["funding_rate_pct"] = _funding_rate(sym)
        except Exception:
            data["funding_rate_pct"] = None

        try:
            data["open_interest"] = _open_interest(sym)
        except Exception:
            data["open_interest"] = None

        try:
            data["basis_pct"] = _basis(sym)
        except Exception:
            data["basis_pct"] = None

        result[sym] = data

    # BTC put/call ratio from Deribit
    try:
        result["BTC"]["put_call_ratio"] = _btc_put_call_ratio()
    except Exception:
        result["BTC"]["put_call_ratio"] = None

    return result
