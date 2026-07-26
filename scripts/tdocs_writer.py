"""
腾讯文档写入工具
每日仪表盘生成后，自动将链接和信号摘要写入腾讯文档
"""

import base64
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 腾讯文档配置
TDOC_FILE_ID = "GTjZswtehqLI"  # 固定文档ID，每日追加


def update_tdocs(signals: List[Dict], signal_summary: Dict,
                 dashboard_path: str = "", dashboard_url: str = "") -> bool:
    """
    更新腾讯文档：追加一行日报记录
    
    Args:
        signals: 信号列表
        signal_summary: 信号摘要
        dashboard_path: 本地文件路径
        dashboard_url: 公网访问URL（如GitHub Pages链接）
    
    Returns:
        bool: 是否成功
    """
    from mcp__tdocs_app__doc import resolve_document_structure, insert_markdown
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 1. 获取文档结构，找到末尾位置
    try:
        structure = resolve_document_structure(file_id=TDOC_FILE_ID)
        last_idx = structure.get("last_index", 89)
    except Exception as e:
        logger.error(f"获取文档结构失败: {e}")
        last_idx = 89
    
    # 2. 构建信号摘要文本
    s_plus = signal_summary.get("s_plus_count", 0)
    s_minus = signal_summary.get("s_minus_count", 0)
    a_plus = signal_summary.get("a_plus_count", 0)
    a_minus = signal_summary.get("a_minus_count", 0)
    
    summary_parts = []
    if s_minus > 0:
        summary_parts.append(f"S-{s_minus}")
    if a_minus > 0:
        summary_parts.append(f"A-{a_minus}")
    if a_plus > 0:
        summary_parts.append(f"A+{a_plus}")
    if s_plus > 0:
        summary_parts.append(f"S+{s_plus}")
    
    summary_text = " ".join(summary_parts) if summary_parts else "中性"
    
    # 3. 构建链接和内容
    if dashboard_url:
        link_text = f"[📊 {today}日报]({dashboard_url})"
    else:
        link_text = f"📊 {today}日报(本地: {dashboard_path})"
    
    # Markdown格式：新一行 | 日期 | 链接 | 摘要 |
    md_content = f"| {today} | {link_text} | {summary_text} |\n"
    
    # 4. 插入文档末尾
    try:
        md_b64 = base64.b64encode(md_content.encode("utf-8")).decode("utf-8")
        result = insert_markdown(
            file_id=TDOC_FILE_ID,
            idx=last_idx,
            base64_markdown=md_b64,
        )
        logger.info(f"腾讯文档已更新: {today} | {summary_text}")
        return True
    except Exception as e:
        logger.error(f"写入腾讯文档失败: {e}")
        return False
