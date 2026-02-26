"""File I/O layer for all .md memory files. No AI logic here."""
from pathlib import Path

BASE_DIR = Path(__file__).parent


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
