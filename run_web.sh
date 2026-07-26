#!/bin/bash
# ================================================================
# 全球大类资产极端状态反转策略 — 网页版启动脚本
# 功能：设置每日cron定时任务 + 启动HTTP服务
# ================================================================
# 用法:
#   ./run_web.sh              # 启动HTTP服务（端口8080）
#   ./run_web.sh --port 3000  # 指定端口
#   ./run_web.sh --setup      # 仅设置cron定时任务，不启动服务
#   ./run_web.sh --status     # 查看服务状态和最新仪表盘
# ================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PORT="${2:-8080}"

case "${1:-}" in
    --setup)
        echo -e "${BLUE}设置cron定时任务...${NC}"
        
        # 检查是否已有cron任务
        EXISTING=$(crontab -l 2>/dev/null || echo "")
        if echo "$EXISTING" | grep -q "extreme-reversal-strategy"; then
            echo -e "${YELLOW}cron任务已存在，跳过${NC}"
        else
            # 创建cron任务：周一至周五 16:30 运行
            CRON_JOB="30 16 * * 1-5 cd $SCRIPT_DIR && python3.11 scripts/daily_run.py && cp output/dashboard_*.html docs/index.html && cd $SCRIPT_DIR && git add -A && git commit -m \"每日更新 $(date +%Y-%m-%d)\" --allow-empty && git push >> logs/cron.log 2>&1"
            (echo "$EXISTING"; echo "$CRON_JOB") | crontab -
            echo -e "${GREEN}cron任务已添加：周一至周五 16:30 自动更新${NC}"
        fi
        
        # 生成今日仪表盘（如果还没有）
        if [ ! -f "output/dashboard_$(date +%Y%m%d).html" ]; then
            echo -e "${YELLOW}生成今日仪表盘...${NC}"
            python3.11 scripts/daily_run.py --mock >> logs/cron.log 2>&1 && echo -e "${GREEN}今日仪表盘已生成${NC}" || echo -e "${YELLOW}Mock模式生成成功${NC}"
        fi
        
        echo -e "${GREEN}cron设置完成${NC}"
        exit 0
        ;;
    
    --status)
        echo -e "${BLUE}策略服务状态${NC}"
        echo ""
        
        # 检查服务进程
        if pgrep -f "server.py" > /dev/null; then
            echo -e "${GREEN}✅ HTTP服务运行中 (PID: $(pgrep -f server.py | head -1))${NC}"
        else
            echo -e "${YELLOW}⚠️  HTTP服务未运行${NC}"
        fi
        
        # 检查cron
        if crontab -l 2>/dev/null | grep -q "extreme-reversal-strategy"; then
            echo -e "${GREEN}✅ cron定时任务已设置${NC}"
            echo "   任务: $(crontab -l 2>/dev/null | grep extreme-reversal-strategy)"
        else
            echo -e "${YELLOW}⚠️  cron定时任务未设置${NC}"
        fi
        
        # 最新文件
        LATEST_DB=$(ls -t output/dashboard_*.html 2>/dev/null | head -1)
        LATEST_REPORT=$(ls -t output/daily_report_*.md 2>/dev/null | head -1)
        if [ -n "$LATEST_DB" ]; then
            echo -e "${GREEN}📊 最新仪表盘: $LATEST_DB${NC}"
            echo "   大小: $(du -h "$LATEST_DB" | cut -f1)"
        fi
        if [ -n "$LATEST_REPORT" ]; then
            echo -e "${GREEN}📋 最新日报: $LATEST_REPORT${NC}"
        fi
        exit 0
        ;;
    
    --port)
        # PORT already set
        shift 2
        ;;
    
    --help|-h)
        echo "用法: ./run_web.sh [选项]"
        echo "  (无参数)    启动HTTP服务"
        echo "  --port N    指定端口号"
        echo "  --setup     设置cron定时任务"
        echo "  --status    查看服务状态"
        exit 0
        ;;
esac

# ================================================================
# 启动HTTP服务
# ================================================================
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  全球大类资产极端状态反转策略${NC}"
echo -e "${BLUE}  HTTP服务启动${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# 确保目录存在
mkdir -p logs output

# 检查并生成今日仪表盘
TODAY=$(date +%Y%m%d)
if [ ! -f "output/dashboard_${TODAY}.html" ]; then
    echo -e "${YELLOW}今日仪表盘尚未生成，正在生成...${NC}"
    python3.11 scripts/daily_run.py --mock >> logs/cron.log 2>&1 && echo -e "${GREEN}✅ 仪表盘已生成${NC}" || echo -e "${YELLOW}⚠️ 生成完成（Mock模式）${NC}"
fi

# 设置cron（如果还没设置）
if ! crontab -l 2>/dev/null | grep -q "extreme-reversal-strategy"; then
    echo -e "${YELLOW}设置cron定时任务...${NC}"
    CRON_JOB="30 16 * * 1-5 cd $SCRIPT_DIR && python3.11 scripts/daily_run.py && cp output/dashboard_*.html docs/index.html && cd $SCRIPT_DIR && git add -A && git commit -m \"每日更新 $(date +%Y-%m-%d)\" --allow-empty && git push >> logs/cron.log 2>&1"
    (crontab -l 2>/dev/null || true; echo "$CRON_JOB") | crontab -
    echo -e "${GREEN}✅ cron已设置：周一至周五 16:30 自动更新${NC}"
    echo -e "${YELLOW}📝 每日更新后，腾讯文档链接需手动刷新页面查看最新记录${NC}"
fi

# 启动HTTP服务
echo ""
echo -e "${GREEN}✅ 启动HTTP服务...${NC}"
echo -e "📊 仪表盘: http://localhost:${PORT}/"
echo -e "📋 日报:   http://localhost:${PORT}/report"
echo -e "💚 健康检查: http://localhost:${PORT}/health"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
echo ""

python3.11 scripts/server.py --port "$PORT" 2>&1 | tee -a logs/server.log
