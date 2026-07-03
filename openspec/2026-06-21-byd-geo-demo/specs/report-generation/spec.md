## ADDED Requirements

### Requirement: PDF 报告生成
系统 SHALL 将分析结果生成格式化的 PDF 报告，包含完整分析内容、图表和结论。

#### Scenario: 生成 PDF
- **WHEN** 用户在分析结果页面点击"导出 PDF"
- **THEN** 系统生成包含以下内容的 PDF 文件：报告标题、话题名称、分析时间、执行摘要、各维度详细分析、情绪分布图表、关键发现、风险预警、建议措施

#### Scenario: PDF 中文支持
- **WHEN** 生成 PDF 报告
- **THEN** 报告中的中文内容 MUST 正确显示，无乱码

### Requirement: 报告存储至 Object Storage
系统 SHALL 将生成的 PDF 报告自动上传至 OCI Object Storage 指定桶中。

#### Scenario: 自动上传
- **WHEN** PDF 报告生成完成
- **THEN** 系统将文件上传至 Object Storage，路径格式为 `reports/{topic_id}/{timestamp}.pdf`

#### Scenario: 存储成功确认
- **WHEN** 上传成功
- **THEN** 系统返回文件的访问 URL（预签名 URL，有效期 24 小时）

### Requirement: 历史报告管理
系统 SHALL 保存所有生成的报告记录，支持查看和下载。

#### Scenario: 报告列表
- **WHEN** 用户在话题页面查看报告历史
- **THEN** 系统展示该话题的所有历史报告（时间、摘要、下载链接）

#### Scenario: 下载报告
- **WHEN** 用户点击某报告的下载按钮
- **THEN** 系统通过预签名 URL 提供 PDF 文件下载

#### Scenario: 删除报告
- **WHEN** 用户选择删除某报告
- **THEN** 系统删除 Object Storage 中的文件并移除列表记录

### Requirement: 报告模板定制
系统 SHALL 提供报告模板，包含标准的排版和品牌元素。

#### Scenario: 报告封面
- **WHEN** 生成 PDF 报告
- **THEN** 报告第一页为封面，包含：比亚迪 Logo 占位、报告标题、话题名称、生成日期、机密标识

#### Scenario: 目录页
- **WHEN** PDF 报告超过 5 页
- **THEN** 报告包含自动生成的目录页
