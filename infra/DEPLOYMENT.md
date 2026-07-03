# BYD GEO 舆情分析系统 - 部署指南

## 部署方式

### 方式一：单机 VM 部署（推荐）

适用于 Ubuntu、CentOS、Oracle Linux、macOS 等环境。

```bash
# 1. 配置环境变量
cp .env.example .env
vi .env  # 填写 OCI_GENAI_API_KEY 等配置

# 2. 一键部署
chmod +x infra/deploy-vm.sh
sudo ./infra/deploy-vm.sh
```

**服务管理：**
```bash
# Linux (systemd)
sudo systemctl start byd-geo
sudo systemctl status byd-geo
sudo journalctl -u byd-geo -f

# macOS (launchctl)
launchctl load ~/Library/LaunchAgents/com.byd.geo.plist
launchctl unload ~/Library/LaunchAgents/com.byd.geo.plist
```

**手动启动（开发模式）：**
```bash
cd backend && source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000

cd frontend && npm start  # 开发服务器
```

### 方式二：OCI Functions 无服务器部署

适用于 Oracle Cloud Infrastructure 环境。

```bash
# 1. 前置条件
#    - OCI CLI 已安装并配置
#    - fn CLI 已安装
#    - Docker 已运行

# 2. 配置环境变量
export OCI_GENAI_API_KEY=your-api-key
export OCI_OBJECT_STORAGE_NAMESPACE=your-namespace
export OCI_COMPARTMENT_ID=your-compartment-id
export OCI_SUBNET_ID=your-subnet-id

# 3. 一键部署
chmod +x infra/deploy-oci.sh
./infra/deploy-oci.sh
```

## 环境变量

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `OCI_GENAI_API_KEY` | OCI GenAI API Key | - | 是 |
| `OCI_GENAI_ENDPOINT` | GenAI 推理端点 | `https://inference.gener...` | 否 |
| `OCI_GENAI_MODEL` | 默认模型 | `xai.grok-4.20-multi-agent-0309` | 否 |
| `OCI_OBJECT_STORAGE_NAMESPACE` | Object Storage 命名空间 | - | VM部署可选 |
| `OCI_OBJECT_STORAGE_BUCKET` | 报告存储桶 | `byd-geo-reports` | 否 |
| `APP_PORT` | 后端端口 | `8000` | 否 |
| `FRONTEND_PORT` | 前端端口 | `3000` | 否 |

## 目录结构

```
byd-geo-demo/
├── backend/                  # Python 后端
│   ├── app/                 # 应用代码
│   ├── tests/               # 单元测试
│   ├── func.yaml            # OCI Functions 配置
│   ├── func.py              # OCI Functions 入口
│   └── requirements.txt     # Python 依赖
├── frontend/                # React 前端
│   ├── src/                 # 源代码
│   └── build/               # 构建产物
├── infra/                   # 部署脚本
│   ├── deploy.sh            # 统一入口
│   ├── deploy-vm.sh         # VM 部署脚本
│   ├── deploy-oci.sh        # OCI 部署脚本
│   └── nginx.conf           # nginx 配置模板
├── .env.example             # 环境变量模板
└── README.md                # 项目说明
```

## 故障排查

### 后端启动失败
```bash
# 检查日志
journalctl -u byd-geo -n 50  # Linux
tail -50 /tmp/byd-geo-error.log  # macOS

# 手动测试
cd backend && source .venv/bin/activate
python -c "from app.main import app; print('OK')"
```

### 前端构建失败
```bash
cd frontend
rm -rf node_modules
npm install
npm run build
```

### PDF 导出失败
- 检查 `OCI_GENAI_API_KEY` 是否配置
- 未配置时使用 Demo 模式（返回模拟数据）
- 查看后端错误日志

### nginx 502 Bad Gateway
```bash
# 检查后端是否运行
curl http://localhost:8000/health

# 检查 nginx 配置
nginx -t
systemctl reload nginx
```
