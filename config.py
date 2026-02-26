# Crypto watchlist — CoinGecko IDs mapped to display symbols
CRYPTO_WATCHLIST = [
    {"id": "bitcoin", "symbol": "BTC"},
    {"id": "solana", "symbol": "SOL"},
    {"id": "hyperliquid", "symbol": "HYPE"},
]

# Major market indices
STOCK_INDICES = {
    "S&P 500": "SPY",
    "Nasdaq 100": "QQQ",
    "Dow Jones": "DIA",
    "VIX (Fear Index)": "^VIX",
}

# All 11 GICS sector ETFs
SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Energy": "XLE",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communications": "XLC",
}

# Gemini model — swap to "gemini-2.5-pro" for deeper analysis
GEMINI_MODEL = "gemini-2.5-flash"

# Grok model — used for real-time X/social analysis
GROK_MODEL = "grok-3"
