"""Economic calendar — Forex Factory public JSON (this week + next week).
FRED API key is used for yield curve in macro.py; FF provides the forward-looking calendar.
"""
import requests
from datetime import datetime, date

FF_THIS_WEEK = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
FF_NEXT_WEEK = "https://nfs.faireconomy.media/ff_calendar_nextweek.json"

_WANTED_IMPACT  = {"High", "Medium"}
_WANTED_COUNTRY = "USD"

# UTC offset → timezone label (US economic data is always Eastern Time)
_OFFSET_LABEL = {-5: "ET", -4: "ET", -6: "CT", -7: "MT", -8: "PT"}


def _parse_ff_event(raw: str) -> tuple[date | None, str | None, str | None]:
    """Parse a FF date string. Returns (date, time_str, timezone_label).
    Example input: '2026-02-27T08:30:00-05:00'
    Example output: (date(2026,2,27), '8:30 AM', 'ET')
    """
    raw = raw.strip()
    try:
        dt = datetime.fromisoformat(raw)
        ev_date  = dt.date()
        time_str = dt.strftime("%I:%M %p").lstrip("0") or "12:00 AM"  # strip leading zero

        tz_label = None
        if dt.utcoffset() is not None:
            offset_h = int(dt.utcoffset().total_seconds() / 3600)
            tz_label = _OFFSET_LABEL.get(offset_h, f"UTC{offset_h:+d}")

        return ev_date, time_str, tz_label
    except ValueError:
        pass

    # Fallback: bare date formats, no time
    for fmt in ("%Y-%m-%d", "%m-%d-%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date(), None, None
        except ValueError:
            continue

    return None, None, None


def _fetch_ff(url: str) -> list[dict]:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_upcoming_events() -> list[dict]:
    """Return upcoming USD high/medium-impact events for this week and next.

    Each event: {date, time, timezone, days_until, name, impact, forecast, previous}
    """
    today = datetime.now().date()
    raw   = []

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

        ev_date, ev_time, ev_tz = _parse_ff_event(ev.get("date", ""))
        if ev_date is None or ev_date < today:
            continue

        days_until = (ev_date - today).days
        events.append({
            "date":       ev_date.isoformat(),
            "time":       ev_time,      # e.g. "8:30 AM"
            "timezone":   ev_tz,        # e.g. "ET"
            "days_until": days_until,
            "name":       ev.get("title", "Unknown"),
            "impact":     ev.get("impact", ""),
            "forecast":   ev.get("forecast", ""),
            "previous":   ev.get("previous", ""),
        })

    # Deduplicate and sort
    seen, unique = set(), []
    for ev in sorted(events, key=lambda x: (x["date"], x["time"] or "")):
        key = (ev["date"], ev["name"])
        if key not in seen:
            seen.add(key)
            unique.append(ev)

    return unique[:12]
