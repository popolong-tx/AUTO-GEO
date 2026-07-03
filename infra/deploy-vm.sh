#!/bin/bash
#==============================================================================
# BYD GEO Demo - 单机 VM 部署脚本
#==============================================================================
# 支持: Ubuntu 22.04/24.04, Oracle Linux 8/9, CentOS 7/8, macOS
#
# 用法:
#   chmod +x deploy-vm.sh
#   sudo ./deploy-vm.sh
#
# 配置:
#   复制 .env.example 为 .env 并填写配置
#==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()   { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
step()  { echo -e "\n${BLUE}━━━ $* ━━━${NC}"; }

node_major_version() {
    if ! command -v node >/dev/null 2>&1; then
        echo 0
        return
    fi
    node -v | sed 's/^v//' | cut -d. -f1
}

ensure_node20_deb() {
    local major
    major="$(node_major_version)"
    if [ "$major" -ge 20 ] 2>/dev/null && command -v npm >/dev/null 2>&1; then
        log "Node.js 版本满足要求: $(node -v), npm: $(npm -v)"
        return
    fi

    warn "Node.js/npm 版本过旧或不完整，切换到 NodeSource Node 20"
    # Ubuntu 自带 nodejs/npm 版本经常过旧，且 npm/libnode-dev 与 NodeSource nodejs 会冲突。
    apt-get remove -y -qq nodejs npm libnode-dev nodejs-doc 2>/dev/null || true
    apt-get autoremove -y -qq 2>/dev/null || true
    apt-get update -qq
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs
    log "Node.js 已安装: $(node -v), npm: $(npm -v)"
}

# ─── 配置 ──────────────────────────────────────────────────────────────────
SERVICE_NAME="${SERVICE_NAME:-byd-geo}"
APP_PORT="${APP_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
VENV_DIR="$PROJECT_DIR/backend/.venv"

# ─── 检测操作系统 ────────────────────────────────────────────────────────
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
log "检测到操作系统: $OS"

# ─── Step 1: 安装系统依赖 ────────────────────────────────────────────────
step "Step 1: 安装系统依赖"

install_system_deps() {
    case "$OS" in
        ubuntu|debian)
            export DEBIAN_FRONTEND=noninteractive
            apt-get update -qq || true
            apt-get -f install -y -qq || true
            apt-get install -y -qq python3 python3-venv python3-pip curl wget build-essential
            ensure_node20_deb
            ;;
        centos|rhel|ol|rocky|alma)
            yum install -y python3 python3-pip nodejs npm curl wget gcc gcc-c++ make
            ;;
        amzn|amazonlinux)
            yum install -y python3 python3-pip nodejs npm curl wget gcc gcc-c++ make
            ;;
        fedora)
            dnf install -y python3 python3-pip nodejs npm curl wget gcc gcc-c++ make
            ;;
        macos)
            if ! command -v brew &>/dev/null; then
                log "安装 Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install python@${PYTHON_VERSION} node npm
            ;;
        *)
            warn "未知操作系统: $OS，尝试继续..."
            ;;
    esac
}

install_system_deps
log "系统依赖安装完成"

# ─── Step 2: 创建 Python 虚拟环境 ────────────────────────────────────────
step "Step 2: 创建 Python 虚拟环境"

cd "$PROJECT_DIR/backend"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    log "虚拟环境已创建: $VENV_DIR"
else
    log "虚拟环境已存在"
fi

source "$VENV_DIR/bin/activate"

log "安装 Python 依赖..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install gunicorn -q
log "Python 依赖安装完成"

# ─── Step 3: 构建前端 ────────────────────────────────────────────────────
step "Step 3: 构建前端"

cd "$PROJECT_DIR/frontend"

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    log "安装前端依赖..."
    npm install 2>/dev/null
fi

# npm 偶发丢失 rollup 的 optional dependency，先强制补装一次再 build
npm install --include=optional 2>/dev/null || true

log "构建前端..."
npm run build
log "前端构建完成"

# ─── Step 4: 配置环境变量 ────────────────────────────────────────────────
step "Step 4: 配置环境变量"

ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"

if [ ! -f "$ENV_FILE" ] && [ -f "$ENV_EXAMPLE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    log "已创建 .env 文件，请编辑填写配置"
    log "  vi $ENV_FILE"
fi

# 加载 .env
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
    log "环境变量已加载"
fi

# ─── Step 5: 创建 systemd 服务 (Linux) ────────────────────────────────────
step "Step 5: 创建系统服务"

create_systemd_service() {
    local SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

    cat > "$SERVICE_FILE" << 'SERVICEEOF'
[Unit]
Description=BYD GEO 舆情分析系统
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=WORKDIR_PLACEHOLDER
Environment="PATH=VENV_PLACEHOLDER/bin:/usr/local/bin:/usr/bin"
EnvironmentFile=ENV_PLACEHOLDER
ExecStart=VENV_PLACEHOLDER/bin/gunicorn app.main:app \
    --host 0.0.0.0 \
    --port APP_PORT_PLACEHOLDER \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 300 \
    --access-logfile /var/log/byd-geo/access.log \
    --error-logfile /var/log/byd-geo/error.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF

    # 替换占位符
    sed -i "s|WORKDIR_PLACEHOLDER|$PROJECT_DIR/backend|g" "$SERVICE_FILE"
    sed -i "s|VENV_PLACEHOLDER|$VENV_DIR|g" "$SERVICE_FILE"
    sed -i "s|ENV_PLACEHOLDER|$ENV_FILE|g" "$SERVICE_FILE"
    sed -i "s|APP_PORT_PLACEHOLDER|$APP_PORT|g" "$SERVICE_FILE"

    log "systemd 服务已创建: $SERVICE_FILE"
}

create_launchd_service() {
    local PLIST_FILE="$HOME/Library/LaunchAgents/com.byd.geo.plist"

    mkdir -p "$HOME/Library/LaunchAgents"

    cat > "$PLIST_FILE" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.byd.geo</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/gunicorn</string>
        <string>app.main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>$APP_PORT</string>
        <string>--workers</string>
        <string>2</string>
        <string>--worker-class</string>
        <string>uvicorn.workers.UvicornWorker</string>
        <string>--timeout</string>
        <string>300</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR/backend</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$VENV_DIR/bin:/usr/local/bin:/usr/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/byd-geo-access.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/byd-geo-error.log</string>
</dict>
</plist>
PLISTEOF

    log "launchd 服务已创建: $PLIST_FILE"
}

case "$OS" in
    ubuntu|debian|centos|rhel|ol|rocky|alma|amzn|fedora)
        mkdir -p /var/log/byd-geo
        create_systemd_service

        systemctl daemon-reload
        systemctl enable "$SERVICE_NAME"
        systemctl restart "$SERVICE_NAME"
        log "服务已启动: systemctl status $SERVICE_NAME"
        ;;
    macos)
        create_launchd_service
        launchctl unload "$HOME/Library/LaunchAgents/com.byd.geo.plist" 2>/dev/null || true
        launchctl load "$HOME/Library/LaunchAgents/com.byd.geo.plist"
        log "服务已启动: launchctl list | grep byd"
        ;;
    *)
        warn "未知操作系统，跳过服务创建"
        ;;
esac

# ─── Step 6: 配置前端反向代理 ────────────────────────────────────────────
step "Step 6: 配置前端服务"

# 创建前端 serve 脚本
cat > "$PROJECT_DIR/frontend/serve.sh" << 'SERVEEOF'
#!/bin/bash
# BYD GEO 前端静态文件服务
cd "$(dirname "$0")/build"

# 使用 Python 内置 HTTP 服务器 (简单)
# 或者使用 nginx (生产环境推荐)
if command -v nginx &>/dev/null; then
    echo "使用 nginx 服务前端..."
    # nginx 配置由下面的 nginx.conf 处理
else
    echo "使用 Python HTTP 服务器..."
    python3 -m http.server "$FRONTEND_PORT" --bind 0.0.0.0
fi
SERVEEOF
chmod +x "$PROJECT_DIR/frontend/serve.sh"

# 创建 nginx 配置
cat > "$PROJECT_DIR/infra/nginx.conf" << 'NGINXEOF'
server {
    listen 80;
    server_name _;

    # 前端静态文件
    location / {
        root FRONTEND_DIR_PLACEHOLDER;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:APP_PORT_PLACEHOLDER;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # SSE 流式响应
    location /api/analyze/stream {
        proxy_pass http://127.0.0.1:APP_PORT_PLACEHOLDER;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        chunked_transfer_encoding off;
    }

    # PDF 下载
    location /api/reports/ {
        proxy_pass http://127.0.0.1:APP_PORT_PLACEHOLDER;
        proxy_set_header Host $host;
        proxy_buffering off;
    }
}
NGINXEOF

python3 - <<PY
from pathlib import Path
p = Path("$PROJECT_DIR/infra/nginx.conf")
text = p.read_text()
text = text.replace("FRONTEND_DIR_PLACEHOLDER", "$PROJECT_DIR/frontend/build")
text = text.replace("APP_PORT_PLACEHOLDER", "$APP_PORT")
p.write_text(text)
PY

# 尝试安装并配置 nginx
if command -v nginx &>/dev/null; then
    cp "$PROJECT_DIR/infra/nginx.conf" /etc/nginx/sites-available/byd-geo.conf
    ln -sf /etc/nginx/sites-available/byd-geo.conf /etc/nginx/sites-enabled/byd-geo.conf
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx
    log "nginx 配置完成"
else
    warn "nginx 未安装，前端将使用独立端口运行"
    warn "安装 nginx: apt install nginx / yum install nginx / brew install nginx"
    warn "配置: cp $PROJECT_DIR/infra/nginx.conf /etc/nginx/sites-available/byd-geo"
fi

# ─── Step 7: 防火墙配置 ────────────────────────────────────────────────
step "Step 7: 配置防火墙"

configure_firewall() {
    case "$OS" in
        ubuntu|debian)
            if command -v ufw &>/dev/null; then
                ufw allow 80/tcp   2>/dev/null || true
                ufw allow 443/tcp  2>/dev/null || true
                ufw allow "$APP_PORT"/tcp 2>/dev/null || true
                ufw allow "$FRONTEND_PORT"/tcp 2>/dev/null || true
                log "防火墙规则已添加 (ufw)"
            fi
            ;;
        centos|rhel|ol|rocky|alma|amzn|fedora)
            if command -v firewall-cmd &>/dev/null; then
                firewall-cmd --permanent --add-port=80/tcp 2>/dev/null || true
                firewall-cmd --permanent --add-port=443/tcp 2>/dev/null || true
                firewall-cmd --permanent --add-port="$APP_PORT"/tcp 2>/dev/null || true
                firewall-cmd --permanent --add-port="$FRONTEND_PORT"/tcp 2>/dev/null || true
                firewall-cmd --reload 2>/dev/null || true
                log "防火墙规则已添加 (firewalld)"
            fi
            ;;
    esac
}

configure_firewall || warn "防火墙配置跳过"

# ─── 完成 ──────────────────────────────────────────────────────────────────
step "部署完成!"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  BYD GEO 舆情分析系统 - VM 部署完成${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  后端 API:  ${BLUE}http://localhost:$APP_PORT${NC}"
echo -e "  前端页面:  ${BLUE}http://localhost:$FRONTEND_PORT${NC} (独立模式)"
echo -e "  前端页面:  ${BLUE}http://localhost${NC} (nginx 模式)"
echo ""
echo -e "  服务管理:"
if [[ "$OS" == "macos" ]]; then
    echo -e "    启动: ${YELLOW}launchctl load ~/Library/LaunchAgents/com.byd.geo.plist${NC}"
    echo -e "    停止: ${YELLOW}launchctl unload ~/Library/LaunchAgents/com.byd.geo.plist${NC}"
    echo -e "    日志: ${YELLOW}tail -f /tmp/byd-geo-error.log${NC}"
else
    echo -e "    启动: ${YELLOW}systemctl start $SERVICE_NAME${NC}"
    echo -e "    停止: ${YELLOW}systemctl stop $SERVICE_NAME${NC}"
    echo -e "    状态: ${YELLOW}systemctl status $SERVICE_NAME${NC}"
    echo -e "    日志: ${YELLOW}journalctl -u $SERVICE_NAME -f${NC}"
fi
echo ""
echo -e "  测试: curl http://localhost:$APP_PORT/health"
echo ""
echo -e "  配置: ${YELLOW}vi $PROJECT_DIR/.env${NC}"
echo ""
