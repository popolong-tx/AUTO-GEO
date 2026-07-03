#!/bin/bash
#==============================================================================
# BYD GEO Demo - 部署入口脚本
#==============================================================================
# 根据环境自动选择部署方式:
#   ./deploy.sh          → 自动检测
#   ./deploy.sh vm       → 单机 VM 部署
#   ./deploy.sh oci      → OCI Functions 部署
#==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  BYD GEO 舆情分析系统 - 部署工具${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  用法:"
echo -e "    ${BLUE}./deploy.sh vm${NC}     → 单机 VM 部署 (Ubuntu/CentOS/macOS)"
echo -e "    ${BLUE}./deploy.sh oci${NC}    → OCI Functions 无服务器部署"
echo -e "    ${BLUE}./deploy.sh${NC}        → 自动检测环境并选择部署方式"
echo ""

MODE="${1:-auto}"

# 自动检测模式
if [ "$MODE" = "auto" ]; then
    # 检查是否在 OCI 环境
    if curl -s --connect-timeout 2 http://169.254.169.254/opc/v2/instance/ &>/dev/null; then
        echo -e "${GREEN}[INFO]${NC} 检测到 OCI 实例环境"
        MODE="oci"
    # 检查是否有 fn CLI
    elif command -v fn &>/dev/null && command -v docker &>/dev/null; then
        echo -e "${GREEN}[INFO]${NC} 检测到 fn + Docker，可部署到 OCI Functions"
        echo -e "${YELLOW}[提示]${NC} 是否部署到 OCI Functions? (y/N)"
        read -r answer
        if [[ "$answer" =~ ^[Yy]$ ]]; then
            MODE="oci"
        else
            MODE="vm"
        fi
    else
        echo -e "${GREEN}[INFO]${NC} 使用单机 VM 部署模式"
        MODE="vm"
    fi
fi

case "$MODE" in
    vm)
        echo -e "\n${GREEN}[INFO]${NC} 启动单机 VM 部署...\n"
        chmod +x "$SCRIPT_DIR/deploy-vm.sh"
        bash "$SCRIPT_DIR/deploy-vm.sh"
        ;;
    oci)
        echo -e "\n${GREEN}[INFO]${NC} 启动 OCI Functions 部署...\n"
        chmod +x "$SCRIPT_DIR/deploy-oci.sh"
        bash "$SCRIPT_DIR/deploy-oci.sh"
        ;;
    *)
        echo -e "${RED}[ERROR]${NC} 未知模式: $MODE"
        echo "用法: $0 [vm|oci]"
        exit 1
        ;;
esac
