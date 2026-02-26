"""File I/O layer for all .md memory files. No AI logic here."""
import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent

_CONV_FILE      = BASE_DIR / "conversation_history.json"
_SOUL_TRACKER   = BASE_DIR / "soul_tracker.json"
_MAX_STORED     = 80   # messages kept on disk per chat
_MAX_IN_PROMPT  = 20   # messages passed into the AI prompt (keeps tokens manageable)
_SOUL_CORRECTION_THRESHOLD = 5   # corrections before SOUL.md refinement triggers
_SOUL_DAY_THRESHOLD        = 3   # minimum days between soul updates


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


def update_active_rules(new_rules_section: str) -> None:
    """Replace the ## Active Rules section in LEARNINGS.md with new content.

    new_rules_section should start with '## Active Rules (Current Best Version)'
    and contain all rules. The trailing '---' separator is added automatically.
    """
    path = BASE_DIR / "LEARNINGS.md"
    content = path.read_text(encoding="utf-8")

    start_marker = "## Active Rules (Current Best Version)"
    end_marker   = "## Mistake Log"

    start_idx = content.find(start_marker)
    end_idx   = content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        return  # Can't safely locate section — leave file untouched

    updated = (
        content[:start_idx]
        + new_rules_section.rstrip()
        + "\n\n---\n\n"
        + content[end_idx:]
    )
    path.write_text(updated, encoding="utf-8")


def update_soul(new_content: str) -> None:
    """Overwrite SOUL.md with refined content."""
    (BASE_DIR / "SOUL.md").write_text(new_content.rstrip() + "\n", encoding="utf-8")


def record_soul_correction() -> None:
    """Increment the correction counter that gates SOUL.md refinement."""
    try:
        data = _load_soul_tracker()
        data["corrections_since_last_update"] = data.get("corrections_since_last_update", 0) + 1
        _SOUL_TRACKER.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def should_update_soul() -> bool:
    """Return True when enough corrections have accumulated and enough days have passed."""
    try:
        data  = _load_soul_tracker()
        count = data.get("corrections_since_last_update", 0)
        if count < _SOUL_CORRECTION_THRESHOLD:
            return False
        last_str = data.get("last_update_date", "")
        if last_str:
            last = datetime.fromisoformat(last_str)
            # Make offset-naive for comparison if needed
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            days_elapsed = (datetime.now(timezone.utc) - last).days
            if days_elapsed < _SOUL_DAY_THRESHOLD:
                return False
        return True
    except Exception:
        return False


def mark_soul_updated() -> None:
    """Reset the correction counter and stamp today as the last soul update."""
    try:
        data = _load_soul_tracker()
        data["corrections_since_last_update"] = 0
        data["last_update_date"] = datetime.now(timezone.utc).isoformat()
        _SOUL_TRACKER.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load_soul_tracker() -> dict:
    if not _SOUL_TRACKER.exists():
        return {}
    try:
        return json.loads(_SOUL_TRACKER.read_text(encoding="utf-8"))
    except Exception:
        return {}


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
