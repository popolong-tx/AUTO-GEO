"""Tests for analysis engine and report generator."""

import pytest
from app.services.analysis_engine import AnalysisEngine
from app.services.report_generator import ReportGenerator


def test_parse_sentiment_valid():
    genai_client = None
    generator = ReportGenerator(genai_client=genai_client)
    content = '''
Some analysis text

```json
{"positive": 0.5, "neutral": 0.3, "negative": 0.2}
```

More text
'''
    result = generator._parse_sentiment(content)
    assert result["positive"] == 0.5
    assert result["neutral"] == 0.3
    assert result["negative"] == 0.2


def test_parse_sentiment_no_json():
    genai_client = None
    generator = ReportGenerator(genai_client=genai_client)
    content = "No sentiment data here"
    result = generator._parse_sentiment(content)
    # Returns zeros when no sentiment found
    assert result["positive"] == 0.0
    assert result["neutral"] == 0.0
    assert result["negative"] == 0.0


def test_parse_sentiment_chinese_inline_distribution():
    genai_client = None
    generator = ReportGenerator(genai_client=genai_client)
    content = "热度量化：情绪分布：正面72%、中性21%、负面7%。"
    result = generator._parse_sentiment(content)
    assert result["positive"] == 0.72
    assert result["neutral"] == 0.21
    assert result["negative"] == 0.07


def test_parse_sentiment_chinese_quantified_bullets():
    genai_client = None
    generator = ReportGenerator(genai_client=genai_client)
    content = """
**情感量化**（基于样本聚类）：
- 正面：68%
- 中性：22%
- 负面：10%
"""
    result = generator._parse_sentiment(content)
    assert result["positive"] == 0.68
    assert result["neutral"] == 0.22
    assert result["negative"] == 0.10


def test_build_analysis_prompt_zh():
    genai_client = None
    generator = ReportGenerator(genai_client=genai_client)
    result = generator.build_analysis_prompt("Test prompt", report_language="zh")
    assert "Test prompt" in result
    assert "舆情分析专家" in result


def test_build_analysis_prompt_en():
    genai_client = None
    generator = ReportGenerator(genai_client=genai_client)
    result = generator.build_analysis_prompt("Test prompt", report_language="en")
    assert "Test prompt" in result
    assert "sentiment analysis expert" in result


def test_enforce_report_tail_sections_zh():
    genai_client = None
    generator = ReportGenerator(genai_client=genai_client)
    content = """# Report

Some content

【社交媒体最新信息】
Social content

【国家覆盖】
Country content

【引用备注】
Citation content

【参考文献】
Reference content
"""
    result = generator._enforce_report_tail_sections(content, report_language="zh")
    # Check that sections are in correct order
    assert result.index("【国家覆盖】") < result.index("【引用备注】")
    assert result.index("【引用备注】") < result.index("【参考文献】")
    assert result.index("【参考文献】") < result.index("【社交媒体最新信息】")


def test_enforce_report_tail_sections_en():
    genai_client = None
    generator = ReportGenerator(genai_client=genai_client)
    content = """# Report

Some content

[Latest Social Updates]
Social content

[Country Coverage]
Country content

[Citation Notes]
Citation content

[References]
Reference content
"""
    result = generator._enforce_report_tail_sections(content, report_language="en")
    # Check that sections are in correct order
    assert result.index("[Country Coverage]") < result.index("[Citation Notes]")
    assert result.index("[Citation Notes]") < result.index("[References]")
    assert result.index("[References]") < result.index("[Latest Social Updates]")
