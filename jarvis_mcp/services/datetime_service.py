"""Date resolution and context generation service.

Centralized date logic ported from jarvis-command-center. Pure functions
with no external service dependencies (only datetime, pytz, re).
"""

import logging
import re
from datetime import datetime, timedelta, timezone as tz
from typing import Any, Optional

import pytz

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Normalize / flatten helpers
# ---------------------------------------------------------------------------

def normalize_date_key(raw: str) -> str:
    """Normalize a date key string for lookup.

    Converts to lowercase, replaces spaces and colons with underscores,
    and collapses multiple whitespace.
    """
    text = raw.strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = text.replace(":", "_")
    return text


def flatten_date_context(nested_context: dict[str, Any]) -> dict[str, Any]:
    """Flatten a nested date context object into a simple key-value map.

    Handles the complex date context structure and extracts dates from:
    - current (today)
    - relative_dates (tomorrow, yesterday, etc.)
    - weekdays (next_monday, next_friday, etc.)
    - weeks.this_week (this_monday, this_tuesday, etc.)
    - time_expressions (at 3pm, at noon, etc.)
    - bucket lists (weekend, weeks, months, years)
    """
    flat: dict[str, Any] = {}

    if not isinstance(nested_context, dict):
        return flat

    # Extract today from current
    current = nested_context.get("current", {})
    if isinstance(current, dict) and isinstance(current.get("utc_start_of_day"), str):
        flat["today"] = current["utc_start_of_day"]

    # Extract relative dates
    relative = nested_context.get("relative_dates", {})
    if isinstance(relative, dict):
        for key, value in relative.items():
            if not isinstance(value, dict):
                continue
            if isinstance(value.get("utc_start_of_day"), str):
                flat[key] = value["utc_start_of_day"]
            elif isinstance(value.get("datetime"), str):
                flat[key] = value["datetime"]

    # Extract bucket lists (weekend, weeks, months, years)
    for bucket_name in ("weekend", "weeks", "months", "years"):
        bucket = nested_context.get(bucket_name, {})
        if not isinstance(bucket, dict):
            continue
        for key, value in bucket.items():
            if not isinstance(value, list):
                continue
            dates = [
                item.get("utc_start_of_day")
                for item in value
                if isinstance(item, dict) and isinstance(item.get("utc_start_of_day"), str)
            ]
            if dates:
                flat[key] = dates

    # Extract weekdays
    weekdays = nested_context.get("weekdays", {})
    if isinstance(weekdays, dict):
        for key, value in weekdays.items():
            if isinstance(value, dict) and isinstance(value.get("utc_start_of_day"), str):
                flat[key] = value["utc_start_of_day"]

    # Extract this_week entries (this_monday, this_tuesday, etc.)
    this_week = nested_context.get("weeks", {}).get("this_week", [])
    if isinstance(this_week, list):
        for entry in this_week:
            if not isinstance(entry, dict):
                continue
            day = entry.get("day")
            if isinstance(day, str) and isinstance(entry.get("utc_start_of_day"), str):
                flat[f"this_{day.strip().lower()}"] = entry["utc_start_of_day"]

    # Extract time expressions
    time_expressions = nested_context.get("time_expressions", {})
    if isinstance(time_expressions, dict):
        for key, value in time_expressions.items():
            if isinstance(value, str):
                flat[normalize_date_key(key)] = value

    return flat


# ---------------------------------------------------------------------------
# Time parsing / modifiers
# ---------------------------------------------------------------------------

def parse_time_string(time_str: str) -> tuple[int, int]:
    """Parse a time string like '9am', '3pm', '9_30am', '3_45pm'.

    Returns (hour, minute) in 24-hour format.
    """
    # Try format with minutes: 9_30am, 3_45pm
    match = re.match(r"(\d+)_(\d+)(am|pm)", time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if match.group(3) == "pm" and hour != 12:
            hour += 12
        elif match.group(3) == "am" and hour == 12:
            hour = 0
        return hour, minute

    # Try format without minutes: 9am, 3pm
    match = re.match(r"(\d+)(am|pm)", time_str)
    if match:
        hour = int(match.group(1))
        if match.group(2) == "pm" and hour != 12:
            hour += 12
        elif match.group(2) == "am" and hour == 12:
            hour = 0
        return hour, 0

    return 0, 0


def apply_time_modifier(base_datetime: str, modifier: str) -> Optional[str]:
    """Apply a time modifier to a base datetime string.

    Modifiers: morning (7am), afternoon (1pm), evening (6pm),
    night (9pm), noon (12pm), midnight (0am), or at_Xpm patterns.
    """
    try:
        normalized = base_datetime.replace("Z", "+00:00") if base_datetime.endswith("Z") else base_datetime
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    time_map = {
        "morning": 7,
        "afternoon": 13,
        "evening": 18,
        "night": 21,
        "noon": 12,
        "midnight": 0,
    }

    if modifier in time_map:
        dt = dt.replace(hour=time_map[modifier], minute=0, second=0, microsecond=0)
    elif modifier.startswith("at_"):
        hour, minute = parse_time_string(modifier[3:])
        dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return dt.astimezone(tz.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Relative time resolution
# ---------------------------------------------------------------------------

RELATIVE_TIME_PATTERN = re.compile(
    r"^in_(\d+)_(minutes|hours|days)(?:_(\d+)_(minutes))?$"
)


def resolve_relative_time(key: str, date_context: dict[str, Any]) -> Optional[str]:
    """Resolve a relative time key like 'in_30_minutes' to an ISO datetime string."""
    match = RELATIVE_TIME_PATTERN.match(key)
    if not match:
        return None

    now_str = (
        date_context.get("current", {}).get("datetime")
        or date_context.get("current", {}).get("utc_start_of_day")
    )
    if not now_str:
        return None

    try:
        normalized = now_str.replace("Z", "+00:00") if now_str.endswith("Z") else now_str
        now = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    offset = timedelta()
    if unit == "minutes":
        offset = timedelta(minutes=amount)
    elif unit == "hours":
        offset = timedelta(hours=amount)
    elif unit == "days":
        offset = timedelta(days=amount)

    # Handle compound: in_1_hours_30_minutes
    if match.group(3) and match.group(4):
        offset += timedelta(minutes=int(match.group(3)))

    result = now + offset
    return result.astimezone(tz.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Main resolution function
# ---------------------------------------------------------------------------

def resolve_date_keys(
    date_keys: list[str],
    date_context: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Resolve date keys to datetime strings.

    Args:
        date_keys: List of date key strings (e.g., ["tomorrow", "morning"])
        date_context: The nested date context object

    Returns:
        Tuple of (resolved_dates, unresolved_keys)
    """
    if not date_keys:
        return [], []

    normalized_keys = [normalize_date_key(key) for key in date_keys if isinstance(key, str)]
    flat_context = flatten_date_context(date_context)

    resolved: list[str] = []
    unresolved: list[str] = []

    for key in normalized_keys:
        # Try relative time resolution first (e.g., in_30_minutes, in_2_hours)
        relative_result = resolve_relative_time(key, date_context)
        if relative_result:
            resolved.append(relative_result)
            continue

        value = flat_context.get(key)
        if isinstance(value, list):
            resolved.extend([v for v in value if isinstance(v, str)])
        elif isinstance(value, str):
            resolved.append(value)
        else:
            # Key not found - track for potential LLM fallback
            # But skip time modifiers (they combine with date keys)
            if key not in {"morning", "afternoon", "evening", "night", "noon", "midnight"} and not key.startswith("at_"):
                unresolved.append(key)

    # Handle date + time modifier combination
    date_key = None
    for key in normalized_keys:
        value = flat_context.get(key)
        if isinstance(value, str):
            date_key = key
            break

    time_key = None
    for key in normalized_keys:
        if key in {"morning", "afternoon", "evening", "night", "noon", "midnight"} or key.startswith("at_"):
            time_key = key
            break

    if date_key and time_key:
        base = flat_context.get(date_key)
        if isinstance(base, str):
            combined = apply_time_modifier(base, time_key)
            if combined:
                resolved.append(combined)
        elif isinstance(base, list):
            for entry in base:
                if not isinstance(entry, str):
                    continue
                combined = apply_time_modifier(entry, time_key)
                if combined:
                    resolved.append(combined)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for entry in resolved:
        if entry in seen:
            continue
        seen.add(entry)
        unique.append(entry)

    return unique, unresolved


# ---------------------------------------------------------------------------
# Date context generation
# ---------------------------------------------------------------------------

def generate_date_context_object(timezone_str: str | None = None) -> dict:
    """Generate a comprehensive date context object with all calculated dates.

    Args:
        timezone_str: Optional timezone string (e.g., "America/New_York").
                      Defaults to UTC.

    Returns:
        dict containing current, relative_dates, weekend, weeks, months,
        years, weekdays, timezone, and time_expressions.
    """
    if timezone_str:
        try:
            user_tz = pytz.timezone(timezone_str)
            utc_now = datetime.now(pytz.UTC)
            now = utc_now.astimezone(user_tz)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning("Unknown timezone %r, falling back to UTC", timezone_str)
            timezone_str = "UTC"
            now = datetime.now(pytz.UTC)
    else:
        timezone_str = "UTC"
        now = datetime.now(pytz.UTC)

    def get_utc_start_of_day(date_obj: datetime, tz_str: str | None) -> str:
        """Get UTC start of day for a given date in user's timezone."""
        if not tz_str:
            return date_obj.strftime("%Y-%m-%dT00:00:00Z")
        try:
            user_tz = pytz.timezone(tz_str)
            start_of_day = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            if start_of_day.tzinfo is None:
                utc_start = user_tz.localize(start_of_day).astimezone(pytz.UTC)
            else:
                utc_start = start_of_day.astimezone(pytz.UTC)
            return utc_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        except (pytz.exceptions.UnknownTimeZoneError, ValueError):
            return date_obj.strftime("%Y-%m-%dT00:00:00Z")

    # Calculate all the date variations
    tomorrow = now + timedelta(days=1)
    yesterday = now - timedelta(days=1)

    # Calculate last_night (yesterday at 7pm local time)
    last_night = yesterday.replace(hour=19, minute=0, second=0, microsecond=0)
    try:
        user_tz = pytz.timezone(timezone_str)
        if last_night.tzinfo is None:
            last_night_utc = user_tz.localize(last_night).astimezone(pytz.UTC)
        else:
            last_night_utc = last_night.astimezone(pytz.UTC)
        last_night_iso = last_night_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except (pytz.exceptions.UnknownTimeZoneError, ValueError):
        last_night_iso = last_night.strftime("%Y-%m-%dT19:00:00Z")

    # Calculate weekend dates
    if now.weekday() == 5:  # Saturday
        this_saturday = now
        this_sunday = now + timedelta(days=1)
        last_saturday = now - timedelta(days=7)
        last_sunday = now - timedelta(days=6)
        next_saturday = now + timedelta(days=7)
        next_sunday = now + timedelta(days=8)
    elif now.weekday() == 6:  # Sunday
        this_saturday = now - timedelta(days=1)
        this_sunday = now
        last_saturday = now - timedelta(days=8)
        last_sunday = now - timedelta(days=7)
        next_saturday = now + timedelta(days=6)
        next_sunday = now + timedelta(days=7)
    else:  # Monday-Friday
        days_until_saturday = (5 - now.weekday()) % 7
        this_saturday = now + timedelta(days=days_until_saturday)
        this_sunday = this_saturday + timedelta(days=1)
        days_since_saturday = now.weekday() + 2
        last_saturday = now - timedelta(days=days_since_saturday)
        last_sunday = last_saturday + timedelta(days=1)
        next_saturday = this_saturday + timedelta(days=7)
        next_sunday = this_sunday + timedelta(days=7)

    # Calculate week dates (Sunday to Saturday)
    if now.weekday() == 6:  # Sunday
        this_week_start = now
    else:
        this_week_start = now - timedelta(days=now.weekday() + 1)
    this_week_end = this_week_start + timedelta(days=6)

    next_week_start = this_week_start + timedelta(days=7)
    next_week_end = next_week_start + timedelta(days=6)

    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = last_week_start + timedelta(days=6)

    # Calculate specific weekdays
    weekday_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    next_weekdays = {}
    for i, day in enumerate(weekday_names):
        next_weekday_date = next_week_start + timedelta(days=i)
        next_weekdays[f"next_{day}"] = next_weekday_date.strftime("%Y-%m-%d")

    last_weekdays = {}
    for i, day in enumerate(weekday_names):
        last_weekday_date = last_week_start + timedelta(days=i)
        last_weekdays[f"last_{day}"] = last_weekday_date.strftime("%Y-%m-%d")

    # Build the comprehensive date context object
    date_context: dict[str, Any] = {
        "current": {
            "date": now.strftime("%A, %B %d %Y"),
            "date_iso": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%I:%M %p"),
            "datetime": now.astimezone(pytz.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "weekday": now.strftime("%A").lower(),
            "weekday_number": now.weekday(),
            "utc_start_of_day": get_utc_start_of_day(now, timezone_str),
        },
        "relative_dates": {
            "tomorrow": {
                "date": tomorrow.strftime("%Y-%m-%d"),
                "utc_start_of_day": get_utc_start_of_day(tomorrow, timezone_str),
            },
            "yesterday": {
                "date": yesterday.strftime("%Y-%m-%d"),
                "utc_start_of_day": get_utc_start_of_day(yesterday, timezone_str),
            },
            "last_night": {
                "date": yesterday.strftime("%Y-%m-%d"),
                "time": "19:00:00",
                "datetime": last_night_iso,
            },
            "day_after_tomorrow": {
                "date": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
                "utc_start_of_day": get_utc_start_of_day(now + timedelta(days=2), timezone_str),
            },
            "day_before_yesterday": {
                "date": (now - timedelta(days=2)).strftime("%Y-%m-%d"),
                "utc_start_of_day": get_utc_start_of_day(now - timedelta(days=2), timezone_str),
            },
        },
        "weekend": {
            "this_weekend": [
                {"day": "Saturday", "date": this_saturday.strftime("%Y-%m-%d"), "utc_start_of_day": get_utc_start_of_day(this_saturday, timezone_str)},
                {"day": "Sunday", "date": this_sunday.strftime("%Y-%m-%d"), "utc_start_of_day": get_utc_start_of_day(this_sunday, timezone_str)},
            ],
            "next_weekend": [
                {"day": "Saturday", "date": next_saturday.strftime("%Y-%m-%d"), "utc_start_of_day": get_utc_start_of_day(next_saturday, timezone_str)},
                {"day": "Sunday", "date": next_sunday.strftime("%Y-%m-%d"), "utc_start_of_day": get_utc_start_of_day(next_sunday, timezone_str)},
            ],
            "last_weekend": [
                {"day": "Saturday", "date": last_saturday.strftime("%Y-%m-%d"), "utc_start_of_day": get_utc_start_of_day(last_saturday, timezone_str)},
                {"day": "Sunday", "date": last_sunday.strftime("%Y-%m-%d"), "utc_start_of_day": get_utc_start_of_day(last_sunday, timezone_str)},
            ],
        },
        "weeks": {
            "this_week": [
                {
                    "day": (this_week_start + timedelta(days=i)).strftime("%A"),
                    "date": (this_week_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                    "utc_start_of_day": get_utc_start_of_day(this_week_start + timedelta(days=i), timezone_str),
                }
                for i in range(7)
            ],
            "next_week": [
                {
                    "day": f"Next {(next_week_start + timedelta(days=i)).strftime('%A')}",
                    "date": (next_week_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                    "utc_start_of_day": get_utc_start_of_day(next_week_start + timedelta(days=i), timezone_str),
                }
                for i in range(7)
            ],
            "last_week": [
                {
                    "day": f"Last {(last_week_start + timedelta(days=i)).strftime('%A')}",
                    "date": (last_week_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                    "utc_start_of_day": get_utc_start_of_day(last_week_start + timedelta(days=i), timezone_str),
                }
                for i in range(7)
            ],
        },
        "months": {
            "this_month": [
                {"date": now.replace(day=1).strftime("%Y-%m-%d"), "utc_start_of_day": get_utc_start_of_day(now.replace(day=1), timezone_str)},
                {"date": ((now.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d"),
                 "utc_start_of_day": get_utc_start_of_day((now.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1), timezone_str)},
            ],
            "next_month": [
                {"date": (now.replace(day=1) + timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d"),
                 "utc_start_of_day": get_utc_start_of_day((now.replace(day=1) + timedelta(days=32)).replace(day=1), timezone_str)},
                {"date": (((now.replace(day=1) + timedelta(days=32)).replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d"),
                 "utc_start_of_day": get_utc_start_of_day(((now.replace(day=1) + timedelta(days=32)).replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1), timezone_str)},
            ],
            "last_month": [
                {"date": ((now.replace(day=1) - timedelta(days=1)).replace(day=1)).strftime("%Y-%m-%d"),
                 "utc_start_of_day": get_utc_start_of_day((now.replace(day=1) - timedelta(days=1)).replace(day=1), timezone_str)},
                {"date": (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d"),
                 "utc_start_of_day": get_utc_start_of_day(now.replace(day=1) - timedelta(days=1), timezone_str)},
            ],
        },
        "years": {
            "this_year": [
                {"date": now.replace(month=1, day=1).strftime("%Y-%m-%d"), "utc_start_of_day": get_utc_start_of_day(now.replace(month=1, day=1), timezone_str)},
                {"date": now.replace(month=12, day=31).strftime("%Y-%m-%d"), "utc_start_of_day": get_utc_start_of_day(now.replace(month=12, day=31), timezone_str)},
            ],
            "next_year": [
                {"date": (now + timedelta(days=365)).replace(month=1, day=1).strftime("%Y-%m-%d"),
                 "utc_start_of_day": get_utc_start_of_day((now + timedelta(days=365)).replace(month=1, day=1), timezone_str)},
                {"date": (now + timedelta(days=365)).replace(month=12, day=31).strftime("%Y-%m-%d"),
                 "utc_start_of_day": get_utc_start_of_day((now + timedelta(days=365)).replace(month=12, day=31), timezone_str)},
            ],
            "last_year": [
                {"date": (now - timedelta(days=365)).replace(month=1, day=1).strftime("%Y-%m-%d"),
                 "utc_start_of_day": get_utc_start_of_day((now - timedelta(days=365)).replace(month=1, day=1), timezone_str)},
                {"date": (now - timedelta(days=365)).replace(month=12, day=31).strftime("%Y-%m-%d"),
                 "utc_start_of_day": get_utc_start_of_day((now - timedelta(days=365)).replace(month=12, day=31), timezone_str)},
            ],
        },
        "weekdays": {
            **{k: {"date": v, "utc_start_of_day": get_utc_start_of_day(datetime.strptime(v, "%Y-%m-%d"), timezone_str)} for k, v in next_weekdays.items()},
            **{k: {"date": v, "utc_start_of_day": get_utc_start_of_day(datetime.strptime(v, "%Y-%m-%d"), timezone_str)} for k, v in last_weekdays.items()},
        },
        "timezone": {
            "user_timezone": timezone_str,
            "current_timezone": str(now.tzinfo) if now.tzinfo else "local",
            "is_dst": now.dst() != timedelta(0) if now.tzinfo else None,
        },
        "time_expressions": _generate_time_expressions(now, timezone_str),
    }

    return date_context


def _generate_time_expressions(now: datetime, timezone_str: str | None = None) -> dict:
    """Generate pre-calculated time expressions for common natural language times."""

    def to_utc_iso(dt: datetime) -> str:
        if timezone_str and dt.tzinfo is None:
            user_tz = pytz.timezone(timezone_str)
            dt = user_tz.localize(dt)
        return dt.astimezone(pytz.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    yesterday = today - timedelta(days=1)

    time_expressions: dict[str, str] = {}

    # Natural language times for today
    time_expressions.update({
        "this morning": to_utc_iso(today.replace(hour=7, minute=0)),
        "this afternoon": to_utc_iso(today.replace(hour=14, minute=0)),
        "this evening": to_utc_iso(today.replace(hour=19, minute=0)),
        "tonight": to_utc_iso(today.replace(hour=20, minute=0)),
        "during lunch": to_utc_iso(today.replace(hour=12, minute=0)),
        "at breakfast": to_utc_iso(today.replace(hour=8, minute=0)),
        "at dinner": to_utc_iso(today.replace(hour=18, minute=0)),
        "at noon": to_utc_iso(today.replace(hour=12, minute=0)),
        "at midnight": to_utc_iso(today.replace(hour=0, minute=0)),
    })

    # Natural language times for tomorrow
    time_expressions.update({
        "tomorrow morning": to_utc_iso(tomorrow.replace(hour=7, minute=0)),
        "tomorrow afternoon": to_utc_iso(tomorrow.replace(hour=14, minute=0)),
        "tomorrow evening": to_utc_iso(tomorrow.replace(hour=19, minute=0)),
        "tomorrow night": to_utc_iso(tomorrow.replace(hour=20, minute=0)),
    })

    # Natural language times for yesterday
    time_expressions.update({
        "yesterday morning": to_utc_iso(yesterday.replace(hour=7, minute=0)),
        "yesterday afternoon": to_utc_iso(yesterday.replace(hour=14, minute=0)),
        "yesterday evening": to_utc_iso(yesterday.replace(hour=19, minute=0)),
        "last night": to_utc_iso(yesterday.replace(hour=20, minute=0)),
    })

    # Exact times - 12 hour format
    for hour in range(1, 13):
        am_hour = hour if hour != 12 else 0
        time_expressions[f"at {hour}am"] = to_utc_iso(today.replace(hour=am_hour, minute=0))

        pm_hour = hour if hour == 12 else hour + 12
        time_expressions[f"at {hour}pm"] = to_utc_iso(today.replace(hour=pm_hour, minute=0))

        # Half hours
        time_expressions[f"at {hour}:30am"] = to_utc_iso(today.replace(hour=am_hour, minute=30))
        time_expressions[f"at {hour}:30pm"] = to_utc_iso(today.replace(hour=pm_hour, minute=30))

        # Quarter hours for common times
        if hour in [9, 10, 11, 1, 2, 3]:
            time_expressions[f"at {hour}:15am"] = to_utc_iso(today.replace(hour=am_hour, minute=15))
            time_expressions[f"at {hour}:45am"] = to_utc_iso(today.replace(hour=am_hour, minute=45))
            time_expressions[f"at {hour}:15pm"] = to_utc_iso(today.replace(hour=pm_hour, minute=15))
            time_expressions[f"at {hour}:45pm"] = to_utc_iso(today.replace(hour=pm_hour, minute=45))

    return time_expressions
