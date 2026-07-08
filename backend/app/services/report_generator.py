"""Report generation with enhanced analysis capabilities.

This module handles:
1. Building analysis prompts with root cause analysis and risk warnings
2. Calling LLM to generate comprehensive reports
3. Post-processing reports (URL validation, section reordering)
4. Parsing sentiment from report content
"""

import json
import re
import asyncio
from datetime import datetime
from typing import Optional, AsyncGenerator

from app.services.genai_client import GenAIClient
from app.services.dashboard_service import DashboardService


class ReportGenerator:
    """Generates sentiment analysis reports with enhanced capabilities."""

    def __init__(self, genai_client: GenAIClient):
        self.genai = genai_client
        self._dashboard_service = DashboardService()
        self.analysis_timeout = 300

    def build_analysis_prompt(
        self,
        base_prompt: str,
        data_content: Optional[dict] = None,
        uploaded_files: Optional[list[dict]] = None,
        social_updates_limit: int = 10,
        raw_search_data: Optional[dict] = None,
        report_language: str = "zh",
        target_region: str = "global",
    ) -> str:
        """Build comprehensive analysis prompt with enhanced requirements.

        Args:
            base_prompt: User's analysis requirements
            data_content: Object Storage reference data
            uploaded_files: User uploaded files with extracted text
            social_updates_limit: Max social updates to include
            raw_search_data: Verified raw data from collection phase
            report_language: Output language (zh/en/bilingual)
            target_region: Target geographic region

        Returns:
            Complete prompt string for model call
        """
        # Language instruction
        if report_language == "en":
            language_prefix = """CRITICAL LANGUAGE REQUIREMENT: You MUST output the ENTIRE report in English only. This includes:
- ALL section titles (Executive Summary, Key Findings, Sentiment Analysis, Country Coverage, Latest Social Updates, References, etc.)
- ALL analysis content, bullet points, and descriptions
- ALL sentiment analysis explanations
- ALL social media update summaries
- ALL source citations and references
- The sentiment JSON block comments

DO NOT use Chinese anywhere in the output. If you find Chinese source material, translate it to English before including it in the report.

"""
        elif report_language == "bilingual":
            language_prefix = """CRITICAL LANGUAGE REQUIREMENT: You MUST output the ENTIRE report in both Chinese and English (bilingual format).
For each section, first provide the Chinese content, then provide the English translation below it.
Format example:
## 执行摘要
[Chinese content]

### Executive Summary
[English content]

Apply this bilingual format to ALL sections including: Executive Summary, Key Findings, Sentiment Analysis, Country Coverage, Latest Social Updates, References, etc.

"""
        else:
            language_prefix = ""

        # Region instruction
        region_instruction = ""
        region_map = {
            "europe": "Europe (focus on Germany, UK, France, Italy, Spain, etc.)",
            "northAmerica": "North America (focus on USA, Canada)",
            "middleEast": "Middle East (focus on Saudi Arabia, UAE, Israel, etc.)",
            "southeastAsia": "Southeast Asia (focus on Thailand, Indonesia, Vietnam, Malaysia, Singapore, etc.)",
            "latinAmerica": "Latin America (focus on Brazil, Mexico, Argentina, etc.)",
            "oceania": "Oceania (focus on Australia, New Zealand)",
        }
        if target_region != "global" and target_region in region_map:
            if report_language == "en":
                region_instruction = f"\n\n## Region Focus\nThis analysis focuses on the {region_map[target_region]} market. Prioritize searching and analyzing information from this region."
            else:
                region_instruction = f"\n\n## 区域聚焦\n本次分析重点聚焦{region_map[target_region]}市场，请在搜索和分析时优先覆盖该区域的相关信息。"

        is_en = report_language == "en"

        # Expert role
        if is_en:
            parts = [
                language_prefix,
                "You are a professional sentiment analysis expert.",
                "Please use your available search tools (x_search / web_search) to fetch the latest sentiment, news, and social media information related to this topic.",
                "If you cannot directly obtain certain information, combine it with the reference data I provide for analysis.",
                f"\n## Analysis Requirements\n{base_prompt}",
                region_instruction,
            ]
        else:
            parts = [
                language_prefix,
                "你是一位专业的舆情分析专家。",
                "请优先使用你可用的搜索工具（x_search / web_search）去抓取与该主题相关的最新舆情、新闻和社媒信息。",
                "如果无法直接获取某些信息，再结合我提供的参考数据进行分析。",
                f"\n## 分析要求\n{base_prompt}",
                region_instruction,
            ]

        # Reference data
        if data_content and "data" in data_content:
            data_str = json.dumps(data_content["data"], ensure_ascii=False, indent=2)
            parts.append(f"\n{'## Reference Data from Object Storage' if is_en else '## 对象存储参考数据'}\n{data_str}")
        elif data_content and data_content.get("error"):
            parts.append(f"\n{'## Reference Data from Object Storage' if is_en else '## 对象存储参考数据'}\n{'Read failed' if is_en else '读取失败'}：{data_content['error']}")

        # Verified raw search data
        if raw_search_data:
            if is_en:
                parts.append(
                    "\n## Verified Raw Search Data (MUST use as priority)\n"
                    "The following data is raw material independently fetched and filtered by the system through x_search / web_search. "
                    "You MUST prioritize these real URLs for country coverage, social media updates, and citations. Do NOT add unverified social media URLs.\n"
                    + json.dumps(raw_search_data, ensure_ascii=False, indent=2)
                )
            else:
                parts.append(
                    "\n## 已校验原始搜索数据（必须优先使用）\n"
                    "以下数据是系统先通过 x_search / web_search 独立获取并过滤后的原始材料。"
                    "你必须优先基于这些真实 URL 做国家覆盖、社交媒体最新信息和引用，不得新增未经检索验证的社媒 URL。\n"
                    + json.dumps(raw_search_data, ensure_ascii=False, indent=2)
                )

        # Uploaded files
        if uploaded_files:
            parts.append("\n" + ("## User Uploaded Reference Files" if is_en else "## 用户上载参考文件"))
            for idx, item in enumerate(uploaded_files, 1):
                extracted = item.get('extracted_text', '')
                excel_lines = []
                if item.get('sheet_name'):
                    excel_lines.append(f"   Excel sheet: {item.get('sheet_name')}")
                if item.get('sheet_rows') is not None:
                    excel_lines.append(f"   Excel rows: {item.get('sheet_rows')}")
                if item.get('excel_columns'):
                    excel_lines.append(f"   Excel columns: {', '.join(map(str, item.get('excel_columns', [])))}")
                parts.append(
                    f"{idx}. {'File name' if is_en else '文件名'}: {item.get('name', '')}\n   {'Link' if is_en else '链接'}: {item.get('url', '')}\n   {'Type' if is_en else '类型'}: {item.get('content_type', '')}\n   {'Size' if is_en else '大小'}: {item.get('size', '')}\n   {'Storage path' if is_en else '存储路径'}: {item.get('storage_path', '')}" + ("\n" + "\n".join(excel_lines) if excel_lines else "") + f"\n   {'Extracted content' if is_en else '提取内容'}: {str(extracted)[:1000]}"
                )

        # Output requirements
        if is_en:
            parts.append(
                "\n## Output Requirements\nCombine: 1) Real-time sentiment information obtained through search tools; 2) Reference file data from Object Storage; 3) User uploaded reference files; 4) Your analysis judgment to output a structured report. You MUST explicitly use web_search and x_search to obtain the latest public information and reflect the latest developments in the main text.\n\nIMPORTANT: ALL URLs and statistical conclusions in the report's Trend Statistics, Country Coverage, Latest Social Updates, and the full analysis report MUST come from the same unified search results and verified raw data. Do NOT make separate assumptions, mix unverified examples, or use model-generated social media links or trend data."
            )
        else:
            parts.append(
                "\n## 输出要求\n请综合：1) 你通过搜索工具获取的实时舆情信息；2) 对象存储中的参考文件数据；3) 用户上载参考文件；4) 你的分析判断，输出结构化报告。必须明确使用 web_search 与 x_search 获取最新公开信息，并在正文中体现最新动态。\n\n重要：报告中的【趋势统计】、【国家覆盖】、【社交媒体最新信息】、以及分析报告全文里的所有 URL 和统计结论，都必须来自同一套统一检索结果与统一校验后的原始数据；不得分别凭空推断、不得混用未校验示例、不得用模型自造的社媒链接或趋势数据。"
            )

        # Sentiment analysis requirements
        if is_en:
            parts.append(
                '\n## Sentiment Analysis Requirements\nProvide verifiable sentiment distribution and strictly output a JSON code block: ```json {"positive":0.xx,"neutral":0.xx,"negative":0.xx} ```. Do NOT output averaged placeholder values (like 0.33/0.34/0.33) unless the evidence is truly completely balanced. Combine the latest evidence from web_search and x_search to make differentiated judgments on positive, neutral, and negative, and explain the basis for each proportion in the "Sentiment Analysis" section to ensure the frontend sentiment chart can directly use this JSON.'
            )
        else:
            parts.append(
                '\n## 情绪分析要求\n请给出可核验的情绪分布，并严格输出一个 JSON 代码块：```json {"positive":0.xx,"neutral":0.xx,"negative":0.xx} ```。禁止输出平均化占位值（如0.33/0.34/0.33）除非正文证据确实完全均衡。请结合 web_search 与 x_search 获取到的最新证据，对正负中性做有区分度的判断，并在"情绪分析"小节逐条解释占比依据，确保前端情绪图可直接使用该 JSON。'
            )

        # Country coverage requirements
        if is_en:
            parts.append(
                "\n## Country Coverage Requirements\nAdd a [Country Coverage] section to count countries/regions with higher information heat for this topic on X or other social media / web-search results.\nYou MUST only count based on real public results returned by x_search / web_search. Do NOT guess, use example data, or use example/placeholder/dummy/fake links.\nEach entry must include: country/region, heat count (number of verifiable real URLs for that country/region), main platforms, evidence URL list.\nIf no verifiable real URLs are found, write: No verifiable country coverage data found. Do NOT fabricate countries or numbers."
            )
        else:
            parts.append(
                "\n## 国家覆盖要求\n请新增【国家覆盖】章节，用于统计该 topic 在 X 或其他社交媒体 / web-search 结果中发布信息热度较高的国家/地区。\n必须只基于 x_search / web_search 返回的真实公开结果统计，禁止猜测、禁止示例数据、禁止使用 example/placeholder/dummy/fake 链接。\n每条必须包含：国家/地区、热度计数（该国家/地区对应的可核验真实 URL 数量）、主要平台、证据 URL 列表。\n如果没有找到可核验真实 URL，请写：未检索到可核验国家覆盖数据。不要编造国家或数字。"
            )

        # Section order requirements
        if is_en:
            parts.append(
                "\n## Section Order Requirements\nThe report must strictly end with the following four independent sections in order: 1. [Country Coverage] 2. [Citation Notes] 3. [References] 4. [Latest Social Updates]. [Latest Social Updates] MUST be the very last section of the entire report."
            )
        else:
            parts.append(
                "\n## 章节顺序要求\n报告结尾必须严格按以下顺序输出四个独立章节：1.【国家覆盖】 2.【引用备注】 3.【参考文献】 4.【社交媒体最新信息】。其中【社交媒体最新信息】必须是全文最后一个章节。"
            )

        # Social media updates requirements
        if is_en:
            parts.append(
                f"\n## Latest Social Updates Requirements\nAdd a [Latest Social Updates] section at the end of the report, listing the most recent X/social media related updates. Each entry must include: time, platform, account or source, summary, real accessible public URL. If an entry comes from x_search, explicitly mark it as 'X/Social Media Source'. This list should output at most {social_updates_limit} entries.\nStrictly prohibit outputting fake URLs, example URLs, or placeholder URLs, such as links containing example, placeholder, dummy, fake, /video/example, /post/example. Social media updates without real URLs must be omitted. Do NOT use platform homepages or guessed links as substitutes. If there are no verifiable real URLs, only write: No social media updates with verified public URLs found."
            )
        else:
            parts.append(
                f"\n## 社交媒体最新信息要求\n请在报告最后新增【社交媒体最新信息】部分，按列表输出最近获取到的 X/社交媒体相关动态。每条必须包含：时间、平台、账号或来源、摘要、真实可访问的公开 URL。若某条来自 x_search，请显式标注为X/社交媒体来源。该列表最多输出 {social_updates_limit} 条。\n严格禁止输出假 URL、示例 URL 或占位 URL，例如包含 example、placeholder、dummy、fake、/video/example、/post/example 的链接。没有真实 URL 的动态必须省略，不要用平台首页或猜测链接替代。若没有可核验真实 URL，请只写：未检索到带真实公开 URL 的社交媒体动态。"
            )

        # Citation requirements
        if is_en:
            parts.append(
                "\n## Citation Requirements\nThe final report MUST include [Citation Notes] and [References] sections at the end. Each citation must include: source title, purpose description, clickable real link.\nCitation Notes must clearly mark which content comes from user uploaded files, which from search tools, which from Object Storage, and which from X/Social Media.\nIf images are cited, note the image filename, Object Storage path, and its visual/OCR summary in the notes."
            )
        else:
            parts.append(
                "\n## 引用要求\n最终报告必须在结尾提供【引用备注】与【参考文献】两部分；每条引用需写明来源标题、用途说明、可点击的具体真实链接。\n引用备注中必须明确标记哪些内容来自用户上载文件、哪些内容来自搜索工具、哪些内容来自对象存储、哪些内容来自 X/社交媒体。\n如果引用了图片，请在备注中写明图片文件名、对象存储路径与其视觉/OCR摘要。"
            )

        # Root cause analysis requirements (NEW)
        if is_en:
            parts.append(
                "\n## Root Cause Analysis Requirements\nProvide a dedicated [Root Cause Analysis] section that:\n"
                "1. Identifies the fundamental causes behind the observed sentiment trends\n"
                "2. Analyzes the chain of events leading to the current situation\n"
                "3. Examines underlying factors (market, technology, policy, consumer behavior)\n"
                "4. Compares with historical patterns if applicable\n"
                "5. Provides evidence-based causal reasoning, not speculation"
            )
        else:
            parts.append(
                "\n## 根因分析要求\n请提供专门的【根因分析】章节，包括：\n"
                "1. 识别观察到的情绪趋势背后的根本原因\n"
                "2. 分析导致当前局势的事件链条\n"
                "3. 检查潜在因素（市场、技术、政策、消费者行为）\n"
                "4. 与历史模式进行比较（如适用）\n"
                "5. 提供基于证据的因果推理，而非推测"
            )

        # Risk warning requirements (NEW)
        if is_en:
            parts.append(
                "\n## Risk Warning Requirements\nProvide a dedicated [Risk Warning] section that:\n"
                "1. Assigns risk levels (HIGH/MEDIUM/LOW) to identified issues\n"
                "2. Provides early warning indicators for potential escalation\n"
                "3. Estimates timeline for potential impact\n"
                "4. Recommends immediate actions for high-risk items\n"
                "5. Monitors specific metrics or events for ongoing assessment"
            )
        else:
            parts.append(
                "\n## 风险预警要求\n请提供专门的【风险预警】章节，包括：\n"
                "1. 为识别的问题分配风险级别（高/中/低）\n"
                "2. 提供潜在升级的早期预警指标\n"
                "3. 估计潜在影响的时间线\n"
                "4. 为高风险项目推荐立即行动\n"
                "5. 监控特定指标或事件以进行持续评估"
            )

        # Action recommendations requirements (NEW)
        if is_en:
            parts.append(
                "\n## Action Recommendations Requirements\nProvide a dedicated [Action Recommendations] section that:\n"
                "1. Short-term responses (within 24-48 hours)\n"
                "2. Medium-term strategies (1-4 weeks)\n"
                "3. Long-term positioning (1-6 months)\n"
                "4. Specific, actionable steps with responsible parties\n"
                "5. Success metrics and KPIs for each recommendation"
            )
        else:
            parts.append(
                "\n## 行动建议要求\n请提供专门的【行动建议】章节，包括：\n"
                "1. 短期应对措施（24-48小时内）\n"
                "2. 中期策略（1-4周）\n"
                "3. 长期定位（1-6个月）\n"
                "4. 具体、可执行的步骤及责任方\n"
                "5. 每项建议的成功指标和KPI"
            )

        return "\n".join(parts)

    def _post_process_report(
        self,
        content: str,
        raw_search_data: Optional[dict],
        report_language: str = "zh",
    ) -> str:
        """Apply post-processing pipeline to the generated report.

        Args:
            content: Raw report content from model
            raw_search_data: Verified raw data for section replacement
            report_language: Report language

        Returns:
            Post-processed report content
        """
        content = self._enforce_report_tail_sections(content, report_language)
        content = self._inject_verified_trend_section(content, raw_search_data, report_language)
        content = self._replace_country_section_with_verified(content, raw_search_data, report_language)
        content = self._replace_social_section_with_verified(content, raw_search_data, report_language)
        content = self._sanitize_report_urls(content, report_language)
        return content

    def _enforce_report_tail_sections(self, content: str, report_language: str = "zh") -> str:
        """Force tail order: Country Coverage -> Citation Notes -> References -> Social Updates."""
        is_en = report_language == "en"
        if is_en:
            markers = ['[Country Coverage]', '[Citation Notes]', '[References]', '[Latest Social Updates]']
        else:
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

    def _inject_verified_trend_section(
        self,
        content: str,
        raw_search_data: Optional[dict],
        report_language: str = "zh",
    ) -> str:
        """Insert verified trend evidence from raw data."""
        if not raw_search_data or not raw_search_data.get("trend"):
            return content

        is_en = report_language == "en"
        if is_en:
            lines = ["[Trend Statistics]", "The following trends are based only on verified x_search / web_search raw data; dates without verified URLs are not included."]
        else:
            lines = ["【趋势统计】", "以下趋势只基于已通过 URL 多重校验的 x_search / web_search 原始数据；未检索到真实 URL 的日期不纳入统计。"]

        for item in raw_search_data.get("trend", [])[:14]:
            urls = [str(url) for url in (item.get("urls") or []) if url]
            if not item.get("date") or not urls:
                continue
            if is_en:
                lines.append(f"- Date: {item.get('date')}; mentions: {item.get('mentions', len(urls))}; reach: {item.get('reach', 0)}; evidence URLs: {', '.join(urls)}")
            else:
                lines.append(f"- 日期：{item.get('date')}；mentions：{item.get('mentions', len(urls))}；reach：{item.get('reach', 0)}；证据 URL：{', '.join(urls)}")

        if len(lines) <= 2:
            return content
        section = "\n".join(lines).strip()

        # Find tail sections to insert before
        if is_en:
            tail_markers = ("[Country Coverage]", "[Citation Notes]", "[References]", "[Latest Social Updates]")
        else:
            tail_markers = ("【国家覆盖】", "【引用备注】", "【参考文献】", "【社交媒体最新信息】")
        first_tail_positions = [pos for marker in tail_markers if (pos := content.find(marker)) != -1]
        if first_tail_positions:
            pos = min(first_tail_positions)
            return content[:pos].rstrip() + "\n\n" + section + "\n\n" + content[pos:].lstrip()
        return content.rstrip() + "\n\n" + section + "\n"

    def _replace_country_section_with_verified(
        self,
        content: str,
        raw_search_data: Optional[dict],
        report_language: str = "zh",
    ) -> str:
        """Replace country coverage section with verified data."""
        is_en = report_language == "en"
        marker = "[Country Coverage]" if is_en else "【国家覆盖】"
        if not raw_search_data or not isinstance(raw_search_data.get("country_coverage"), list):
            return content

        coverage_rows = [item for item in raw_search_data.get("country_coverage", []) if isinstance(item, dict)]
        summary = raw_search_data.get("collection_summary") if isinstance(raw_search_data.get("collection_summary"), dict) else {}
        lines = [marker]
        if coverage_rows:
            if is_en:
                lines.append(
                    'The following country/region coverage is based only on the same batch of verified x_search / web_search raw evidence; results that cannot be reliably attributed to a country are counted under "Global/Unattributed".'
                )
            else:
                lines.append(
                    '以下国家/地区覆盖只基于同一批已通过 URL 校验的 x_search / web_search 原始证据聚合；无法可靠归属国家的真实结果统一计入"全球/未归属"。'
                )
            if summary:
                if is_en:
                    lines.append(
                        f"- Data consistency: user selected max {summary.get('requested_social_updates', 0)} social items; raw candidate target {summary.get('raw_candidates_requested', 0)}; verified passed {summary.get('verified_social_updates', 0)}; country coverage evidence total {summary.get('country_coverage_total', 0)}; note: {summary.get('shortfall_reason', '')}."
                    )
                else:
                    lines.append(
                        f"- 数据一致性：用户选择社媒最多 {summary.get('requested_social_updates', 0)} 条；原始候选抓取目标 {summary.get('raw_candidates_requested', 0)} 条；实际校验通过 {summary.get('verified_social_updates', 0)} 条；国家覆盖证据总量 {summary.get('country_coverage_total', 0)} 条；说明：{summary.get('shortfall_reason', '')}。"
                    )
            for item in coverage_rows:
                urls = [str(url) for url in (item.get("urls") or []) if url]
                if not urls:
                    continue
                platforms = item.get("platforms") or []
                if not isinstance(platforms, list):
                    platforms = [platforms]
                if is_en:
                    lines.append(
                        f"- Country/Region: {item.get('country', 'Global/Unattributed')}; heat count: {item.get('coverage', len(urls))}; main platforms: {', '.join(str(p) for p in platforms if p) or 'Unlabeled'}; evidence URLs: {', '.join(urls)}."
                    )
                else:
                    lines.append(
                        f"- 国家/地区：{item.get('country', '全球/未归属')}；热度计数：{item.get('coverage', len(urls))}；主要平台：{', '.join(str(p) for p in platforms if p) or '未标注'}；证据 URL 列表：{'、'.join(urls)}。"
                    )
        if len(lines) == 1:
            lines.append("No verifiable country coverage data found." if is_en else "未检索到可核验国家覆盖数据。")

        section = "\n".join(lines).strip()
        idx = content.find(marker)
        if idx == -1:
            if is_en:
                first_tail_positions = [pos for m in ("[Citation Notes]", "[References]", "[Latest Social Updates]") if (pos := content.find(m)) != -1]
            else:
                first_tail_positions = [pos for m in ("【引用备注】", "【参考文献】", "【社交媒体最新信息】") if (pos := content.find(m)) != -1]
            if first_tail_positions:
                pos = min(first_tail_positions)
                return content[:pos].rstrip() + "\n\n" + section + "\n\n" + content[pos:].lstrip()
            return content.rstrip() + "\n\n" + section + "\n"

        if is_en:
            next_positions = [content.find(m, idx + 1) for m in ("[Trend Statistics]", "[Citation Notes]", "[References]", "[Latest Social Updates]") if content.find(m, idx + 1) != -1]
        else:
            next_positions = [content.find(f"【{m}】", idx + 1) for m in ("趋势统计", "引用备注", "参考文献", "社交媒体最新信息") if content.find(f"【{m}】", idx + 1) != -1]
        end = min(next_positions) if next_positions else len(content)
        return content[:idx].rstrip() + "\n\n" + section + "\n\n" + content[end:].lstrip()

    def _replace_social_section_with_verified(
        self,
        content: str,
        raw_search_data: Optional[dict],
        report_language: str = "zh",
    ) -> str:
        """Replace social updates section with verified URLs only."""
        is_en = report_language == "en"
        marker = "[Latest Social Updates]" if is_en else "【社交媒体最新信息】"
        head = content[:content.find(marker)].rstrip() if marker in content else content.rstrip()
        validator = self._dashboard_service
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
                urls = [u.rstrip(")],.，。；;:：") for u in re.findall(r"https?://[^\s)\]}，。；;、]+", line)]
                urls = [u for u in urls if validator._is_real_url(u)]
                for url in urls:
                    verified_items.append({"time": "", "platform": "", "account": "", "summary": line.strip(), "url": url})

        lines = [marker]
        summary = raw_search_data.get("collection_summary") if raw_search_data and isinstance(raw_search_data.get("collection_summary"), dict) else {}
        if summary:
            if is_en:
                lines.append(
                    f"Data consistency: user selected max {summary.get('requested_social_updates', 0)} social items; raw candidate target {summary.get('raw_candidates_requested', 0)}; verified passed URL check {summary.get('verified_social_updates', 0)}; reason for not reaching target: {summary.get('shortfall_reason', '')}."
                )
            else:
                lines.append(
                    f"数据一致性：用户选择社媒最多 {summary.get('requested_social_updates', 0)} 条；原始候选抓取目标 {summary.get('raw_candidates_requested', 0)} 条；实际通过 URL 校验 {summary.get('verified_social_updates', 0)} 条；未达到设定值原因：{summary.get('shortfall_reason', '')}。"
                )
        if verified_items:
            seen = set()
            for item in verified_items:
                url = item["url"]
                if url in seen:
                    continue
                seen.add(url)
                parts = []
                if item.get("time"):
                    parts.append(f"{'Time' if is_en else '时间'}：{item['time']}")
                if item.get("platform"):
                    parts.append(f"{'Platform' if is_en else '平台'}：{item['platform']}")
                if item.get("account"):
                    parts.append(f"{'Account/Source' if is_en else '账号/来源'}：{item['account']}")
                if item.get("summary"):
                    parts.append(f"{'Summary' if is_en else '摘要'}：{item['summary'][:240]}")
                parts.append(f"{'Link' if is_en else '链接'}：{url}")
                lines.append("- " + ("; " if is_en else "；").join(parts))
        else:
            lines.append("No social media updates with verified public URLs found." if is_en else "未检索到带真实公开 URL 的社交媒体动态。")
        return head + "\n\n" + "\n".join(lines).strip() + "\n"

    def _sanitize_report_urls(self, content: str, report_language: str = "zh") -> str:
        """Remove report lines containing invalid/hallucinated social URLs."""
        is_en = report_language == "en"
        validator = self._dashboard_service
        cleaned_lines = []
        removed = 0
        for line in content.splitlines():
            urls = [u.rstrip(")],.，。；;:：") for u in re.findall(r"https?://[^\s)\]}，。；;、]+", line)]
            if urls and any(not validator._is_real_url(url) for url in urls):
                removed += 1
                continue
            cleaned_lines.append(line)
        cleaned = "\n".join(cleaned_lines)
        if removed:
            if is_en:
                marker = f"\n\n[Data Cleaning Note]\nFiltered {removed} social media/citation records that did not pass URL multi-verification, to avoid displaying model-generated fake links.\n"
                insert_pos = cleaned.find("[Citation Notes]")
            else:
                marker = f"\n\n【数据清洗说明】\n已过滤 {removed} 条未通过 URL 多重校验的社交媒体/引用记录，避免展示模型生成的假链接。\n"
                insert_pos = cleaned.find("【引用备注】")
            if insert_pos != -1:
                cleaned = cleaned[:insert_pos].rstrip() + marker + "\n" + cleaned[insert_pos:]
            else:
                cleaned = cleaned.rstrip() + marker
        return cleaned

    def _parse_sentiment(self, content: str) -> dict:
        """Extract sentiment scores from analysis content.

        Prefer explicit JSON blocks, but also support common Chinese report text.
        If no valid distribution is found, return zeros.
        """
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
            (r'情绪分布[：:]\s*正面\s*(\d+(?:\.\d+)?)%[、,，\s]*中性\s*(\d+(?:\.\d+)?)%[、,，\s]*负面\s*(\d+(?:\.\d+)?)%',
             ("positive", "neutral", "negative")),
            (r'情感量化[\s\S]{0,120}?正面[：:]\s*(\d+(?:\.\d+)?)%[\s\S]{0,120}?中性[：:]\s*(\d+(?:\.\d+)?)%[\s\S]{0,120}?负面[：:]\s*(\d+(?:\.\d+)?)%',
             ("positive", "neutral", "negative")),
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

        return {"positive": 0.0, "neutral": 0.0, "negative": 0.0}

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        data_content: Optional[dict] = None,
        uploaded_files: Optional[list[dict]] = None,
        image_inputs: Optional[list[dict]] = None,
        social_updates_limit: int = 10,
        raw_search_data: Optional[dict] = None,
        report_language: str = "zh",
        target_region: str = "global",
    ) -> str:
        """Generate analysis report (non-streaming).

        Args:
            prompt: Base analysis prompt
            model: Model ID to use
            data_content: Object Storage reference data
            uploaded_files: User uploaded files
            image_inputs: Base64 encoded images
            social_updates_limit: Max social updates
            raw_search_data: Verified raw data from collection
            report_language: Output language
            target_region: Target region

        Returns:
            Post-processed report content
        """
        full_prompt = self.build_analysis_prompt(
            prompt,
            data_content,
            uploaded_files,
            social_updates_limit=social_updates_limit,
            raw_search_data=raw_search_data,
            report_language=report_language,
            target_region=target_region,
        )

        content = await asyncio.wait_for(
            self.genai.analyze_with_tools(
                full_prompt,
                model=model,
                tools=[{"type": "x_search"}, {"type": "web_search"}],
                image_inputs=image_inputs,
            ),
            timeout=self.analysis_timeout,
        )

        return self._post_process_report(content, raw_search_data, report_language)

    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        data_content: Optional[dict] = None,
        uploaded_files: Optional[list[dict]] = None,
        image_inputs: Optional[list[dict]] = None,
        social_updates_limit: int = 10,
        raw_search_data: Optional[dict] = None,
        report_language: str = "zh",
        target_region: str = "global",
    ) -> AsyncGenerator[str, None]:
        """Generate analysis report with streaming.

        Args:
            prompt: Base analysis prompt
            model: Model ID to use
            data_content: Object Storage reference data
            uploaded_files: User uploaded files
            image_inputs: Base64 encoded images
            social_updates_limit: Max social updates
            raw_search_data: Verified raw data from collection
            report_language: Output language
            target_region: Target region

        Yields:
            Streaming chunks, then final processed text with marker
        """
        full_prompt = self.build_analysis_prompt(
            prompt,
            data_content,
            uploaded_files,
            social_updates_limit=social_updates_limit,
            raw_search_data=raw_search_data,
            report_language=report_language,
            target_region=target_region,
        )

        # Stream raw chunks to frontend
        buffered = []
        async for chunk in self.genai.analyze_stream(full_prompt, model=model, image_inputs=image_inputs):
            buffered.append(chunk)
            yield chunk

        # Post-process the full text
        final_text = self._post_process_report(
            "".join(buffered),
            raw_search_data,
            report_language,
        )

        # Yield processed text with marker
        yield f"\n__PROCESSED_FINAL__\n{final_text}"
