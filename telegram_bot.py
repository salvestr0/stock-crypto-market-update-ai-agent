import os
import re
import requests

TELEGRAM_API = "https://api.telegram.org"
MAX_MSG_LENGTH = 4000  # Buffer below Telegram's 4096 hard limit


def _split_message(text: str) -> list[str]:
    """Split a long message at newlines to avoid cutting mid-sentence."""
    if len(text) <= MAX_MSG_LENGTH:
        return [text]

    chunks = []
    current = ""
    for line in text.split("\n"):
        candidate = current + line + "\n"
        if len(candidate) > MAX_MSG_LENGTH:
            if current:
                chunks.append(current.strip())
            current = line + "\n"
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _to_telegram_markdown(text: str) -> str:
    """Convert standard markdown to Telegram's legacy Markdown format."""
    # **bold** → *bold*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text, flags=re.DOTALL)
    # Replace * used as a bullet (line starts with optional whitespace then * then space)
    text = re.sub(r'(?m)^(\s*)\*(\s+)', r'\1-\2', text)
    return text


def get_updates(offset: int) -> list:
    """Long-poll Telegram for new updates. Returns list of update dicts, empty list on error."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return []

    url = f"{TELEGRAM_API}/bot{bot_token}/getUpdates"
    params = {"offset": offset, "timeout": 30}

    try:
        response = requests.get(url, params=params, timeout=35)
        if response.ok:
            return response.json().get("result", [])
    except requests.exceptions.RequestException:
        pass

    return []


def send_reply(chat_id: str, text: str) -> None:
    """Send a message to a specific chat_id. Splits if over 4000 chars."""
    text = _to_telegram_markdown(text)
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in your .env file")

    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    chunks = _split_message(text)

    for chunk in chunks:
        payload = {"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=15)

        if not response.ok:
            payload.pop("parse_mode")
            response = requests.post(url, json=payload, timeout=15)
            response.raise_for_status()


def send_photo(chat_id: str, image_bytes: bytes, caption: str = "") -> None:
    """Send a photo to a specific chat_id via multipart/form-data."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in your .env file")

    url = f"{TELEGRAM_API}/bot{bot_token}/sendPhoto"
    caption = caption[:1024]  # Telegram hard limit

    files = {"photo": ("chart.png", image_bytes, "image/png")}
    data = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}

    response = requests.post(url, data=data, files=files, timeout=30)
    if not response.ok:
        # Retry without Markdown if parse failed
        data.pop("parse_mode")
        response = requests.post(url, data=data, files=files, timeout=30)
        response.raise_for_status()


def send_message(text: str) -> None:
    """Send a message to the configured Telegram chat. Splits if over 4000 chars."""
    text = _to_telegram_markdown(text)
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in your .env file"
        )

    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    chunks = _split_message(text)

    for chunk in chunks:
        # Try Markdown first, fall back to plain text if parsing fails
        payload = {"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=15)

        if not response.ok:
            # Telegram rejected the markdown — retry as plain text
            payload.pop("parse_mode")
            response = requests.post(url, json=payload, timeout=15)
            response.raise_for_status()
