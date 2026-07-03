"""Tests for analysis engine."""

import pytest
from app.services.analysis_engine import AnalysisEngine


def test_parse_sentiment_valid():
    engine = AnalysisEngine(genai_client=None, storage_service=None)
    content = '''
Some analysis text

```json
{"positive": 0.5, "neutral": 0.3, "negative": 0.2}
```

More text
'''
    result = engine._parse_sentiment(content)
    assert result["positive"] == 0.5
    assert result["neutral"] == 0.3
    assert result["negative"] == 0.2


def test_parse_sentiment_no_json():
    engine = AnalysisEngine(genai_client=None, storage_service=None)
    content = "No sentiment data here"
    result = engine._parse_sentiment(content)
    # Returns default equal distribution
    assert result["positive"] == 0.33
    assert result["neutral"] == 0.34
    assert result["negative"] == 0.33


def test_parse_sentiment_chinese_inline_distribution():
    engine = AnalysisEngine(genai_client=None, storage_service=None)
    content = "热度量化：情绪分布：正面72%、中性21%、负面7%。"
    result = engine._parse_sentiment(content)
    assert result["positive"] == 0.72
    assert result["neutral"] == 0.21
    assert result["negative"] == 0.07


def test_parse_sentiment_chinese_quantified_bullets():
    engine = AnalysisEngine(genai_client=None, storage_service=None)
    content = """
**情感量化**（基于样本聚类）：
- 正面：68%
- 中性：22%
- 负面：10%
"""
    result = engine._parse_sentiment(content)
    assert result["positive"] == 0.68
    assert result["neutral"] == 0.22
    assert result["negative"] == 0.10


def test_build_prompt_no_data():
    engine = AnalysisEngine(genai_client=None, storage_service=None)
    result = engine._build_prompt("Test prompt")
    assert "Test prompt" in result
    assert "结构化" in result


def test_build_prompt_with_data():
    engine = AnalysisEngine(genai_client=None, storage_service=None)
    data = {"format": "json", "data": [{"key": "value"}]}
    result = engine._build_prompt("Test prompt", data)
    assert "Test prompt" in result
    assert "参考数据" in result
    assert "key" in result
