import yfinance as yf
from config import STOCK_INDICES, SECTOR_ETFS


def _fetch_ticker_performance(ticker: str, period: str = "5d") -> dict:
    """Return 1d and 5d percentage change for a given ticker."""
    t = yf.Ticker(ticker)
    hist = t.history(period=period)

    if len(hist) < 2:
        return {"ticker": ticker, "error": "insufficient data"}

    prev_close = hist["Close"].iloc[-2]
    current = hist["Close"].iloc[-1]
    change_1d = ((current - prev_close) / prev_close) * 100

    first = hist["Close"].iloc[0]
    change_5d = ((current - first) / first) * 100

    return {
        "ticker": ticker,
        "price": round(float(current), 2),
        "change_1d_pct": round(float(change_1d), 2),
        "change_5d_pct": round(float(change_5d), 2),
    }


def get_indices_data() -> dict:
    """Fetch performance for major market indices."""
    results = {}
    for name, ticker in STOCK_INDICES.items():
        try:
            results[name] = _fetch_ticker_performance(ticker)
        except Exception as e:
            results[name] = {"ticker": ticker, "error": str(e)}
    return results


def get_sector_performance() -> dict:
    """Fetch 1d and 5d performance for all 11 GICS sector ETFs."""
    results = {}
    for sector, ticker in SECTOR_ETFS.items():
        try:
            results[sector] = _fetch_ticker_performance(ticker)
        except Exception as e:
            results[sector] = {"ticker": ticker, "error": str(e)}
    return results
