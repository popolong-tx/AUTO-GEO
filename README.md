# AUTO GEO 舆情分析系统

基于 OCI GenAI Grok 模型的汽车行业舆情监测与分析平台，支持实时数据采集、智能分析和多渠道通知推送。

## 功能特性

- **智能数据采集**：通过 LLM + 搜索工具获取 5 倍原始社交数据
- **深度分析**：根因分析、风险预警、行动建议
- **多数据源融合**：Object Storage 数据 + 用户上传文件 + 实时搜索
- **流式输出**：实时展示分析结果，带打字机效果
- **PDF 报告导出**：一键生成专业格式 PDF 报告
- **多渠道通知**：Webhook + 龙虾接口推送
- **提示词在线编辑**：支持修改、重置、版本回滚

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          前端 (React)                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ 首页     │  │ 话题页   │  │ 设置页   │  │ 登录页   │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP/SSE
┌────────────────────────────▼────────────────────────────────────────┐
│                        后端 (FastAPI)                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      API 路由层                              │   │
│  │  topics.py │ analysis.py │ reports.py │ settings.py │ auth  │   │
│  └─────────────────────────────┬───────────────────────────────┘   │
│                                │                                    │
│  ┌─────────────────────────────▼───────────────────────────────┐   │
│  │                      服务层                                  │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │   │
│  │  │ AnalysisEngine  │  │ DashboardService│  │ PDFGenerator│ │   │
│  │  │ (分析编排)      │  │ (数据提取)      │  │ (PDF生成)   │ │   │
│  │  └────────┬────────┘  └─────────────────┘  └─────────────┘ │   │
│  │           │                                                  │   │
│  │  ┌────────▼────────┐  ┌─────────────────┐  ┌─────────────┐ │   │
│  │  │RawDataCollector │  │ ReportGenerator │  │ Integration │ │   │
│  │  │ (数据采集)      │  │ (报告生成)      │  │ (通知推送)  │ │   │
│  │  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘ │   │
│  └───────────│────────────────────│──────────────────│────────┘   │
│              │                    │                  │              │
│  ┌───────────▼────────────────────▼──────────────────▼────────┐   │
│  │                      基础设施层                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │   │
│  │  │ GenAIClient │  │ ObjectStore │  │ AuthService         │ │   │
│  │  │ (LLM调用)   │  │ (存储操作)  │  │ (认证授权)          │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  OCI GenAI   │    │ OCI Object   │    │  外部系统    │
│  (Grok模型)  │    │ Storage      │    │  Webhook/龙虾│
└──────────────┘    └──────────────┘    └──────────────┘
```

## 分析流程

### 阶段一：数据获取

```
用户请求
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   RawDataCollector                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ 构建采集    │───▶│ 调用LLM     │───▶│ JSON解析    │ │
│  │ 提示词      │    │ x_search    │    │ 提取数据    │ │
│  │ (5倍数量)   │    │ web_search  │    │             │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                            │            │
│  ┌─────────────┐    ┌─────────────┐    ┌──▼──────────┐ │
│  │ 生成MD报告  │◀──│ 归一化处理  │◀──│ URL验证     │ │
│  │ 持久化存储  │    │ 国家/平台   │    │ 去重过滤    │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────┘
    │
    │ 输出: raw_data dict + markdown report
    ▼
```

**数据结构：**
```json
{
  "social_updates": [
    {"time": "...", "platform": "...", "account": "...", "summary": "...", "url": "...", "country": "..."}
  ],
  "country_coverage": [
    {"country": "...", "coverage": 0, "platforms": ["..."], "urls": ["..."]}
  ],
  "trend": [
    {"date": "YYYY-MM-DD", "mentions": 0, "reach": 0, "urls": ["..."]}
  ],
  "references": [
    {"title": "...", "source": "...", "url": "...", "summary": "..."}
  ],
  "collection_summary": {
    "requested_social_updates": 10,
    "raw_candidates_requested": 30,
    "verified_social_updates": 8,
    "shortfall_reason": "..."
  }
}
```

### 阶段二：数据分析

```
原始数据 + 上传文件
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   ReportGenerator                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ 构建分析    │───▶│ 调用LLM     │───▶│ 流式输出    │ │
│  │ 提示词      │    │ x_search    │    │ (前端实时)  │ │
│  │ (增强版)    │    │ web_search  │    │             │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                            │            │
│  ┌─────────────┐    ┌─────────────┐    ┌──▼──────────┐ │
│  │ 情绪解析    │◀──│ URL清洗     │◀──│ 后处理管道  │ │
│  │ 提取分数    │    │ 章节重排    │    │ (5步处理)   │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────┘
    │
    │ 输出: AnalysisResult (content + sentiment)
    ▼
```

**增强提示词要求：**
- 根因分析：识别事件根本原因、因果链条、潜在因素
- 风险预警：风险级别（高/中/低）、预警指标、影响时间线
- 行动建议：短期（24-48h）、中期（1-4周）、长期（1-6月）

**后处理管道：**
1. `_enforce_report_tail_sections()` - 强制尾部章节顺序
2. `_inject_verified_trend_section()` - 注入验证后的趋势数据
3. `_replace_country_section_with_verified()` - 替换国家覆盖数据
4. `_replace_social_section_with_verified()` - 替换社交媒体数据
5. `_sanitize_report_urls()` - 清洗无效URL

### 阶段三：通知推送

```
分析结果
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   IntegrationService                     │
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ Webhook     │    │ 龙虾接口    │    │ 风险预警    │ │
│  │ ───────────│    │ ───────────│    │ ───────────│ │
│  │ • 3次重试   │    │ • HMAC签名  │    │ • 高风险    │ │
│  │ • 指数退避  │    │ • Bearer认证│    │ • 单独推送  │ │
│  │ • 4xx不重试 │    │ • 超时30s   │    │ • 即时通知  │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                         │
│  通知负载:                                              │
│  {                                                      │
│    "event": "analysis_completed",                       │
│    "topic_id": "...",                                   │
│    "analysis_id": "...",                                │
│    "sentiment": {...},                                  │
│    "risk_level": "high|medium|low",                     │
│    "warnings": ["预警1", "预警2"],                      │
│    "content_preview": "..."                             │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
```

## 项目结构

```
BYDGEO/
├── backend/                        # Python 后端
│   ├── app/
│   │   ├── routers/               # API 路由
│   │   │   ├── topics.py          # 话题管理
│   │   │   ├── analysis.py        # 分析接口（含 SSE）
│   │   │   ├── reports.py         # 报告管理
│   │   │   ├── dashboard.py       # 仪表盘数据
│   │   │   ├── settings.py        # 系统设置
│   │   │   └── auth.py            # 认证授权
│   │   ├── services/              # 业务服务
│   │   │   ├── analysis_engine.py      # 分析引擎（编排）
│   │   │   ├── raw_data_collector.py   # 原始数据采集
│   │   │   ├── report_generator.py     # 报告生成
│   │   │   ├── integration_service.py  # 通知推送
│   │   │   ├── dashboard_service.py    # 仪表盘数据提取
│   │   │   ├── genai_client.py         # OCI GenAI 客户端
│   │   │   ├── object_storage.py       # Object Storage 操作
│   │   │   ├── pdf_generator.py        # PDF 生成
│   │   │   └── auth_service.py         # 认证服务
│   │   ├── models/                # 数据模型
│   │   │   └── topic.py           # Topic, AnalysisResult 等
│   │   └── utils/                 # 工具函数
│   │       ├── store.py           # 数据持久化
│   │       └── config.py          # 配置管理
│   ├── tests/                     # 单元测试
│   └── requirements.txt
├── frontend/                      # React 前端
│   ├── src/
│   │   ├── components/            # UI 组件
│   │   │   ├── MentionsReachTrendChart.tsx
│   │   │   ├── CountryCoverageChart.tsx
│   │   │   ├── SentimentChart.tsx
│   │   │   ├── StreamingContent.tsx
│   │   │   └── ...
│   │   ├── pages/                 # 页面
│   │   │   ├── HomePage.tsx
│   │   │   ├── TopicPage.tsx
│   │   │   └── ...
│   │   ├── constants/             # 共享常量
│   │   │   └── topicConfig.ts
│   │   ├── utils/                 # 工具函数
│   │   │   ├── urlValidator.ts
│   │   │   └── contentExtractors.ts
│   │   ├── services/              # API 调用
│   │   └── i18n/                  # 国际化
│   └── package.json
├── infra/                         # 部署脚本
│   ├── deploy-vm.sh              # VM 部署
│   ├── deploy-oci.sh             # OCI Functions 部署
│   └── nginx.conf                # Nginx 配置
├── docs/                          # 文档
└── .env.example                   # 环境变量模板
```

## 快速开始

### 1. 环境准备

```bash
# 安装 Python 依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
npm install
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际值：
# - OCI_GENAI_API_KEY: OCI GenAI API Key
# - OCI_OBJECT_STORAGE_NAMESPACE: Object Storage 命名空间
# - AUTOGEO_ADMIN_PASSWORD: 管理员密码（首次运行会自动哈希）
```

### 3. 本地开发

**后端：**
```bash
cd backend
source .venv/bin/activate  # 如果使用虚拟环境
python -m uvicorn app.main:app --reload --port 8000
```

**前端：**
```bash
cd frontend
npm run dev
```

访问 http://localhost:5173

### 4. 部署

**VM 部署（推荐）：**
```bash
chmod +x infra/deploy-vm.sh
sudo ./infra/deploy-vm.sh
```

**OCI Functions 部署：**
```bash
chmod +x infra/deploy-oci.sh
./infra/deploy-oci.sh
```

## API 接口

### 话题管理
- `GET /api/topics` - 获取话题列表
- `GET /api/topics/{id}` - 获取话题详情
- `PUT /api/topics/{id}/prompt` - 更新提示词
- `POST /api/topics/{id}/prompt/reset` - 重置提示词
- `GET /api/topics/{id}/prompt/history` - 提示词历史

### 分析
- `POST /api/analyze` - 执行分析（同步）
- `POST /api/analyze/stream` - 执行分析（SSE 流式）
- `GET /api/analyze/history/{topicId}` - 分析历史

### 报告
- `POST /api/reports/generate/{analysisId}` - 生成 PDF 报告
- `GET /api/reports/list/{topicId}` - 报告列表
- `GET /api/reports/download/{topicId}/{reportId}` - 下载报告

### 仪表盘
- `GET /api/dashboard/{topicId}` - 获取仪表盘数据
- `GET /api/dashboard/{topicId}/sources` - 获取数据源列表

### 系统
- `GET /health` - 健康检查
- `GET /api/models` - 可用模型列表
- `GET /api/settings` - 获取系统设置
- `PUT /api/settings` - 更新系统设置

### 认证
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出
- `GET /api/auth/me` - 获取当前用户

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+, FastAPI, OpenAI SDK |
| 前端 | React 18, TypeScript, Ant Design 5, ECharts |
| AI | OCI GenAI (Grok 4.20 Multi-Agent / Grok 4.3) |
| 存储 | OCI Object Storage, 本地 JSON 文件 |
| 部署 | VM (systemd) / OCI Functions (Serverless) |
| PDF | ReportLab |
| 通知 | Webhook (HTTP POST), 龙虾接口 |

## 配置说明

### OCI GenAI 端点

```
https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/v1
```

### 模型选择

| 模型 ID | 说明 |
|---------|------|
| xai.grok-4.20-multi-agent-0309 | 多智能体模型，适合复杂分析（默认） |
| xai.grok-4.3 | 通用模型，适合快速分析 |

### 通知配置

在 `data/integration_settings.json` 中配置：

```json
{
  "general_webhook_enabled": true,
  "general_webhook_url": "https://your-webhook-endpoint.com/notify",
  "general_webhook_secret": "your-secret",
  "lobster_url": "https://lobster-api.example.com/notify",
  "lobster_api_key": "your-api-key",
  "events": {
    "analysis_completed": true,
    "risk_warning": true,
    "error_alert": true
  },
  "targets": [
    {
      "name": "主通知",
      "enabled": true,
      "url": "https://target1.com/webhook",
      "secret": "secret1",
      "description": "主要通知目标"
    }
  ]
}
```

## 数据存储

### 目录结构

```
~/.autogeo_daily_snapshots/     # 每日分析快照
~/.autogeo_raw_data/            # 原始数据采集报告
backend/data/
├── dashboard.json              # 仪表盘数据
├── reports.json                # 报告历史
├── auth_config.json            # 认证配置
├── integration_settings.json   # 通知配置
└── report_snapshots/           # 报告快照
```

### 缓存策略

- **内存缓存**：`_daily_cache` 存储当日分析结果（24小时有效）
- **文件快照**：`~/.autogeo_daily_snapshots/` 持久化存储
- **原始数据**：`~/.autogeo_raw_data/` 保存采集的 MD 报告和 JSON 数据

## 许可证

内部演示使用，仅供舆情分析团队。
