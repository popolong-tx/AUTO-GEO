## Context

比亚迪需要一个舆情监测分析演示系统，部署在 OCI 上，利用 Grok 大模型进行多话题深度分析。系统需要仿照 Meltwater 融文舆情监测系统的界面风格，支持 4 个预设话题的分析和 PDF 报告导出。

当前状态：无已有系统，需从零构建。OCI GenAI 推理端点已就绪（OpenAI 兼容格式），Object Storage 可用。

## Goals / Non-Goals

**Goals:**
- 构建可部署在 OCI Functions 上的无服务器舆情分析应用
- 集成 OCI GenAI Grok 模型进行智能分析
- 提供仿 Meltwater 风格的专业 Web 仪表盘
- 支持 4 个话题页面，提示词可在线编辑
- 支持从 Object Storage 读取数据 + Grok 搜索联合分析
- 生成 PDF 报告并存储至 Object Storage

**Non-Goals:**
- 不实现实时数据采集爬虫（使用已有数据 + Grok 搜索）
- 不实现用户认证系统（Demo 性质）
- 不支持自定义话题创建（仅 4 个预设话题）
- 不实现多租户隔离

## Decisions

### 1. 后端架构：OCI Functions (Python)

**选择**: 使用 OCI Functions 部署 Python 后端服务

**理由**:
- 符合无服务器要求，按需计费
- OCI Functions 原生支持 Python 3.11
- 可直接使用 OCI SDK 访问 Object Storage 和 GenAI

**替代方案**:
- OCI Container Instances：需要管理容器生命周期
- Compute VM：需要运维，不符合无服务器要求

### 2. 前端架构：单页应用 (React + Ant Design)

**选择**: React + Ant Design Pro 构建前端，部署为静态网站（Object Storage + CDN）

**理由**:
- Ant Design Pro 提供丰富的企业级组件，适合仿 Meltwater 仪表盘风格
- 静态部署成本低，与 OCI CDN 集成良好
- React 生态成熟，图表库（ECharts/Recharts）丰富

**替代方案**:
- Vue + Element Plus：同样可行，但 Ant Design Pro 的仪表盘模板更接近 Meltwater 风格
- 服务端渲染（Next.js）：增加复杂度，Demo 不需要 SEO

### 3. AI 调用方式：OpenAI SDK 兼容格式

**选择**: 使用 OpenAI Python SDK，配置 OCI GenAI 端点作为 base_url

**理由**:
- OCI GenAI 推理端点兼容 OpenAI API 格式
- 代码简洁，可直接使用 `responses.create()` 接口
- 支持流式响应，提升用户体验

### 4. PDF 生成：ReportLab

**选择**: 使用 ReportLab 生成 PDF 报告

**理由**:
- 纯 Python 实现，无系统依赖，适合 Functions 环境
- 支持中文排版（需配置中文字体）
- 轻量级，Functions 冷启动快

**替代方案**:
- WeasyPrint：依赖系统库（Cairo/Pango），Functions 环境部署复杂
- wkhtmltopdf：需要二进制文件，不适合轻量 Functions

### 5. 数据流架构

```
前端 (React) → API Gateway → OCI Functions (Python)
                                   ↓
                              OCI GenAI (Grok)
                                   ↓
                         Object Storage (数据+报告)
```

- 前端通过 API Gateway 调用 Functions
- Functions 调用 Grok 模型进行分析
- 分析结果生成 PDF 存入 Object Storage
- 前端通过预签名 URL 下载报告

## Risks / Trade-offs

- **[Grok 模型响应时间]** → 使用流式响应改善用户体验；设置合理超时（120s）
- **[Functions 冷启动延迟]** → 预留并发实例；前端显示加载状态
- **[中文 PDF 排版]** → 需要在 Functions 层打包中文字体文件；测试多种字体兼容性
- **[OCI GenAI 区域限制]** → 确认 us-chicago-1 区域端点可用性；备选其他区域端点
- **[提示词长度限制]** → 在线编辑器设置字符计数和上限提示
