"""Tests for the schedule helper functions in lib.galaxy_social."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from lib.galaxy_social import describe_schedule, parse_schedule


class TestParseSchedule:
    def test_none_returns_none(self):
        assert parse_schedule(None) is None

    def test_utc_schedule_is_parsed_as_utc(self):
        schedule = parse_schedule("2026-10-20 07:00 UTC")
        assert schedule == datetime(2026, 10, 20, 7, 0, tzinfo=timezone.utc)

    def test_named_zone_is_converted_to_utc(self):
        schedule = parse_schedule("2026-10-20 09:00 Europe/Berlin")
        assert schedule == datetime(2026, 10, 20, 7, 0, tzinfo=timezone.utc)

    def test_schedule_keeps_the_requested_wall_clock_time(self):
        schedule = parse_schedule("2026-10-20 09:00 Europe/Berlin")
        local = schedule.astimezone(ZoneInfo("Europe/Berlin")).replace(tzinfo=None)
        assert local == datetime(2026, 10, 20, 9, 0)

    def test_surrounding_whitespace_is_tolerated(self):
        assert parse_schedule("  2026-10-20 07:00 UTC  ") == datetime(
            2026, 10, 20, 7, 0, tzinfo=timezone.utc
        )

    @pytest.mark.parametrize(
        "value",
        [
            "2026-10-20",                # no time
            "2026-10-20 07:00",          # no time zone
            "2026-10-20 07:00 UTCX",     # unknown zone
            "not a date UTC",            # bad date
            "2026-13-40 07:00 UTC",      # bad date values
            "2026-10-20 07:00:00 UTC",   # unexpected seconds
        ],
    )
    def test_invalid_schedule_raises_with_hint(self, value):
        with pytest.raises(ValueError) as excinfo:
            parse_schedule(value)
        message = str(excinfo.value)
        assert "Invalid schedule" in message
        assert "schedule:" in message  # usage hint is part of the message

    def test_nonexistent_local_time_raises(self):
        # 02:30 does not exist on 2026-03-29 in Europe/Berlin (spring forward).
        with pytest.raises(ValueError):
            parse_schedule("2026-03-29 02:30 Europe/Berlin")

    def test_ambiguous_local_time_is_resolved_to_first_occurrence(self):
        # 02:30 happens twice on 2026-10-25 in Europe/Berlin (fall back);
        # the code resolves it to the first occurrence (CEST, fold=0).
        schedule = parse_schedule("2026-10-25 02:30 Europe/Berlin")
        assert schedule == datetime(2026, 10, 25, 0, 30, tzinfo=timezone.utc)


class TestDescribeSchedule:
    def test_mentions_all_displayed_zones(self):
        schedule = parse_schedule("2026-10-20 07:00 UTC")
        description = describe_schedule(schedule)
        assert "07:00 UTC" in description
        for city in ("Berlin", "New York", "Los Angeles"):
            assert city in description
