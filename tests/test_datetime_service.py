"""Tests for datetime service - date resolution and context generation.

Ported from jarvis-command-center/tests/test_date_resolution.py and extended.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch


class TestNormalizeDateKey:
    """Tests for normalizing date key strings."""

    def test_basic_string(self):
        from jarvis_mcp.services.datetime_service import normalize_date_key
        assert normalize_date_key("tomorrow") == "tomorrow"

    def test_with_spaces(self):
        from jarvis_mcp.services.datetime_service import normalize_date_key
        assert normalize_date_key("next week") == "next_week"

    def test_with_multiple_spaces(self):
        from jarvis_mcp.services.datetime_service import normalize_date_key
        assert normalize_date_key("next   week") == "next_week"

    def test_with_colon(self):
        from jarvis_mcp.services.datetime_service import normalize_date_key
        assert normalize_date_key("at:noon") == "at_noon"

    def test_uppercase(self):
        from jarvis_mcp.services.datetime_service import normalize_date_key
        assert normalize_date_key("TOMORROW") == "tomorrow"

    def test_mixed_case_and_spaces(self):
        from jarvis_mcp.services.datetime_service import normalize_date_key
        assert normalize_date_key("Next Week") == "next_week"

    def test_whitespace_trimmed(self):
        from jarvis_mcp.services.datetime_service import normalize_date_key
        assert normalize_date_key("  tomorrow  ") == "tomorrow"


class TestFlattenDateContext:
    """Tests for flattening nested date context objects."""

    def test_empty_context(self):
        from jarvis_mcp.services.datetime_service import flatten_date_context
        assert flatten_date_context({}) == {}

    def test_non_dict_input(self):
        from jarvis_mcp.services.datetime_service import flatten_date_context
        assert flatten_date_context(None) == {}
        assert flatten_date_context([]) == {}

    def test_current_today(self):
        from jarvis_mcp.services.datetime_service import flatten_date_context
        context = {
            "current": {
                "utc_start_of_day": "2025-01-15T00:00:00Z"
            }
        }
        result = flatten_date_context(context)
        assert result["today"] == "2025-01-15T00:00:00Z"

    def test_relative_dates(self):
        from jarvis_mcp.services.datetime_service import flatten_date_context
        context = {
            "relative_dates": {
                "tomorrow": {"utc_start_of_day": "2025-01-16T00:00:00Z"},
                "yesterday": {"utc_start_of_day": "2025-01-14T00:00:00Z"}
            }
        }
        result = flatten_date_context(context)
        assert result["tomorrow"] == "2025-01-16T00:00:00Z"
        assert result["yesterday"] == "2025-01-14T00:00:00Z"

    def test_relative_dates_with_datetime_field(self):
        from jarvis_mcp.services.datetime_service import flatten_date_context
        context = {
            "relative_dates": {
                "now": {"datetime": "2025-01-15T10:30:00Z"}
            }
        }
        result = flatten_date_context(context)
        assert result["now"] == "2025-01-15T10:30:00Z"

    def test_weekdays(self):
        from jarvis_mcp.services.datetime_service import flatten_date_context
        context = {
            "weekdays": {
                "next_monday": {"utc_start_of_day": "2025-01-20T00:00:00Z"},
                "next_friday": {"utc_start_of_day": "2025-01-24T00:00:00Z"}
            }
        }
        result = flatten_date_context(context)
        assert result["next_monday"] == "2025-01-20T00:00:00Z"
        assert result["next_friday"] == "2025-01-24T00:00:00Z"

    def test_this_week_entries(self):
        from jarvis_mcp.services.datetime_service import flatten_date_context
        context = {
            "weeks": {
                "this_week": [
                    {"day": "Monday", "utc_start_of_day": "2025-01-13T00:00:00Z"},
                    {"day": "Tuesday", "utc_start_of_day": "2025-01-14T00:00:00Z"}
                ]
            }
        }
        result = flatten_date_context(context)
        assert result["this_monday"] == "2025-01-13T00:00:00Z"
        assert result["this_tuesday"] == "2025-01-14T00:00:00Z"

    def test_time_expressions(self):
        from jarvis_mcp.services.datetime_service import flatten_date_context
        context = {
            "time_expressions": {
                "at 3pm": "2025-01-15T15:00:00Z",
                "at noon": "2025-01-15T12:00:00Z"
            }
        }
        result = flatten_date_context(context)
        assert result["at_3pm"] == "2025-01-15T15:00:00Z"
        assert result["at_noon"] == "2025-01-15T12:00:00Z"

    def test_bucket_lists(self):
        from jarvis_mcp.services.datetime_service import flatten_date_context
        context = {
            "weekend": {
                "this_weekend": [
                    {"utc_start_of_day": "2025-01-18T00:00:00Z"},
                    {"utc_start_of_day": "2025-01-19T00:00:00Z"}
                ]
            }
        }
        result = flatten_date_context(context)
        assert result["this_weekend"] == ["2025-01-18T00:00:00Z", "2025-01-19T00:00:00Z"]


class TestParseTimeString:
    """Tests for parsing time strings."""

    def test_simple_am(self):
        from jarvis_mcp.services.datetime_service import parse_time_string
        hour, minute = parse_time_string("9am")
        assert hour == 9
        assert minute == 0

    def test_simple_pm(self):
        from jarvis_mcp.services.datetime_service import parse_time_string
        hour, minute = parse_time_string("3pm")
        assert hour == 15
        assert minute == 0

    def test_with_minutes_am(self):
        from jarvis_mcp.services.datetime_service import parse_time_string
        hour, minute = parse_time_string("9_30am")
        assert hour == 9
        assert minute == 30

    def test_with_minutes_pm(self):
        from jarvis_mcp.services.datetime_service import parse_time_string
        hour, minute = parse_time_string("3_45pm")
        assert hour == 15
        assert minute == 45

    def test_12am_midnight(self):
        from jarvis_mcp.services.datetime_service import parse_time_string
        hour, minute = parse_time_string("12am")
        assert hour == 0
        assert minute == 0

    def test_12pm_noon(self):
        from jarvis_mcp.services.datetime_service import parse_time_string
        hour, minute = parse_time_string("12pm")
        assert hour == 12
        assert minute == 0

    def test_invalid_format(self):
        from jarvis_mcp.services.datetime_service import parse_time_string
        hour, minute = parse_time_string("invalid")
        assert hour == 0
        assert minute == 0


class TestApplyTimeModifier:
    """Tests for applying time modifiers to base datetime."""

    def test_morning_modifier(self):
        from jarvis_mcp.services.datetime_service import apply_time_modifier
        result = apply_time_modifier("2025-01-15T00:00:00Z", "morning")
        assert result == "2025-01-15T07:00:00Z"

    def test_afternoon_modifier(self):
        from jarvis_mcp.services.datetime_service import apply_time_modifier
        result = apply_time_modifier("2025-01-15T00:00:00Z", "afternoon")
        assert result == "2025-01-15T13:00:00Z"

    def test_evening_modifier(self):
        from jarvis_mcp.services.datetime_service import apply_time_modifier
        result = apply_time_modifier("2025-01-15T00:00:00Z", "evening")
        assert result == "2025-01-15T18:00:00Z"

    def test_night_modifier(self):
        from jarvis_mcp.services.datetime_service import apply_time_modifier
        result = apply_time_modifier("2025-01-15T00:00:00Z", "night")
        assert result == "2025-01-15T21:00:00Z"

    def test_noon_modifier(self):
        from jarvis_mcp.services.datetime_service import apply_time_modifier
        result = apply_time_modifier("2025-01-15T00:00:00Z", "noon")
        assert result == "2025-01-15T12:00:00Z"

    def test_midnight_modifier(self):
        from jarvis_mcp.services.datetime_service import apply_time_modifier
        result = apply_time_modifier("2025-01-15T00:00:00Z", "midnight")
        assert result == "2025-01-15T00:00:00Z"

    def test_at_specific_time(self):
        from jarvis_mcp.services.datetime_service import apply_time_modifier
        result = apply_time_modifier("2025-01-15T00:00:00Z", "at_3pm")
        assert result == "2025-01-15T15:00:00Z"

    def test_at_specific_time_with_minutes(self):
        from jarvis_mcp.services.datetime_service import apply_time_modifier
        result = apply_time_modifier("2025-01-15T00:00:00Z", "at_3_30pm")
        assert result == "2025-01-15T15:30:00Z"

    def test_invalid_base_datetime(self):
        from jarvis_mcp.services.datetime_service import apply_time_modifier
        result = apply_time_modifier("invalid", "morning")
        assert result is None

    def test_handles_non_z_timezone(self):
        from jarvis_mcp.services.datetime_service import apply_time_modifier
        result = apply_time_modifier("2025-01-15T00:00:00+00:00", "noon")
        assert result == "2025-01-15T12:00:00Z"


class TestResolveDateKeys:
    """Tests for resolving date keys to datetime strings."""

    def test_single_key(self):
        from jarvis_mcp.services.datetime_service import resolve_date_keys
        date_context = {
            "relative_dates": {
                "tomorrow": {"utc_start_of_day": "2025-01-16T00:00:00Z"}
            }
        }
        resolved, unresolved = resolve_date_keys(["tomorrow"], date_context)
        assert resolved == ["2025-01-16T00:00:00Z"]
        assert unresolved == []

    def test_multiple_keys(self):
        from jarvis_mcp.services.datetime_service import resolve_date_keys
        date_context = {
            "relative_dates": {
                "tomorrow": {"utc_start_of_day": "2025-01-16T00:00:00Z"},
                "yesterday": {"utc_start_of_day": "2025-01-14T00:00:00Z"}
            }
        }
        resolved, unresolved = resolve_date_keys(["tomorrow", "yesterday"], date_context)
        assert "2025-01-16T00:00:00Z" in resolved
        assert "2025-01-14T00:00:00Z" in resolved

    def test_unresolved_keys(self):
        from jarvis_mcp.services.datetime_service import resolve_date_keys
        date_context = {
            "relative_dates": {
                "tomorrow": {"utc_start_of_day": "2025-01-16T00:00:00Z"}
            }
        }
        resolved, unresolved = resolve_date_keys(["next_fortnight"], date_context)
        assert resolved == []
        assert unresolved == ["next_fortnight"]

    def test_date_with_time_modifier(self):
        from jarvis_mcp.services.datetime_service import resolve_date_keys
        date_context = {
            "relative_dates": {
                "tomorrow": {"utc_start_of_day": "2025-01-16T00:00:00Z"}
            }
        }
        resolved, unresolved = resolve_date_keys(["tomorrow", "morning"], date_context)
        assert "2025-01-16T07:00:00Z" in resolved
        # Raw base date should be removed when combined with time modifier
        assert "2025-01-16T00:00:00Z" not in resolved

    def test_time_modifiers_not_unresolved(self):
        from jarvis_mcp.services.datetime_service import resolve_date_keys
        date_context = {
            "relative_dates": {
                "tomorrow": {"utc_start_of_day": "2025-01-16T00:00:00Z"}
            }
        }
        resolved, unresolved = resolve_date_keys(["morning"], date_context)
        assert "morning" not in unresolved

    def test_empty_input(self):
        from jarvis_mcp.services.datetime_service import resolve_date_keys
        resolved, unresolved = resolve_date_keys([], {})
        assert resolved == []
        assert unresolved == []

    def test_list_values_in_context(self):
        from jarvis_mcp.services.datetime_service import resolve_date_keys
        date_context = {
            "weekend": {
                "this_weekend": [
                    {"utc_start_of_day": "2025-01-18T00:00:00Z"},
                    {"utc_start_of_day": "2025-01-19T00:00:00Z"}
                ]
            }
        }
        resolved, unresolved = resolve_date_keys(["this_weekend"], date_context)
        assert "2025-01-18T00:00:00Z" in resolved
        assert "2025-01-19T00:00:00Z" in resolved

    def test_deduplication(self):
        from jarvis_mcp.services.datetime_service import resolve_date_keys
        date_context = {
            "relative_dates": {
                "tomorrow": {"utc_start_of_day": "2025-01-16T00:00:00Z"}
            }
        }
        resolved, unresolved = resolve_date_keys(["tomorrow", "tomorrow"], date_context)
        assert resolved.count("2025-01-16T00:00:00Z") == 1

    def test_relative_time_key(self):
        from jarvis_mcp.services.datetime_service import resolve_date_keys
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        date_context = {
            "current": {"datetime": now.isoformat().replace("+00:00", "Z")}
        }
        resolved, unresolved = resolve_date_keys(["in_30_minutes"], date_context)
        expected = (now + timedelta(minutes=30)).isoformat().replace("+00:00", "Z")
        assert resolved == [expected]
        assert unresolved == []

    def test_mixed_semantic_and_relative(self):
        from jarvis_mcp.services.datetime_service import resolve_date_keys
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        date_context = {
            "current": {"datetime": now.isoformat().replace("+00:00", "Z")},
            "relative_dates": {
                "tomorrow": {"utc_start_of_day": "2025-01-16T00:00:00Z"}
            }
        }
        resolved, unresolved = resolve_date_keys(["tomorrow", "in_30_minutes"], date_context)
        assert "2025-01-16T00:00:00Z" in resolved
        expected_relative = (now + timedelta(minutes=30)).isoformat().replace("+00:00", "Z")
        assert expected_relative in resolved
        assert unresolved == []


class TestResolveRelativeTime:
    """Tests for resolving relative time keys to ISO datetimes."""

    def _make_context(self, now: datetime) -> dict:
        return {"current": {"datetime": now.isoformat().replace("+00:00", "Z")}}

    def test_resolve_relative_minutes(self):
        from jarvis_mcp.services.datetime_service import resolve_relative_time
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = resolve_relative_time("in_30_minutes", self._make_context(now))
        expected = (now + timedelta(minutes=30)).isoformat().replace("+00:00", "Z")
        assert result == expected

    def test_resolve_relative_hours(self):
        from jarvis_mcp.services.datetime_service import resolve_relative_time
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = resolve_relative_time("in_2_hours", self._make_context(now))
        expected = (now + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
        assert result == expected

    def test_resolve_relative_days(self):
        from jarvis_mcp.services.datetime_service import resolve_relative_time
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = resolve_relative_time("in_3_days", self._make_context(now))
        expected = (now + timedelta(days=3)).isoformat().replace("+00:00", "Z")
        assert result == expected

    def test_resolve_relative_compound(self):
        from jarvis_mcp.services.datetime_service import resolve_relative_time
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = resolve_relative_time("in_1_hours_30_minutes", self._make_context(now))
        expected = (now + timedelta(hours=1, minutes=30)).isoformat().replace("+00:00", "Z")
        assert result == expected

    def test_resolve_invalid_relative_key(self):
        from jarvis_mcp.services.datetime_service import resolve_relative_time
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = resolve_relative_time("in_abc_minutes", self._make_context(now))
        assert result is None

    def test_resolve_non_matching_key(self):
        from jarvis_mcp.services.datetime_service import resolve_relative_time
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = resolve_relative_time("tomorrow", self._make_context(now))
        assert result is None

    def test_resolve_missing_current_datetime(self):
        from jarvis_mcp.services.datetime_service import resolve_relative_time
        result = resolve_relative_time("in_30_minutes", {})
        assert result is None


class TestGenerateDateContextObject:
    """Tests for generating date context objects."""

    def test_returns_dict(self):
        from jarvis_mcp.services.datetime_service import generate_date_context_object
        result = generate_date_context_object()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        from jarvis_mcp.services.datetime_service import generate_date_context_object
        result = generate_date_context_object()
        assert "current" in result
        assert "relative_dates" in result
        assert "weekend" in result
        assert "weeks" in result
        assert "months" in result
        assert "years" in result
        assert "weekdays" in result
        assert "timezone" in result
        assert "time_expressions" in result

    def test_current_has_expected_fields(self):
        from jarvis_mcp.services.datetime_service import generate_date_context_object
        result = generate_date_context_object()
        current = result["current"]
        assert "date" in current
        assert "date_iso" in current
        assert "time" in current
        assert "datetime" in current
        assert "weekday" in current
        assert "weekday_number" in current
        assert "utc_start_of_day" in current

    def test_relative_dates_keys(self):
        from jarvis_mcp.services.datetime_service import generate_date_context_object
        result = generate_date_context_object()
        relative = result["relative_dates"]
        assert "tomorrow" in relative
        assert "yesterday" in relative
        assert "last_night" in relative
        assert "day_after_tomorrow" in relative
        assert "day_before_yesterday" in relative

    def test_with_timezone(self):
        from jarvis_mcp.services.datetime_service import generate_date_context_object
        result = generate_date_context_object("America/New_York")
        assert result["timezone"]["user_timezone"] == "America/New_York"

    def test_with_invalid_timezone_falls_back(self):
        from jarvis_mcp.services.datetime_service import generate_date_context_object
        # Should not crash, falls back to local time
        result = generate_date_context_object("Invalid/Timezone")
        assert isinstance(result, dict)
        assert "current" in result

    def test_utc_start_of_day_format(self):
        from jarvis_mcp.services.datetime_service import generate_date_context_object
        result = generate_date_context_object("UTC")
        utc_start = result["current"]["utc_start_of_day"]
        assert utc_start.endswith("Z")
        assert "T00:00:00Z" in utc_start

    def test_weekdays_contains_next_and_last(self):
        from jarvis_mcp.services.datetime_service import generate_date_context_object
        result = generate_date_context_object()
        weekdays = result["weekdays"]
        assert "next_monday" in weekdays
        assert "last_monday" in weekdays

    def test_time_expressions_generated(self):
        from jarvis_mcp.services.datetime_service import generate_date_context_object
        result = generate_date_context_object("UTC")
        time_expr = result["time_expressions"]
        assert "this morning" in time_expr
        assert "at noon" in time_expr
        assert "tonight" in time_expr

    def test_weekend_structure(self):
        from jarvis_mcp.services.datetime_service import generate_date_context_object
        result = generate_date_context_object()
        weekend = result["weekend"]
        assert "this_weekend" in weekend
        assert "next_weekend" in weekend
        assert "last_weekend" in weekend
        assert len(weekend["this_weekend"]) == 2
