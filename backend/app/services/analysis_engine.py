"""Sentiment analysis engine combining Object Storage data with Grok search."""

import json
import asyncio
import uuid
from datetime import datetime
from typing import Optional, AsyncGenerator, Any

from app.services.genai_client import GenAIClient
from app.services.object_storage import ObjectStorageService
from app.models.topic import AnalysisResult, DEFAULT_TOPICS
from app.services.dashboard_service import DashboardService



class AnalysisEngine:
    """Orchestrates sentiment analysis with multiple data sources.

    Note: This engine does not itself fetch live web data. It can only pass the
    prompt to Grok/OCI GenAI and optionally merge in Object Storage content.
    If live web/社媒抓取 is needed, the application must add a separate crawler
    or search tool before calling this engine.
    """

    def __init__(self, genai_client: GenAIClient | None, storage_service: ObjectStorageService | None):
        self.genai = genai_client
        self.storage = storage_service
        self.analysis_timeout = 120
        self._daily_cache: dict[str, AnalysisResult] = {}

    def _build_prompt(self, base_prompt: str, data_content: Optional[dict] = None, analysis_date: Optional[str] = None) -> str:
        """Build final analysis prompt by merging base prompt with data."""
        date_line = f"\n## 分析基准日期\n{analysis_date}" if analysis_date else ""


        system_instruction = """你是一位专业的舆情分析专家。请基于以下分析要求，提供结构化的深度分析报告。

你的分析必须包含以下结构（使用 Markdown 格式）：

## 执行摘要
[200字以内的核心发现概述]

## 详细分析

### 技术传播维度
[分析内容]

### 用户体验维度
[分析内容]

### 竞品对比维度
[分析内容]

### 市场影响维度
[分析内容]

### 风险预警维度
[分析内容]

## 情绪分析
请以JSON格式提供情绪量化数据：
```json
{"positive": 0.0, "neutral": 0.0, "negative": 0.0}
```
其中数值为0-1之间的小数，总和为1。

## 关键发现
- [发现1]
- [发现2]
- [发现3]

## 风险预警
- [风险1]
- [风险2]

## 建议措施
- [建议1]
- [建议2]
- [建议3]
"""

        parts = [system_instruction, f"\n## 分析要求\n{base_prompt}"]

        if data_content and "data" in data_content:
            data_str = json.dumps(data_content["data"], ensure_ascii=False, indent=2)
            parts.append(f"\n## 参考数据\n以下是来自数据源的补充信息，请结合分析：\n{data_str}")

        return "\n".join(parts)


    def _build_tool_prompt(
        self,
        base_prompt: str,
        data_content: Optional[dict] = None,
        uploaded_files: Optional[list[dict]] = None,
        social_updates_limit: int = 10,
        analysis_date: Optional[str] = None,
        raw_search_data: Optional[dict] = None,
    ) -> str:
        """Build a prompt for Grok tool-enabled retrieval plus reference-file context."""
        parts = [
            "你是一位专业的舆情分析专家。",
            "请优先使用你可用的搜索工具（x_search / web_search）去抓取与该主题相关的最新舆情、新闻和社媒信息。",
            "如果无法直接获取某些信息，再结合我提供的参考数据进行分析。",
            f"\n## 分析要求\n{base_prompt}",
        ]
        if data_content and "data" in data_content:
            data_str = json.dumps(data_content["data"], ensure_ascii=False, indent=2)
            parts.append(f"\n## 对象存储参考数据\n{data_str}")
        elif data_content and data_content.get("error"):
            parts.append(f"\n## 对象存储参考数据\n读取失败：{data_content['error']}")
        if raw_search_data:
            parts.append(
                "\n## 已校验原始搜索数据（必须优先使用）\n"
                "以下数据是系统先通过 x_search / web_search 独立获取并过滤后的原始材料。"
                "你必须优先基于这些真实 URL 做国家覆盖、社交媒体最新信息和引用，不得新增未经检索验证的社媒 URL。\n"
                + json.dumps(raw_search_data, ensure_ascii=False, indent=2)
            )
        if uploaded_files:
            parts.append("\n## 用户上载参考文件")
            for idx, item in enumerate(uploaded_files, 1):
                extracted = item.get('extracted_text', '')
                excel_lines = []
                if item.get('sheet_name'):
                    excel_lines.append(f"   Excel sheet：{item.get('sheet_name')}")
                if item.get('sheet_rows') is not None:
                    excel_lines.append(f"   Excel 行数：{item.get('sheet_rows')}")
                if item.get('excel_columns'):
                    excel_lines.append(f"   Excel 列：{', '.join(map(str, item.get('excel_columns', [])))}")
                parts.append(
                    f"{idx}. 文件名：{item.get('name', '')}\n   链接：{item.get('url', '')}\n   类型：{item.get('content_type', '')}\n   大小：{item.get('size', '')}\n   存储路径：{item.get('storage_path', '')}" + ("\n" + "\n".join(excel_lines) if excel_lines else "") + f"\n   提取内容：{str(extracted)[:1000]}"
                )
        parts.append(
            "\n## 输出要求\n请综合：1) 你通过搜索工具获取的实时舆情信息；2) 对象存储中的参考文件数据；3) 用户上载参考文件；4) 你的分析判断，输出结构化报告。必须明确使用 web_search 与 x_search 获取最新公开信息，并在正文中体现最新动态。\n\n重要：报告中的【趋势统计】、【国家覆盖】、【社交媒体最新信息】、以及分析报告全文里的所有 URL 和统计结论，都必须来自同一套统一检索结果与统一校验后的原始数据；不得分别凭空推断、不得混用未校验示例、不得用模型自造的社媒链接或趋势数据。"
        )
        parts.append(
            "\n## 情绪分析要求\n请给出可核验的情绪分布，并严格输出一个 JSON 代码块：```json {\"positive\":0.xx,\"neutral\":0.xx,\"negative\":0.xx} ```。禁止输出平均化占位值（如0.33/0.34/0.33）除非正文证据确实完全均衡。请结合 web_search 与 x_search 获取到的最新证据，对正负中性做有区分度的判断，并在“情绪分析”小节逐条解释占比依据，确保前端情绪图可直接使用该 JSON。"
        )
        parts.append(
            "\n## 国家覆盖要求\n请新增【国家覆盖】章节，用于统计该 topic 在 X 或其他社交媒体 / web-search 结果中发布信息热度较高的国家/地区。\n必须只基于 x_search / web_search 返回的真实公开结果统计，禁止猜测、禁止示例数据、禁止使用 example/placeholder/dummy/fake 链接。\n每条必须包含：国家/地区、热度计数（该国家/地区对应的可核验真实 URL 数量）、主要平台、证据 URL 列表。\n如果没有找到可核验真实 URL，请写：未检索到可核验国家覆盖数据。不要编造国家或数字。"
        )
        parts.append(
            "\n## 章节顺序要求\n报告结尾必须严格按以下顺序输出四个独立章节：1.【国家覆盖】 2.【引用备注】 3.【参考文献】 4.【社交媒体最新信息】。其中【社交媒体最新信息】必须是全文最后一个章节。"
        )
        parts.append(
            f"\n## 社交媒体最新信息要求\n请在报告最后新增【社交媒体最新信息】部分，按列表输出最近获取到的 X/社交媒体相关动态。每条必须包含：时间、平台、账号或来源、摘要、真实可访问的公开 URL。若某条来自 x_search，请显式标注为X/社交媒体来源。该列表最多输出 {social_updates_limit} 条。\n严格禁止输出假 URL、示例 URL 或占位 URL，例如包含 example、placeholder、dummy、fake、/video/example、/post/example 的链接。没有真实 URL 的动态必须省略，不要用平台首页或猜测链接替代。若没有可核验真实 URL，请只写：未检索到带真实公开 URL 的社交媒体动态。"
        )
        parts.append(
            "\n## 引用要求\n最终报告必须在结尾提供【引用备注】与【参考文献】两部分；每条引用需写明来源标题、用途说明、可点击的具体真实链接。\n引用备注中必须明确标记哪些内容来自用户上载文件、哪些内容来自搜索工具、哪些内容来自对象存储、哪些内容来自 X/社交媒体。\n如果引用了图片，请在备注中写明图片文件名、对象存储路径与其视觉/OCR摘要。"
        )
        return "\n".join(parts)

    def _build_raw_collection_prompt(self, base_prompt: str, social_updates_limit: int = 10) -> str:
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

数量限制：social_updates 最多 {social_updates_limit} 条；country_coverage 最多 8 个国家/地区；trend 最多 14 个日期点；references 最多 12 条。
trend 的 mentions 必须等于该日期下通过真实 URL 校验的社媒/新闻条目数量；reach 只有在检索结果明确给出浏览量、互动量、转发量、点赞量等可核验数字时才填写，否则填 0。每个 trend 点必须带 urls 证据列表；没有真实 URL 的日期不能输出。不要编造趋势、不要输出示例 Day 1/Day 2。
""".strip()

    def _extract_json_object(self, text: str) -> dict:
        import re
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

    def _sanitize_raw_search_data(self, payload: dict, social_updates_limit: int = 10) -> dict:
        validator = DashboardService()

        def clean_url(url: Any) -> str:
            if not url:
                return ""
            value = str(url).strip().rstrip(")],.，。；;:：")
            return value if validator._is_real_url(value) else ""

        social_updates = []
        raw_social = payload.get("social_updates") if isinstance(payload, dict) else []
        for item in raw_social if isinstance(raw_social, list) else []:
            if not isinstance(item, dict):
                continue
            url = clean_url(item.get("url"))
            if not url:
                continue
            social_updates.append({
                "time": str(item.get("time", ""))[:80],
                "platform": str(item.get("platform", ""))[:60],
                "account": str(item.get("account", ""))[:120],
                "summary": str(item.get("summary", ""))[:500],
                "url": url,
                "country": str(item.get("country", ""))[:80],
            })
            if len(social_updates) >= social_updates_limit:
                break

        country_map: dict[str, dict] = {}
        raw_countries = payload.get("country_coverage") if isinstance(payload, dict) else []
        for item in raw_countries if isinstance(raw_countries, list) else []:
            if not isinstance(item, dict):
                continue
            country = str(item.get("country", "")).strip()
            urls = [clean_url(url) for url in (item.get("urls") or [])]
            urls = [url for url in urls if url]
            if not country or not urls:
                continue
            platforms = item.get("platforms") or []
            if not isinstance(platforms, list):
                platforms = [platforms]
            entry = country_map.setdefault(country, {"country": country, "coverage": 0, "platforms": set(), "urls": []})
            for url in urls:
                if url not in entry["urls"]:
                    entry["urls"].append(url)
                    entry["coverage"] += 1
            for platform in platforms:
                if platform:
                    entry["platforms"].add(str(platform)[:60])

        for item in social_updates:
            country = item.get("country") or ""
            if not country:
                continue
            entry = country_map.setdefault(country, {"country": country, "coverage": 0, "platforms": set(), "urls": []})
            if item["url"] not in entry["urls"]:
                entry["urls"].append(item["url"])
                entry["coverage"] += 1
            if item.get("platform"):
                entry["platforms"].add(item["platform"])

        country_coverage = [
            {"country": v["country"], "coverage": v["coverage"], "platforms": sorted(v["platforms"]), "urls": v["urls"][:5]}
            for v in country_map.values()
            if v["coverage"] > 0 and v["urls"]
        ]
        country_coverage.sort(key=lambda x: x["coverage"], reverse=True)

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
            if not urls:
                # Keep the row so the trend chart can still show an aggregated point, but without evidence URLs.
                trend.append({"date": date[:40], "mentions": max(1, mentions), "reach": max(reach, 0), "urls": []})
                continue
            trend.append({"date": date[:40], "mentions": max(1, mentions), "reach": max(reach, 0), "urls": urls[:8]})
        trend.sort(key=lambda x: x["date"])

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

        return {"social_updates": social_updates, "country_coverage": country_coverage[:8], "trend": trend[:14], "references": references}

    async def _collect_raw_search_data(self, prompt: str, model: Optional[str], social_updates_limit: int) -> dict:
        collection_prompt = self._build_raw_collection_prompt(prompt, social_updates_limit=social_updates_limit)
        try:
            raw_text = await asyncio.wait_for(
                self.genai.analyze_with_tools(
                    collection_prompt,
                    model=model,
                    tools=[{"type": "x_search"}, {"type": "web_search"}],
                    max_tokens=4096,
                ),
                timeout=self.analysis_timeout,
            )
        except Exception as exc:
            return {"social_updates": [], "country_coverage": [], "references": [], "collection_error": str(exc)[:300]}
        return self._sanitize_raw_search_data(self._extract_json_object(raw_text), social_updates_limit=social_updates_limit)

    def _inject_verified_trend_section(self, content: str, raw_search_data: Optional[dict]) -> str:
        """Insert verified trend evidence so dashboard trend is derived from raw x/web search data, not demo values."""
        if not raw_search_data or not raw_search_data.get("trend"):
            return content
        lines = ["【趋势统计】", "以下趋势只基于已通过 URL 多重校验的 x_search / web_search 原始数据；未检索到真实 URL 的日期不纳入统计。"]
        for item in raw_search_data.get("trend", [])[:14]:
            urls = [str(url) for url in (item.get("urls") or []) if url]
            if not item.get("date") or not urls:
                continue
            lines.append(
                f"- 日期：{item.get('date')}；mentions：{item.get('mentions', len(urls))}；reach：{item.get('reach', 0)}；证据 URL：{', '.join(urls)}"
            )
        if len(lines) <= 2:
            return content
        section = "\n".join(lines).strip()
        first_tail_positions = [pos for marker in ("【国家覆盖】", "【引用备注】", "【参考文献】", "【社交媒体最新信息】") if (pos := content.find(marker)) != -1]
        if first_tail_positions:
            pos = min(first_tail_positions)
            return content[:pos].rstrip() + "\n\n" + section + "\n\n" + content[pos:].lstrip()
        return content.rstrip() + "\n\n" + section + "\n"

    def _replace_social_section_with_verified(self, content: str, raw_search_data: Optional[dict]) -> str:
        """Force the final social-media section to contain only verified raw-search URLs."""
        marker = "【社交媒体最新信息】"
        head = content[:content.find(marker)].rstrip() if marker in content else content.rstrip()
        validator = DashboardService()
        verified_items = []

        if raw_search_data and isinstance(raw_search_data.get("social_updates"), list):
            for item in raw_search_data.get("social_updates", []):
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url", "")).strip().rstrip(")],.，。；;:：")
                if not validator._is_real_url(url):
                    continue
                verified_items.append({
                    "time": str(item.get("time", "")).strip(),
                    "platform": str(item.get("platform", "")).strip(),
                    "account": str(item.get("account", "")).strip(),
                    "summary": str(item.get("summary", "")).strip(),
                    "url": url,
                })

        # If raw data is unavailable, conservatively filter the model's existing social section.
        if not verified_items and marker in content:
            section = content[content.find(marker) + len(marker):].strip()
            for line in section.splitlines():
                urls = [u.rstrip(")],.，。；;:：") for u in __import__("re").findall(r"https?://[^\s)\]}，。；;、]+", line)]
                urls = [u for u in urls if validator._is_real_url(u)]
                for url in urls:
                    verified_items.append({"time": "", "platform": "", "account": "", "summary": line.strip(), "url": url})

        lines = [marker]
        if verified_items:
            seen = set()
            for item in verified_items:
                url = item["url"]
                if url in seen:
                    continue
                seen.add(url)
                parts = []
                if item.get("time"):
                    parts.append(f"时间：{item['time']}")
                if item.get("platform"):
                    parts.append(f"平台：{item['platform']}")
                if item.get("account"):
                    parts.append(f"账号/来源：{item['account']}")
                if item.get("summary"):
                    parts.append(f"摘要：{item['summary'][:240]}")
                parts.append(f"链接：{url}")
                lines.append("- " + "；".join(parts))
        else:
            lines.append("未检索到带真实公开 URL 的社交媒体动态。")
        return head + "\n\n" + "\n".join(lines).strip() + "\n"

    def _sanitize_report_urls(self, content: str) -> str:
        """Remove report lines containing invalid/hallucinated social URLs."""
        validator = DashboardService()
        cleaned_lines = []
        removed = 0
        for line in content.splitlines():
            urls = [u.rstrip(")],.，。；;:：") for u in __import__("re").findall(r"https?://[^\s)\]}，。；;、]+", line)]
            if urls and any(not validator._is_real_url(url) for url in urls):
                removed += 1
                continue
            cleaned_lines.append(line)
        cleaned = "\n".join(cleaned_lines)
        if removed:
            marker = f"\n\n【数据清洗说明】\n已过滤 {removed} 条未通过 URL 多重校验的社交媒体/引用记录，避免展示模型生成的假链接。\n"
            insert_pos = cleaned.find("【引用备注】")
            if insert_pos != -1:
                cleaned = cleaned[:insert_pos].rstrip() + marker + "\n" + cleaned[insert_pos:]
            else:
                cleaned = cleaned.rstrip() + marker
        return cleaned


    def _enforce_report_tail_sections(self, content: str) -> str:
        """Force tail order: 引用备注 -> 参考文献 -> 社交媒体最新信息."""
        markers = ['【国家覆盖】', '【引用备注】', '【参考文献】', '【社交媒体最新信息】']
        positions = {m: content.find(m) for m in markers}
        found = {m: pos for m, pos in positions.items() if pos != -1}
        if not found:
            return content
        first = min(found.values())
        head = content[:first].rstrip()
        sections = {}
        ordered_found = sorted(found.items(), key=lambda kv: kv[1])
        for idx, (marker, start) in enumerate(ordered_found):
            end = ordered_found[idx + 1][1] if idx + 1 < len(ordered_found) else len(content)
            sections[marker] = content[start:end].strip()
        tail_parts = [sections[m] for m in markers if m in sections]
        return head + "\n\n" + "\n\n".join(tail_parts).strip() + "\n"

    def _analysis_day_key(self, topic_id: str, custom_title: str = "") -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        return f"{today}:{topic_id}:{custom_title.strip()}"

    def _snapshot_key(self, topic_id: str, custom_title: str = "") -> str:
        return self._analysis_day_key(topic_id, custom_title)

    def _snapshot_meta_key(self, topic_id: str, custom_title: str = "") -> str:
        return self._analysis_day_key(topic_id, custom_title) + ":meta"

    def _detect_major_event(self, text: str) -> bool:
        import re
        patterns = [
            r"重大事件", r"突发", r"紧急", r"危机", r"收购", r"诉讼",
            r"召回", r"事故", r"爆炸", r"裁员", r"制裁", r"禁令",
            r"SEC", r"DOJ", r"FDA", r"DOD", r"1260h", r"停产", r"破产",
        ]
        return any(re.search(p, text, re.I) for p in patterns)

    async def _snapshot_is_valid(self, topic_id: str, custom_title: str, prompt: str, current_payload: Optional[dict] = None) -> bool:
        import os, json
        meta_path = self._snapshot_path(self._snapshot_meta_key(topic_id, custom_title))
        if not os.path.exists(meta_path):
            return False
        try:
            meta = json.loads(open(meta_path, "r", encoding="utf-8").read())
        except Exception:
            return False
        if meta.get("prompt") != prompt:
            return False
        if self._detect_major_event(current_payload.get("content", "") if current_payload else ""):
            return False
        return True

    def _snapshot_path(self, key: str) -> str:
        import os
        base = os.path.expanduser("~/.bydgeo_daily_snapshots")
        os.makedirs(base, exist_ok=True)
        safe = key.replace(":", "__")
        return os.path.join(base, f"{safe}.json")

    async def _load_daily_snapshot(self, topic_id: str, custom_title: str = "") -> Optional[dict]:
        import os
        path = self._snapshot_path(self._snapshot_key(topic_id, custom_title))
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def _save_daily_snapshot(self, topic_id: str, custom_title: str, payload: dict) -> None:
        path = self._snapshot_path(self._snapshot_key(topic_id, custom_title))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _clear_daily_state(self, topic_id: str, custom_title: str = "") -> None:
        import os
        day_key = self._analysis_day_key(topic_id, custom_title)
        self._daily_cache.pop(day_key, None)
        for key in [self._snapshot_key(topic_id, custom_title), self._snapshot_meta_key(topic_id, custom_title)]:
            path = self._snapshot_path(key)
            if os.path.exists(path):
                os.remove(path)

    def _parse_sentiment(self, content: str) -> dict:
        """Extract sentiment scores from analysis content.

        Prefer explicit JSON blocks, but also support common Chinese report text
        such as "情绪分布：正面72%、中性21%、负面7%". If no valid distribution
        is found, return the neutral fallback used by the UI.
        """
        import re

        def normalize(values: dict[str, float]) -> dict:
            total = sum(values.values())
            if total <= 0:
                raise ZeroDivisionError("sentiment total is zero")
            return {
                "positive": round(values.get("positive", 0) / total, 2),
                "neutral": round(values.get("neutral", 0) / total, 2),
                "negative": round(values.get("negative", 0) / total, 2),
            }

        json_match = re.search(r'```json\s*(\{[^}]+\})\s*```', content, re.S)
        if json_match:
            try:
                sentiment = json.loads(json_match.group(1))
                return normalize({
                    "positive": float(sentiment.get("positive", 0)),
                    "neutral": float(sentiment.get("neutral", 0)),
                    "negative": float(sentiment.get("negative", 0)),
                })
            except (json.JSONDecodeError, ZeroDivisionError, TypeError, ValueError):
                pass

        patterns = [
            # 情绪分布：正面72%、中性21%、负面7%
            (r'情绪分布[：:]\s*正面\s*(\d+(?:\.\d+)?)%[、,，\s]*中性\s*(\d+(?:\.\d+)?)%[、,，\s]*负面\s*(\d+(?:\.\d+)?)%',
             ("positive", "neutral", "negative")),
            # 情感量化... 正面：68% ... 中性：22% ... 负面：10%
            (r'情感量化[\s\S]{0,120}?正面[：:]\s*(\d+(?:\.\d+)?)%[\s\S]{0,120}?中性[：:]\s*(\d+(?:\.\d+)?)%[\s\S]{0,120}?负面[：:]\s*(\d+(?:\.\d+)?)%',
             ("positive", "neutral", "negative")),
            # 量化声音平衡：整体正面约52-58%，负面约35-40%，中性10%
            (r'整体正面约\s*(\d+(?:\.\d+)?)(?:-\d+(?:\.\d+)?)?%[\s\S]{0,80}?负面约\s*(\d+(?:\.\d+)?)(?:-\d+(?:\.\d+)?)?%[\s\S]{0,50}?中性\s*(\d+(?:\.\d+)?)%',
             ("positive", "negative", "neutral")),
        ]
        for pattern, keys in patterns:
            match = re.search(pattern, content)
            if not match:
                continue
            try:
                raw = {key: float(value) for key, value in zip(keys, match.groups())}
                return normalize(raw)
            except (ZeroDivisionError, TypeError, ValueError):
                continue

        # Avoid silently fabricating a misleading balanced distribution when the report正文没有可解析的情绪量化。
        return {"positive": 0.0, "neutral": 0.0, "negative": 0.0}

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
    ) -> AnalysisResult:
        """Run full analysis pipeline."""
        day_key = self._analysis_day_key(topic_id, custom_title)
        if force_refresh:
            self._clear_daily_state(topic_id, custom_title)
        cached = self._daily_cache.get(day_key)
        if cached is not None and not force_refresh:
            return cached

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

        # Load external data if configured
        data_content = None
        if data_source_path and data_bucket:
            data_content = await self.storage.read_data_file(data_bucket, data_source_path)

        ref_texts = []
        image_inputs = []
        if uploaded_files and self.storage:
            for item in uploaded_files:
                storage_path = item.get("storage_path")
                if not storage_path:
                    continue
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
                base64_ref = await self.storage.read_reference_base64(data_bucket or "", storage_path)
                if base64_ref.get("base64"):
                    image_inputs.append(base64_ref)
                    ref_texts.append({
                        "name": item.get("name", ""),
                        "storage_path": storage_path,
                        "text": f"IMAGE_BASE64::{storage_path}::{base64_ref.get('token_hint', '')}",
                        "url": item.get("url", ""),
                    })
        merged_uploaded_files = uploaded_files or []
        if ref_texts:
            merged_uploaded_files = [
                {**item, "extracted_text": next((r["text"] for r in ref_texts if r["storage_path"] == item.get("storage_path")), "")}
                for item in merged_uploaded_files
            ]

        # Step 1: collect and sanitize raw x_search/web_search data before analysis.
        raw_search_data = await self._collect_raw_search_data(prompt, model, social_updates_limit)

        # Step 2: build merged prompt with verified raw data, then call the model for analysis.
        full_prompt = self._build_tool_prompt(
            prompt,
            data_content,
            merged_uploaded_files,
            social_updates_limit=social_updates_limit,
            raw_search_data=raw_search_data,
        )

        # Call Grok model with search tools enabled
        content = await asyncio.wait_for(
            self.genai.analyze_with_tools(
                full_prompt,
                model=model,
                tools=[{"type": "x_search"}, {"type": "web_search"}],
                image_inputs=image_inputs,
            ),
            timeout=self.analysis_timeout,
        )

        content = self._sanitize_report_urls(self._replace_social_section_with_verified(self._inject_verified_trend_section(self._enforce_report_tail_sections(content), raw_search_data), raw_search_data))
        if force_refresh:
            refresh_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            content = f"【重分析标记】\n本报告由“重新分析”触发强制重生成。\n重生成时间：{refresh_stamp}\n\n" + content

        # Parse sentiment
        sentiment = self._parse_sentiment(content)

        result = AnalysisResult(
            id=str(uuid.uuid4()),
            topic_id=topic_id,
            model=self.genai.get_model_id(model),
            prompt=prompt,
            content=content,
            sentiment=sentiment,
            created_at=datetime.now(),
        )
        self._daily_cache[day_key] = result
        payload = result.model_dump()
        await self._save_daily_snapshot(topic_id, custom_title, payload)
        await self._save_daily_snapshot(topic_id, custom_title + "__meta", {"prompt": prompt, "content": content[:4000], "force_refresh": force_refresh, "generated_at": datetime.now().isoformat()})
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
    ) -> AsyncGenerator[str, None]:
        """Run analysis with streaming response."""
        if force_refresh:
            self._clear_daily_state(topic_id, custom_title)
        snapshot = await self._load_daily_snapshot(topic_id, custom_title)
        if snapshot and not force_refresh:
            yield snapshot["content"]
            return

        data_content = None
        if data_source_path and data_bucket:
            data_content = await self.storage.read_data_file(data_bucket, data_source_path)

        image_inputs = []
        if uploaded_files and self.storage:
            for item in uploaded_files:
                storage_path = item.get("storage_path")
                if not storage_path:
                    continue
                base64_ref = await self.storage.read_reference_base64(data_bucket or "", storage_path)
                if base64_ref.get("base64"):
                    image_inputs.append(base64_ref)

        raw_search_data = await self._collect_raw_search_data(prompt, model, social_updates_limit)
        full_prompt = self._build_tool_prompt(
            prompt,
            data_content,
            uploaded_files,
            social_updates_limit=social_updates_limit,
            raw_search_data=raw_search_data,
        )

        # Stream raw chunks to the frontend in real-time for immediate display
        buffered = []
        async for chunk in self.genai.analyze_stream(full_prompt, model=model, image_inputs=image_inputs):
            buffered.append(chunk)
            yield chunk

        # Post-process the full text after streaming completes
        final_text = self._sanitize_report_urls(self._replace_social_section_with_verified(self._inject_verified_trend_section(self._enforce_report_tail_sections("".join(buffered)), raw_search_data), raw_search_data))
        if force_refresh:
            refresh_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            final_text = f"【重分析标记】\n本报告由“重新分析”触发强制重生成。\n重生成时间：{refresh_stamp}\n\n" + final_text

        # Yield a special marker so the router can distinguish the processed final text
        # from the raw streaming chunks
        yield f"\n__PROCESSED_FINAL__\n{final_text}"

        result_payload = {
            "id": str(uuid.uuid4()),
            "topic_id": topic_id,
            "model": self.genai.get_model_id(model),
            "prompt": prompt,
            "content": final_text,
            "sentiment": self._parse_sentiment(final_text),
            "created_at": datetime.now().isoformat(),
        }
        await self._save_daily_snapshot(topic_id, custom_title, result_payload)
        await self._save_daily_snapshot(topic_id, custom_title + "__meta", {"prompt": prompt, "content": final_text[:4000], "force_refresh": force_refresh, "generated_at": datetime.now().isoformat()})
        self._daily_cache[self._analysis_day_key(topic_id, custom_title)] = AnalysisResult(
            id=result_payload["id"],
            topic_id=result_payload["topic_id"],
            model=result_payload["model"],
            prompt=result_payload["prompt"],
            content=result_payload["content"],
            sentiment=result_payload["sentiment"],
            created_at=datetime.fromisoformat(result_payload["created_at"]),
        )
