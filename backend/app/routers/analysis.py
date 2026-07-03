"""Analysis API routes with SSE streaming support."""

import uuid
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sse_starlette.sse import EventSourceResponse

from app.models.topic import AnalysisRequest, AnalysisResult
from app.services.dashboard_service import DashboardService
from app.routers.topics import _topics
from app.routers.auth import require_auth
from app.utils.store import analysis_history, add_analysis_result, clear_topic_reports, clear_report_snapshots, save_dashboard
from app.services.integration_service import notify_event

LOCAL_REFERENCE_UPLOADS = {}
REQUEST_REFERENCE_UPLOADS = {}

MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_UPLOAD_CACHE_ITEMS = 50
UPLOAD_CACHE_TTL_SECONDS = 3600  # 1 hour

router = APIRouter(prefix="/api/analyze", tags=["analysis"])

@router.post("/upload-reference-local")
async def upload_reference_file_local(topic_id: str = Form(...), file: UploadFile = File(...), _user: str = Depends(require_auth)):
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")
    content = bytearray()
    while True:
        chunk = await file.read(8192)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail=f"文件大小超过限制（最大 {MAX_UPLOAD_SIZE // 1024 // 1024} MB）")
    content = bytes(content)
    safe_name = file.filename or "reference_file"
    _evict_expired_uploads()
    upload_id = uuid.uuid4().hex
    storage_path = f"refs/{topic_id}/{upload_id[:8]}_{safe_name}"
    import time
    REQUEST_REFERENCE_UPLOADS[upload_id] = {
        "content": content,
        "content_type": file.content_type or "application/octet-stream",
        "name": safe_name,
        "topic_id": topic_id,
        "storage_path": storage_path,
        "_uploaded_at": time.time(),
    }
    return {
        "name": safe_name,
        "url": f"/api/analyze/reference-local/{upload_id}",
        "storage_path": storage_path,
        "upload_id": upload_id,
        "content_type": file.content_type,
        "size": len(content),
        "local": True,
    }

@router.get("/reference-local/{upload_id}")
async def get_local_reference(upload_id: str):
    item = REQUEST_REFERENCE_UPLOADS.get(upload_id)
    if not item:
        raise HTTPException(status_code=404, detail="Local reference not found")
    return {"name": item["name"], "content_type": item["content_type"], "size": len(item["content"]) }

_engine = None


def set_engine(engine):
    global _engine
    _engine = engine


async def _cleanup_request_uploads(upload_ids: list[str]):
    for upload_id in upload_ids:
        REQUEST_REFERENCE_UPLOADS.pop(upload_id, None)


def _evict_expired_uploads():
    """Remove uploads that have exceeded the TTL or if cache is too large."""
    import time
    now = time.time()
    # Remove expired entries
    expired = [uid for uid, item in REQUEST_REFERENCE_UPLOADS.items()
               if now - item.get("_uploaded_at", now) > UPLOAD_CACHE_TTL_SECONDS]
    for uid in expired:
        REQUEST_REFERENCE_UPLOADS.pop(uid, None)
    # If still too many, remove oldest
    if len(REQUEST_REFERENCE_UPLOADS) > MAX_UPLOAD_CACHE_ITEMS:
        sorted_ids = sorted(REQUEST_REFERENCE_UPLOADS.keys(),
                           key=lambda uid: REQUEST_REFERENCE_UPLOADS[uid].get("_uploaded_at", 0))
        for uid in sorted_ids[:len(REQUEST_REFERENCE_UPLOADS) - MAX_UPLOAD_CACHE_ITEMS]:
            REQUEST_REFERENCE_UPLOADS.pop(uid, None)



def _save_dashboard_for_result(result):
    try:
        dashboard = DashboardService().build_from_analysis(result)
        topic_id = getattr(result, "topic_id", "")
        if topic_id:
            save_dashboard(topic_id, dashboard)
    except Exception as e:
        print(f"[analysis] dashboard save skipped: {e}")


@router.post("")
async def run_analysis(req: AnalysisRequest, _user: str = Depends(require_auth)):
    """Run analysis and return complete result."""
    if req.topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")

    topic = _topics[req.topic_id]
    data_source = req.data_source_path or topic.data_source_path
    clear_topic_reports(req.topic_id)
    clear_report_snapshots(req.topic_id)

    # For custom-report, prepend the custom title to the prompt
    prompt = topic.prompt
    if req.topic_id == "custom-report" and req.custom_title:
        prompt = f"针对「{req.custom_title}」进行分析。\n\n{topic.prompt}"

    request_uploads = []
    upload_ids = []
    for f in req.uploaded_files:
        item = f.model_dump()
        upload_id = item.get("upload_id")
        if upload_id and upload_id in REQUEST_REFERENCE_UPLOADS:
            payload = REQUEST_REFERENCE_UPLOADS[upload_id]
            item.setdefault("storage_path", payload.get("storage_path"))
            item.setdefault("content_type", payload.get("content_type"))
            item.setdefault("name", payload.get("name"))
            request_uploads.append(item)
            upload_ids.append(upload_id)
        else:
            request_uploads.append(item)

    try:
        result = await _engine.analyze(
            topic_id=req.topic_id,
            prompt=prompt,
            model=req.model,
            data_source_path=data_source,
            uploaded_files=request_uploads,
            custom_title=req.custom_title or "",
            social_updates_limit=req.social_updates_limit,
            force_refresh=getattr(req, "force_refresh", False),
        )
        add_analysis_result(req.topic_id, result)
        _save_dashboard_for_result(result)

        await notify_event('analysis_completed', {
            'event': 'analysis_completed',
            'topic_id': req.topic_id,
            'custom_title': req.custom_title or '',
            'analysis_id': result.id,
            'model': result.model,
            'created_at': result.created_at.isoformat(),
            'sentiment': result.sentiment,
            'content_preview': result.content[:1500],
        })

        try:
            from app.routers.reports import _pdf_generator, add_report
            from datetime import datetime as dt
            import uuid as _uuid
            if _pdf_generator:
                pdf_bytes = _pdf_generator.generate(
                    topic_name=topic.name,
                    content=result.content,
                    sentiment=result.sentiment,
                    model=result.model,
                )
                timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
                report_id = str(_uuid.uuid4())[:8]
                filename = f"BYD_{topic.name}_{timestamp}.pdf"
                add_report(req.topic_id, {
                    "id": report_id,
                    "analysis_id": result.id,
                    "topic_id": req.topic_id,
                    "topic_name": topic.name,
                    "filename": filename,
                    "size": len(pdf_bytes),
                    "model": result.model,
                    "content": result.content,
                    "sentiment": result.sentiment,
                    "created_at": dt.now().isoformat(),
                })
        except Exception as e:
            print(f"[analysis] report generation skipped: {e}")

        return result.model_dump()
    except asyncio.TimeoutError:
        await notify_event('error_alert', {
            'event': 'analysis_failed',
            'topic_id': req.topic_id,
            'custom_title': req.custom_title or '',
            'error_type': 'TimeoutError',
            'message': 'Analysis timed out',
        })
        raise HTTPException(status_code=504, detail="Analysis timed out")
    except Exception as e:
        import logging
        logging.exception("Analysis failed for topic %s", req.topic_id)
        await notify_event('error_alert', {
            'event': 'analysis_failed',
            'topic_id': req.topic_id,
            'custom_title': req.custom_title or '',
            'error_type': type(e).__name__,
            'message': str(e),
        })
        raise HTTPException(status_code=500, detail="分析失败，请稍后重试")
    finally:
        await _cleanup_request_uploads(upload_ids)


@router.post("/stream")
async def run_analysis_stream(req: AnalysisRequest, _user: str = Depends(require_auth)):
    """Run analysis with SSE streaming response."""
    if req.topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")

    topic = _topics[req.topic_id]
    data_source = req.data_source_path or topic.data_source_path
    clear_topic_reports(req.topic_id)
    clear_report_snapshots(req.topic_id)

    # For custom-report, prepend the custom title to the prompt
    prompt = topic.prompt
    if req.topic_id == "custom-report" and req.custom_title:
        prompt = f"针对「{req.custom_title}」进行分析。\n\n{topic.prompt}"

    async def event_generator():
        full_content = []
        request_uploads = []
        upload_ids = []
        for f in req.uploaded_files:
            item = f.model_dump()
            upload_id = item.get("upload_id")
            if upload_id and upload_id in REQUEST_REFERENCE_UPLOADS:
                payload = REQUEST_REFERENCE_UPLOADS[upload_id]
                item.setdefault("storage_path", payload.get("storage_path"))
                item.setdefault("content_type", payload.get("content_type"))
                item.setdefault("name", payload.get("name"))
                request_uploads.append(item)
                upload_ids.append(upload_id)
            else:
                request_uploads.append(item)
        try:
            processed_text = None
            async for chunk in _engine.analyze_stream(
                topic_id=req.topic_id,
                prompt=prompt,
                model=req.model,
                data_source_path=data_source,
                uploaded_files=request_uploads,
                custom_title=req.custom_title or "",
                social_updates_limit=req.social_updates_limit,
                force_refresh=getattr(req, "force_refresh", False),
            ):
                # The engine yields a special marker with the post-processed final text
                if chunk.startswith("\n__PROCESSED_FINAL__\n"):
                    processed_text = chunk[len("\n__PROCESSED_FINAL__\n"):]
                else:
                    full_content.append(chunk)
                    yield {"event": "chunk", "data": json.dumps({"text": chunk}, ensure_ascii=False)}

            # Use the post-processed text if available, otherwise fall back to raw
            full_text = processed_text if processed_text is not None else "".join(full_content)
            result = AnalysisResult(
                id=str(uuid.uuid4()),
                topic_id=req.topic_id,
                model=_engine.genai.get_model_id(req.model),
                prompt=prompt,
                content=full_text,
                sentiment=_engine._parse_sentiment(full_text),
                created_at=datetime.now(),
            )

            add_analysis_result(req.topic_id, result)
            _save_dashboard_for_result(result)

            await notify_event('analysis_completed', {
                'event': 'analysis_completed',
                'topic_id': req.topic_id,
                'custom_title': req.custom_title or '',
                'analysis_id': result.id,
                'model': result.model,
                'created_at': result.created_at.isoformat(),
                'sentiment': result.sentiment,
                'content_preview': full_text[:1500],
            })

            # Auto-generate PDF and add to report history
            try:
                from app.routers.reports import _pdf_generator, add_report
                from app.routers.topics import _topics as all_topics
                from datetime import datetime as dt
                import uuid as _uuid

                topic_obj = all_topics.get(req.topic_id)
                topic_name = topic_obj.name if topic_obj else req.topic_id

                if _pdf_generator:
                    pdf_bytes = _pdf_generator.generate(
                        topic_name=topic_name,
                        content=full_text,
                        sentiment=result.sentiment,
                        model=result.model,
                    )
                    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
                    report_id = str(_uuid.uuid4())[:8]
                    filename = f"BYD_{topic_name}_{timestamp}.pdf"

                    add_report(req.topic_id, {
                        "id": report_id,
                        "analysis_id": result.id,
                        "topic_id": req.topic_id,
                        "topic_name": topic_name,
                        "filename": filename,
                        "size": len(pdf_bytes),
                        "model": result.model,
                        "content": full_text,
                        "sentiment": result.sentiment,
                        "created_at": dt.now().isoformat(),
                    })
            except Exception as e:
                print(f"[analysis] stream report generation skipped: {e}")

            yield {"event": "done", "data": json.dumps({
                "id": result.id,
                "content": full_text,
                "sentiment": result.sentiment,
                "model": result.model,
                "created_at": result.created_at.isoformat(),
            }, ensure_ascii=False)}
        except Exception as e:
            await notify_event('error_alert', {
                'event': 'analysis_stream_failed',
                'topic_id': req.topic_id,
                'custom_title': req.custom_title or '',
                'error_type': type(e).__name__,
                'message': str(e),
            })
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())


@router.get("/history/{topic_id}")
async def get_analysis_history(topic_id: str):
    """Get analysis history for a topic."""
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")
    history = analysis_history.get(topic_id, [])
    return {"results": [r.model_dump() for r in history]}


@router.get("/result/{analysis_id}")
async def get_analysis_result(analysis_id: str):
    """Get a specific analysis result."""
    for topic_history in analysis_history.values():
        for result in topic_history:
            if result.id == analysis_id:
                return result.model_dump()
    raise HTTPException(status_code=404, detail="Analysis result not found")
