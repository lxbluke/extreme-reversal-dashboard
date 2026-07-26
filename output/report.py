"""
Markdown日报生成器
"""

from datetime import datetime
from typing import Dict, List
from config.settings import SIGNAL_LEVELS, NORMAL_RANGES, PRIMARY_VALUATION


def _get_range_text(name: str, key: str = "pe") -> str:
    """获取正常区间文本"""
    r = NORMAL_RANGES.get(name, NORMAL_RANGES.get("default", {}))
    if key == "pe":
        vals = r.get("pe", [15, 35])
        return f"{vals[0]}~{vals[1]}x"
    elif key == "pb":
        vals = r.get("pb", [1.5, 5])
        return f"{vals[0]}~{vals[1]}x"
    return ""


def generate_daily_report(signals: List[Dict], market_data: Dict,
                          signal_summary: Dict, trading_suggestions: List[Dict] = None) -> str:
    """
    生成Markdown格式日报
    
    Args:
        signals: 信号列表（按|评分|降序）
        market_data: 市场环境数据
        signal_summary: 信号摘要统计
        trading_suggestions: 调仓建议
    
    Returns:
        str: Markdown日报内容
    """
    today = datetime.now().strftime("%Y年%m月%d日")
    now_time = datetime.now().strftime("%H:%M")
    
    lines = []
    lines.append(f"# 全球大类资产极端状态反转策略 — 日报")
    lines.append(f"**日期：{today}** | **生成时间：{now_time} CST**")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 一、市场环境速览
    lines.append("## 一、市场环境速览")
    lines.append("")
    lines.append("| 指标 | 数值 | 状态 |")
    lines.append("|------|------|------|")
    
    macro = market_data.get("macro", {})
    overview = market_data.get("market_overview", {})
    
    # ERP
    erp_data = macro.get("cn_premium_value", {})
    erp_value = erp_data.get("EquityPremium") or erp_data.get("value") or erp_data.get("erp", "N/A")
    try:
        erp_val_f = float(erp_value) if erp_value else None
    except (ValueError, TypeError):
        erp_val_f = None
    
    if erp_val_f is not None:
        erp_status = "偏高" if erp_val_f > 3.5 else ("偏低" if erp_val_f < 2.0 else "正常")
        erp_display = f"{erp_val_f:.2f}%"
    else:
        erp_status = "待采集"
        erp_display = str(erp_value)
    lines.append(f"| 股债性价比(ERP) | {erp_display} | {erp_status} |")
    
    # 涨跌比
    changedist = overview.get("changedist", {})
    up_count = changedist.get("up_count", "N/A")
    down_count = changedist.get("down_count", "N/A")
    up_ratio = changedist.get("up_ratio_pct") or changedist.get("up_ratio", 0)
    if isinstance(up_ratio, (int, float)):
        up_ratio_str = f"{up_ratio:.0f}%" if up_ratio > 1 else f"{up_ratio*100:.0f}%"
    else:
        up_ratio_str = "N/A"
    lines.append(f"| 涨跌比 | {up_count}/{down_count} | 上涨占比 {up_ratio_str} |")
    
    # 北向资金
    hsgt = overview.get("hsgt", {})
    north_flow = hsgt.get("net_flow", hsgt.get("north_net", "N/A"))
    lines.append(f"| 北向资金 | {north_flow} | - |")
    
    # 市场估值
    val_overview = overview.get("valuation", {})
    lines.append(f"| 市场估值 | - | 待采集 |")
    
    lines.append("")
    
    # 二、做多信号区
    long_signals = [s for s in signals if s.get("direction") == "long" and abs(s.get("composite_score", 0)) >= 0.25]
    lines.append("## 二、🟢 做多信号区")
    lines.append("")
    
    if long_signals:
        lines.append("| 资产 | 信号 | 评分 | PE(正常区间) | 近3月涨跌幅 | 交易标的 | 仓位 |")
        lines.append("|------|------|------|-------------|------------|---------|------|")
        for s in long_signals:
            level = s.get("signal_label", "N")
            score = s.get("composite_score", 0)
            pe_pct = f"{s.get('pe_percentile', 0)*100:.0f}%" if s.get("pe_percentile") else "N/A"
            pe_range = _get_range_text(s.get('asset_name', ''), 'pe')
            pe_display = f"{pe_pct} (正常{pe_range})"
            ret_3m = f"{s.get('return_3m', 0):.1f}%" if s.get("return_3m") else "N/A"
            # 提取ETF代码
            trade_tool = s.get("trade_tool", {})
            etf_code = trade_tool.get("code", "")
            etf_name = trade_tool.get("name", "")
            if etf_code:
                tool_display = f"{etf_code}"
            else:
                tool_display = "N/A"
            pos = f"{s.get('position_pct', 0)*100:.1f}%" if s.get("position_pct") else "N/A"
            lines.append(f"| {s['asset_name']} | {level} | {score:.2f} | {pe_display} | {ret_3m} | {tool_display} | {pos} |")
    else:
        lines.append("> 当前无做多信号")
    
    lines.append("")
    
    # 三、做空信号区
    short_signals = [s for s in signals if s.get("direction") == "short" and abs(s.get("composite_score", 0)) >= 0.25]
    lines.append("## 三、🔴 做空信号区")
    lines.append("")
    
    if short_signals:
        lines.append("| 资产 | 信号 | 评分 | PE(正常区间) | 近3月涨跌幅 | 交易标的 | 仓位 |")
        lines.append("|------|------|------|-------------|------------|---------|------|")
        for s in short_signals:
            level = s.get("signal_label", "N")
            score = s.get("composite_score", 0)
            pe_pct = f"{s.get('pe_percentile', 0)*100:.0f}%" if s.get("pe_percentile") else "N/A"
            pe_range = _get_range_text(s.get('asset_name', ''), 'pe')
            pe_display = f"{pe_pct} (正常{pe_range})"
            ret_3m = f"{s.get('return_3m', 0):.1f}%" if s.get("return_3m") else "N/A"
            trade_tool = s.get("trade_tool", {})
            tool_type = trade_tool.get("type", "")
            etf_code = trade_tool.get("code", "")
            etf_name = trade_tool.get("name", "")
            leverage = trade_tool.get("leverage")
            if etf_code:
                lev_str = f"{abs(leverage)}x " if leverage and leverage < 0 else ""
                tool_display = f"{lev_str}{etf_code}"
            else:
                tool_display = "买Put/反向ETF"
            pos = f"{s.get('position_pct', 0)*100:.1f}%" if s.get("position_pct") else "N/A"
            lines.append(f"| {s['asset_name']} | {level} | {score:.2f} | {pe_display} | {ret_3m} | {tool_display} | {pos} |")
    else:
        lines.append("> 当前无做空信号")
    
    lines.append("")
    
    # 四、观察区
    watch_signals = [s for s in signals if 0.25 <= abs(s.get("composite_score", 0)) < 0.5]
    lines.append("## 四、🟡 观察区")
    lines.append("")
    if watch_signals:
        lines.append("| 资产 | 方向 | 评分 | 确认条件 |")
        lines.append("|------|------|------|---------|")
        for s in watch_signals:
            dir_label = "偏多" if s.get("direction") == "long" else "偏空"
            confirmations = "；".join(s.get("confirmations", [])) or "待确认"
            lines.append(f"| {s['asset_name']} | {dir_label} | {s['composite_score']:.2f} | {confirmations} |")
    else:
        lines.append("> 当前无观察信号")
    
    lines.append("")
    
    # 五、调仓建议
    if trading_suggestions:
        lines.append("## 五、调仓建议")
        lines.append("")
        for ts in trading_suggestions:
            action = ts.get("action", "")
            asset = ts.get("asset", "")
            suggestion = ts.get("suggestion", "")
            lines.append(f"- **{action}**: {asset} — {suggestion}")
    
    lines.append("")
    
    # 六、风险提示
    lines.append("## 六、风险提示")
    lines.append("")
    lines.append("1. **做空风险极高**：建议使用ETF期权Put/反向ETF，控制单头寸在10-15%")
    lines.append("2. **极端状态可能持续**：极端估值不等于立即反转，需等催化剂确认拐点")
    lines.append("3. **数据时效**：部分指标为T-1数据，盘中可能有变化")
    lines.append("4. **本报告仅供参考**：不构成投资建议，请自行判断风险")
    lines.append("")
    
    # 信号统计
    lines.append("## 附录：信号统计")
    lines.append("")
    lines.append(f"- 总信号数：{signal_summary.get('total_signals', 0)}")
    lines.append(f"- 极端信号(|score|≥0.5)：{signal_summary.get('extreme_signals', 0)}")
    lines.append(f"- S+强做多：{signal_summary.get('s_plus_count', 0)} | S-强做空：{signal_summary.get('s_minus_count', 0)}")
    lines.append(f"- A+做多：{signal_summary.get('a_plus_count', 0)} | A-做空：{signal_summary.get('a_minus_count', 0)}")
    lines.append(f"- 做多信号：{signal_summary.get('long_count', 0)} | 做空信号：{signal_summary.get('short_count', 0)}")
    
    return "\n".join(lines)
