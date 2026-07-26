"""
全球大类资产极端状态反转策略 — HTTP服务
提供固定URL访问最新生成的HTML仪表盘
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import OUTPUT_DIR

app = FastAPI(title="全球大类资产极端状态反转策略", version="1.0.0")


def get_latest_dashboard_path() -> Path:
    """获取最新生成的仪表盘文件路径"""
    today = datetime.now().strftime("%Y%m%d")
    today_path = OUTPUT_DIR / f"dashboard_{today}.html"
    if today_path.exists():
        return today_path
    
    # 如果今天还没生成，取最近的文件
    html_files = sorted(OUTPUT_DIR.glob("dashboard_*.html"), reverse=True)
    if html_files:
        return html_files[0]
    
    return None


def get_latest_report_path() -> Path:
    """获取最新日报路径"""
    today = datetime.now().strftime("%Y%m%d")
    today_path = OUTPUT_DIR / f"daily_report_{today}.md"
    if today_path.exists():
        return today_path
    
    md_files = sorted(OUTPUT_DIR.glob("daily_report_*.md"), reverse=True)
    if md_files:
        return md_files[0]
    
    return None


@app.get("/", response_class=HTMLResponse)
def index():
    """首页 — 显示最新仪表盘"""
    dashboard = get_latest_dashboard_path()
    if dashboard and dashboard.exists():
        with open(dashboard, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    else:
        return """
        <html>
        <head><title>全球大类资产极端状态反转策略</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                   background: #0f1117; color: #e0e0e0; 
                   display: flex; justify-content: center; align-items: center; 
                   height: 100vh; text-align: center; }
            .card { background: #1a1d2e; padding: 40px; border-radius: 12px; }
            h1 { color: #4CAF50; }
        </style>
        </head>
        <body>
            <div class="card">
                <h1>🌐 全球大类资产极端状态反转策略</h1>
                <p>今日仪表盘尚未生成</p>
                <p>请运行 <code>./run.sh</code> 生成后刷新页面</p>
                <p style="color: #8890a4; font-size: 12px;">每日收盘后15:30自动更新</p>
            </div>
        </body>
        </html>
        """


@app.get("/report")
def get_report():
    """获取最新日报 (Markdown)"""
    report = get_latest_report_path()
    if report and report.exists():
        with open(report, "r", encoding="utf-8") as f:
            content = f.read()
        return Response(content=content, media_type="text/markdown")
    return Response(content="日报尚未生成", media_type="text/plain")


@app.get("/health")
def health():
    """健康检查"""
    dashboard = get_latest_dashboard_path()
    return {
        "status": "ok",
        "latest_dashboard": str(dashboard.name) if dashboard else None,
        "dashboard_exists": dashboard is not None and dashboard.exists(),
        "generated_at": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"🚀 启动HTTP服务: http://{host}:{port}")
    print(f"📊 仪表盘: http://localhost:{port}/")
    print(f"📋 日报: http://localhost:{port}/report")
    uvicorn.run(app, host=host, port=port, log_level="info")
