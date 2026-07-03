"""Report generation and management API routes."""

import uuid
from datetime import datetime
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.routers.topics import _topics
from app.routers.auth import require_auth
from app.utils.store import analysis_history, add_report, get_reports, delete_report, clear_topic_reports, clear_all_reports, save_report_snapshot, load_report_snapshot, clear_report_snapshots

router = APIRouter(prefix="/api/reports", tags=["reports"])

_pdf_generator = None
_storage_service = None
_reports_bucket = "byd-geo-reports"


def set_dependencies(pdf_generator, storage_service, bucket):
    global _pdf_generator, _storage_service, _reports_bucket
    _pdf_generator = pdf_generator
    _storage_service = storage_service
    _reports_bucket = bucket


def _find_analysis(analysis_id: str):
    """Find analysis result by ID across all topics."""
    for topic_history in analysis_history.values():
        for result in topic_history:
            if result.id == analysis_id:
                return result
    return None


@router.post("/generate/{analysis_id}")
async def generate_report(analysis_id: str, _user: str = Depends(require_auth)):
    """Generate PDF report and return directly as browser download."""
    try:
        analysis = _find_analysis(analysis_id)
        if not analysis:
            known = [r.id for h in analysis_history.values() for r in h]
            raise HTTPException(status_code=404, detail=f"Analysis not found: {analysis_id}. Known: {known}")

        topic = _topics.get(analysis.topic_id)
        topic_name = topic.name if topic else analysis.topic_id

        pdf_bytes = _pdf_generator.generate(
            topic_name=topic_name,
            content=analysis.content,
            sentiment=analysis.sentiment,
            model=analysis.model,
        )
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.exception("Error generating report")
        raise HTTPException(status_code=500, detail="报告生成失败，请稍后重试")

    # Record report in history
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_id = str(uuid.uuid4())[:8]
    filename = f"BYD_{topic_name}_{timestamp}.pdf"

    report_record = {
        "id": report_id,
        "analysis_id": analysis_id,
        "topic_id": analysis.topic_id,
        "topic_name": topic_name,
        "filename": filename,
        "size": len(pdf_bytes),
        "model": analysis.model,
        "content": analysis.content,
        "sentiment": analysis.sentiment,
        "created_at": datetime.now().isoformat(),
    }
    add_report(analysis.topic_id, report_record)
    save_report_snapshot(analysis.topic_id, report_id, report_record)

    # Best effort upload to Object Storage
    if _storage_service:
        try:
            object_name = f"reports/{analysis.topic_id}/{timestamp}_{report_id}.pdf"
            await _storage_service.upload_report(
                bucket=_reports_bucket, object_name=object_name, content=pdf_bytes,
            )
        except Exception:
            pass

    encoded_filename = quote(filename)

    async def iter_pdf():
        yield pdf_bytes

    return StreamingResponse(
        iter_pdf(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@router.get("/download/{topic_id}/{report_id}")
async def download_report(topic_id: str, report_id: str):
    """Download a report PDF by regenerating from stored data."""
    reports = get_reports(topic_id)
    report = next((r for r in reports if r.get("id") == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    content = report.get("content", "")
    sentiment = report.get("sentiment", {"positive": 0.33, "neutral": 0.34, "negative": 0.33})
    model = report.get("model", "")
    topic_name = report.get("topic_name", topic_id)

    pdf_bytes = _pdf_generator.generate(
        topic_name=topic_name,
        content=content,
        sentiment=sentiment,
        model=model,
    )

    filename = report.get("filename", f"BYD_{topic_name}.pdf")
    encoded_filename = quote(filename)

    async def iter_pdf():
        yield pdf_bytes

    return StreamingResponse(
        iter_pdf(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@router.get("/list/{topic_id}")
async def list_reports(topic_id: str):
    """List all reports for a topic."""
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Use in-memory store (works with or without Object Storage)
    reports = get_reports(topic_id)

    # Rehydrate from snapshot files if the in-memory history was cleared
    try:
        import os
        snapshot_base = os.path.join(os.path.dirname(__file__), "..", "..", "data", "report_snapshots", topic_id)
        if os.path.exists(snapshot_base):
            for report_id in os.listdir(snapshot_base):
                if not any(r.get("id") == report_id.replace('.json','') for r in reports):
                    snapshot = load_report_snapshot(topic_id, report_id.replace('.json',''))
                    if snapshot:
                        reports.append(snapshot)
    except Exception:
        pass

    # If Object Storage is configured, merge with stored reports
    if _storage_service:
        try:
            os_reports = await _storage_service.list_reports(bucket=_reports_bucket, topic_id=topic_id)
            for report in os_reports:
                report_name = report.get("name", "")
                report["download_url"] = await _storage_service.get_presigned_url(
                    bucket=_reports_bucket, object_name=report_name,
                )
                report["filename"] = report.get("filename") or report_name.rsplit("/", 1)[-1]
            # Merge, avoiding duplicates by stable filename
            existing_filenames = {r.get("filename") for r in reports if r.get("filename")}
            for os_r in os_reports:
                if os_r.get("filename") not in existing_filenames:
                    reports.append(os_r)
        except Exception:
            pass

    return {"reports": reports}


@router.delete("/{topic_id}/{report_id}")
async def delete_report_endpoint(topic_id: str, report_id: str, _user: str = Depends(require_auth)):
    """Delete a report from history."""
    success = delete_report(topic_id, report_id)
    if not success:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"status": "success"}


@router.post("/clear/{topic_id}")
async def clear_topic(topic_id: str, _user: str = Depends(require_auth)):
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")
    count = clear_topic_reports(topic_id)
    clear_report_snapshots(topic_id)
    return {"status": "success", "cleared": count}


@router.post("/clear-all")
async def clear_all(_user: str = Depends(require_auth)):
    count = clear_all_reports()
    clear_report_snapshots(None)
    return {"status": "success", "cleared": count}
