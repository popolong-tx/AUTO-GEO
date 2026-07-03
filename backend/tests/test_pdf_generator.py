"""Tests for PDF generator."""

import pytest
from app.services.pdf_generator import PDFGenerator


def test_generate_basic():
    gen = PDFGenerator()
    content = """
## 执行摘要
这是测试摘要内容。

### 技术传播维度
- 测试要点1
- 测试要点2

### 用户体验维度
用户反馈分析内容。
"""
    pdf_bytes = gen.generate(
        topic_name="测试话题",
        content=content,
        sentiment={"positive": 0.6, "neutral": 0.3, "negative": 0.1},
    )
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b'%PDF'


def test_generate_with_markdown():
    gen = PDFGenerator()
    content = """
## 执行摘要
测试内容

## 详细分析

### 维度一
- 要点1
- 要点2

### 维度二
详细分析内容。

## 情绪分析
```json
{"positive": 0.5, "neutral": 0.3, "negative": 0.2}
```

## 关键发现
- 发现1
- 发现2

## 建议措施
- 建议1
- 建议2
"""
    pdf_bytes = gen.generate(topic_name="完整测试", content=content)
    assert len(pdf_bytes) > 1000
