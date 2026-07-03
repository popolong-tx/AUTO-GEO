"""Dashboard construction helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from collections import defaultdict
from urllib.parse import urlparse


@dataclass
class ParsedEvidence:
    title: str = ""
    summary: str = ""
    url: str = ""
    source_type: str = "unknown"


class DashboardService:
    """Build a minimal dashboard dict from an AnalysisResult-like object."""

    METRIC_NAMES = {
        "total_mentions": "Total Mentions",
        "total_reach": "Total Reach",
        "total_ave": "Total AVE",
    }

    def build_dashboard(self, analysis_result: Any) -> dict[str, Any]:
        content = getattr(analysis_result, "content", "") or ""
        sentiment = getattr(analysis_result, "sentiment", {}) or {}

        metrics = self._extract_metrics(content)
        sources = self._extract_source_evidence(content)
        country_coverage = self._extract_country_coverage(content)
        trend = self._extract_trend(content)

        return {
            "topic_id": getattr(analysis_result, "topic_id", ""),
            "analysis_id": getattr(analysis_result, "id", ""),
            "generated_at": getattr(analysis_result, "created_at", None),
            "metrics": metrics,
            "sentiment": sentiment,
            "sources": sources,
            "country_coverage": country_coverage,
            "trend": trend,
        }


    def build_from_analysis(self, analysis_result: Any) -> dict[str, Any]:
        return self.build_dashboard(analysis_result)

    def _extract_metrics(self, content: str) -> dict[str, dict[str, Any]]:
        metrics: dict[str, dict[str, Any]] = {}
        patterns = {
            "total_mentions": [r"Total Mentions\s*[:：]\s*([\d,]+(?:\.\d+)?)", r"(?:总提及|提及总数|mentions)\s*[:：]\s*([\d,]+(?:\.\d+)?)"],
            "total_reach": [r"Total Reach\s*[:：]\s*([\d,]+(?:\.\d+)?)", r"(?:总覆盖|覆盖总量|reach)\s*[:：]\s*([\d,]+(?:\.\d+)?)"],
            "total_ave": [r"Total AVE\s*[:：]\s*([\d,]+(?:\.\d+)?)", r"(?:AVE总计|总AVE|ave)\s*[:：]\s*([\d,]+(?:\.\d+)?)"],
        }

        for key, regexes in patterns.items():
            value = None
            for regex in regexes:
                match = re.search(regex, content, re.IGNORECASE)
                if match:
                    value = self._to_number(match.group(1))
                    break
            metrics[self.METRIC_NAMES[key]] = {"name": self.METRIC_NAMES[key], "value": value}
        return metrics

    def _extract_source_evidence(self, content: str) -> list[dict[str, Any]]:
        sections = self._split_sections(content)
        combined_text = "\n".join(
            sections.get(name, "") for name in ("参考文献", "社交媒体最新信息", "引用备注")
        )
        if not combined_text.strip():
            combined_text = content

        evidence: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for line in combined_text.splitlines():
            parsed = self._parse_evidence_line(line)
            if not parsed:
                continue
            key = (parsed.title, parsed.url)
            if key in seen:
                continue
            seen.add(key)
            evidence.append(
                {
                    "title": parsed.title,
                    "summary": parsed.summary,
                    "url": parsed.url,
                    "source_type": parsed.source_type,
                }
            )
        return evidence

    def _extract_country_coverage(self, content: str) -> list[dict[str, Any]]:
        section = self._find_section(content, "国家覆盖")
        candidates = section or "\n".join(
            self._split_sections(content).get(name, "") for name in ("趋势统计", "社交媒体最新信息", "参考文献", "引用备注")
        )
        grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"country": "", "coverage": 0, "urls": [], "platforms": set(), "summary": ""})
        for line in candidates.splitlines():
            text = line.strip().lstrip("-•*0123456789.、 ")
            if not text:
                continue
            urls = [u.rstrip(")],.，。；;:：") for u in re.findall(r"https?://[^\s)\]}，。；;、]+", text)]
            urls = [u for u in urls if self._is_real_url(u)]
            country = self._extract_country_from_line(text)
            if not country:
                continue
            item = grouped[country]
            item["country"] = country
            item["summary"] = item["summary"] or (text if len(text) <= 180 else text[:177] + "...")
            if urls:
                for url in urls:
                    if url not in item["urls"]:
                        item["urls"].append(url)
                        item["coverage"] += 1
            else:
                item["coverage"] += 1
            platform = self._extract_platform(text, urls[0] if urls else country)
            if platform:
                item["platforms"].add(platform)
        rows = []
        for item in grouped.values():
            rows.append({
                "country": item["country"],
                "coverage": item["coverage"],
                "urls": item["urls"][:5],
                "platforms": sorted(item["platforms"]),
                "summary": item["summary"],
                "source_type": "coverage",
            })
        return sorted(rows, key=lambda x: x["coverage"], reverse=True)[:8]

    def _extract_trend(self, content: str) -> list[dict[str, Any]]:
        trend_section = self._find_section(content, "趋势统计")
        sections = self._split_sections(content)
        candidates = trend_section or "\n".join(sections.get(name, "") for name in ("社交媒体最新信息", "参考文献", "引用备注")) or content
        by_date: dict[str, dict[str, Any]] = defaultdict(lambda: {"date": "", "mentions": 0, "reach": 0, "urls": []})
        for line in candidates.splitlines():
            text = line.strip()
            urls = [u.rstrip(")],.，。；;:：") for u in re.findall(r"https?://[^\s)\]}，。；;、]+", text)]
            urls = [u for u in urls if self._is_real_url(u)]
            date = self._extract_date_from_line(text)
            if not date:
                continue
            item = by_date[date]
            item["date"] = date
            # Count a mention even if the line has no explicit URL but clearly belongs to the trend section.
            if urls:
                for url in urls:
                    if url not in item["urls"]:
                        item["urls"].append(url)
                        item["mentions"] += 1
            else:
                item["mentions"] += 1
            item["reach"] += self._extract_reach_from_line(text)
        rows = list(by_date.values())
        rows.sort(key=lambda x: x["date"])
        return rows[:14]

    def _extract_date_from_line(self, text: str) -> str:
        explicit = re.search(r"(?:时间|日期|date)\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})", text, re.IGNORECASE)
        if explicit:
            return explicit.group(1).replace("/", "-")
        any_date = re.search(r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b", text)
        return any_date.group(1).replace("/", "-") if any_date else ""

    def _extract_reach_from_line(self, text: str) -> int:
        match = re.search(r"(?:reach|浏览|观看|播放|点赞|转发|互动)\s*[:：]?\s*([\d,]+)", text, re.IGNORECASE)
        if not match:
            return 0
        try:
            return int(match.group(1).replace(",", ""))
        except Exception:
            return 0

    def _is_real_url(self, url: str) -> bool:
        if not url:
            return False
        lowered = url.lower()
        bad_markers = ("example", "placeholder", "dummy", "fake", "/video/example", "/post/example", "/watch/example")
        if any(marker in lowered for marker in bad_markers):
            return False
        parsed = urlparse(url)
        host = parsed.netloc.lower().removeprefix("www.")
        path = parsed.path.strip("/")
        if not host or not path:
            return False
        # High-risk/generated-looking social URLs must match real platform ID shapes.
        if host in ("x.com", "twitter.com"):
            parts = path.split("/")
            if len(parts) < 3 or parts[1].lower() != "status":
                return False
            status_id = parts[2]
            if not re.fullmatch(r"\d{15,22}", status_id):
                return False
            # Common model hallucination pattern observed in reports.
            if status_id in {"1808123456789123456"} or re.search(r"(123456|234567|345678|456789|567890|678901|789012|890123)", status_id):
                return False
        if host == "tiktok.com":
            parts = path.split("/")
            if len(parts) < 3 or not parts[0].startswith("@") or parts[1].lower() != "video":
                return False
            video_id = parts[2]
            if not re.fullmatch(r"\d{17,22}", video_id):
                return False
            if video_id in {"1234567890"} or re.search(r"(?:1234567890|0123456789|9876543210)", video_id):
                return False
        if host == "facebook.com":
            # Reject obviously fabricated examples such as /groups/.../posts/abc123.
            if re.search(r"/(posts|videos|photos)/abc\d+", path, re.IGNORECASE):
                return False
            if re.search(r"/(posts|videos|photos)/", path, re.IGNORECASE):
                tail = path.rstrip("/").split("/")[-1]
                if not re.fullmatch(r"\d{8,}", tail):
                    return False
        # Platform homepages are not evidence URLs for a specific item.
        if re.match(r"https?://(?:www\.)?(x|twitter|tiktok|youtube|instagram|facebook|reddit|linkedin)\.com/?$", lowered):
            return False
        return True

    def _extract_country_from_line(self, text: str) -> str:
        explicit = re.search(r"(?:国家/地区|国家|地区)\s*[:：]\s*([^，,；;\n]+)", text)
        if explicit:
            return explicit.group(1).strip()
        patterns = [
            (r"\b(?:US|USA|United States)\b|美国", "美国"),
            (r"\b(?:UK|United Kingdom|Britain)\b|英国", "英国"),
            (r"\b(?:Germany|DE)\b|德国", "德国"),
            (r"\b(?:Japan|JP|JPN)\b|日本", "日本"),
            (r"\b(?:France|FR)\b|法国", "法国"),
            (r"\b(?:Canada|CA)\b|加拿大", "加拿大"),
            (r"\b(?:Australia|AU)\b|澳大利亚", "澳大利亚"),
            (r"\b(?:India|IN)\b|印度", "印度"),
            (r"\b(?:Brazil|BR)\b|巴西", "巴西"),
            (r"\b(?:China|CN)\b|中国", "中国"),
            (r"\b(?:Korea|KR|South Korea)\b|韩国", "韩国"),
            (r"\b(?:Singapore|SG)\b|新加坡", "新加坡"),
        ]
        for regex, country in patterns:
            if re.search(regex, text, re.IGNORECASE):
                return country
        return ""

    def _extract_platform(self, text: str, url: str) -> str:
        haystack = f"{text} {url}".lower()
        for key, name in (("twitter.com", "X"), ("x.com", "X"), ("tiktok", "TikTok"), ("youtube", "YouTube"), ("instagram", "Instagram"), ("facebook", "Facebook"), ("reddit", "Reddit"), ("linkedin", "LinkedIn")):
            if key in haystack:
                return name
        if "web_search" in haystack:
            return "web_search"
        return "web"

    def _find_section(self, content: str, marker: str) -> str:
        idx = content.find(f"【{marker}】")
        if idx == -1:
            return ""
        next_positions = [content.find(f"【{m}】", idx + 1) for m in ("趋势统计", "引用备注", "参考文献", "社交媒体最新信息", "国家覆盖") if content.find(f"【{m}】", idx + 1) != -1]
        end = min(next_positions) if next_positions else len(content)
        return content[idx:end]

    def _split_sections(self, content: str) -> dict[str, str]:
        markers = ["引用备注", "参考文献", "社交媒体最新信息"]
        positions: list[tuple[int, str]] = []
        for marker in markers:
            pos = content.find(f"【{marker}】")
            if pos != -1:
                positions.append((pos, marker))
        positions.sort()
        sections: dict[str, str] = {}
        for i, (start, marker) in enumerate(positions):
            end = positions[i + 1][0] if i + 1 < len(positions) else len(content)
            sections[marker] = content[start:end]
        return sections

    def _parse_evidence_line(self, line: str) -> ParsedEvidence | None:
        text = line.strip().lstrip("-•*0123456789.、 ")
        if not text:
            return None
        if len(text) < 8:
            return None

        url_match = re.search(r"https?://[^\s)\]}，。；;、]+", text)
        url = url_match.group(0).rstrip(")],.，。；;:：") if url_match else ""
        title = text
        if url:
            title = text.replace(url_match.group(0), "").strip(" -:：|()[]{}")
        title = re.sub(r"^(来源|source)\s*[:：]\s*", "", title, flags=re.IGNORECASE).strip()
        source_hint = re.search(r"\b(X|YouTube|Reddit|Instagram|Facebook|TikTok|LinkedIn)\b", text, re.IGNORECASE)
        if not title:
            title = url or text[:80]

        # Reject placeholder / example URLs so they never reach the UI.
        bad_url_markers = [
            "example",
            "/video/example",
            "/watch/example",
            "/post/example",
            "placeholder",
            "dummy",
            "fake",
        ]
        if url and any(marker in url.lower() for marker in bad_url_markers):
            return None

        # Keep only genuinely useful entries; if we cannot derive a real URL,
        # preserve the record but mark it as inaccessible instead of inventing one.
        if not url:
            return None
        source_type = "social" if source_hint else "reference"
        summary = text if len(text) <= 240 else text[:237] + "..."
        if not url:
            summary = f"{summary} (URL unavailable)"
        return ParsedEvidence(title=title, summary=summary, url=url, source_type=source_type)

    def _to_number(self, value: str) -> int | float | None:
        cleaned = value.replace(",", "").strip()
        try:
            number = float(cleaned)
        except ValueError:
            return None
        return int(number) if number.is_integer() else number
