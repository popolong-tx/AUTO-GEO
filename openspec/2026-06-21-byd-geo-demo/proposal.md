## Why

比亚迪（BYD）作为全球新能源汽车龙头企业，需要一套专业的舆情监测与分析系统来跟踪关键事件的市场反应。当前缺少一个集成 OCI GenAI 能力、支持多话题深度分析、可生成 PDF 报告的演示应用。本项目旨在构建一个 GEO DEMO，展示 OCI Functions 无服务器架构 + Grok 大模型的舆情分析能力。

## What Changes

- 新建 OCI Functions 无服务器后端，调用 OCI GenAI 推理端点（Grok 模型）进行舆情分析
- 新建前端 Web 应用，仿照 Meltwater 融文舆情监测系统界面风格
- 支持 4 个独立话题页面，每个话题配有可在线编辑的分析提示词
- 集成 OCI Object Storage 读取外部数据源，结合 Grok 搜索能力进行综合分析
- 支持生成并导出 PDF 格式的分析报告，存储至 Object Storage
- 支持模型选择（xai.grok-4.20-multi-agent-0309 / xai.grok-4.3）

## Capabilities

### New Capabilities

- `oci-genai-integration`: OCI GenAI 推理端点集成，支持 Grok 模型调用、流式响应、模型切换
- `sentiment-analysis-engine`: 舆情分析引擎，整合 Object Storage 数据与 Grok 搜索结果，执行多维度分析
- `topic-management`: 话题管理模块，支持 4 个预设话题的 CRUD、提示词在线编辑
- `report-generation`: PDF 报告生成与导出，支持存储至 OCI Object Storage
- `web-dashboard`: 前端仪表盘，仿 Meltwater 风格，包含话题导航、分析结果展示、报告管理

### Modified Capabilities

（无已有能力需要修改）

## Impact

- **OCI 资源**: Functions、Object Storage、GenAI Inference endpoints
- **依赖**: Python 3.11+, OpenAI SDK, ReportLab/WeasyPrint (PDF), FastAPI, 前端框架 (React/Vue)
- **API**: OCI GenAI REST API (OpenAI 兼容格式), OCI Object Storage API
- **安全**: OCI IAM 签名认证, API Key 管理
