"""Raw social data collection, validation, and persistence.

This module handles:
1. Calling LLM to collect raw social media data (5x requested amount)
2. Processing uploaded files as data sources
3. Validating and deduplicating URLs
4. Generating MD temporary files for intermediate data
"""

import json
import re
import os
import asyncio
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

from app.services.genai_client import GenAIClient
from app.services.dashboard_service import DashboardService


# Default paths for temporary data storage
RAW_DATA_DIR = Path.home() / ".autogeo_raw_data"


class RawDataCollector:
    """Collects, validates, and persists raw social media data."""

    def __init__(self, genai_client: GenAIClient):
        self.genai = genai_client
        self._dashboard_service = DashboardService()
        self.analysis_timeout = 300
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _build_collection_prompt(
        self,
        base_prompt: str,
        social_updates_limit: int = 10,
        raw_candidates_limit: Optional[int] = None,
    ) -> str:
        """Build prompt for raw data collection phase."""
        raw_candidates_limit = raw_candidates_limit or max(social_updates_limit * 3, social_updates_limit)
        return f"""
你是舆情原始数据采集器。请只做检索和证据整理，不做长篇分析。

检索主题：
{base_prompt}

任务：
1. 使用 x_search 和 web_search 获取与主题相关的最新公开信息。
2. 只保留真实、具体、可点击的公开 URL；禁止输出示例链接、猜测链接、平台首页或占位链接。
3. 对 X/Twitter、Facebook、TikTok 等社交媒体链接要格外保守：如果不能确认是具体帖子/视频/文章 URL，就不要输出。
4. 输出 JSON，且只输出 JSON，不要 Markdown。

JSON schema：
{{
  "social_updates": [
    {{"time":"", "platform":"", "account":"", "summary":"", "url":"", "country":""}}
  ],
  "country_coverage": [
    {{"country":"", "coverage": 0, "platforms": [], "urls": []}}
  ],
  "trend": [
    {{"date":"YYYY-MM-DD", "mentions": 0, "reach": 0, "urls": []}}
  ],
  "references": [
    {{"title":"", "source":"", "url":"", "summary":""}}
  ]
}}

数量限制：先尽量抓取 social_updates 原始候选最多 {raw_candidates_limit} 条（约为用户选择 {social_updates_limit} 条的 2-3 倍），再由系统进行 URL 校验、去重和截断，最终 verified_social_updates 最多保留 {social_updates_limit} 条；country_coverage 最多 8 个国家/地区；trend 最多 14 个日期点；references 最多 12 条。
如果校验后真实可核验的社交媒体动态仍少于 {social_updates_limit} 条，不要补假数据；必须在 collection_summary 中说明 requested_social_updates、raw_candidates_requested、verified_social_updates、shortfall_reason。
country_coverage 的覆盖计数必须与已校验 evidence 对齐：能归属国家/地区的按真实国家/地区聚合；无法可靠归属国家/地区但 URL 真实的社媒/网页结果，统一放入"全球/未归属"，不要硬猜国家。这样国家覆盖总量应能解释社媒/网页证据总量，避免前后数量不一致。
trend 的 mentions 必须等于该日期下通过真实 URL 校验的社媒/新闻条目数量；reach 只有在检索结果明确给出浏览量、互动量、转发量、点赞量等可核验数字时才填写，否则填 0。每个 trend 点必须带 urls 证据列表；没有真实 URL 的日期不能输出。不要编造趋势、不要输出示例 Day 1/Day 2。
""".strip()

    def _extract_json_object(self, text: str) -> dict:
        """Extract JSON object from model response text."""
        if not text:
            return {}
        fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.I)
        raw = fence.group(1) if fence else text
        if not raw.strip().startswith("{"):
            start = raw.find("{")
            end = raw.rfind("}")
            raw = raw[start:end + 1] if start != -1 and end != -1 and end > start else "{}"
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _sanitize_raw_data(
        self,
        payload: dict,
        social_updates_limit: int = 10,
        raw_candidates_limit: Optional[int] = None,
    ) -> dict:
        """Validate and sanitize raw data from model response."""
        validator = self._dashboard_service
        raw_candidates_limit = raw_candidates_limit or max(social_updates_limit * 3, social_updates_limit)

        def clean_url(url: Any) -> str:
            if not url:
                return ""
            value = str(url).strip().rstrip(")],.，。；;:：")
            return value if validator._is_real_url(value) else ""

        def normalize_country(value: Any) -> str:
            text = str(value or "").strip().strip("*：:，,；;。")
            if not text:
                return "全球/未归属"
            lowered = text.lower()
            aliases = {
                "global": "全球/未归属", "worldwide": "全球/未归属", "international": "全球/未归属", "unknown": "全球/未归属",
                "us": "美国", "usa": "美国", "united states": "美国", "united states / us": "美国",
                "uk": "英国", "united kingdom": "英国", "united kingdom / uk": "英国",
                "china": "中国", "cn": "中国", "canada": "加拿大", "germany": "德国", "india": "印度",
                "japan": "日本", "france": "法国", "australia": "澳大利亚",
            }
            return aliases.get(lowered, text)

        def normalize_platforms(value: Any) -> list[str]:
            if value is None:
                return []
            values = value if isinstance(value, list) else [value]
            return [str(v)[:60] for v in values if str(v).strip()]

        # Process social updates
        social_updates = []
        seen_social_urls: set[str] = set()
        raw_social = payload.get("social_updates") if isinstance(payload, dict) else []
        raw_social_count = len(raw_social) if isinstance(raw_social, list) else 0
        invalid_social_count = 0

        for item in raw_social if isinstance(raw_social, list) else []:
            if not isinstance(item, dict):
                invalid_social_count += 1
                continue
            url = clean_url(item.get("url"))
            if not url or url in seen_social_urls:
                invalid_social_count += 1
                continue
            seen_social_urls.add(url)
            social_updates.append({
                "time": str(item.get("time", ""))[:80],
                "platform": str(item.get("platform", ""))[:60],
                "account": str(item.get("account", ""))[:120],
                "summary": str(item.get("summary", ""))[:500],
                "url": url,
                "country": normalize_country(item.get("country")),
            })
            if len(social_updates) >= social_updates_limit:
                break

        # Process country coverage
        country_map: dict[str, dict] = {}

        def add_country_evidence(country: str, url: str, platforms: list[str], summary: str = "") -> None:
            country = normalize_country(country)
            if not url:
                return
            entry = country_map.setdefault(country, {"country": country, "coverage": 0, "platforms": set(), "urls": [], "summary": ""})
            if url not in entry["urls"]:
                entry["urls"].append(url)
                entry["coverage"] += 1
            for platform in platforms:
                if platform:
                    entry["platforms"].add(platform)
            if summary and not entry["summary"]:
                entry["summary"] = summary[:240]

        raw_countries = payload.get("country_coverage") if isinstance(payload, dict) else []
        for item in raw_countries if isinstance(raw_countries, list) else []:
            if not isinstance(item, dict):
                continue
            country = normalize_country(item.get("country"))
            urls = [clean_url(url) for url in (item.get("urls") or [])]
            urls = [url for url in urls if url]
            platforms = normalize_platforms(item.get("platforms"))
            for url in urls:
                add_country_evidence(country, url, platforms, str(item.get("summary", "")))

        for item in social_updates:
            add_country_evidence(
                item.get("country") or "全球/未归属",
                item["url"],
                [item.get("platform") or validator._extract_platform(item.get("summary", ""), item["url"])],
                item.get("summary", ""),
            )

        country_coverage = [
            {"country": v["country"], "coverage": v["coverage"], "platforms": sorted(v["platforms"]), "urls": v["urls"], "summary": v.get("summary", "")}
            for v in country_map.values()
            if v["coverage"] > 0 and v["urls"]
        ]
        country_coverage.sort(key=lambda x: x["coverage"], reverse=True)

        # Process trend data
        trend = []
        raw_trend = payload.get("trend") if isinstance(payload, dict) else []
        for item in raw_trend if isinstance(raw_trend, list) else []:
            if not isinstance(item, dict):
                continue
            urls = [clean_url(url) for url in (item.get("urls") or [])]
            urls = [url for url in urls if url]
            date = str(item.get("date") or item.get("label") or "").strip()
            if not date:
                continue
            mentions = int(float(item.get("mentions") or len(urls) or 1))
            try:
                reach = int(float(item.get("reach") or 0))
            except Exception:
                reach = 0
            trend.append({"date": date[:40], "mentions": max(1, mentions), "reach": max(reach, 0), "urls": urls[:8]})
        trend.sort(key=lambda x: x["date"])

        # Process references
        references = []
        raw_refs = payload.get("references") if isinstance(payload, dict) else []
        for item in raw_refs if isinstance(raw_refs, list) else []:
            if not isinstance(item, dict):
                continue
            url = clean_url(item.get("url"))
            if not url:
                continue
            references.append({
                "title": str(item.get("title", ""))[:200],
                "source": str(item.get("source", ""))[:100],
                "url": url,
                "summary": str(item.get("summary", ""))[:500],
            })
            if len(references) >= 12:
                break

        # Build summary
        shortfall = max(0, social_updates_limit - len(social_updates))
        summary = {
            "requested_social_updates": social_updates_limit,
            "raw_candidates_requested": raw_candidates_limit,
            "raw_social_updates": raw_social_count,
            "verified_social_updates": len(social_updates),
            "invalid_or_duplicate_social_updates": invalid_social_count,
            "country_coverage_total": sum(item["coverage"] for item in country_coverage),
            "shortfall_reason": "真实可核验社媒 URL 少于设定值" if shortfall else "已达到设定值或真实结果上限",
        }

        return {
            "social_updates": social_updates,
            "country_coverage": country_coverage[:8],
            "trend": trend[:14],
            "references": references,
            "collection_summary": summary,
        }

    async def collect(
        self,
        prompt: str,
        model: Optional[str] = None,
        social_updates_limit: int = 10,
    ) -> dict:
        """Collect raw social data from LLM with search tools.

        Args:
            prompt: Base analysis prompt
            model: Model ID to use
            social_updates_limit: Number of verified social updates to return

        Returns:
            Validated and sanitized raw data dict
        """
        raw_candidates_limit = max(social_updates_limit * 3, social_updates_limit)
        collection_prompt = self._build_collection_prompt(
            prompt,
            social_updates_limit=social_updates_limit,
            raw_candidates_limit=raw_candidates_limit,
        )

        try:
            raw_text = await asyncio.wait_for(
                self.genai.analyze_with_tools(
                    collection_prompt,
                    model=model,
                    tools=[{"type": "x_search"}, {"type": "web_search"}],
                    max_tokens=max(4096, min(16000, 1800 + raw_candidates_limit * 120)),
                ),
                timeout=self.analysis_timeout,
            )
        except Exception as exc:
            return {
                "social_updates": [],
                "country_coverage": [],
                "references": [],
                "collection_summary": {
                    "requested_social_updates": social_updates_limit,
                    "raw_candidates_requested": raw_candidates_limit,
                    "verified_social_updates": 0,
                    "shortfall_reason": str(exc)[:300],
                },
                "collection_error": str(exc)[:300],
            }

        return self._sanitize_raw_data(
            self._extract_json_object(raw_text),
            social_updates_limit=social_updates_limit,
            raw_candidates_limit=raw_candidates_limit,
        )

    def generate_markdown_report(
        self,
        topic_id: str,
        raw_data: dict,
        uploaded_files: Optional[list[dict]] = None,
        model: str = "",
    ) -> str:
        """Generate a Markdown report of the raw data collection.

        Args:
            topic_id: Topic identifier
            raw_data: Sanitized raw data dict
            uploaded_files: List of uploaded file metadata
            model: Model used for collection

        Returns:
            Markdown formatted report string
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary = raw_data.get("collection_summary", {})

        lines = [
            f"# 原始数据采集报告",
            f"",
            f"- **主题**: {topic_id}",
            f"- **采集时间**: {timestamp}",
            f"- **模型**: {model}",
            f"",
        ]

        # Social updates section
        social_updates = raw_data.get("social_updates", [])
        lines.append(f"## 社交媒体更新 ({len(social_updates)} 条)")
        lines.append("")
        if social_updates:
            lines.append("| 时间 | 平台 | 账号 | 摘要 | URL | 国家 |")
            lines.append("|------|------|------|------|-----|------|")
            for item in social_updates:
                time = item.get("time", "")
                platform = item.get("platform", "")
                account = item.get("account", "")
                summary_text = item.get("summary", "")[:50]
                url = item.get("url", "")
                country = item.get("country", "")
                lines.append(f"| {time} | {platform} | {account} | {summary_text} | {url} | {country} |")
        else:
            lines.append("无验证通过的社交媒体更新")
        lines.append("")

        # Country coverage section
        country_coverage = raw_data.get("country_coverage", [])
        lines.append(f"## 国家覆盖 ({len(country_coverage)} 个国家)")
        lines.append("")
        if country_coverage:
            lines.append("| 国家 | 覆盖数 | 主要平台 | 证据URL |")
            lines.append("|------|--------|----------|---------|")
            for item in country_coverage:
                country = item.get("country", "")
                coverage = item.get("coverage", 0)
                platforms = ", ".join(item.get("platforms", []))
                urls = ", ".join(item.get("urls", [])[:3])
                lines.append(f"| {country} | {coverage} | {platforms} | {urls} |")
        else:
            lines.append("无验证通过的国家覆盖数据")
        lines.append("")

        # Trend data section
        trend = raw_data.get("trend", [])
        lines.append(f"## 趋势数据 ({len(trend)} 个日期点)")
        lines.append("")
        if trend:
            lines.append("| 日期 | 提及数 | 覆盖量 | 证据URL |")
            lines.append("|------|--------|--------|---------|")
            for item in trend:
                date = item.get("date", "")
                mentions = item.get("mentions", 0)
                reach = item.get("reach", 0)
                urls = ", ".join(item.get("urls", [])[:2])
                lines.append(f"| {date} | {mentions} | {reach} | {urls} |")
        else:
            lines.append("无验证通过的趋势数据")
        lines.append("")

        # References section
        references = raw_data.get("references", [])
        lines.append(f"## 参考文献 ({len(references)} 条)")
        lines.append("")
        if references:
            lines.append("| 标题 | 来源 | URL | 摘要 |")
            lines.append("|------|------|-----|------|")
            for item in references:
                title = item.get("title", "")[:40]
                source = item.get("source", "")
                url = item.get("url", "")
                summary_text = item.get("summary", "")[:50]
                lines.append(f"| {title} | {source} | {url} | {summary_text} |")
        else:
            lines.append("无验证通过的参考文献")
        lines.append("")

        # Uploaded files section
        if uploaded_files:
            lines.append(f"## 上传文件 ({len(uploaded_files)} 个)")
            lines.append("")
            for item in uploaded_files:
                name = item.get("name", "")
                summary_text = item.get("extracted_text", "")[:100]
                lines.append(f"- **{name}**: {summary_text}")
            lines.append("")

        # Data quality summary
        lines.append("## 数据质量摘要")
        lines.append("")
        lines.append(f"- 请求采集数: {summary.get('requested_social_updates', 0)}")
        lines.append(f"- 原始候选数: {summary.get('raw_candidates_requested', 0)}")
        lines.append(f"- 原始社交更新: {summary.get('raw_social_updates', 0)}")
        lines.append(f"- 验证通过数: {summary.get('verified_social_updates', 0)}")
        lines.append(f"- 无效/重复数: {summary.get('invalid_or_duplicate_social_updates', 0)}")
        lines.append(f"- 国家覆盖证据总数: {summary.get('country_coverage_total', 0)}")
        lines.append(f"- 未达标原因: {summary.get('shortfall_reason', '无')}")
        lines.append("")

        return "\n".join(lines)

    def save_raw_data(
        self,
        topic_id: str,
        raw_data: dict,
        markdown_report: str,
        analysis_id: Optional[str] = None,
    ) -> Path:
        """Save raw data and markdown report to disk in an isolated directory.

        Each analysis run gets its own directory:
            ~/.autogeo_raw_data/{topic_id}_{timestamp}_{analysis_id}/
                ├── raw_data.md
                ├── raw_data.json
                └── metadata.json

        Args:
            topic_id: Topic identifier
            raw_data: Raw data dict
            markdown_report: Markdown formatted report
            analysis_id: Optional analysis ID for unique identification

        Returns:
            Path to the analysis directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Create unique directory name
        dir_name = f"{topic_id}_{timestamp}"
        if analysis_id:
            dir_name += f"_{analysis_id[:8]}"

        analysis_dir = RAW_DATA_DIR / dir_name
        analysis_dir.mkdir(parents=True, exist_ok=True)

        # Save markdown report
        md_path = analysis_dir / "raw_data.md"
        md_path.write_text(markdown_report, encoding="utf-8")

        # Save raw JSON data
        json_path = analysis_dir / "raw_data.json"
        json_path.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # Save metadata
        metadata = {
            "topic_id": topic_id,
            "analysis_id": analysis_id,
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "social_updates_count": len(raw_data.get("social_updates", [])),
            "country_coverage_count": len(raw_data.get("country_coverage", [])),
            "trend_count": len(raw_data.get("trend", [])),
            "references_count": len(raw_data.get("references", [])),
        }
        meta_path = analysis_dir / "metadata.json"
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        return analysis_dir

    def load_raw_data(self, analysis_dir: Path) -> Optional[dict]:
        """Load raw data from an analysis directory.

        Args:
            analysis_dir: Path to the analysis directory

        Returns:
            Raw data dict or None if not found
        """
        json_path = analysis_dir / "raw_data.json"
        if not json_path.exists():
            return None
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def list_analyses(self, topic_id: Optional[str] = None) -> list[dict]:
        """List all analysis runs, optionally filtered by topic.

        Args:
            topic_id: Optional topic ID filter

        Returns:
            List of analysis metadata dicts
        """
        analyses = []
        if not RAW_DATA_DIR.exists():
            return analyses

        for dir_path in sorted(RAW_DATA_DIR.iterdir(), reverse=True):
            if not dir_path.is_dir():
                continue
            meta_path = dir_path / "metadata.json"
            if not meta_path.exists():
                continue
            try:
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                metadata["directory"] = str(dir_path)
                if topic_id is None or metadata.get("topic_id") == topic_id:
                    analyses.append(metadata)
            except Exception:
                continue

        return analyses
