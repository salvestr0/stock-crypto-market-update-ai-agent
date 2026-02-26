"""Chart generation — OHLCV fetching + mplfinance TradingView-style candlestick charts.

Data sources:
  - Binance  (primary crypto, no auth)
  - CoinGecko (fallback for non-Binance tokens like HYPE)
  - yfinance  (stocks)
"""
import io
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")  # headless / Windows — must be before any other matplotlib import
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import mplfinance as mpf
import pandas as pd
import requests
import yfinance as yf

# ---------------------------------------------------------------------------
# Interval helpers
# ---------------------------------------------------------------------------

# Binance interval strings
_BINANCE_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}

# CoinGecko: how many days of history to request for each interval
_COINGECKO_DAYS = {
    "1m":  1,
    "5m":  1,
    "15m": 2,
    "30m": 3,
    "1h":  7,
    "4h":  30,
    "1d":  90,
}

# Resample freq for CoinGecko ticks → OHLCV
_RESAMPLE_FREQ = {
    "1m":  "1min",
    "5m":  "5min",
    "15m": "15min",
    "30m": "30min",
    "1h":  "1h",
    "4h":  "4h",
    "1d":  "1D",
}

# yfinance (period, interval) pairs
_YF_PARAMS = {
    "1m":  ("1d",  "1m"),
    "5m":  ("5d",  "5m"),
    "15m": ("5d",  "15m"),
    "30m": ("1mo", "30m"),
    "1h":  ("1mo", "1h"),
    "4h":  ("3mo", "1h"),   # fetch 1h then resample to 4H
    "1d":  ("1y",  "1d"),
}

# Known CoinGecko IDs for common tickers
_COINGECKO_IDS = {
    "BTC":  "bitcoin",
    "ETH":  "ethereum",
    "SOL":  "solana",
    "BNB":  "binancecoin",
    "XRP":  "ripple",
    "ADA":  "cardano",
    "AVAX": "avalanche-2",
    "DOGE": "dogecoin",
    "DOT":  "polkadot",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "UNI":  "uniswap",
    "ATOM": "cosmos",
    "LTC":  "litecoin",
    "BCH":  "bitcoin-cash",
    "NEAR": "near",
    "APT":  "aptos",
    "ARB":  "arbitrum",
    "OP":   "optimism",
    "SUI":  "sui",
    "HYPE": "hyperliquid",
    "WIF":  "dogwifcoin",
    "PEPE": "pepe",
    "BONK": "bonk",
    "SEI":  "sei-network",
    "INJ":  "injective-protocol",
    "TIA":  "celestia",
    "PYTH": "pyth-network",
    "JTO":  "jito-governance-token",
}

# ---------------------------------------------------------------------------
# Chart style
# ---------------------------------------------------------------------------

def _make_style():
    """TradingView-inspired dark style."""
    return mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mpf.make_marketcolors(
            up="#26a69a",
            down="#ef5350",
            edge={"up": "#26a69a", "down": "#ef5350"},
            wick={"up": "#26a69a", "down": "#ef5350"},
            volume={"up": "#26a69a55", "down": "#ef535055"},
        ),
        facecolor="#131722",
        figcolor="#131722",
        gridcolor="#1e222d",
        gridstyle="--",
        gridaxis="both",
        y_on_right=True,
        rc={
            "axes.labelcolor": "#b2b5be",
            "xtick.color": "#b2b5be",
            "ytick.color": "#b2b5be",
            "axes.edgecolor": "#2a2e39",
        },
    )


# ---------------------------------------------------------------------------
# Binance OHLCV
# ---------------------------------------------------------------------------

def _fetch_binance(symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
    """Fetch OHLCV from Binance. Raises on failure."""
    if interval not in _BINANCE_INTERVALS:
        raise ValueError(f"Unsupported Binance interval: {interval}")

    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": f"{symbol.upper()}USDT", "interval": interval, "limit": limit}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if not data or isinstance(data, dict):
        raise ValueError(f"No Binance data for {symbol}")

    df = pd.DataFrame(data, columns=[
        "open_time", "Open", "High", "Low", "Close", "Volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore",
    ])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index("open_time")
    df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
    df.index.name = "Date"
    return df


# ---------------------------------------------------------------------------
# CoinGecko OHLCV
# ---------------------------------------------------------------------------

def _coingecko_id(symbol: str) -> str:
    """Return CoinGecko coin ID for a ticker symbol. Raises if not found."""
    sym = symbol.upper()
    if sym in _COINGECKO_IDS:
        return _COINGECKO_IDS[sym]

    # Try search endpoint
    url = "https://api.coingecko.com/api/v3/search"
    resp = requests.get(url, params={"query": symbol}, timeout=10)
    resp.raise_for_status()
    coins = resp.json().get("coins", [])
    if not coins:
        raise ValueError(f"CoinGecko: no coin found for {symbol}")

    # Prefer exact symbol match
    for coin in coins:
        if coin.get("symbol", "").upper() == sym:
            return coin["id"]
    return coins[0]["id"]


def _fetch_coingecko(symbol: str, interval: str) -> pd.DataFrame:
    """Fetch price ticks from CoinGecko and resample to OHLCV. Raises on failure."""
    coin_id = _coingecko_id(symbol)
    days = _COINGECKO_DAYS.get(interval, 7)
    freq = _RESAMPLE_FREQ.get(interval, "1h")

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    prices = resp.json().get("prices", [])

    if not prices:
        raise ValueError(f"CoinGecko: no price data for {symbol}")

    ts = pd.DataFrame(prices, columns=["timestamp", "price"])
    ts["timestamp"] = pd.to_datetime(ts["timestamp"], unit="ms", utc=True)
    ts = ts.set_index("timestamp")

    # Resample ticks → OHLCV
    ohlcv = ts["price"].resample(freq).agg(
        Open="first", High="max", Low="min", Close="last"
    ).dropna()

    # Synthetic volume (proportional to price range)
    ohlcv["Volume"] = (ohlcv["High"] - ohlcv["Low"]) / ohlcv["Close"] * 1_000_000

    ohlcv.index.name = "Date"
    return ohlcv


# ---------------------------------------------------------------------------
# yfinance OHLCV
# ---------------------------------------------------------------------------

def _fetch_yfinance(ticker: str, interval: str) -> pd.DataFrame:
    """Fetch OHLCV from yfinance. Raises on failure."""
    period, yf_interval = _YF_PARAMS.get(interval, ("1mo", "1h"))
    resample_to_4h = interval == "4h"

    tk = yf.Ticker(ticker.upper())
    df = tk.history(period=period, interval=yf_interval)

    if df.empty:
        raise ValueError(f"yfinance: no data for {ticker}")

    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()

    # Strip timezone so mplfinance doesn't complain
    if hasattr(df.index, "tz") and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index.name = "Date"

    if resample_to_4h:
        df = df.resample("4h").agg(
            Open="first", High="max", Low="min", Close="last", Volume="sum"
        ).dropna()

    return df


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------

def _build_chart(df: pd.DataFrame, title: str, current_price: float) -> bytes:
    """Render a TradingView-style candlestick chart. Returns PNG bytes."""
    style = _make_style()

    # Adaptive MAs — skip if not enough rows
    mav = []
    if len(df) >= 50:
        mav = [20, 50]
    elif len(df) >= 20:
        mav = [20]

    # Current price dashed line (must be a Series with same index as df)
    price_line = pd.Series([current_price] * len(df), index=df.index)
    ap = [mpf.make_addplot(
        price_line,
        color="#ffd700",
        linestyle="--",
        width=1.0,
        secondary_y=False,
    )]

    fig, axes = mpf.plot(
        df,
        type="candle",
        style=style,
        title=f"  {title}",
        volume=True,
        mav=mav if mav else None,
        addplot=ap,
        figsize=(12, 7),
        returnfig=True,
        tight_layout=True,
    )

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close("all")
    buf.seek(0)
    return buf.read()


def _format_caption(symbol: str, current_price: float, prev_price: float, interval: str) -> str:
    """Build Telegram caption with price, change %, and interval label."""
    change_pct = ((current_price - prev_price) / prev_price * 100) if prev_price else 0
    arrow = "▲" if change_pct >= 0 else "▼"
    sign = "+" if change_pct >= 0 else ""

    if current_price >= 1000:
        price_str = f"${current_price:,.2f}"
    elif current_price >= 1:
        price_str = f"${current_price:.4f}".rstrip("0").rstrip(".")
    else:
        price_str = f"${current_price:.6f}".rstrip("0").rstrip(".")

    return f"*{symbol.upper()}* — {price_str}  {arrow} {sign}{change_pct:.2f}% ({interval} chart)"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_crypto_chart(symbol: str, interval: str = "1h") -> tuple[bytes, str]:
    """Fetch crypto OHLCV and return (png_bytes, caption).

    Tries Binance first; falls back to CoinGecko on failure.
    """
    interval = interval.lower()
    df = None
    errors = []

    # 1. Binance
    try:
        df = _fetch_binance(symbol, interval)
    except Exception as e:
        errors.append(f"Binance: {e}")

    # 2. CoinGecko fallback
    if df is None:
        try:
            df = _fetch_coingecko(symbol, interval)
        except Exception as e:
            errors.append(f"CoinGecko: {e}")

    if df is None or df.empty:
        raise ValueError(f"No crypto data for {symbol}: {'; '.join(errors)}")

    current_price = float(df["Close"].iloc[-1])
    prev_price = float(df["Open"].iloc[0])
    title = f"{symbol.upper()} / USDT  |  {interval}"
    png = _build_chart(df, title, current_price)
    caption = _format_caption(symbol, current_price, prev_price, interval)
    return png, caption


def get_stock_chart(ticker: str, interval: str = "1h") -> tuple[bytes, str]:
    """Fetch stock OHLCV from yfinance and return (png_bytes, caption)."""
    interval = interval.lower()
    df = _fetch_yfinance(ticker, interval)

    current_price = float(df["Close"].iloc[-1])
    prev_price = float(df["Open"].iloc[0])
    title = f"{ticker.upper()}  |  {interval}"
    png = _build_chart(df, title, current_price)
    caption = _format_caption(ticker, current_price, prev_price, interval)
    return png, caption
