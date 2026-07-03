## ADDED Requirements

### Requirement: Grok 模型调用
系统 SHALL 通过 OCI GenAI 推理端点调用 Grok 模型，使用 OpenAI 兼容的 API 格式。系统 MUST 支持以下模型：
- `xai.grok-4.20-multi-agent-0309`
- `xai.grok-4.3`

#### Scenario: 默认模型调用
- **WHEN** 用户发起话题分析请求且未指定模型
- **THEN** 系统使用 `xai.grok-4.20-multi-agent-0309` 作为默认模型调用 OCI GenAI 端点

#### Scenario: 指定模型调用
- **WHEN** 用户在界面上选择 `xai.grok-4.3` 模型并发起分析
- **THEN** 系统使用指定的 `xai.grok-4.3` 模型进行调用

#### Scenario: 模型调用失败
- **WHEN** OCI GenAI 端点返回错误或超时
- **THEN** 系统返回清晰的错误信息，并建议用户重试或切换模型

### Requirement: 流式响应支持
系统 SHALL 支持从 Grok 模型获取流式响应，逐步展示分析结果。

#### Scenario: 流式输出
- **WHEN** 用户发起分析请求
- **THEN** 系统通过 SSE (Server-Sent Events) 逐步返回分析文本，前端实时渲染

#### Scenario: 流式中断处理
- **WHEN** 流式响应在中途断开
- **THEN** 系统保留已接收的内容，并提示用户可基于已有内容继续或重新分析

### Requirement: OCI 认证配置
系统 SHALL 使用 OCI IAM 签名认证访问 GenAI 端点。API Key 等敏感配置 MUST 通过环境变量注入，不得硬编码。

#### Scenario: 正常认证
- **WHEN** Functions 部署并配置了正确的 OCI 凭证
- **THEN** 系统成功通过认证并调用 GenAI API

#### Scenario: 认证失败
- **WHEN** OCI 凭证无效或过期
- **THEN** 系统返回 401 错误并提示管理员检查配置

### Requirement: Object Storage 数据读取
系统 SHALL 支持从 OCI Object Storage 读取预存的分析数据文件（JSON/CSV），作为分析输入的一部分。

#### Scenario: 读取数据文件
- **WHEN** 分析请求指定 Object Storage 中的数据文件路径
- **THEN** 系统读取文件内容并与提示词合并，作为模型输入

#### Scenario: 文件不存在
- **WHEN** 指定的 Object Storage 路径不存在
- **THEN** 系统跳过外部数据，仅使用提示词和 Grok 搜索结果进行分析，并在报告中标注数据来源
