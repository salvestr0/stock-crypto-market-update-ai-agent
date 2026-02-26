"""Economic calendar — Forex Factory public JSON (this week + next week).
FRED API key is used for yield curve in macro.py; FF provides the forward-looking calendar.
"""
import requests
from datetime import datetime, date

FF_THIS_WEEK = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
FF_NEXT_WEEK = "https://nfs.faireconomy.media/ff_calendar_nextweek.json"

# Only surface USD events at these impact levels
_WANTED_IMPACT  = {"High", "Medium"}
_WANTED_COUNTRY = "USD"


def _parse_ff_date(raw: str) -> date | None:
    """Parse Forex Factory date strings — handles ISO 8601 with offset and bare dates."""
    raw = raw.strip()
    # ISO 8601 with timezone offset: 2026-02-27T08:30:00-05:00
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        pass
    # Fallback plain formats
    for fmt in ("%Y-%m-%d", "%m-%d-%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _fetch_ff(url: str) -> list[dict]:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_upcoming_events() -> list[dict]:
    """Return upcoming USD high/medium-impact events for this week and next.

    Each event: {date, days_until, name, impact, forecast, previous}
    """
    today = datetime.now().date()
    raw = []

    for url in (FF_THIS_WEEK, FF_NEXT_WEEK):
        try:
            raw.extend(_fetch_ff(url))
        except Exception:
            pass

    events = []
    for ev in raw:
        if ev.get("country") != _WANTED_COUNTRY:
            continue
        if ev.get("impact") not in _WANTED_IMPACT:
            continue

        ev_date = _parse_ff_date(ev.get("date", ""))
        if ev_date is None or ev_date < today:
            continue

        days_until = (ev_date - today).days
        events.append({
            "date":       ev_date.isoformat(),
            "days_until": days_until,
            "name":       ev.get("title", "Unknown"),
            "impact":     ev.get("impact", ""),
            "forecast":   ev.get("forecast", ""),
            "previous":   ev.get("previous", ""),
        })

    # Deduplicate same event on same date, sort by date
    seen = set()
    unique = []
    for ev in sorted(events, key=lambda x: x["date"]):
        key = (ev["date"], ev["name"])
        if key not in seen:
            seen.add(key)
            unique.append(ev)

    return unique[:12]
