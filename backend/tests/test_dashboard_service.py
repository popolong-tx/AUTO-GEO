"""Tests for DashboardService parsing."""

from types import SimpleNamespace

from app.services.dashboard_service import DashboardService


def test_build_dashboard_parses_metrics_and_sources():
    service = DashboardService()
    analysis = SimpleNamespace(
        topic_id="topic-1",
        id="analysis-1",
        created_at="2026-06-30T12:00:00Z",
        sentiment={"positive": 0.6, "neutral": 0.3, "negative": 0.1},
        content="""
Total Mentions: 1,234
Total Reach: 56,789
Total AVE: 98.5

【参考文献】
- 来源: Example Article https://example.com/article
- Reddit discussion https://reddit.com/r/example
- 来源: Example Article https://example.com/article
""",
    )

    dashboard = service.build_dashboard(analysis)

    assert dashboard["topic_id"] == "topic-1"
    assert dashboard["analysis_id"] == "analysis-1"
    assert dashboard["generated_at"] == "2026-06-30T12:00:00Z"
    assert dashboard["sentiment"] == analysis.sentiment
    assert dashboard["metrics"]["Total Mentions"]["value"] == 1234
    assert dashboard["metrics"]["Total Reach"]["value"] == 56789
    assert dashboard["metrics"]["Total AVE"]["value"] == 98.5
    assert len(dashboard["sources"]) == 2
    assert dashboard["sources"][0]["title"] == "Example Article"
    assert dashboard["sources"][0]["url"] == "https://example.com/article"
    assert dashboard["sources"][0]["source_type"] == "reference"
    assert dashboard["sources"][1]["source_type"] == "social"


def test_build_from_analysis_uses_same_parsing():
    service = DashboardService()
    analysis = SimpleNamespace(
        topic_id="topic-2",
        id="analysis-2",
        created_at=None,
        sentiment={},
        content="""
mentions: 42
reach: 1,000
ave: 12.75

Some other text without source hints.
""",
    )

    dashboard = service.build_from_analysis(analysis)

    assert dashboard["metrics"]["Total Mentions"]["value"] == 42
    assert dashboard["metrics"]["Total Reach"]["value"] == 1000
    assert dashboard["metrics"]["Total AVE"]["value"] == 12.75
    assert dashboard["sources"] == []
