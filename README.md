# 汽车行业 GEO 舆情分析系统

基于 OCI GenAI Grok 模型的汽车行业舆情监测与分析平台，可以部署在 Oracle Cloud Infrastructure (OCI) Functions 以及虚拟机上。

## 功能特性

- **4 大话题分析**：闪充发布会、Q1财报、智驾芯片发布会、1260h清单事件
- **Grok 模型驱动**：支持 xai.grok-4.20-multi-agent-0309 和 xai.grok-4.3
- **多数据源融合**：Object Storage 预存数据 + Grok 实时搜索
- **流式输出**：实时展示分析结果，带打字机效果
- **PDF 报告导出**：一键生成专业格式 PDF 报告
- **提示词在线编辑**：支持修改、重置、版本回滚
- **Meltwater 风格界面**：深蓝/深灰专业仪表盘风格

## 项目结构

```
byd-geo-demo/
├── backend/                    # Python 后端
│   ├── app/
│   │   ├── routers/           # API 路由
│   │   │   ├── topics.py      # 话题管理
│   │   │   ├── analysis.py    # 分析接口（含 SSE）
│   │   │   └── reports.py     # 报告管理
│   │   ├── services/          # 业务服务
│   │   │   ├── genai_client.py    # OCI GenAI 客户端
│   │   │   ├── object_storage.py  # Object Storage 操作
│   │   │   ├── analysis_engine.py # 分析引擎
│   │   │   └── pdf_generator.py   # PDF 生成
│   │   ├── models/            # 数据模型
│   │   └── utils/             # 工具函数
│   ├── tests/                 # 单元测试
│   ├── func.py                # OCI Functions 入口
│   ├── func.yaml              # Functions 配置
│   └── requirements.txt
├── frontend/                  # React 前端
│   ├── src/
│   │   ├── components/        # UI 组件
│   │   ├── pages/             # 页面
│   │   ├── services/          # API 调用
│   │   └── styles/            # 样式主题
│   └── package.json
├── infra/
│   └── deploy.sh              # OCI 部署脚本
└── .env.example               # 环境变量模板
```

## 快速开始

### 1. 环境准备

```bash
# 安装 OCI CLI
bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"

# 安装 fn CLI
curl -LSs https://raw.githubusercontent.com/fnproject/cli/master/install | sh

# 配置 OCI
oci setup config
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际值：
# - OCI_GENAI_API_KEY: OCI GenAI API Key
# - OCI_OBJECT_STORAGE_NAMESPACE: Object Storage 命名空间
# - OCI_OBJECT_STORAGE_BUCKET: 报告存储桶名称
```

### 3. 本地开发

**后端：**
```bash
cd backend
pip install -r requirements.txt
export OCI_GENAI_API_KEY=your-key
python -m uvicorn app.main:app --reload --port 8000
```

**前端：**
```bash
cd frontend
npm install
npm start
```

访问 http://localhost:3000

### 4. 部署到 OCI Functions

```bash
# 设置环境变量
export OCI_GENAI_API_KEY=your-key
export OCI_OBJECT_STORAGE_NAMESPACE=your-namespace

# 执行部署
chmod +x infra/deploy.sh
./infra/deploy.sh
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
- `DELETE /api/reports/{objectName}` - 删除报告

### 系统
- `GET /health` - 健康检查
- `GET /api/models` - 可用模型列表

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11, FastAPI, OpenAI SDK |
| 前端 | React 18, Ant Design 5, ECharts |
| AI | OCI GenAI (Grok 4.20/4.3) |
| 存储 | OCI Object Storage |
| 部署 | OCI Functions (Serverless) |
| PDF | ReportLab |

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

## 许可证

内部演示使用，仅供  舆情分析团队。
