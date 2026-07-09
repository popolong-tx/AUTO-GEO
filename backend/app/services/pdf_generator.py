"""PDF report generator using ReportLab."""

import os
import re
import io
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Image as RLImage,
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


def _register_chinese_font():
    """Register a Chinese font for PDF generation."""
    font_paths = [
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/System/Library/Fonts/Supplemental/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Songti.ttc",
        "/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/STHeiti Light.ttc",
        os.path.join(os.path.dirname(__file__), "..", "utils", "fonts", "NotoSansSC-Regular.ttf"),
        os.path.join(os.path.dirname(__file__), "..", "utils", "fonts", "NotoSansCJK-Regular.ttc"),
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                if font_path.lower().endswith('.ttc'):
                    # TTC can fail with TTFont on some environments; try direct registration only if supported.
                    try:
                        pdfmetrics.registerFont(TTFont("ChineseFont", font_path))
                        return "ChineseFont"
                    except Exception:
                        continue
                pdfmetrics.registerFont(TTFont("ChineseFont", font_path))
                return "ChineseFont"
            except Exception:
                continue
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light"
    except Exception:
        return "Helvetica"


FONT_NAME = _register_chinese_font()


def _wrap_chinese_text(text: str) -> str:
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class PDFGenerator:
    """Generate formatted PDF reports from analysis results."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Configure custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name="CoverTitle",
            fontName=FONT_NAME,
            fontSize=28,
            leading=36,
            alignment=1,
            spaceAfter=20,
            textColor=colors.HexColor("#1a365d"),
        ))
        self.styles.add(ParagraphStyle(
            name="CoverSubtitle",
            fontName=FONT_NAME,
            fontSize=16,
            leading=24,
            alignment=1,
            spaceAfter=10,
            textColor=colors.HexColor("#4a5568"),
        ))
        self.styles.add(ParagraphStyle(
            name="SectionTitle",
            fontName=FONT_NAME,
            fontSize=18,
            leading=24,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor("#1a365d"),
            borderWidth=0,
            borderColor=colors.HexColor("#3182ce"),
            borderPadding=5,
        ))
        self.styles.add(ParagraphStyle(
            name="SubSection",
            fontName=FONT_NAME,
            fontSize=14,
            leading=20,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor("#2d3748"),
        ))
        self.styles.add(ParagraphStyle(
            name="BodyCN",
            fontName=FONT_NAME,
            fontSize=10,
            leading=16,
            spaceAfter=6,
            textColor=colors.HexColor("#2d3748"),
        ))
        self.styles.add(ParagraphStyle(
            name="BulletCN",
            fontName=FONT_NAME,
            fontSize=10,
            leading=16,
            leftIndent=20,
            spaceAfter=4,
            textColor=colors.HexColor("#4a5568"),
        ))

    def _header_footer(self, canvas, doc, language: str = "zh"):
        """Draw header and footer on each page."""
        canvas.saveState()
        is_en = language == "en"
        # Header line
        canvas.setStrokeColor(colors.HexColor("#3182ce"))
        canvas.setLineWidth(2)
        canvas.line(20*mm, A4[1] - 15*mm, A4[0] - 20*mm, A4[1] - 15*mm)
        # Header text
        canvas.setFont(FONT_NAME if FONT_NAME else "Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#718096"))
        header_text = "AUTO GEO Sentiment Report" if is_en else "AUTO GEO 舆情分析报告"
        canvas.drawString(20*mm, A4[1] - 13*mm, _wrap_chinese_text(header_text))
        # Footer
        canvas.line(20*mm, 15*mm, A4[0] - 20*mm, 15*mm)
        time_label = "Generated at" if is_en else "生成时间"
        canvas.drawString(20*mm, 10*mm, _wrap_chinese_text(f"{time_label}: {datetime.now().strftime('%Y-%m-%d %H:%M')}"))
        page_label = "Page" if is_en else "第"
        page_suffix = "" if is_en else "页"
        canvas.drawRightString(A4[0] - 20*mm, 10*mm, _wrap_chinese_text(f"{page_label} {doc.page}{page_suffix}"))
        canvas.restoreState()

    def _create_cover(self, topic_name: str, analysis_date: str, language: str = "zh") -> list:
        """Create cover page elements."""
        is_en = language == "en"
        elements = []
        elements.append(Spacer(1, 80*mm))
        elements.append(Paragraph(_wrap_chinese_text("AUTO GEO"), self.styles["CoverTitle"]))
        title = "Sentiment Analysis Report" if is_en else "舆情分析报告"
        elements.append(Paragraph(_wrap_chinese_text(title), self.styles["CoverTitle"]))
        elements.append(Spacer(1, 15*mm))
        elements.append(Paragraph(_wrap_chinese_text(topic_name), self.styles["CoverSubtitle"]))
        elements.append(Spacer(1, 10*mm))
        date_label = "Analysis Date" if is_en else "分析日期"
        elements.append(Paragraph(_wrap_chinese_text(f"{date_label}: {analysis_date}"), self.styles["CoverSubtitle"]))
        elements.append(Spacer(1, 5*mm))
        confidential = "CONFIDENTIAL - Internal Use Only" if is_en else "机密 - 仅供内部使用"
        elements.append(Paragraph(_wrap_chinese_text(confidential), ParagraphStyle(
            "Confidential", fontName=FONT_NAME, fontSize=10,
            alignment=1, textColor=colors.HexColor("#e53e3e"),
        )))
        elements.append(PageBreak())
        return elements

    def _create_sentiment_chart(self, sentiment: dict, language: str = "zh") -> Drawing:
        """Create a sentiment pie chart."""
        is_en = language == "en"
        d = Drawing(300, 200)
        pie = Pie()
        pie.x = 75
        pie.y = 25
        pie.width = 150
        pie.height = 150
        pie.data = [
            sentiment.get("positive", 0.33) * 100,
            sentiment.get("neutral", 0.34) * 100,
            sentiment.get("negative", 0.33) * 100,
        ]
        pie.labels = None
        pie.slices.strokeWidth = 1
        pie.slices.strokeColor = colors.white
        pie.slices[0].fillColor = colors.HexColor("#48bb78")
        pie.slices[1].fillColor = colors.HexColor("#ecc94b")
        pie.slices[2].fillColor = colors.HexColor("#f56565")
        d.add(pie)
        # Legend with bilingual labels
        if is_en:
            labels = [("Positive", "#48bb78"), ("Neutral", "#ecc94b"), ("Negative", "#f56565")]
        else:
            labels = [("正面", "#48bb78"), ("中性", "#ecc94b"), ("负面", "#f56565")]
        for i, (label, color) in enumerate(labels):
            d.add(Rect(250, 140 - i*25, 12, 12, fillColor=colors.HexColor(color)))
            d.add(String(268, 143 - i*25, f"{label}: {pie.data[i]:.0f}%", fontName=FONT_NAME, fontSize=9))
        return d

    def _parse_markdown_sections(self, content: str, language: str = "zh") -> list:
        """Parse markdown content into reportlab elements."""
        is_en = language == "en"
        elements = []
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith("## "):
                title = line[3:].strip()
                # Check for sentiment JSON block (support both Chinese and English)
                if "情绪分析" in title or "Sentiment Analysis" in title:
                    elements.append(Paragraph(_wrap_chinese_text(title), self.styles["SectionTitle"]))
                    # Look for JSON block
                    json_found = False
                    for j in range(i+1, min(i+10, len(lines))):
                        if "```json" in lines[j]:
                            json_str = ""
                            for k in range(j+1, min(j+5, len(lines))):
                                if "```" in lines[k]:
                                    break
                                json_str += lines[k]
                            try:
                                import json
                                sentiment = json.loads(json_str)
                                elements.append(self._create_sentiment_chart(sentiment))
                            except Exception as e:
                                elements.append(Paragraph("[情绪图解析失败，已跳过]", self.styles["BodyCN"]))
                            i = k + 1
                            json_found = True
                            break
                    if not json_found:
                        i += 1
                    continue
                elements.append(Paragraph(_wrap_chinese_text(title), self.styles["SectionTitle"]))

            elif line.startswith("### "):
                elements.append(Paragraph(_wrap_chinese_text(line[4:].strip()), self.styles["SubSection"]))

            elif line.startswith("- "):
                elements.append(Paragraph(_wrap_chinese_text(f"• {line[2:].strip()}"), self.styles["BulletCN"]))

            elif line.startswith("```"):
                # Skip code blocks
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    i += 1
                i += 1
                continue

            elif line:
                elements.append(Paragraph(_wrap_chinese_text(line), self.styles["BodyCN"]))

            i += 1
        return elements

    def generate(
        self,
        topic_name: str,
        content: str,
        sentiment: Optional[dict] = None,
        model: str = "",
        language: str = "zh",
    ) -> bytes:
        """Generate a PDF report from analysis content."""
        is_en = language == "en"
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=25*mm,
            bottomMargin=25*mm,
        )

        elements = []
        # Cover page
        date_format = "%Y-%m-%d" if is_en else "%Y年%m月%d日"
        elements.extend(self._create_cover(
            topic_name,
            datetime.now().strftime(date_format),
            language=language,
        ))

        # Analysis content
        elements.extend(self._parse_markdown_sections(content, language=language))

        # Use lambda to pass language to header_footer callback
        header_footer_fn = lambda canvas, doc: self._header_footer(canvas, doc, language=language)
        doc.build(elements, onFirstPage=header_footer_fn, onLaterPages=header_footer_fn)
        return buffer.getvalue()
