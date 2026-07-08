"""Sentiment analysis engine combining Object Storage data with Grok search.

This module orchestrates the analysis pipeline:
1. Data collection (via RawDataCollector)
2. Report generation (via ReportGenerator)
3. Result persistence and caching
"""

import json
import asyncio
import uuid
import os
from datetime import datetime
from typing import Optional, AsyncGenerator

from app.services.genai_client import GenAIClient
from app.services.object_storage import ObjectStorageService
from app.services.raw_data_collector import RawDataCollector
from app.services.report_generator import ReportGenerator
from app.models.topic import AnalysisResult


class AnalysisEngine:
    """Orchestrates sentiment analysis with multiple data sources.

    Uses RawDataCollector for data collection and ReportGenerator for report creation.
    """

    def __init__(self, genai_client: GenAIClient | None, storage_service: ObjectStorageService | None):
        self.genai = genai_client
        self.storage = storage_service
        self.analysis_timeout = 300  # 5 minutes for two-stage analysis
        self._daily_cache: dict[str, AnalysisResult] = {}
        self._collector = RawDataCollector(genai_client)
        self._generator = ReportGenerator(genai_client)

    def _analysis_day_key(self, topic_id: str, custom_title: str = "") -> str:
        """Generate cache key for daily analysis."""
        today = datetime.now().strftime("%Y-%m-%d")
        return f"{today}:{topic_id}:{custom_title.strip()}"

    def _snapshot_path(self, key: str) -> str:
        """Get path for snapshot file."""
        base = os.path.expanduser("~/.autogeo_daily_snapshots")
        os.makedirs(base, exist_ok=True)
        safe = key.replace(":", "__")
        return os.path.join(base, f"{safe}.json")

    def _snapshot_key(self, topic_id: str, custom_title: str = "") -> str:
        """Generate snapshot key."""
        return self._analysis_day_key(topic_id, custom_title)

    def _snapshot_meta_key(self, topic_id: str, custom_title: str = "") -> str:
        """Generate snapshot meta key."""
        return self._analysis_day_key(topic_id, custom_title) + ":meta"

    def _detect_major_event(self, text: str) -> bool:
        """Detect if content contains major event keywords."""
        import re
        patterns = [
            r"重大事件", r"突发", r"紧急", r"危机", r"收购", r"诉讼",
            r"召回", r"事故", r"爆炸", r"裁员", r"制裁", r"禁令",
            r"SEC", r"DOJ", r"FDA", r"DOD", r"1260h", r"停产", r"破产",
        ]
        return any(re.search(p, text, re.I) for p in patterns)

    async def _snapshot_is_valid(self, topic_id: str, custom_title: str, prompt: str, current_payload: Optional[dict] = None) -> bool:
        """Check if snapshot is still valid."""
        import json
        meta_path = self._snapshot_path(self._snapshot_meta_key(topic_id, custom_title))
        if not os.path.exists(meta_path):
            return False
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            return False
        if meta.get("prompt") != prompt:
            return False
        if self._detect_major_event(current_payload.get("content", "") if current_payload else ""):
            return False
        return True

    async def _load_daily_snapshot(self, topic_id: str, custom_title: str = "") -> Optional[dict]:
        """Load snapshot from disk."""
        import json
        path = self._snapshot_path(self._snapshot_key(topic_id, custom_title))
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    async def _save_daily_snapshot(self, topic_id: str, custom_title: str, payload: dict) -> None:
        """Save snapshot to disk."""
        import json
        path = self._snapshot_path(self._snapshot_key(topic_id, custom_title))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _clear_daily_state(self, topic_id: str, custom_title: str = "") -> None:
        """Clear cached state for a topic."""
        day_key = self._analysis_day_key(topic_id, custom_title)
        self._daily_cache.pop(day_key, None)
        for key in [self._snapshot_key(topic_id, custom_title), self._snapshot_meta_key(topic_id, custom_title)]:
            path = self._snapshot_path(key)
            if os.path.exists(path):
                os.remove(path)

    async def _load_uploaded_files(
        self,
        uploaded_files: list[dict],
        data_bucket: str,
    ) -> tuple[list[dict], list[dict]]:
        """Process uploaded files and extract text/images.

        Args:
            uploaded_files: List of uploaded file metadata
            data_bucket: Object Storage bucket name

        Returns:
            Tuple of (merged_uploaded_files, image_inputs)
        """
        ref_texts = []
        image_inputs = []

        if not self.storage:
            return uploaded_files or [], []

        for item in uploaded_files:
            storage_path = item.get("storage_path")
            if not storage_path:
                continue

            # Extract text
            extracted = await self.storage.extract_reference_text(data_bucket or "", storage_path)
            if extracted.get("data") or extracted.get("preview"):
                extra_fields = {}
                if extracted.get("format") == "excel":
                    extra_fields = {
                        "sheet_name": extracted.get("sheet_name") or item.get("sheet_name"),
                        "sheet_rows": extracted.get("sheet_rows") or item.get("sheet_rows"),
                        "excel_columns": extracted.get("columns") or item.get("excel_columns") or [],
                    }
                ref_texts.append({
                    "name": item.get("name", ""),
                    "storage_path": storage_path,
                    "text": extracted.get("preview") or extracted.get("data"),
                    "url": item.get("url", ""),
                    **extra_fields,
                })

            # Extract images
            base64_ref = await self.storage.read_reference_base64(data_bucket or "", storage_path)
            if base64_ref.get("base64"):
                image_inputs.append(base64_ref)
                ref_texts.append({
                    "name": item.get("name", ""),
                    "storage_path": storage_path,
                    "text": f"IMAGE_BASE64::{storage_path}::{base64_ref.get('token_hint', '')}",
                    "url": item.get("url", ""),
                })

        # Merge extracted text into uploaded files
        merged_uploaded_files = uploaded_files or []
        if ref_texts:
            merged_uploaded_files = [
                {**item, "extracted_text": next((r["text"] for r in ref_texts if r["storage_path"] == item.get("storage_path")), "")}
                for item in merged_uploaded_files
            ]

        return merged_uploaded_files, image_inputs

    def _add_force_refresh_marker(self, content: str, report_language: str) -> str:
        """Add force refresh marker to content if applicable."""
        refresh_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if report_language == "en":
            return f'[Re-analysis Mark]\nThis report was force-regenerated by "Re-analyze".\nRegeneration time: {refresh_stamp}\n\n' + content
        else:
            return f'【重分析标记】\n本报告由"重新分析"触发强制重生成。\n重生成时间：{refresh_stamp}\n\n' + content

    async def analyze(
        self,
        topic_id: str,
        prompt: str,
        model: Optional[str] = None,
        data_source_path: Optional[str] = None,
        data_bucket: str = "",
        uploaded_files: Optional[list[dict]] = None,
        custom_title: str = "",
        social_updates_limit: int = 10,
        force_refresh: bool = False,
        report_language: str = "zh",
        target_region: str = "global",
    ) -> AnalysisResult:
        """Run full analysis pipeline.

        Args:
            topic_id: Topic identifier
            prompt: Analysis prompt
            model: Model ID to use
            data_source_path: Object Storage data file path
            data_bucket: Object Storage bucket
            uploaded_files: User uploaded files
            custom_title: Custom report title
            social_updates_limit: Max social updates to collect
            force_refresh: Force re-analysis ignoring cache
            report_language: Output language (zh/en/bilingual)
            target_region: Target geographic region

        Returns:
            AnalysisResult with content, sentiment, etc.
        """
        # Check cache
        day_key = self._analysis_day_key(topic_id, custom_title)
        if force_refresh:
            self._clear_daily_state(topic_id, custom_title)

        cached = self._daily_cache.get(day_key)
        if cached is not None and not force_refresh:
            return cached

        # Check snapshot
        snapshot = await self._load_daily_snapshot(topic_id, custom_title)
        if snapshot and not force_refresh and await self._snapshot_is_valid(topic_id, custom_title, prompt, snapshot):
            result = AnalysisResult(
                id=snapshot["id"],
                topic_id=snapshot["topic_id"],
                model=snapshot["model"],
                prompt=snapshot["prompt"],
                content=snapshot["content"],
                sentiment=snapshot["sentiment"],
                created_at=datetime.fromisoformat(snapshot["created_at"]),
            )
            self._daily_cache[day_key] = result
            return result

        # Load external data
        data_content = None
        if data_source_path and data_bucket and self.storage:
            data_content = await self.storage.read_data_file(data_bucket, data_source_path)

        # Process uploaded files
        merged_uploaded_files, image_inputs = await self._load_uploaded_files(
            uploaded_files or [], data_bucket
        )

        # Generate analysis ID upfront for file isolation
        analysis_id = str(uuid.uuid4())

        # Step 1: Collect raw social data
        raw_search_data = await self._collector.collect(
            prompt, model, social_updates_limit
        )

        # Save raw data as markdown report in isolated directory
        markdown_report = self._collector.generate_markdown_report(
            topic_id, raw_search_data, merged_uploaded_files, model or ""
        )
        self._collector.save_raw_data(topic_id, raw_search_data, markdown_report, analysis_id)

        # Add delay between API calls to avoid rate limits
        await asyncio.sleep(5)

        # Step 2: Generate analysis report
        content = await self._generator.generate(
            prompt=prompt,
            model=model,
            data_content=data_content,
            uploaded_files=merged_uploaded_files,
            image_inputs=image_inputs,
            social_updates_limit=social_updates_limit,
            raw_search_data=raw_search_data,
            report_language=report_language,
            target_region=target_region,
        )

        # Add force refresh marker if applicable
        if force_refresh:
            content = self._add_force_refresh_marker(content, report_language)

        # Parse sentiment
        sentiment = self._generator._parse_sentiment(content)

        # Create result
        result = AnalysisResult(
            id=analysis_id,
            topic_id=topic_id,
            model=self.genai.get_model_id(model),
            prompt=prompt,
            content=content,
            sentiment=sentiment,
            created_at=datetime.now(),
        )

        # Persist result
        self._daily_cache[day_key] = result
        payload = result.model_dump()
        await self._save_daily_snapshot(topic_id, custom_title, payload)
        await self._save_daily_snapshot(
            topic_id,
            custom_title + "__meta",
            {
                "prompt": prompt,
                "content": content[:4000],
                "force_refresh": force_refresh,
                "generated_at": datetime.now().isoformat(),
            },
        )

        return result

    async def analyze_stream(
        self,
        topic_id: str,
        prompt: str,
        model: Optional[str] = None,
        data_source_path: Optional[str] = None,
        data_bucket: str = "",
        uploaded_files: Optional[list[dict]] = None,
        custom_title: str = "",
        social_updates_limit: int = 10,
        force_refresh: bool = False,
        report_language: str = "zh",
        target_region: str = "global",
    ) -> AsyncGenerator[str, None]:
        """Run analysis with streaming response.

        Args:
            topic_id: Topic identifier
            prompt: Analysis prompt
            model: Model ID to use
            data_source_path: Object Storage data file path
            data_bucket: Object Storage bucket
            uploaded_files: User uploaded files
            custom_title: Custom report title
            social_updates_limit: Max social updates to collect
            force_refresh: Force re-analysis ignoring cache
            report_language: Output language (zh/en/bilingual)
            target_region: Target geographic region

        Yields:
            Streaming chunks, then final processed text with marker
        """
        if force_refresh:
            self._clear_daily_state(topic_id, custom_title)

        # Check daily cache
        day_key = self._analysis_day_key(topic_id, custom_title)
        cached = self._daily_cache.get(day_key)
        if cached is not None and not force_refresh:
            yield cached.content
            return

        # Check snapshot
        snapshot = await self._load_daily_snapshot(topic_id, custom_title)
        if snapshot and not force_refresh:
            yield snapshot["content"]
            return

        # Helper function to yield progress messages (separate from report content)
        def progress(msg: str):
            return f"\n__PROGRESS__\n{msg}\n__END_PROGRESS__\n"

        # Progress: Starting analysis
        is_en = report_language == "en"
        if is_en:
            yield progress("🔍 **Starting Analysis**")
        else:
            yield progress("🔍 **开始分析**")

        # Load external data
        data_content = None
        if data_source_path and data_bucket and self.storage:
            if is_en:
                yield progress("📂 Loading reference data from Object Storage...")
            else:
                yield progress("📂 正在从对象存储加载参考数据...")
            data_content = await self.storage.read_data_file(data_bucket, data_source_path)

        # Process uploaded files (only images for streaming)
        image_inputs = []
        if uploaded_files and self.storage:
            if is_en:
                yield progress(f"📎 Processing {len(uploaded_files)} uploaded files...")
            else:
                yield progress(f"📎 正在处理 {len(uploaded_files)} 个上传文件...")
            for item in uploaded_files:
                storage_path = item.get("storage_path")
                if not storage_path:
                    continue
                base64_ref = await self.storage.read_reference_base64(data_bucket or "", storage_path)
                if base64_ref.get("base64"):
                    image_inputs.append(base64_ref)

        # Generate analysis ID upfront for file isolation
        analysis_id = str(uuid.uuid4())

        # Step 1: Collect raw social data
        if is_en:
            yield progress("🌐 **Step 1/2: Collecting Raw Social Data**")
            yield progress(f"📡 Calling LLM with x_search / web_search tools (requesting {social_updates_limit * 3} candidates)...")
        else:
            yield progress("🌐 **第一步：采集原始社交数据**")
            yield progress(f"📡 正在调用大模型，使用 x_search / web_search 工具采集数据（请求 {social_updates_limit * 3} 条候选）...")

        raw_search_data = await self._collector.collect(
            prompt, model, social_updates_limit
        )

        # Show collection results
        summary = raw_search_data.get("collection_summary", {})
        verified_count = summary.get("verified_social_updates", 0)
        country_count = len(raw_search_data.get("country_coverage", []))
        trend_count = len(raw_search_data.get("trend", []))

        if is_en:
            yield progress(f"✅ **Data Collection Complete**")
            yield progress(f"- Verified social updates: **{verified_count}** items\n- Country coverage: **{country_count}** countries/regions\n- Trend data points: **{trend_count}** dates")
        else:
            yield progress(f"✅ **数据采集完成**")
            yield progress(f"- 验证通过的社交更新：**{verified_count}** 条\n- 国家覆盖：**{country_count}** 个国家/地区\n- 趋势数据点：**{trend_count}** 个日期")

        # Save raw data as markdown report in isolated directory
        markdown_report = self._collector.generate_markdown_report(
            topic_id, raw_search_data, uploaded_files, model or ""
        )
        self._collector.save_raw_data(topic_id, raw_search_data, markdown_report, analysis_id)

        if is_en:
            yield progress("💾 Raw data saved to local storage")
            yield progress("⏳ Waiting 5 seconds before next API call (rate limit protection)...")
        else:
            yield progress("💾 原始数据已保存到本地存储")
            yield progress("⏳ 等待 5 秒后进行下一次 API 调用（速率限制保护）...")

        # Add delay between API calls to avoid rate limits
        await asyncio.sleep(5)

        # Step 2: Generate analysis report with streaming
        if is_en:
            yield progress("📊 **Step 2/2: Generating Analysis Report**")
            yield progress("🧠 Calling LLM for deep analysis with root cause analysis and risk warnings...")
        else:
            yield progress("📊 **第二步：生成分析报告**")
            yield progress("🧠 正在调用大模型进行深度分析（包含根因分析和风险预警）...")

        final_text = None
        async for chunk in self._generator.generate_stream(
            prompt=prompt,
            model=model,
            data_content=data_content,
            uploaded_files=uploaded_files,
            image_inputs=image_inputs,
            social_updates_limit=social_updates_limit,
            raw_search_data=raw_search_data,
            report_language=report_language,
            target_region=target_region,
        ):
            # Capture the final processed text from the marker
            if chunk.startswith("\n__PROCESSED_FINAL__\n"):
                final_text = chunk[len("\n__PROCESSED_FINAL__\n"):]
            else:
                yield chunk

        # Save snapshot if we got final text
        if final_text:
            sentiment = self._generator._parse_sentiment(final_text)
            result_payload = {
                "id": analysis_id,
                "topic_id": topic_id,
                "model": self.genai.get_model_id(model),
                "prompt": prompt,
                "content": final_text,
                "sentiment": sentiment,
                "created_at": datetime.now().isoformat(),
            }
            await self._save_daily_snapshot(topic_id, custom_title, result_payload)
            await self._save_daily_snapshot(
                topic_id,
                custom_title + "__meta",
                {
                    "prompt": prompt,
                    "content": final_text[:4000],
                    "force_refresh": force_refresh,
                    "generated_at": datetime.now().isoformat(),
                },
            )
            self._daily_cache[self._analysis_day_key(topic_id, custom_title)] = AnalysisResult(
                id=result_payload["id"],
                topic_id=result_payload["topic_id"],
                model=result_payload["model"],
                prompt=result_payload["prompt"],
                content=result_payload["content"],
                sentiment=result_payload["sentiment"],
                created_at=datetime.fromisoformat(result_payload["created_at"]),
            )
