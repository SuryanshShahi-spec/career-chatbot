import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Assets.monitor import MonitorDB


def test_monitor_records_search_api_and_session_metrics() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "metrics.db")
        monitor = MonitorDB(db_path=db_path)

        monitor.record_search("Data Analyst", "Bangalore", "in", 5, 3, 12, 180.5, "success")
        monitor.record_api_call("adzuna", "job_search", 180.5, status_code=200, success=True)
        monitor.record_session("demo-session", "2026-08-02T00:00:00+00:00", "2026-08-02T00:05:00+00:00", 300.0, 8, 3, 2, 2, 0)

        summary = monitor.get_summary()

        assert summary["search_stats"]["total_searches"] == 1
        assert summary["search_stats"]["successful"] == 1
        assert summary["api_health"][0]["service"] == "adzuna"
        assert summary["session_stats"]["total_sessions"] == 1
        assert summary["session_stats"]["total_messages"] == 8
