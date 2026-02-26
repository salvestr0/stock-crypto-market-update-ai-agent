"""Crypto derivatives data — Binance Futures + Deribit options.
All endpoints are public and require no API keys.
"""
import requests

BINANCE_FUTURES = "https://fapi.binance.com/fapi/v1"
BINANCE_SPOT    = "https://api.binance.com/api/v3"
DERIBIT         = "https://www.deribit.com/api/v2/public"

SYMBOLS = ["BTC", "ETH"]


def _funding_rate(symbol: str) -> float | None:
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
    resp = requests.get(
        f"{BINANCE_FUTURES}/openInterest",
        params={"symbol": f"{symbol}USDT"},
        timeout=10,
    )
    resp.raise_for_status()
    return float(resp.json().get("openInterest", 0))


def _basis(symbol: str) -> float | None:
    """Basis = (futures mark price - spot price) / spot price * 100."""
    spot_r = requests.get(f"{BINANCE_SPOT}/ticker/price",    params={"symbol": f"{symbol}USDT"}, timeout=10)
    fut_r  = requests.get(f"{BINANCE_FUTURES}/ticker/price", params={"symbol": f"{symbol}USDT"}, timeout=10)
    spot_r.raise_for_status()
    fut_r.raise_for_status()
    spot = float(spot_r.json()["price"])
    fut  = float(fut_r.json()["price"])
    return round((fut - spot) / spot * 100, 4)


def _taker_volume(symbol: str) -> dict:
    """24h taker buy vs sell volume from Binance Futures hourly klines.
    taker_buy_ratio > 0.55 = aggressive buyers dominating (bullish pressure)
    taker_buy_ratio < 0.45 = aggressive sellers dominating (bearish pressure)
    Kline fields: [0]=open_time [7]=quote_volume [10]=taker_buy_quote_volume
    """
    resp = requests.get(
        f"{BINANCE_FUTURES}/klines",
        params={"symbol": f"{symbol}USDT", "interval": "1h", "limit": 24},
        timeout=10,
    )
    resp.raise_for_status()
    candles = resp.json()

    total_vol  = sum(float(c[7])  for c in candles)
    taker_buy  = sum(float(c[10]) for c in candles)

    if total_vol == 0:
        return {}

    buy_ratio = round(taker_buy / total_vol, 4)
    return {
        "taker_buy_ratio":  buy_ratio,
        "total_volume_usd": round(total_vol),
        "bias":             "BUYERS" if buy_ratio > 0.55 else ("SELLERS" if buy_ratio < 0.45 else "NEUTRAL"),
    }


def _btc_options_analysis() -> dict:
    """Enhanced BTC options from Deribit:
    - put/call OI ratio
    - OI distribution: ATM (±5%), OTM calls (5-20% above), OTM puts (5-20% below)
    """
    # Get spot price for zone classification
    spot_r = requests.get(f"{BINANCE_SPOT}/ticker/price", params={"symbol": "BTCUSDT"}, timeout=10)
    spot_r.raise_for_status()
    spot = float(spot_r.json()["price"])

    resp = requests.get(
        f"{DERIBIT}/get_book_summary_by_currency",
        params={"currency": "BTC", "kind": "option"},
        timeout=20,
    )
    resp.raise_for_status()
    instruments = resp.json().get("result", [])

    put_oi = call_oi = atm_oi = otm_call_oi = otm_put_oi = 0.0

    for inst in instruments:
        name = inst.get("instrument_name", "")
        oi   = inst.get("open_interest") or 0
        parts = name.split("-")
        if len(parts) < 4:
            continue
        try:
            strike = float(parts[2])
        except ValueError:
            continue

        is_call = name.endswith("-C")
        is_put  = name.endswith("-P")

        if is_call:
            call_oi += oi
        elif is_put:
            put_oi += oi

        pct = (strike - spot) / spot * 100
        if abs(pct) <= 5:
            atm_oi += oi
        elif 5 < pct <= 20:
            otm_call_oi += oi
        elif -20 <= pct < -5:
            otm_put_oi += oi

    return {
        "spot_price":    round(spot),
        "put_call_ratio": round(put_oi / call_oi, 3) if call_oi else None,
        "atm_oi":        round(atm_oi),
        "otm_call_oi":   round(otm_call_oi),
        "otm_put_oi":    round(otm_put_oi),
    }


def get_crypto_derivatives() -> dict:
    """Return funding rates, OI, basis, liquidations for BTC+ETH and BTC options analysis."""
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

        try:
            data["taker_volume"] = _taker_volume(sym)
        except Exception:
            data["taker_volume"] = None

        result[sym] = data

    # BTC enhanced options analysis from Deribit
    try:
        result["BTC"]["options"] = _btc_options_analysis()
    except Exception:
        result["BTC"]["options"] = None

    return result
