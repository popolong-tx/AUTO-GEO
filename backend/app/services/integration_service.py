"""Integration service for webhook and external API notifications.

This module handles:
1. Webhook notifications with retry mechanism
2. Lobster interface integration
3. Risk warning notifications
4. Event-based notification dispatch
"""

import asyncio
import hashlib
import hmac
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Optional

SETTINGS_FILE = Path(__file__).resolve().parents[2] / 'data' / 'integration_settings.json'

# Import the canonical DEFAULT_SETTINGS from the settings router to avoid duplication
from app.routers.settings import DEFAULT_SETTINGS


def load_integration_settings() -> dict:
    """Load integration settings from file with defaults."""
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
    """Build list of enabled notification targets.

    Args:
        settings: Integration settings dict

    Returns:
        List of enabled target dicts
    """
    targets = [t for t in settings.get('targets', []) if t.get('enabled') and t.get('url')]
    if not targets and settings.get('general_webhook_enabled') and settings.get('general_webhook_url'):
        targets = [{
            'name': '默认Webhook',
            'url': settings.get('general_webhook_url', ''),
            'secret': settings.get('general_webhook_secret', ''),
            'description': '默认通用通知目标',
        }]
    return targets


def _compute_signature(payload: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for payload.

    Args:
        payload: Raw bytes of the payload
        secret: Secret key for signing

    Returns:
        Hex digest of HMAC-SHA256
    """
    return hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256,
    ).hexdigest()


def post_event(target: dict, payload: dict[str, Any]) -> dict:
    """Send a single webhook notification.

    Args:
        target: Target configuration with url, secret, name
        payload: Event payload to send

    Returns:
        Result dict with status information
    """
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    secret = target.get('secret', '')

    headers = {
        'Content-Type': 'application/json',
        'X-AUTOGEO-Event': payload.get('event', 'unknown'),
    }

    # Use HMAC signature if secret is provided
    if secret:
        signature = _compute_signature(payload_bytes, secret)
        headers['X-AUTOGEO-Signature-256'] = f'sha256={signature}'
        headers['X-AUTOGEO-Webhook-Secret'] = secret  # Legacy support

    request = urllib.request.Request(
        target['url'],
        data=payload_bytes,
        headers=headers,
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            body = resp.read().decode('utf-8', 'ignore')
            return {
                'target': target.get('name', 'default'),
                'ok': True,
                'status': resp.status,
                'response_preview': body[:300],
            }
    except urllib.error.HTTPError as e:
        return {
            'target': target.get('name', 'default'),
            'ok': False,
            'status': e.code,
            'error': f'HTTP {e.code}',
            'detail': e.read().decode('utf-8', 'ignore')[:500],
        }
    except urllib.error.URLError as e:
        return {
            'target': target.get('name', 'default'),
            'ok': False,
            'error': 'URL Error',
            'detail': str(getattr(e, 'reason', e)),
        }
    except Exception as e:
        return {
            'target': target.get('name', 'default'),
            'ok': False,
            'error': type(e).__name__,
            'detail': str(e),
        }


async def post_event_with_retry(
    target: dict,
    payload: dict[str, Any],
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> dict:
    """Send webhook notification with exponential backoff retry.

    Args:
        target: Target configuration
        payload: Event payload
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)

    Returns:
        Result dict from final attempt
    """
    last_result = None

    for attempt in range(max_retries):
        result = await asyncio.to_thread(post_event, target, payload)
        last_result = result

        if result.get('ok'):
            result['attempt'] = attempt + 1
            return result

        # Don't retry on client errors (4xx)
        status = result.get('status')
        if status and 400 <= status < 500:
            result['attempt'] = attempt + 1
            result['retryable'] = False
            return result

        # Wait before retry (exponential backoff)
        if attempt < max_retries - 1:
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)

    last_result['attempt'] = max_retries
    last_result['retryable'] = False
    return last_result


async def async_post_event(target: dict, payload: dict[str, Any]) -> dict:
    """Async wrapper around post_event to avoid blocking the event loop.

    Args:
        target: Target configuration
        payload: Event payload

    Returns:
        Result dict
    """
    return await asyncio.to_thread(post_event, target, payload)


async def notify_event(event_name: str, payload: dict[str, Any]) -> dict:
    """Send notification to all enabled targets for an event.

    Args:
        event_name: Name of the event (e.g., 'analysis_completed')
        payload: Event payload data

    Returns:
        Aggregated results from all targets
    """
    settings = load_integration_settings()
    if not settings.get('events', {}).get(event_name, False):
        return {'ok': False, 'skipped': True, 'reason': f'event_disabled:{event_name}', 'results': []}

    targets = build_targets(settings)
    if not targets:
        return {'ok': False, 'skipped': True, 'reason': 'no_enabled_targets', 'results': []}

    # Add event name to payload
    payload['event'] = event_name
    payload['timestamp'] = time.time()

    # Send to all targets with retry
    results = await asyncio.gather(
        *(post_event_with_retry(target, payload) for target in targets)
    )

    success_count = sum(1 for r in results if r.get('ok'))
    return {
        'ok': success_count > 0,
        'success_count': success_count,
        'failure_count': len(results) - success_count,
        'results': list(results),
    }


async def notify_risk_warning(
    topic_id: str,
    analysis_id: str,
    risk_level: str,
    warnings: list[str],
    sentiment: Optional[dict] = None,
) -> dict:
    """Send risk warning notification.

    Args:
        topic_id: Topic identifier
        analysis_id: Analysis result ID
        risk_level: Risk level (high/medium/low)
        warnings: List of warning messages
        sentiment: Sentiment scores

    Returns:
        Notification result
    """
    payload = {
        'event': 'risk_warning',
        'topic_id': topic_id,
        'analysis_id': analysis_id,
        'risk_level': risk_level,
        'warnings': warnings,
        'sentiment': sentiment or {},
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }

    settings = load_integration_settings()
    targets = build_targets(settings)

    if not targets:
        return {'ok': False, 'skipped': True, 'reason': 'no_enabled_targets'}

    # Send to all targets with retry
    results = await asyncio.gather(
        *(post_event_with_retry(target, payload) for target in targets)
    )

    success_count = sum(1 for r in results if r.get('ok'))
    return {
        'ok': success_count > 0,
        'success_count': success_count,
        'failure_count': len(results) - success_count,
        'results': list(results),
    }


async def notify_lobster(
    lobster_url: str,
    payload: dict[str, Any],
    api_key: Optional[str] = None,
) -> dict:
    """Send notification to Lobster interface.

    Args:
        lobster_url: Lobster API endpoint URL
        payload: Payload to send
        api_key: Optional API key for authentication

    Returns:
        Result dict
    """
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')

    headers = {
        'Content-Type': 'application/json',
        'X-AUTOGEO-Source': 'auto-geo',
    }

    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
        signature = _compute_signature(payload_bytes, api_key)
        headers['X-AUTOGEO-Signature-256'] = f'sha256={signature}'

    request = urllib.request.Request(
        lobster_url,
        data=payload_bytes,
        headers=headers,
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            body = resp.read().decode('utf-8', 'ignore')
            return {
                'target': 'lobster',
                'ok': True,
                'status': resp.status,
                'response_preview': body[:500],
            }
    except urllib.error.HTTPError as e:
        return {
            'target': 'lobster',
            'ok': False,
            'status': e.code,
            'error': f'HTTP {e.code}',
            'detail': e.read().decode('utf-8', 'ignore')[:500],
        }
    except urllib.error.URLError as e:
        return {
            'target': 'lobster',
            'ok': False,
            'error': 'URL Error',
            'detail': str(getattr(e, 'reason', e)),
        }
    except Exception as e:
        return {
            'target': 'lobster',
            'ok': False,
            'error': type(e).__name__,
            'detail': str(e),
        }


async def notify_analysis_complete(
    topic_id: str,
    analysis_id: str,
    model: str,
    sentiment: dict,
    content_preview: str,
    risk_level: Optional[str] = None,
    warnings: Optional[list[str]] = None,
    report_url: Optional[str] = None,
    pdf_url: Optional[str] = None,
) -> dict:
    """Send comprehensive analysis completion notification.

    Args:
        topic_id: Topic identifier
        analysis_id: Analysis result ID
        model: Model used for analysis
        sentiment: Sentiment scores
        content_preview: Preview of report content
        risk_level: Optional risk level assessment
        warnings: Optional list of warnings
        report_url: Optional URL to full report
        pdf_url: Optional URL to PDF report

    Returns:
        Aggregated notification results
    """
    payload = {
        'event': 'analysis_completed',
        'topic_id': topic_id,
        'analysis_id': analysis_id,
        'model': model,
        'sentiment': sentiment,
        'content_preview': content_preview[:1500],
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }

    # Add optional fields
    if risk_level:
        payload['risk_level'] = risk_level
    if warnings:
        payload['warnings'] = warnings
    if report_url:
        payload['report_url'] = report_url
    if pdf_url:
        payload['pdf_url'] = pdf_url

    # Send webhook notification
    webhook_result = await notify_event('analysis_completed', payload)

    # Send risk warning if high risk
    risk_result = None
    if risk_level == 'high' and warnings:
        risk_result = await notify_risk_warning(
            topic_id=topic_id,
            analysis_id=analysis_id,
            risk_level=risk_level,
            warnings=warnings,
            sentiment=sentiment,
        )

    # Send to Lobster if configured
    lobster_result = None
    settings = load_integration_settings()
    lobster_url = settings.get('lobster_url')
    if lobster_url:
        lobster_result = await notify_lobster(
            lobster_url=lobster_url,
            payload=payload,
            api_key=settings.get('lobster_api_key'),
        )

    return {
        'webhook': webhook_result,
        'risk_warning': risk_result,
        'lobster': lobster_result,
    }
