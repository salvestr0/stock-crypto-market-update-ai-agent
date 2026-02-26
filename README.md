# Sarah — AI Market Intelligence Agent

Sarah is an autonomous market agent that delivers daily crypto and stock briefings to Telegram, answers freeform questions, generates live price charts, and self-corrects her own hypotheses over time.

---

## What Sarah Does

- **Daily briefings** — scheduled market update split into two Telegram messages: one for crypto, one for stocks
- **Live charts** — candlestick charts on demand for any crypto or stock (`$BTC`, `$HYPE 5m`, `/chart AAPL 1h`)
- **Self-review** — every 4 hours she audits her own market calls and flags shaky hypotheses
- **Self-correction** — at each update run she compares her previous predictions against fresh data and automatically logs mistakes to `LEARNINGS.md`
- **Q&A** — ask her anything via Telegram and she answers from her live market state

---

## Architecture

```
bot.py              Daemon entry point — scheduler thread + Telegram polling loop
main.py             One-shot run (no polling)
agent.py            All Gemini AI calls (analysis, brain update, self-review, Q&A, auto-correction)
grok_agent.py       Grok/xAI — real-time X/social pulse
chart.py            OHLCV fetching + mplfinance candlestick chart generation
telegram_bot.py     Telegram HTTP helpers (send_message, send_reply, send_photo, get_updates)
memory.py           File I/O for .md memory files
config.py           Watchlist, indices, sector ETFs, model constants
fetchers/
  crypto.py         CoinGecko — prices, trending, global stats, category narratives
  stocks.py         yfinance — major indices, sector ETFs
```

### Memory files

| File | Purpose |
|------|---------|
| `BRAIN.md` | Live market state — overwritten every run |
| `SOUL.md` | Sarah's identity, expertise, and trading mindset |
| `LEARNINGS.md` | Auto-updated mistake log + active trading rules |
| `SELF-REVIEW.md` | 4-hourly self-audit log |

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a `.env` file

```env
GEMINI_API_KEY=your_gemini_api_key
XAI_API_KEY=your_xai_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
DAILY_UPDATE_TIME=07:00
```

- **Gemini** — [Google AI Studio](https://aistudio.google.com)
- **xAI (Grok)** — [console.x.ai](https://console.x.ai)
- **Telegram bot** — create via [@BotFather](https://t.me/BotFather), get your chat ID from [@userinfobot](https://t.me/userinfobot)

### 3. Run

```bash
python bot.py
```

For a one-shot update without the polling loop:

```bash
python main.py
```

---

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/update` | Run a full market update now |
| `/brain` | View Sarah's current live market state |
| `/review` | Trigger a self-review now |
| `/learnings` | View her active trading rules |
| `/ask <question>` | Ask Sarah anything |
| `/chart <SYMBOL> [interval]` | Get a candlestick chart |
| `/help` | Show all commands |

### Live charts

Send any of the following and Sarah will reply with a chart:

```
$BTC
$HYPE 5m
$SOL 4h
/chart AAPL 1h
What is ETH price?
Show me a BTC daily chart
```

**Supported intervals:** `1m` `5m` `15m` `30m` `1h` `4h` `1d`

**Chart data sources:**
- Binance (primary crypto)
- CoinGecko (fallback — covers tokens not on Binance like HYPE)
- yfinance (stocks)

---

## How Sarah Self-Learns

Every update run Sarah:

1. Reads her previous `BRAIN.md` (last run's hypotheses and regime calls)
2. Fetches fresh market data
3. Asks Gemini: *were any of those hypotheses clearly invalidated by what actually happened?*
4. Logs each confirmed mistake to `LEARNINGS.md` with root cause and a rule update
5. Sends a Telegram notification summarising what she got wrong

Every 4 hours she also runs a self-review that stress-tests her active hypotheses and flags which calls look shaky — before the market proves her wrong.

Her `LEARNINGS.md` active rules are fed back into every `/ask` response, so her answers improve over time.

---

## Customisation

**Change the watchlist** — edit `CRYPTO_WATCHLIST` in `config.py`

**Swap the AI model** — edit `GEMINI_MODEL` in `config.py`
- `gemini-2.5-flash` — fast, cheap (default)
- `gemini-2.5-pro` — deeper reasoning

**Change the update schedule** — set `DAILY_UPDATE_TIME` in `.env` (24h format, e.g. `08:30`)

**Edit Sarah's persona** — modify `SOUL.md` directly
