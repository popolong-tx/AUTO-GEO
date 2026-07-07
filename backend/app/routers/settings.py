from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routers.auth import require_auth

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTINGS_FILE = Path(__file__).resolve().parents[2] / 'data' / 'integration_settings.json'
SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_SETTINGS = {
    'general_webhook_enabled': False,
    'general_webhook_url': '',
    'general_webhook_secret': '',
    'general_webhook_note': '用于将通用分析结果通知到其他系统，也可供龙虾或其他系统回调/调用。',
    'events': {
        'analysis_completed': True,
        'report_generated': False,
        'upload_completed': False,
        'error_alert': False,
    },
    'targets': [
        {
            'name': '默认Webhook',
            'enabled': False,
            'url': '',
            'secret': '',
            'description': '默认通用通知目标',
        }
    ],
}


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        import json
        data = json.loads(SETTINGS_FILE.read_text())
        merged = {**DEFAULT_SETTINGS, **data}
        merged['events'] = {**DEFAULT_SETTINGS['events'], **data.get('events', {})}
        merged['targets'] = data.get('targets', DEFAULT_SETTINGS['targets'])
        return merged
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(data: dict) -> dict:
    import json
    merged = {**DEFAULT_SETTINGS, **data}
    merged['events'] = {**DEFAULT_SETTINGS['events'], **data.get('events', {})}
    merged['targets'] = data.get('targets', DEFAULT_SETTINGS['targets'])
    SETTINGS_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2))
    return merged


class WebhookTarget(BaseModel):
    name: str = '默认Webhook'
    enabled: bool = False
    url: str = ''
    secret: str = ''
    description: str = ''


class IntegrationSettingsRequest(BaseModel):
    general_webhook_enabled: bool = False
    general_webhook_url: str = ''
    general_webhook_secret: str = ''
    general_webhook_note: str = DEFAULT_SETTINGS['general_webhook_note']
    events: dict = DEFAULT_SETTINGS['events']
    targets: list[WebhookTarget] = DEFAULT_SETTINGS['targets']


@router.get('')
async def get_settings(_user: str = Depends(require_auth)):
    return load_settings()


@router.put('')
async def update_settings(req: IntegrationSettingsRequest, _user: str = Depends(require_auth)):
    return save_settings(req.model_dump())


@router.post('/test-webhook')
async def test_webhook(req: IntegrationSettingsRequest, _user: str = Depends(require_auth)):
    import asyncio
    from app.services.integration_service import async_post_event

    enabled_targets = [t for t in req.targets if t.enabled and t.url]
    if not enabled_targets:
        if not req.general_webhook_enabled or not req.general_webhook_url:
            raise HTTPException(status_code=400, detail='未配置可用的 Webhook 目标')
        enabled_targets = [{
            'name': '默认Webhook',
            'url': req.general_webhook_url,
            'secret': req.general_webhook_secret,
        }]

    test_payload = {
        'type': 'autogeo.test',
        'message': 'AUTO GEO 通用信息 Webhook 测试成功',
        'source': 'AUTO GEO',
    }
    results = await asyncio.gather(*(async_post_event(t, {**test_payload, 'target': t.get('name', 'default')}) for t in enabled_targets))

    success_count = sum(1 for r in results if r.get('ok'))
    return {
        'ok': success_count > 0,
        'success_count': success_count,
        'failure_count': len(results) - success_count,
        'results': results,
    }
