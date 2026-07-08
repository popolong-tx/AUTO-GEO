"""Latest Information API routes for real-time social media data collection."""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.routers.auth import require_auth
from app.services.genai_client import GenAIClient
from app.services.raw_data_collector import RawDataCollector
from app.services.pdf_generator import PDFGenerator

router = APIRouter(prefix="/api/latest-info", tags=["latest-info"])

# Service instances (set by main.py)
_collector: Optional[RawDataCollector] = None
_pdf_generator: Optional[PDFGenerator] = None


def set_dependencies(genai_client: GenAIClient, pdf_generator: PDFGenerator):
    """Set service dependencies."""
    global _collector, _pdf_generator
    _collector = RawDataCollector(genai_client)
    _pdf_generator = pdf_generator


class CollectRequest(BaseModel):
    """Request model for data collection."""
    topic: str
    social_updates_limit: int = 10
    model: Optional[str] = None
    language: str = "zh"


class ExportPdfRequest(BaseModel):
    """Request model for PDF export."""
    topic: str
    data: dict
    language: str = "zh"


@router.post("/collect")
async def collect_latest_info(req: CollectRequest, _user: str = Depends(require_auth)):
    """Collect latest social media information for a given topic.

    Uses x_search and web_search tools to fetch real-time data.
    """
    if not _collector:
        raise HTTPException(status_code=500, detail="Service not initialized")

    if not req.topic or len(req.topic.strip()) < 2:
        raise HTTPException(status_code=400, detail="Topic must be at least 2 characters")

    try:
        # Collect raw data
        raw_data = await _collector.collect(
            prompt=req.topic,
            model=req.model,
            social_updates_limit=req.social_updates_limit,
        )

        # Generate markdown report
        markdown_report = _collector.generate_markdown_report(
            topic_id=req.topic.replace(" ", "_")[:50],
            raw_data=raw_data,
            uploaded_files=None,
            model=req.model or "",
        )

        # Save to disk
        analysis_id = str(uuid.uuid4())
        _collector.save_raw_data(
            topic_id=req.topic.replace(" ", "_")[:50],
            raw_data=raw_data,
            markdown_report=markdown_report,
            analysis_id=analysis_id,
        )

        return {
            "success": True,
            "data": raw_data,
            "markdown": markdown_report,
            "analysis_id": analysis_id,
        }

    except Exception as e:
        import logging
        logging.exception("Failed to collect latest info")
        raise HTTPException(status_code=500, detail=f"Data collection failed: {str(e)}")


@router.post("/export-pdf")
async def export_latest_info_pdf(req: ExportPdfRequest, _user: str = Depends(require_auth)):
    """Export collected data as PDF report."""
    if not _pdf_generator:
        raise HTTPException(status_code=500, detail="PDF generator not initialized")

    try:
        # Build content from data
        data = req.data
        is_en = req.language == "en"

        lines = []

        # Title
        if is_en:
            lines.append(f"# Latest Information Report: {req.topic}")
            lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        else:
            lines.append(f"# 最新信息报告：{req.topic}")
            lines.append(f"\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Summary
        summary = data.get("collection_summary", {})
        social_count = summary.get("verified_social_updates", 0)
        country_count = len(data.get("country_coverage", []))
        trend_count = len(data.get("trend", []))
        ref_count = len(data.get("references", []))

        if is_en:
            lines.append("## Data Overview")
            lines.append(f"- Social Updates: {social_count} items")
            lines.append(f"- Country Coverage: {country_count} countries/regions")
            lines.append(f"- Trend Data Points: {trend_count} dates")
            lines.append(f"- References: {ref_count} sources\n")
        else:
            lines.append("## 数据概览")
            lines.append(f"- 社交媒体更新：{social_count} 条")
            lines.append(f"- 国家覆盖：{country_count} 个国家/地区")
            lines.append(f"- 趋势数据点：{trend_count} 个日期")
            lines.append(f"- 参考文献：{ref_count} 条来源\n")

        # Social Updates
        social_updates = data.get("social_updates", [])
        if is_en:
            lines.append(f"## Social Media Updates ({len(social_updates)} items)")
        else:
            lines.append(f"## 社交媒体更新 ({len(social_updates)} 条)")

        if social_updates:
            lines.append("")
            for item in social_updates:
                time_str = item.get("time", "")
                platform = item.get("platform", "")
                account = item.get("account", "")
                summary_text = item.get("summary", "")[:100]
                url = item.get("url", "")
                lines.append(f"- [{time_str}] {platform} - {account}")
                lines.append(f"  {summary_text}")
                lines.append(f"  Link: {url}\n")
        else:
            lines.append("No data available\n" if is_en else "暂无数据\n")

        # Country Coverage
        country_coverage = data.get("country_coverage", [])
        if is_en:
            lines.append(f"## Country Coverage ({len(country_coverage)} countries)")
        else:
            lines.append(f"## 国家覆盖 ({len(country_coverage)} 个国家)")

        if country_coverage:
            lines.append("")
            for item in country_coverage:
                country = item.get("country", "")
                coverage = item.get("coverage", 0)
                platforms = ", ".join(item.get("platforms", []))
                lines.append(f"- {country}: {coverage} items ({platforms})")
            lines.append("")
        else:
            lines.append("No data available\n" if is_en else "暂无数据\n")

        # Trend Data
        trend = data.get("trend", [])
        if is_en:
            lines.append(f"## Trend Data ({len(trend)} dates)")
        else:
            lines.append(f"## 趋势数据 ({len(trend)} 个日期)")

        if trend:
            lines.append("")
            for item in trend:
                date = item.get("date", "")
                mentions = item.get("mentions", 0)
                reach = item.get("reach", 0)
                lines.append(f"- {date}: {mentions} mentions, {reach} reach")
            lines.append("")
        else:
            lines.append("No data available\n" if is_en else "暂无数据\n")

        # References
        references = data.get("references", [])
        if is_en:
            lines.append(f"## References ({len(references)} sources)")
        else:
            lines.append(f"## 参考文献 ({len(references)} 条来源)")

        if references:
            lines.append("")
            for item in references:
                title = item.get("title", "")
                source = item.get("source", "")
                url = item.get("url", "")
                summary_text = item.get("summary", "")[:80]
                lines.append(f"- [{source}] {title}")
                lines.append(f"  {summary_text}")
                lines.append(f"  Link: {url}\n")
        else:
            lines.append("No data available\n" if is_en else "暂无数据\n")

        content = "\n".join(lines)

        # Generate PDF
        pdf_bytes = _pdf_generator.generate(
            topic_name=req.topic,
            content=content,
            sentiment=None,
            model="Latest Info Collection",
        )

        # Return as streaming response
        filename = f"LatestInfo_{req.topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        async def iter_pdf():
            yield pdf_bytes

        from urllib.parse import quote
        encoded_filename = quote(filename)

        return StreamingResponse(
            iter_pdf(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
        )

    except Exception as e:
        import logging
        logging.exception("Failed to export PDF")
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")
