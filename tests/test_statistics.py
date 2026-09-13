# -*- coding: utf-8 -*-
"""Облік матчів: жоден прийнятий матч не повинен губитися."""
import json
from datetime import datetime, timedelta

import pytest

from report_exporter import ReportExporter
from stats_tracker import Statistics


@pytest.fixture
def stats(tmp_path):
    return Statistics(stats_dir=tmp_path / "stats")


def started_seconds_ago(stats, seconds):
    stats.current_session["search_started_at"] = \
        (datetime.now() - timedelta(seconds=seconds)).isoformat()


def test_match_with_known_wait_time(stats):
    started_seconds_ago(stats, 42)
    stats.match_accepted()

    summary = stats.get_summary()
    assert summary["total_matches_accepted"] == 1
    assert summary["average_wait_time"] == pytest.approx(42, abs=1)


def test_match_counted_when_search_started_manually(stats):
    """Регресія: пошук, запущений вручну в Dota, губив прийнятий матч."""
    stats.match_accepted()

    summary = stats.get_summary()
    assert summary["total_matches_accepted"] == 1
    assert summary["today_accepted"] == 1
    assert stats.data["sessions"][0]["wait_time_seconds"] is None


def test_unknown_wait_time_does_not_skew_average(stats):
    started_seconds_ago(stats, 60)
    stats.match_accepted()
    stats.match_accepted()  # час невідомий

    summary = stats.get_summary()
    assert summary["total_matches_accepted"] == 2
    assert summary["average_wait_time"] == pytest.approx(60, abs=1)


def test_start_search_keeps_first_timestamp(stats):
    stats.start_search()
    first = stats.current_session["search_started_at"]

    stats.start_search()

    assert stats.current_session["search_started_at"] == first


def test_match_missed_is_counted(stats):
    stats.match_missed()

    summary = stats.get_summary()
    assert summary["total_matches_missed"] == 1
    assert summary["today_missed"] == 1


def test_get_daily_stats_does_not_touch_saved_data(stats):
    """Регресія: середній час дописувався у statistics.json через посилання."""
    started_seconds_ago(stats, 10)
    stats.match_accepted()

    stats.get_daily_stats(days=7)
    stats._save_stats()

    saved = json.loads(stats.stats_file.read_text(encoding="utf-8"))
    today = datetime.now().strftime("%Y-%m-%d")
    assert "average_wait_time" not in saved["daily_stats"][today]


def test_daily_average_ignores_unknown_waits(stats):
    started_seconds_ago(stats, 30)
    stats.match_accepted()
    stats.match_accepted()

    today = stats.get_daily_stats(days=1)[0]
    assert today["matches_accepted"] == 2
    assert today["average_wait_time"] == pytest.approx(30, abs=1)


def test_exports_survive_unknown_wait_time(stats, tmp_path):
    """Регресія: форматування None у CSV валило експорт."""
    stats.match_accepted()

    results = ReportExporter(stats).export_all(tmp_path / "exports")

    assert all(results.values())
    csv_text = next((tmp_path / "exports").glob("*.csv")).read_text(encoding="utf-8-sig")
    assert "—" in csv_text
