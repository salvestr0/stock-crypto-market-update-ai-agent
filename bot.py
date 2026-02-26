"""Autonomous daemon — scheduler + Telegram polling loop.

Usage: python bot.py
"""
import os
import re
import time
import threading
from collections import deque
from datetime import datetime

# Load env before any os.getenv calls
from dotenv import load_dotenv
load_dotenv()

import schedule

from main import build_crypto_payload, build_stock_payload
from agent import generate_market_update, generate_brain_update, generate_self_review, answer_question, generate_auto_correction
from grok_agent import get_x_social_pulse
from telegram_bot import send_message, get_updates, send_reply, send_photo
from memory import read_file, write_brain, log_review, log_learning
from chart import get_crypto_chart, get_stock_chart

CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
UPDATE_TIME = os.getenv("DAILY_UPDATE_TIME", "07:00")

# Per-chat conversation history — keeps last 10 messages (5 exchanges)
_HISTORY: dict[str, deque] = {}
_MAX_HISTORY = 10


def _history_add(chat_id: str, role: str, content: str) -> None:
    if chat_id not in _HISTORY:
        _HISTORY[chat_id] = deque(maxlen=_MAX_HISTORY)
    _HISTORY[chat_id].append({"role": role, "content": content})


def _history_get(chat_id: str) -> list[dict]:
    return list(_HISTORY.get(chat_id, []))


# ---------------------------------------------------------------------------
# Scheduled jobs
# ---------------------------------------------------------------------------

def run_full_update():
    """Fetch data, generate analysis, update BRAIN.md, send to Telegram."""
    try:
        date_str = datetime.now().strftime("%A, %B %d %Y")
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running full update...")

        # Read previous brain BEFORE fetching new data — used for self-correction
        old_brain = read_file("BRAIN.md")

        crypto_data = build_crypto_payload()
        stock_data = build_stock_payload()

        # Auto-correction: compare old hypotheses against fresh data
        print("  Checking previous hypotheses for corrections...")
        try:
            corrections = generate_auto_correction(old_brain, crypto_data, stock_data)
            if corrections:
                for c in corrections:
                    title = c.get("title", "Unknown")
                    entry = (
                        f"**What I said:** {c.get('what_i_said', '')}\n"
                        f"**What happened:** {c.get('what_happened', '')}\n"
                        f"**Root cause:** {c.get('root_cause', '')}\n"
                        f"**Rule update:** {c.get('rule_update', '')}\n"
                        f"**Category:** {c.get('category', '')}"
                    )
                    log_learning(title, entry)
                    print(f"  ✓ Logged correction: {title}")

                summary_lines = "\n".join(f"- {c.get('title', '')}" for c in corrections)
                send_message(f"🧠 *Sarah self-corrected {len(corrections)} hypothesis(es):*\n{summary_lines}")
            else:
                print("  ✓ No corrections needed")
        except Exception as e:
            print(f"  ✗ Auto-correction check failed: {e}")

        print("  Generating analysis with Gemini...")
        crypto_analysis, stock_analysis = generate_market_update(crypto_data, stock_data)

        social_pulse = ""
        try:
            print("  Fetching X social pulse with Grok...")
            social_pulse = get_x_social_pulse()
        except Exception as e:
            print(f"  ✗ X social pulse — {e}")

        # Update BRAIN.md with live market state
        print("  Updating BRAIN.md...")
        brain_content = generate_brain_update(crypto_data, stock_data, crypto_analysis + "\n\n" + stock_analysis)
        write_brain(brain_content)
        print("  ✓ BRAIN.md updated")

        # Message 1: Crypto
        header = f"🗓 *Daily Market Update — {date_str}*\n{'─' * 34}\n\n"
        crypto_msg = header + crypto_analysis
        if social_pulse:
            crypto_msg += "\n\n" + social_pulse
        send_message(crypto_msg)

        # Message 2: Stocks
        if stock_analysis:
            send_message(stock_analysis)

        print("  ✓ Sent to Telegram")

    except Exception as e:
        print(f"  ✗ run_full_update failed: {e}")
        try:
            send_message(f"⚠️ Full update failed: {e}")
        except Exception:
            pass


def run_self_review():
    """Read BRAIN.md, generate review entry, log to SELF-REVIEW.md, send summary."""
    try:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running self-review...")
        brain = read_file("BRAIN.md")
        entry = generate_self_review(brain)
        log_review(entry)
        print("  ✓ SELF-REVIEW.md updated")

        summary = entry[:1000] + ("..." if len(entry) > 1000 else "")
        send_message(f"🔍 *Self-Review Complete*\n\n{summary}")

    except Exception as e:
        print(f"  ✗ run_self_review failed: {e}")


# ---------------------------------------------------------------------------
# Chart detection + handling
# ---------------------------------------------------------------------------

# Bare tickers recognised without a $ prefix
_BARE_TICKERS = {
    "BTC", "ETH", "SOL", "HYPE", "DOGE", "XRP", "AVAX", "BNB", "ADA",
    "MATIC", "DOT", "LINK", "LTC", "BCH", "NEAR", "APT", "ARB", "OP",
    "SUI", "WIF", "PEPE", "BONK", "SEI", "INJ", "TIA", "SPY", "QQQ",
    "AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "META", "GOOGL",
}

# Words that signal a price/chart intent
_CHART_TRIGGERS = re.compile(
    r"\b(price|chart|how much|what is|show|current|now|candle|graph|plot)\b",
    re.IGNORECASE,
)

# Timeframe patterns
_TIMEFRAME_RE = re.compile(
    r"\b(1m|5m|15m|30m|1h|4h|1d|daily|hourly)\b",
    re.IGNORECASE,
)

_TIMEFRAME_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "hourly": "1h",
    "4h": "4h",
    "1d": "1d", "daily": "1d",
}


def _detect_chart_request(text: str) -> dict | None:
    """Return {symbol, interval} if text looks like a price/chart query, else None."""
    # Check for $SYMBOL
    dollar_match = re.search(r"\$([A-Za-z]{2,6})", text)
    bare_match = None

    if not dollar_match:
        # Check for bare known tickers
        words = re.findall(r"\b([A-Za-z]{2,6})\b", text)
        for w in words:
            if w.upper() in _BARE_TICKERS:
                bare_match = w.upper()
                break

    symbol = None
    if dollar_match:
        symbol = dollar_match.group(1).upper()
    elif bare_match:
        symbol = bare_match

    if not symbol:
        return None

    # $ prefix alone is enough; otherwise need a trigger word
    if not dollar_match and not _CHART_TRIGGERS.search(text):
        return None

    # Extract timeframe
    tf_match = _TIMEFRAME_RE.search(text)
    interval = _TIMEFRAME_MAP.get(tf_match.group(1).lower(), "1h") if tf_match else "1h"

    return {"symbol": symbol, "interval": interval}


def _handle_chart_request(chat_id: str, symbol: str, interval: str):
    """Fetch OHLCV chart and send as photo to chat_id."""
    send_reply(chat_id, f"📊 Fetching {symbol} {interval} chart...")

    # Try crypto first
    try:
        img, caption = get_crypto_chart(symbol, interval)
        send_photo(chat_id, img, caption)
        return
    except Exception as crypto_err:
        pass

    # Fallback to stocks
    try:
        img, caption = get_stock_chart(symbol, interval)
        send_photo(chat_id, img, caption)
        return
    except Exception as stock_err:
        pass

    send_reply(
        chat_id,
        f"❌ Couldn't find *{symbol}*. Try $BTC, $SOL, $HYPE, $AAPL, $SPY",
    )


# ---------------------------------------------------------------------------
# Message handling
# ---------------------------------------------------------------------------

def _handle_ask(chat_id: str, question: str):
    """Answer a freeform question using agent context and conversation history."""
    try:
        soul      = read_file("SOUL.md")
        brain     = read_file("BRAIN.md")
        learnings = read_file("LEARNINGS.md")
        history   = _history_get(chat_id)

        _history_add(chat_id, "user", question)
        answer = answer_question(question, soul, brain, learnings, history)
        _history_add(chat_id, "assistant", answer)

        send_reply(chat_id, answer)
    except Exception as e:
        send_reply(chat_id, f"⚠️ Error answering question: {e}")


def handle_message(chat_id: str, text: str):
    """Route incoming Telegram message to the appropriate handler."""
    text = text.strip()
    cmd = text.lower()

    if cmd == "/help":
        reply = (
            "🤖 *Market Agent Commands*\n\n"
            "/update — Run full market update now\n"
            "/brain — View current BRAIN.md state\n"
            "/review — Trigger self-review now\n"
            "/learnings — View active trading rules\n"
            "/ask <question> — Ask the agent anything\n"
            "/chart <SYMBOL> [interval] — Price chart (e.g. /chart HYPE 5m)\n\n"
            "*Chart shortcuts:*\n"
            "  `$BTC` `$SOL 4h` `$HYPE 5m` — send $SYMBOL to get a chart\n"
            "  _Or ask: \"What is AAPL price?\", \"Show BTC 1h chart\"_\n\n"
            "_Intervals: 1m 5m 15m 30m 1h 4h 1d (default: 1h)_"
        )
        send_reply(chat_id, reply)

    elif cmd == "/update":
        send_reply(chat_id, "⚙️ Running full update...")
        run_full_update()

    elif cmd == "/brain":
        brain = read_file("BRAIN.md")
        truncated = brain[:3500] + ("..." if len(brain) > 3500 else "")
        send_reply(chat_id, truncated)

    elif cmd == "/review":
        send_reply(chat_id, "🔍 Running self-review...")
        run_self_review()

    elif cmd == "/learnings":
        learnings = read_file("LEARNINGS.md")
        start = learnings.find("## Active Rules")
        end = learnings.find("## Mistake Log")
        if start != -1 and end != -1:
            section = learnings[start:end].strip()
        elif start != -1:
            section = learnings[start:start + 3000].strip()
        else:
            section = learnings[:3000]
        send_reply(chat_id, section)

    elif cmd.startswith("/ask "):
        question = text[5:].strip()
        _handle_ask(chat_id, question)

    elif cmd.startswith("/chart"):
        # /chart SYMBOL [interval]
        parts = text.split()[1:]  # drop "/chart"
        if not parts:
            send_reply(chat_id, "Usage: /chart <SYMBOL> [interval]\nExample: /chart BTC 4h")
            return
        symbol = parts[0].lstrip("$").upper()
        interval = _TIMEFRAME_MAP.get(parts[1].lower(), "1h") if len(parts) > 1 else "1h"
        _handle_chart_request(chat_id, symbol, interval)

    else:
        # Chart detection — before freeform fallback
        chart_req = _detect_chart_request(text)
        if chart_req:
            _handle_chart_request(chat_id, chart_req["symbol"], chart_req["interval"])
        else:
            # Treat anything unrecognised as a freeform question
            _handle_ask(chat_id, text)


# ---------------------------------------------------------------------------
# Polling loop
# ---------------------------------------------------------------------------

def polling_loop():
    """Main Telegram long-polling loop. Runs in the main thread."""
    offset = 0
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Polling for messages (chat_id filter: {CHAT_ID})...")

    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message") or update.get("edited_message")
            if not message:
                continue

            chat_id = str(message.get("chat", {}).get("id", ""))
            text = message.get("text", "")

            if not text:
                continue

            # Security: only respond to the configured chat
            if chat_id != str(CHAT_ID):
                print(f"  ⚠ Ignored message from unknown chat_id {chat_id}")
                continue

            print(f"  → [{datetime.now().strftime('%H:%M:%S')}] {text[:80]}")
            try:
                handle_message(chat_id, text)
            except Exception as e:
                print(f"  ✗ handle_message error: {e}")


# ---------------------------------------------------------------------------
# Scheduler thread
# ---------------------------------------------------------------------------

def _scheduler_thread():
    """Run the schedule loop in a background daemon thread."""
    schedule.every().day.at(UPDATE_TIME).do(run_full_update)
    schedule.every(4).hours.do(run_self_review)

    print(f"[Scheduler] Daily update at {UPDATE_TIME} | Self-review every 4h")

    while True:
        schedule.run_pending()
        time.sleep(30)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("🤖 Market Agent starting...")
    print(f"  Daily update time : {UPDATE_TIME}")
    print(f"  Self-review period: every 4h")
    print(f"  Telegram chat ID  : {CHAT_ID}")

    # Start scheduler in background
    t = threading.Thread(target=_scheduler_thread, daemon=True)
    t.start()

    # Send startup notification
    try:
        send_message("👋 Sarah online. /help for commands.")
        print("  ✓ Startup notification sent")
    except Exception as e:
        print(f"  ✗ Startup notification failed: {e}")

    # Block forever in polling loop
    polling_loop()
