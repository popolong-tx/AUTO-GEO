import asyncio
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

SETTINGS_FILE = Path(__file__).resolve().parents[2] / 'data' / 'integration_settings.json'

# Import the canonical DEFAULT_SETTINGS from the settings router to avoid duplication
from app.routers.settings import DEFAULT_SETTINGS


def load_integration_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        data = json.loads(SETTINGS_FILE.read_text())
        merged = {**DEFAULT_SETTINGS, **data}
        merged['events'] = {**DEFAULT_SETTINGS['events'], **data.get('events', {})}
        merged['targets'] = data.get('targets', [])
        return merged
    except Exception:
        return DEFAULT_SETTINGS.copy()


def build_targets(settings: dict) -> list[dict]:
    targets = [t for t in settings.get('targets', []) if t.get('enabled') and t.get('url')]
    if not targets and settings.get('general_webhook_enabled') and settings.get('general_webhook_url'):
        targets = [{
            'name': '默认Webhook',
            'url': settings.get('general_webhook_url', ''),
            'secret': settings.get('general_webhook_secret', ''),
            'description': '默认通用通知目标',
        }]
    return targets


def post_event(target: dict, payload: dict[str, Any]) -> dict:
    request = urllib.request.Request(
        target['url'],
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'X-BYDGEO-Webhook-Secret': target.get('secret', ''),
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            body = resp.read().decode('utf-8', 'ignore')
            return {'target': target.get('name', 'default'), 'ok': True, 'status': resp.status, 'response_preview': body[:300]}
    except urllib.error.HTTPError as e:
        return {'target': target.get('name', 'default'), 'ok': False, 'status': e.code, 'error': f'HTTP {e.code}', 'detail': e.read().decode('utf-8', 'ignore')[:500]}
    except urllib.error.URLError as e:
        return {'target': target.get('name', 'default'), 'ok': False, 'error': 'URL Error', 'detail': str(getattr(e, 'reason', e))}
    except Exception as e:
        return {'target': target.get('name', 'default'), 'ok': False, 'error': type(e).__name__, 'detail': str(e)}


async def async_post_event(target: dict, payload: dict[str, Any]) -> dict:
    """Async wrapper around post_event to avoid blocking the event loop."""
    return await asyncio.to_thread(post_event, target, payload)


async def notify_event(event_name: str, payload: dict[str, Any]) -> dict:
    settings = load_integration_settings()
    if not settings.get('events', {}).get(event_name, False):
        return {'ok': False, 'skipped': True, 'reason': f'event_disabled:{event_name}', 'results': []}
    targets = build_targets(settings)
    if not targets:
        return {'ok': False, 'skipped': True, 'reason': 'no_enabled_targets', 'results': []}
    results = await asyncio.gather(*(async_post_event(target, payload) for target in targets))
    success_count = sum(1 for r in results if r.get('ok'))
    return {'ok': success_count > 0, 'success_count': success_count, 'failure_count': len(results) - success_count, 'results': list(results)}
