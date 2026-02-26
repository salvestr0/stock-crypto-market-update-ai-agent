import requests
from config import CRYPTO_WATCHLIST

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
HEADERS = {"accept": "application/json"}


def get_watchlist_data() -> list:
    """Fetch price, market cap, and performance for the watchlist coins."""
    ids = ",".join(c["id"] for c in CRYPTO_WATCHLIST)
    url = f"{COINGECKO_BASE}/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ids,
        "order": "market_cap_desc",
        "sparkline": False,
        "price_change_percentage": "24h,7d",
    }
    response = requests.get(url, params=params, headers=HEADERS, timeout=15)
    response.raise_for_status()
    raw = response.json()

    result = []
    for coin in raw:
        result.append({
            "name": coin.get("name"),
            "symbol": coin.get("symbol", "").upper(),
            "price_usd": coin.get("current_price"),
            "market_cap_usd": coin.get("market_cap"),
            "market_cap_rank": coin.get("market_cap_rank"),
            "change_24h_pct": coin.get("price_change_percentage_24h"),
            "change_7d_pct": coin.get("price_change_percentage_7d_in_currency"),
            "volume_24h_usd": coin.get("total_volume"),
            "ath_usd": coin.get("ath"),
            "ath_change_pct": coin.get("ath_change_percentage"),
        })
    return result


def get_trending_coins() -> list:
    """Fetch the top trending coins on CoinGecko right now."""
    url = f"{COINGECKO_BASE}/search/trending"
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    coins = response.json().get("coins", [])[:7]

    result = []
    for item in coins:
        c = item.get("item", {})
        result.append({
            "name": c.get("name"),
            "symbol": c.get("symbol"),
            "market_cap_rank": c.get("market_cap_rank"),
            "score": c.get("score"),
        })
    return result


def get_global_market() -> dict:
    """Fetch global crypto market statistics."""
    url = f"{COINGECKO_BASE}/global"
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    data = response.json().get("data", {})

    return {
        "total_market_cap_usd": data.get("total_market_cap", {}).get("usd"),
        "total_volume_24h_usd": data.get("total_volume", {}).get("usd"),
        "btc_dominance_pct": round(data.get("market_cap_percentage", {}).get("btc", 0), 2),
        "eth_dominance_pct": round(data.get("market_cap_percentage", {}).get("eth", 0), 2),
        "market_cap_change_24h_pct": data.get("market_cap_change_percentage_24h_usd"),
        "active_cryptocurrencies": data.get("active_cryptocurrencies"),
    }


def get_top_categories() -> list:
    """Fetch crypto categories ranked by 24h market cap change — reveals narrative flows."""
    url = f"{COINGECKO_BASE}/coins/categories"
    params = {"order": "market_cap_change_24h_desc"}
    response = requests.get(url, params=params, headers=HEADERS, timeout=15)
    response.raise_for_status()
    data = response.json()

    result = []
    for cat in data[:20]:
        result.append({
            "name": cat.get("name"),
            "market_cap_usd": cat.get("market_cap"),
            "change_24h_pct": cat.get("market_cap_change_24h"),
            "volume_24h_usd": cat.get("volume_24h"),
            "top_3_coins": cat.get("top_3_coins", []),
        })
    return result
