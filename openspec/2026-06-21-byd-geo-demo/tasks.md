## 1. 项目初始化与基础设施

- [x] 1.1 创建项目目录结构（backend/、frontend/、infra/）
- [x] 1.2 编写 OCI Functions func.yaml 配置文件
- [x] 1.3 编写 requirements.txt（openai、reportlab、fastapi、uvicorn、oci-sdk）
- [x] 1.4 配置 OCI 部署脚本（fn deploy 命令封装）
- [x] 1.5 创建 .env.example 模板文件（OCI 端点、API Key、Object Storage 桶名）

## 2. OCI GenAI 集成模块

- [x] 2.1 实现 OCI GenAI 客户端封装（基于 OpenAI SDK，支持 base_url 配置）
- [x] 2.2 实现模型选择逻辑（grok-4.20-multi-agent-0309 / grok-4.3）
- [x] 2.3 实现流式响应处理（SSE 推送）
- [x] 2.4 实现 OCI Object Storage 数据读取功能
- [x] 2.5 实现数据源融合逻辑（Object Storage 数据 + 提示词合并）

## 3. 舆情分析引擎

- [x] 3.1 实现分析请求处理流程（接收话题ID+提示词+数据源配置）
- [x] 3.2 实现结构化分析结果解析（摘要、维度分析、情绪评分、发现、风险、建议）
- [x] 3.3 实现情绪量化计算逻辑
- [x] 3.4 实现超时控制（120秒）与部分结果返回
- [x] 3.5 实现分析结果持久化（存储至 Object Storage）

## 4. 话题管理模块

- [x] 4.1 实现 4 个预设话题的数据模型与初始数据
- [x] 4.2 实现话题 CRUD API（列表、详情、更新）
- [x] 4.3 实现提示词在线编辑 API（保存、重置、历史记录）
- [x] 4.4 实现提示词版本管理（修改历史、回滚）
- [x] 4.5 实现数据源路径配置与验证 API

## 5. PDF 报告生成模块

- [x] 5.1 实现 ReportLab PDF 生成基础模板（封面、页眉页脚、目录）
- [x] 5.2 实现中文字体打包与配置
- [x] 5.3 实现分析结果到 PDF 内容的映射渲染
- [x] 5.4 实现情绪分布图表生成（饼图/柱状图）
- [x] 5.5 实现 PDF 上传至 Object Storage 并生成预签名 URL
- [x] 5.6 实现报告列表查询与删除 API

## 6. FastAPI 后端服务

- [x] 6.1 搭建 FastAPI 应用骨架（路由、中间件、异常处理）
- [x] 6.2 实现话题相关 API 路由（/api/topics）
- [x] 6.3 实现分析相关 API 路由（/api/analyze，含 SSE 流式端点）
- [x] 6.4 实现报告相关 API 路由（/api/reports）
- [x] 6.5 实现提示词管理 API 路由（/api/prompts）
- [x] 6.6 编写 OCI Functions 入口函数（func.py）

## 7. 前端应用开发

- [x] 7.1 初始化 React + Ant Design Pro 项目
- [x] 7.2 实现全局布局（顶部导航、左侧菜单、内容区）仿 Meltwater 风格
- [x] 7.3 实现首页话题卡片网格展示
- [x] 7.4 实现话题分析页面（操作区 + 结果展示区）
- [x] 7.5 实现模型选择器组件
- [x] 7.6 实现提示词编辑器组件（模态框 + 保存/重置/历史）
- [x] 7.7 实现流式文本展示组件（打字机效果）
- [x] 7.8 实现情绪分布图表组件（ECharts/Recharts）
- [x] 7.9 实现报告列表与下载组件
- [x] 7.10 实现加载状态、错误处理、空状态展示
- [x] 7.11 实现响应式布局适配（桌面端 + 平板端）

## 8. 集成测试与部署

- [x] 8.1 编写后端单元测试（GenAI 客户端、分析引擎、PDF 生成）
- [x] 8.2 编写 API 集成测试
- [x] 8.3 前端构建优化与打包
- [x] 8.4 编写 OCI Functions 部署文档
- [x] 8.5 编写 README 使用说明
- [x] 8.6 端到端验证（分析 → PDF 生成 → 下载完整流程）
