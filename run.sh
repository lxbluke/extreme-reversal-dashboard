#!/bin/bash
# ================================================================
# 全球大类资产极端状态反转策略 — 一键运行脚本
# ================================================================
# 用法:
#   ./run.sh              # 完整模式（所有资产类别）
#   ./run.sh --quick      # 快速模式（仅A股+宏观）
#   ./run.sh --mock       # Mock模式（使用模拟数据测试）
#   ./run.sh --install    # 安装依赖
# ================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  全球大类资产极端状态反转策略${NC}"
echo -e "${BLUE}  Extreme Reversal Strategy for Global Asset Classes${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# 检查Python版本
PYTHON_CMD="python3.11"
if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD="python3"
    if ! command -v $PYTHON_CMD &> /dev/null; then
        echo -e "${RED}错误: 未找到Python 3${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}Python: $($PYTHON_CMD --version)${NC}"

# 创建必要目录
mkdir -p logs data_cache output

# 参数处理
MODE="${1:-}"

if [ "$MODE" = "--install" ]; then
    echo -e "${YELLOW}安装依赖...${NC}"
    $PYTHON_CMD -m pip install -q numpy pandas 2>/dev/null || true
    echo -e "${GREEN}依赖安装完成${NC}"
    exit 0
fi

# 运行策略
echo -e "${YELLOW}开始运行策略...${NC}"
echo ""

if [ "$MODE" = "--mock" ]; then
    echo -e "${BLUE}模式: Mock (模拟数据测试)${NC}"
    $PYTHON_CMD scripts/daily_run.py --mock
elif [ "$MODE" = "--quick" ]; then
    echo -e "${BLUE}模式: 快速 (仅A股+宏观)${NC}"
    $PYTHON_CMD scripts/daily_run.py --quick
else
    echo -e "${BLUE}模式: 完整 (所有资产类别)${NC}"
    $PYTHON_CMD scripts/daily_run.py
fi

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}  运行成功!${NC}"
    echo -e "${GREEN}============================================================${NC}"
    
    # 显示最新输出文件
    LATEST_DASHBOARD=$(ls -t output/dashboard_*.html 2>/dev/null | head -1)
    LATEST_REPORT=$(ls -t output/daily_report_*.md 2>/dev/null | head -1)
    
    if [ -n "$LATEST_DASHBOARD" ]; then
        echo -e "📊 仪表盘: ${GREEN}$LATEST_DASHBOARD${NC}"
    fi
    if [ -n "$LATEST_REPORT" ]; then
        echo -e "📋 日报: ${GREEN}$LATEST_REPORT${NC}"
    fi
else
    echo -e "${RED}============================================================${NC}"
    echo -e "${RED}  运行失败 (exit code: $EXIT_CODE)${NC}"
    echo -e "${RED}============================================================${NC}"
    echo "请查看日志: logs/daily_run.log"
fi

exit $EXIT_CODE
