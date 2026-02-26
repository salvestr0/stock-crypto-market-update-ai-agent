"""File I/O layer for all .md memory files. No AI logic here."""
import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent

_CONV_FILE      = BASE_DIR / "conversation_history.json"
_MAX_STORED     = 80   # messages kept on disk per chat
_MAX_IN_PROMPT  = 20   # messages passed into the AI prompt (keeps tokens manageable)


def read_file(name: str) -> str:
    """Read a .md file from the project directory. Returns empty string if missing."""
    path = BASE_DIR / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_brain(content: str) -> None:
    """Overwrite BRAIN.md entirely — it's live state, not a log."""
    (BASE_DIR / "BRAIN.md").write_text(content, encoding="utf-8")


def log_review(entry: str) -> None:
    """Prepend a review entry to SELF-REVIEW.md immediately after the log marker."""
    _prepend_to_log("SELF-REVIEW.md", "<!-- Most recent review at the top -->", entry)


def log_learning(title: str, entry: str) -> None:
    """Prepend a mistake/learning entry to LEARNINGS.md after the log marker."""
    formatted = f"### {title}\n\n{entry}"
    _prepend_to_log("LEARNINGS.md", "<!-- Most recent first -->", formatted)


def load_conversation(chat_id: str) -> list[dict]:
    """Load persisted conversation history for a chat_id.
    Returns the last _MAX_IN_PROMPT messages for use in the AI prompt.
    """
    if not _CONV_FILE.exists():
        return []
    try:
        data = json.loads(_CONV_FILE.read_text(encoding="utf-8"))
        messages = data.get(str(chat_id), [])
        return messages[-_MAX_IN_PROMPT:]
    except (json.JSONDecodeError, Exception):
        return []


def save_message(chat_id: str, role: str, content: str) -> None:
    """Append a single message to the persisted conversation history."""
    try:
        data = {}
        if _CONV_FILE.exists():
            try:
                data = json.loads(_CONV_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception):
                data = {}

        key = str(chat_id)
        if key not in data:
            data[key] = []

        data[key].append({
            "role":      role,
            "content":   content,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        })

        # Trim to max stored length
        data[key] = data[key][-_MAX_STORED:]

        _CONV_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass  # Never let a save failure break the conversation


def _prepend_to_log(filename: str, marker: str, entry: str) -> None:
    """Find marker comment in file and insert entry immediately after it."""
    path = BASE_DIR / filename
    content = path.read_text(encoding="utf-8")

    idx = content.find(marker)
    if idx == -1:
        # Marker not found — append to end rather than silently failing
        path.write_text(content.rstrip() + "\n\n" + entry + "\n", encoding="utf-8")
        return

    insert_at = idx + len(marker)
    updated = content[:insert_at] + "\n\n" + entry + "\n" + content[insert_at:]
    path.write_text(updated, encoding="utf-8")
