#!/bin/bash
#==============================================================================
# BYD GEO Demo - OCI Functions 部署脚本
#==============================================================================
# 前置条件:
#   1. OCI CLI 已安装并配置 (oci setup config)
#   2. fn CLI 已安装 (curl -LSs https://raw.githubusercontent.com/fnproject/cli/master/install | sh)
#   3. Docker 已安装并运行
#   4. 已设置环境变量 (见下方 .env 配置)
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

# ─── 配置 ──────────────────────────────────────────────────────────────────
APP_NAME="${OCI_APP_NAME:-byd-geo-app}"
FUNC_NAME="${OCI_FUNC_NAME:-byd-geo-demo}"
NAMESPACE="${OCI_OBJECT_STORAGE_NAMESPACE:-}"
BUCKET="${OCI_OBJECT_STORAGE_BUCKET:-byd-geo-reports}"
DATA_BUCKET="${OCI_OBJECT_STORAGE_DATA_BUCKET:-byd-geo-data}"
COMPARTMENT_ID="${OCI_COMPARTMENT_ID:-}"
SUBNET_ID="${OCI_SUBNET_ID:-}"
GENAI_ENDPOINT="${OCI_GENAI_ENDPOINT:-https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/v1}"
GENAI_MODEL="${OCI_GENAI_MODEL:-xai.grok-4.20-multi-agent-0309}"

# ─── 前置检查 ──────────────────────────────────────────────────────────────
step "Step 0: 环境检查"

check_cmd() {
    command -v "$1" &>/dev/null || error "$1 未安装。$2"
}

check_cmd "oci"     "安装: https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm"
check_cmd "fn"      "安装: curl -LSs https://raw.githubusercontent.com/fnproject/cli/master/install | sh"
check_cmd "docker"  "安装: https://docs.docker.com/get-docker/"

# 检查 OCI 认证
if ! oci iam user list --limit 1 &>/dev/null 2>&1; then
    error "OCI CLI 未认证。请运行: oci setup config"
fi
log "OCI CLI 认证正常"

# 检查必要环境变量
[ -z "${OCI_GENAI_API_KEY:-}" ] && error "请设置 OCI_GENAI_API_KEY 环境变量"
[ -z "$NAMESPACE" ]  && error "请设置 OCI_OBJECT_STORAGE_NAMESPACE 环境变量"
[ -z "$COMPARTMENT_ID" ] && warn "OCI_COMPARTMENT_ID 未设置，将跳过自动创建资源"

# ─── Step 1: 创建 OCI 资源 ────────────────────────────────────────────────
step "Step 1: 创建 OCI 资源"

# 获取 Compartment ID (如果未指定)
if [ -z "$COMPARTMENT_ID" ]; then
    COMPARTMENT_ID=$(oci iam compartment list --query 'data[0]."compartment-id"' --raw-output 2>/dev/null || echo "")
    if [ -z "$COMPARTMENT_ID" ]; then
        error "无法获取 Compartment ID，请设置 OCI_COMPARTMENT_ID"
    fi
    log "使用 Compartment: $COMPARTMENT_ID"
fi

# 创建 Object Storage 桶 (如果不存在)
create_bucket() {
    local bucket_name=$1
    if ! oci os bucket get --bucket-name "$bucket_name" &>/dev/null 2>&1; then
        log "创建 Object Storage 桶: $bucket_name"
        oci os bucket create \
            --name "$bucket_name" \
            --compartment-id "$COMPARTMENT_ID" \
            --access-type ObjectRead 2>/dev/null || warn "桶 $bucket_name 创建失败（可能已存在）"
    else
        log "桶 $bucket_name 已存在"
    fi
}

create_bucket "$BUCKET"
create_bucket "$DATA_BUCKET"

# 创建 VCN 和子网 (如果未指定 Subnet)
if [ -z "$SUBNET_ID" ] && [ -n "$COMPARTMENT_ID" ]; then
    log "创建 VCN..."
    VCN_ID=$(oci network vcn create \
        --compartment-id "$COMPARTMENT_ID" \
        --cidr-blocks '["10.0.0.0/16"]' \
        --display-name "byd-geo-vcn" \
        --query 'data.id' --raw-output 2>/dev/null || echo "")

    if [ -n "$VCN_ID" ]; then
        log "VCN 已创建: $VCN_ID"

        # 创建子网
        SUBNET_ID=$(oci network subnet create \
            --compartment-id "$COMPARTMENT_ID" \
            --vcn-id "$VCN_ID" \
            --cidr-block "10.0.0.0/24" \
            --display-name "byd-geo-subnet" \
            --query 'data.id' --raw-output 2>/dev/null || echo "")

        if [ -n "$SUBNET_ID" ]; then
            log "子网已创建: $SUBNET_ID"
        else
            error "子网创建失败"
        fi
    else
        warn "VCN 创建失败，请手动创建子网并设置 OCI_SUBNET_ID"
    fi
fi

# ─── Step 2: 部署 OCI Functions ──────────────────────────────────────────
step "Step 2: 部署 OCI Functions"

cd "$PROJECT_DIR/backend"

# 创建应用
log "创建/更新 Functions 应用: $APP_NAME"
if [ -n "$SUBNET_ID" ]; then
    fn create app "$APP_NAME" \
        --annotation oracle.com/oci/subnetIds="[\"$SUBNET_ID\"]" \
        2>/dev/null || log "应用 $APP_NAME 已存在"
else
    fn create app "$APP_NAME" 2>/dev/null || log "应用 $APP_NAME 已存在"
fi

# 配置应用环境变量
log "配置应用环境变量..."
fn config app "$APP_NAME" OCI_GENAI_ENDPOINT "$GENAI_ENDPOINT"
fn config app "$APP_NAME" OCI_GENAI_API_KEY "$OCI_GENAI_API_KEY"
fn config app "$APP_NAME" OCI_GENAI_MODEL "$GENAI_MODEL"
fn config app "$APP_NAME" OCI_OBJECT_STORAGE_NAMESPACE "$NAMESPACE"
fn config app "$APP_NAME" OCI_OBJECT_STORAGE_BUCKET "$BUCKET"
fn config app "$APP_NAME" OCI_OBJECT_STORAGE_DATA_BUCKET "$DATA_BUCKET"

# 部署 Function
log "部署 Function: $FUNC_NAME"
fn -v deploy --app "$APP_NAME" --no-bump

# 获取 Function URL
FUNC_URL=$(fn inspect fn "$APP_NAME" "$FUNC_NAME" 2>/dev/null | grep -o '"url":"[^"]*"' | cut -d'"' -f4 || echo "")

# ─── Step 3: 部署前端 ─────────────────────────────────────────────────────
step "Step 3: 部署前端到 Object Storage"

cd "$PROJECT_DIR/frontend"

log "构建前端..."
npm install --legacy-peer-deps 2>/dev/null
npm run build

log "上传前端文件到 Object Storage..."
FRONTEND_BUCKET="${OCI_FRONTEND_BUCKET:-byd-geo-frontend}"
create_bucket "$FRONTEND_BUCKET"

oci os object bulk-upload \
    --bucket-name "$FRONTEND_BUCKET" \
    --dir build \
    --region "$OCI_REGION" \
    --auth api_key 2>/dev/null || warn "前端上传失败，请手动上传 build/ 目录到 $FRONTEND_BUCKET"

# 启用静态网站
oci os bucket update \
    --name "$FRONTEND_BUCKET" \
    --public-access-type ObjectRead \
    --versioning Disabled 2>/dev/null || warn "无法设置公开访问"

# ─── 完成 ──────────────────────────────────────────────────────────────────
step "部署完成!"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  BYD GEO 舆情分析系统 - OCI 部署完成${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Function URL: ${BLUE}${FUNC_URL:-请检查 OCI Console}${NC}"
echo -e "  前端 URL:     ${BLUE}https://$FRONTEND_BUCKET.compat.objectstorage.$OCI_REGION.oraclecloud.com/${NC}"
echo -e "  报告存储桶:   ${BLUE}$BUCKET${NC}"
echo -e "  数据存储桶:   ${BLUE}$DATA_BUCKET${NC}"
echo ""
echo -e "  测试: curl -X POST ${FUNC_URL:-<FUNC_URL>} -H 'Content-Type: application/json' -d '{\"method\":\"GET\",\"path\":\"/health\"}'"
echo ""
