"""Shared in-memory data store with JSON persistence for reports, dashboard data, and refresh config."""

import json
import os
from app.models.topic import AnalysisResult, RefreshConfig

# Eviction limits to prevent unbounded memory growth
MAX_ANALYSIS_HISTORY_PER_TOPIC = 20
MAX_REPORTS_PER_TOPIC = 50

# Global analysis history: topic_id -> list of AnalysisResult
analysis_history: dict[str, list[AnalysisResult]] = {}


def add_analysis_result(topic_id: str, result: AnalysisResult):
    """Add an analysis result to history with eviction."""
    if topic_id not in analysis_history:
        analysis_history[topic_id] = []
    analysis_history[topic_id].insert(0, result)
    # Evict oldest results if we exceed the limit
    if len(analysis_history[topic_id]) > MAX_ANALYSIS_HISTORY_PER_TOPIC:
        analysis_history[topic_id] = analysis_history[topic_id][:MAX_ANALYSIS_HISTORY_PER_TOPIC]


# Persistent reports history
REPORTS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports.json")
REPORT_SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "report_snapshots")

# Persistent dashboard data
DASHBOARD_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "dashboard.json")

# Persistent refresh configuration
REFRESH_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "refresh_config.json")


def _load_reports() -> dict:
    """Load reports from JSON file."""
    try:
        if os.path.exists(REPORTS_FILE):
            with open(REPORTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[store] load reports failed: {e}")
    return {}


def _save_json_atomic(path: str, data: dict, label: str):
    """Save JSON to file atomically."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_file = path + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, path)
    except Exception as e:
        print(f"[store] save {label} failed: {e}")


def _save_reports(data: dict):
    """Save reports to JSON file."""
    _save_json_atomic(REPORTS_FILE, data, "reports")


# Load on module import
reports_history: dict[str, list[dict]] = _load_reports()

# Load dashboard on module import
dashboard_data: dict = {}
try:
    if os.path.exists(DASHBOARD_FILE):
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            dashboard_data = json.load(f)
except Exception as e:
    print(f"[store] load dashboard failed: {e}")

refresh_config: RefreshConfig = RefreshConfig()
try:
    if os.path.exists(REFRESH_CONFIG_FILE):
        with open(REFRESH_CONFIG_FILE, "r", encoding="utf-8") as f:
            refresh_config = RefreshConfig.model_validate(json.load(f))
except Exception as e:
    print(f"[store] load refresh config failed: {e}")


def load_dashboard(topic_id: str | None = None) -> dict:
    """Load dashboard data from JSON file."""
    global dashboard_data
    try:
        if os.path.exists(DASHBOARD_FILE):
            with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
                dashboard_data = json.load(f)
        else:
            dashboard_data = {}
    except Exception as e:
        print(f"[store] load dashboard failed: {e}")
        dashboard_data = {}
    if topic_id:
        return dashboard_data.get(topic_id, {}) if isinstance(dashboard_data, dict) else {}
    return dashboard_data


def save_dashboard(topic_id: str | dict, data: dict | None = None):
    """Save dashboard data to JSON file.

    Backward compatible call forms:
    - save_dashboard(data_dict) -> saves full mapping
    - save_dashboard(topic_id, data_dict) -> saves one topic entry
    """
    global dashboard_data
    if data is None:
        dashboard_data = topic_id if isinstance(topic_id, dict) else {}
    else:
        if not isinstance(dashboard_data, dict):
            dashboard_data = {}
        dashboard_data[str(topic_id)] = data or {}
    _save_json_atomic(DASHBOARD_FILE, dashboard_data, "dashboard")


def get_dashboard(topic_id: str | None = None) -> dict:
    """Get in-memory dashboard data."""
    if topic_id:
        return dashboard_data.get(topic_id, {}) if isinstance(dashboard_data, dict) else {}
    return dashboard_data


def load_refresh_config() -> RefreshConfig:
    """Load refresh configuration from disk."""
    global refresh_config
    try:
        if os.path.exists(REFRESH_CONFIG_FILE):
            with open(REFRESH_CONFIG_FILE, "r", encoding="utf-8") as f:
                refresh_config = RefreshConfig.model_validate(json.load(f))
        else:
            refresh_config = RefreshConfig()
    except Exception as e:
        print(f"[store] load refresh config failed: {e}")
        refresh_config = RefreshConfig()
    return refresh_config


def save_refresh_config(config: RefreshConfig | dict):
    """Save refresh configuration to disk."""
    global refresh_config
    refresh_config = config if isinstance(config, RefreshConfig) else RefreshConfig.model_validate(config)
    _save_json_atomic(REFRESH_CONFIG_FILE, refresh_config.model_dump(), "refresh config")


def get_refresh_config() -> RefreshConfig:
    """Get in-memory refresh configuration."""
    return refresh_config


def add_report(topic_id: str, report: dict):
    """Add a generated report to history."""
    if topic_id not in reports_history:
        reports_history[topic_id] = []
    reports_history[topic_id].insert(0, report)
    # Evict oldest reports if we exceed the limit
    if len(reports_history[topic_id]) > MAX_REPORTS_PER_TOPIC:
        reports_history[topic_id] = reports_history[topic_id][:MAX_REPORTS_PER_TOPIC]
    _save_reports(reports_history)


def get_reports(topic_id: str) -> list[dict]:
    """Get all reports for a topic."""
    return reports_history.get(topic_id, [])


def delete_report(topic_id: str, report_id: str) -> bool:
    """Delete a report from history."""
    if topic_id not in reports_history:
        return False
    original_len = len(reports_history[topic_id])
    reports_history[topic_id] = [r for r in reports_history[topic_id] if r.get("id") != report_id]
    _save_reports(reports_history)
    return len(reports_history[topic_id]) < original_len


def clear_dashboard(topic_id: str | None = None) -> int:
    """Clear stored dashboard data."""
    global dashboard_data
    if topic_id:
        if isinstance(dashboard_data, dict) and topic_id in dashboard_data:
            dashboard_data.pop(topic_id, None)
            _save_json_atomic(DASHBOARD_FILE, dashboard_data, "dashboard")
            return 1
        return 0
    had_data = int(bool(dashboard_data))
    dashboard_data = {}
    _save_json_atomic(DASHBOARD_FILE, dashboard_data, "dashboard")
    return had_data


def update_refresh_config(enabled: bool | None = None, updates_per_day: int | None = None, update_hours: list[int] | None = None) -> RefreshConfig:
    """Update and persist refresh configuration."""
    global refresh_config
    data = refresh_config.model_dump()
    if enabled is not None:
        data["enabled"] = enabled
    if updates_per_day is not None:
        data["updates_per_day"] = updates_per_day
    if update_hours is not None:
        data["update_hours"] = update_hours
    refresh_config = RefreshConfig.model_validate(data)
    save_refresh_config(refresh_config)
    return refresh_config


def clear_topic_reports(topic_id: str) -> int:
    """Clear all stored reports for a topic."""
    if topic_id not in reports_history:
        return 0
    count = len(reports_history[topic_id])
    reports_history[topic_id] = []
    _save_reports(reports_history)
    return count


def clear_all_reports() -> int:
    """Clear all stored reports across topics."""
    count = sum(len(v) for v in reports_history.values())
    reports_history.clear()
    _save_reports(reports_history)
    return count


def _snapshot_file(topic_id: str, report_id: str) -> str:
    base = os.path.join(os.path.dirname(__file__), "..", "..", "data", "report_snapshots", topic_id)
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"{report_id}.json")


def save_report_snapshot(topic_id: str, report_id: str, report: dict):
    with open(_snapshot_file(topic_id, report_id), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def load_report_snapshot(topic_id: str, report_id: str) -> dict | None:
    path = _snapshot_file(topic_id, report_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_report_snapshots(topic_id: str | None = None) -> int:
    base = os.path.join(os.path.dirname(__file__), "..", "..", "data", "report_snapshots")
    if not os.path.exists(base):
        return 0
    removed = 0
    if topic_id:
        topic_dir = os.path.join(base, topic_id)
        if os.path.exists(topic_dir):
            for fn in os.listdir(topic_dir):
                os.remove(os.path.join(topic_dir, fn))
                removed += 1
            try:
                os.rmdir(topic_dir)
            except OSError:
                pass
    else:
        for root, _, files in os.walk(base):
            for fn in files:
                os.remove(os.path.join(root, fn))
                removed += 1
    return removed
