"""Dashboard API routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.routers.topics import _topics
from app.routers.auth import require_auth
from app.utils.store import clear_dashboard, get_dashboard, load_dashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _get_topic_dashboard(topic_id: str) -> dict:
    dashboard = get_dashboard(topic_id)
    if not dashboard:
        dashboard = load_dashboard(topic_id)
    return dashboard if isinstance(dashboard, dict) else {}


def _parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_iso_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/{topic_id}")
async def get_topic_dashboard_view(topic_id: str):
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")
    dashboard = _get_topic_dashboard(topic_id)
    return {"topic_id": topic_id, "dashboard": dashboard}


@router.get("/{topic_id}/refresh-status")
async def get_topic_refresh_status(topic_id: str):
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")

    dashboard = _get_topic_dashboard(topic_id)
    refreshed_at = _parse_iso_datetime(
        dashboard.get("last_refreshed_at")
        or dashboard.get("generated_at")
        or dashboard.get("updated_at")
    )

    refresh_interval_minutes = dashboard.get("refresh_interval_minutes")
    if not isinstance(refresh_interval_minutes, int) or refresh_interval_minutes <= 0:
        refresh_interval_minutes = 60

    next_refresh_at = refreshed_at + timedelta(minutes=refresh_interval_minutes) if refreshed_at else None
    return {
        "topic_id": topic_id,
        "last_refreshed_at": _format_iso_datetime(refreshed_at),
        "next_refresh_at": _format_iso_datetime(next_refresh_at),
        "refresh_interval_minutes": refresh_interval_minutes,
    }


@router.get("/{topic_id}/sources")
async def get_topic_dashboard_sources(topic_id: str):
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")
    dashboard = _get_topic_dashboard(topic_id)
    return {"topic_id": topic_id, "sources": dashboard.get("sources", [])}


@router.get("/{topic_id}/sources/{source_id}")
async def get_topic_dashboard_source(topic_id: str, source_id: str):
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")
    dashboard = _get_topic_dashboard(topic_id)
    for item in dashboard.get("sources", []):
        if str(item.get("id", "")) == source_id:
            return item
    raise HTTPException(status_code=404, detail="Source not found")


@router.delete("/{topic_id}")
async def clear_topic_dashboard(topic_id: str, _user: str = Depends(require_auth)):
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")
    removed = clear_dashboard(topic_id)
    return {"topic_id": topic_id, "removed": removed}
