import sys
from datetime import datetime
from dotenv import load_dotenv

from fetchers.crypto import (
    get_watchlist_data,
    get_trending_coins,
    get_global_market,
    get_top_categories,
)
from fetchers.stocks import get_indices_data, get_sector_performance
from agent import generate_market_update
from grok_agent import get_x_social_pulse
from telegram_bot import send_message


def _safe_fetch(label: str, fn, fallback):
    """Run a data-fetch function and return fallback on any error."""
    try:
        result = fn()
        print(f"  ✓ {label}")
        return result
    except Exception as e:
        print(f"  ✗ {label} — {e}")
        return fallback


def build_crypto_payload() -> dict:
    print("\nFetching crypto data...")
    return {
        "watchlist": _safe_fetch("Watchlist prices (BTC/SOL/HYPE)", get_watchlist_data, []),
        "trending_coins": _safe_fetch("Trending coins", get_trending_coins, []),
        "global_market": _safe_fetch("Global market stats", get_global_market, {}),
        "categories_by_performance": _safe_fetch("Category narratives", get_top_categories, []),
    }


def build_stock_payload() -> dict:
    print("\nFetching stock data...")
    return {
        "major_indices": _safe_fetch("Major indices", get_indices_data, {}),
        "sector_etfs": _safe_fetch("Sector ETFs", get_sector_performance, {}),
    }


def main():
    load_dotenv()

    date_str = datetime.now().strftime("%A, %B %d %Y")
    print(f"\n{'='*50}")
    print(f"  Market Update Agent — {date_str}")
    print(f"{'='*50}")

    crypto_data = build_crypto_payload()
    stock_data = build_stock_payload()

    print("\nGenerating market analysis with Gemini 2.5...")
    crypto_analysis, stock_analysis = generate_market_update(crypto_data, stock_data)

    print("Fetching X social pulse with Grok...")
    social_pulse = _safe_fetch("X social pulse (Grok)", get_x_social_pulse, "")

    header = f"🗓 *Daily Market Update — {date_str}*\n{'─' * 34}\n\n"
    crypto_msg = header + crypto_analysis
    if social_pulse:
        crypto_msg += "\n\n" + social_pulse

    print("\nSending to Telegram...")
    send_message(crypto_msg)
    if stock_analysis:
        send_message(stock_analysis)

    print("\n✅ Done! Market update sent to Telegram.\n")


if __name__ == "__main__":
    main()
