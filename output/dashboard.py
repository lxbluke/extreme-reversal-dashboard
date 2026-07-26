"""
HTML交互式仪表盘生成器
使用Chart.js实现雷达图和信号卡片
"""

import json
from datetime import datetime
from typing import Dict, List
from pathlib import Path
from config.settings import SIGNAL_LEVELS, OUTPUT_DIR, NORMAL_RANGES, ERP_RANGE, RSI_RANGE, PRIMARY_VALUATION


def _score_to_radar(score: float) -> float:
    """将[-1,1]评分转为[0,100]的雷达图值"""
    return abs(score) * 100


def _get_normal_range(asset_name: str) -> Dict:
    """获取资产的正常估值区间"""
    for key in [asset_name, "default"]:
        if key in NORMAL_RANGES:
            return NORMAL_RANGES[key]
    return NORMAL_RANGES["default"]


def _format_flow(val) -> str:
    """格式化资金流数据（单位：亿）"""
    if val is None:
        return "N/A"
    try:
        v = float(val) / 1e8  # 转换为亿
        return f"{v:+.1f}亿"
    except (ValueError, TypeError):
        return str(val)


def _erp_status(erp_val) -> dict:
    """判断ERP状态，返回状态+解读"""
    default = {"status": "N/A", "interpret": "数据不足", "style": "", "advice": ""}
    if erp_val is None:
        return default
    try:
        v = float(erp_val)
        if v < ERP_RANGE["extreme_low"]:
            return {
                "status": "🔴 极度高估",
                "interpret": f"ERP {v:.1f}% < {ERP_RANGE['extreme_low']}%",
                "style": "color:#F44336",
                "advice": "股票极贵，建议减仓 → 增配债券"
            }
        elif v < ERP_RANGE["overvalued"]:
            return {
                "status": "⚠️ 偏高估",
                "interpret": f"ERP {v:.1f}% (股债性价比弱)",
                "style": "color:#FF9800",
                "advice": "股票偏贵，可适当降低股票仓位"
            }
        elif v < ERP_RANGE["normal_min"]:
            return {
                "status": "🟡 偏中性（略高）",
                "interpret": f"ERP {v:.1f}%（接近正常下限）",
                "style": "color:#FFC107",
                "advice": "股票略贵，观望为主"
            }
        elif v <= ERP_RANGE["normal_max"]:
            return {
                "status": "🟢 正常",
                "interpret": f"ERP {v:.1f}%（股债中性合理）",
                "style": "color:#4CAF50",
                "advice": "股票性价比中性，按策略执行"
            }
        elif v <= ERP_RANGE["undervalued"]:
            return {
                "status": "🟢 偏低估",
                "interpret": f"ERP {v:.1f}%（股票有吸引力）",
                "style": "color:#2E7D32",
                "advice": "股票偏便宜，可加仓"
            }
        elif v < ERP_RANGE["extreme_high"]:
            return {
                "status": "🟢 明显低估",
                "interpret": f"ERP {v:.1f}%（股票性价比高）",
                "style": "color:#1B5E20",
                "advice": "股票便宜，建议加仓股票"
            }
        else:
            return {
                "status": "🟢 极度低估",
                "interpret": f"ERP {v:.1f}% > {ERP_RANGE['undervalued']}%",
                "style": "color:#006400",
                "advice": "历史级低估区域，大力买入股票"
            }
    except (ValueError, TypeError):
        return default


def generate_dashboard(signals: List[Dict], market_data: Dict,
                       signal_summary: Dict, trading_suggestions: List[Dict] = None,
                       sector_fund_ranking: Dict = None) -> str:
    """
    生成完整的HTML仪表盘

    Args:
        signals: 信号列表
        market_data: 市场环境数据
        signal_summary: 信号摘要
        trading_suggestions: 调仓建议

    Returns:
        str: HTML内容
    """
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")

    # 分类信号
    long_signals = [s for s in signals if s.get("direction") == "long" and abs(s.get("composite_score", 0)) >= 0.25]
    short_signals = [s for s in signals if s.get("direction") == "short" and abs(s.get("composite_score", 0)) >= 0.25]
    watch_signals = [s for s in signals if 0.25 <= abs(s.get("composite_score", 0)) < 0.5]
    extreme_signals = [s for s in signals if abs(s.get("composite_score", 0)) >= 0.5]

    # 构建卡片HTML
    def build_signal_card(s: Dict) -> str:
        level = s.get("signal_level", "NEUTRAL")
        label = s.get("signal_label", "N")
        color = s.get("color", "#808080")
        score = s.get("composite_score", 0)
        v_score = s.get("valuation_score", 0)
        m_score = s.get("momentum_score", 0)
        s_score_val = s.get("sentiment_score", 0)
        n_score = s.get("narrative_score", 0)

        # 估值分位显示
        pe_pct = f"{s.get('pe_percentile', 0)*100:.0f}%" if s.get("pe_percentile") is not None else "N/A"
        pb_pct = f"{s.get('pb_percentile', 0)*100:.0f}%" if s.get("pb_percentile") is not None else "N/A"
        ret_3m = f"{s.get('return_3m', 0):+.1f}%" if s.get('return_3m') is not None else "N/A"
        rsi_val = s.get('rsi_14', None)
        rsi = f"{rsi_val:.0f}" if rsi_val is not None else "N/A"

        # PE正常区间
        asset_name = s.get('asset_name', '')
        normal = _get_normal_range(asset_name)
        pe_range = normal.get("pe", [15, 35])
        pb_range = normal.get("pb", [1.5, 5])
        pe_range_str = f"{pe_range[0]}~{pe_range[1]}x"
        pb_range_str = f"{pb_range[0]}~{pb_range[1]}x"

        # PE实际值（如有）
        pe_actual = s.get("details", {}).get("valuation_detail", {}).get("pe_ttm")
        pe_actual_str = f"{pe_actual:.1f}x" if pe_actual else pe_pct

        # RSI状态
        rsi_status = ""
        if rsi_val is not None:
            if rsi_val >= RSI_RANGE["overbought"]:
                rsi_status = "⚠️超买"
            elif rsi_val <= RSI_RANGE["oversold"]:
                rsi_status = "🟢超卖"
            else:
                rsi_status = "正常"

        # 资金流向数据
        fund_flow = s.get("details", {}).get("valuation_detail", {}).get("fund_flow", {})
        if not fund_flow and s.get("trade_tool"):
            fund_flow = s.get("trade_tool", {})
        main_flow_5d = s.get("details", {}).get("valuation_detail", {}).get("fund_flow_5d")

        confirmations = "<br>".join(s.get("confirmations", [])) or "无"
        suggestion = s.get("trade_suggestion", "")
        pos_pct = f"{s.get('position_pct', 0)*100:.1f}%" if s.get("position_pct") else "N/A"

        # 方向图标
        icon = "🟢" if s.get("direction") == "long" else ("🔴" if s.get("direction") == "short" else "⚪")

        # 提取ETF标的信息
        trade_tool = s.get("trade_tool", {})
        tool_code = trade_tool.get("code", "")
        tool_type = trade_tool.get("type", "")
        tool_name = trade_tool.get("name", "")
        alt_code = trade_tool.get("alt_code", "")
        leverage = trade_tool.get("leverage")

        etf_display = ""
        if tool_code:
            if "反向ETF" in tool_type or leverage and leverage < 0:
                lev_str = f"{abs(leverage)}x" if leverage else ""
                etf_display = f'<div class="etf-line"><span class="etf-label">📉 做空工具</span><span class="etf-code-short">{tool_code}</span><span class="etf-name">{tool_name}</span></div>'
            elif tool_type == "ETF期权Put":
                etf_display = f'<div class="etf-line"><span class="etf-label">📉 做空工具</span><span class="etf-code-short">买Put {tool_code}</span><span class="etf-name">{tool_name}</span></div>'
            elif tool_type == "ETF融券":
                etf_display = f'<div class="etf-line"><span class="etf-label">📉 做空工具</span><span class="etf-code-short">融券 {tool_code}</span><span class="etf-name">{tool_name}</span></div>'
            else:
                etf_display = f'<div class="etf-line"><span class="etf-label">📗 做多工具</span><span class="etf-code-long">{tool_code}</span><span class="etf-name">{tool_name}</span></div>'
            if alt_code:
                etf_display += f'<div class="etf-line" style="margin-top:2px"><span class="etf-label">备选</span><span class="etf-code-alt">{alt_code}</span></div>'

        return f'''
        <div class="signal-card" style="border-left: 6px solid {color}; background: linear-gradient(135deg, {color}15 0%, {color}05 100%);">
            <div class="card-header">
                <span class="signal-icon">{icon}</span>
                <span class="signal-level" style="color: {color}">{label}</span>
                <span class="signal-score">{score:+.2f}</span>
            </div>
            <h3>{s.get('asset_name', 'Unknown')}</h3>
            <div class="card-body">
                <div class="score-row">
                    <span class="score-item">估值 <b>{v_score:+.2f}</b></span>
                    <span class="score-item">动量 <b>{m_score:+.2f}</b></span>
                    <span class="score-item">情绪 <b>{s_score_val:+.2f}</b></span>
                    <span class="score-item">叙事 <b>{n_score:+.2f}</b></span>
                </div>
                {etf_display}
                <div class="data-grid">
                    <div><span class="label">PE</span><span class="value">{pe_actual_str} <span class="normal-range">(正常{pe_range_str})</span></span></div>
                    <div><span class="label">PB分位</span><span class="value">{pb_pct} <span class="normal-range">(正常{pb_range_str})</span></span></div>
                    <div><span class="label">近3月涨跌幅</span><span class="value">{ret_3m}</span></div>
                    <div><span class="label">RSI(14)</span><span class="value">{rsi} <span class="rsi-status">{rsi_status}</span></span></div>
                </div>
                <div class="suggestion">{suggestion}</div>
                <div class="position" style="font-size:13px">建议仓位: <b>{pos_pct}</b></div>
                <details class="detail-panel">
                    <summary>📋 详细数据</summary>
                    <div class="detail-content">
                        <div class="detail-row"><span>四维评分</span><span>估值{v_score:+.2f} | 动量{m_score:+.2f} | 情绪{s_score_val:+.2f} | 叙事{n_score:+.2f}</span></div>
                        <div class="detail-row"><span>PE分位</span><span>{pe_pct}（正常区间 {pe_range_str}）</span></div>
                        <div class="detail-row"><span>近1月涨跌幅</span><span>{s.get('return_1m', 0):+.1f}%</span></div>
                        <div class="detail-row"><span>确认条件</span><span>{confirmations}</span></div>
                    </div>
                </details>
            </div>
        </div>'''

    # ============================================================
    # 紧凑列表行渲染（新布局，取代卡片）
    # ============================================================
    def build_signal_row(s: Dict, direction: str = "long") -> str:
        """生成紧凑的信号列表行"""
        level = s.get("signal_level", "NEUTRAL")
        label = s.get("signal_label", "N")
        color = s.get("color", "#808080")
        score = s.get("composite_score", 0)
        v_score = s.get("valuation_score", 0)
        m_score = s.get("momentum_score", 0)
        s_score_val = s.get("sentiment_score", 0)
        n_score = s.get("narrative_score", 0)

        asset_name = s.get('asset_name', '')
        asset_class = s.get('asset_class', '')

        # 获取该行业/资产的主估值指标
        primary_key = PRIMARY_VALUATION.get(asset_name) or PRIMARY_VALUATION.get(asset_class, "pe")

        # 根据主估值指标提取对应的分位数和实际值
        if primary_key == "pb":
            val_pct = f"{s.get('pb_percentile', 0)*100:.0f}%" if s.get("pb_percentile") is not None else "N/A"
            val_actual = s.get("details", {}).get("valuation_detail", {}).get("pb")
            val_label = "PB"
        elif primary_key == "ps":
            val_pct = f"{s.get('ps_percentile', 0)*100:.0f}%" if s.get("ps_percentile") is not None else "N/A"
            val_actual = s.get("details", {}).get("valuation_detail", {}).get("ps_ttm")
            val_label = "PS"
        elif primary_key == "dividend_yield":
            val_pct = f"{s.get('pe_percentile', 0)*100:.0f}%" if s.get("pe_percentile") is not None else "N/A"
            val_actual = s.get("details", {}).get("valuation_detail", {}).get("dividend_yield")
            val_label = "DY"
        else:  # pe default
            val_pct = f"{s.get('pe_percentile', 0)*100:.0f}%" if s.get("pe_percentile") is not None else "N/A"
            val_actual = s.get("details", {}).get("valuation_detail", {}).get("pe_ttm")
            val_label = "PE"

        # 同时保留PE分位用于详情面板
        pe_pct = f"{s.get('pe_percentile', 0)*100:.0f}%" if s.get("pe_percentile") is not None else "N/A"
        pb_pct = f"{s.get('pb_percentile', 0)*100:.0f}%" if s.get("pb_percentile") is not None else "N/A"
        ret_3m = f"{s.get('return_3m', 0):+.1f}%" if s.get('return_3m') is not None else "N/A"
        rsi_val = s.get('rsi_14', None)
        confirmations = "<br>".join(s.get("confirmations", [])) or "无"
        suggestion = s.get("trade_suggestion", "")
        pos_pct = f"{s.get('position_pct', 0)*100:.1f}%" if s.get("position_pct") else "N/A"

        normal = _get_normal_range(asset_name)
        val_range = normal.get(primary_key, [15, 35]) if primary_key in normal else normal.get("pe", [15, 35])
        val_range_str = f"{val_range[0]}~{val_range[1]}x" if primary_key != "dividend_yield" else f"{val_range[0]}~{val_range[1]}%"
        val_display = f"{val_actual:.1f}" if val_actual else val_pct
        if primary_key != "dividend_yield":
            val_display += "x" if val_actual else ""
        else:
            val_display += "%" if val_actual else ""

        trade_tool = s.get("trade_tool", {})
        tool_code = trade_tool.get("code", "")
        leverage = trade_tool.get("leverage")
        tool_display = ""
        if tool_code:
            if "反向ETF" in trade_tool.get("type", "") or (leverage and leverage < 0):
                tool_display = f'{abs(leverage)}x ' if leverage else ''
                tool_display += tool_code
            elif trade_tool.get("type") == "ETF期权Put":
                tool_display = f"买Put {tool_code}"
            elif trade_tool.get("type") == "ETF融券":
                tool_display = f"融券 {tool_code}"
            else:
                tool_display = tool_code
        else:
            tool_display = "—"

        # 方向图标 + 颜色
        icon = "🟢" if direction == "long" else ("🔴" if direction == "short" else "⚪")

        return f'''
        <div class="signal-row" onclick="var d=this.querySelector('.row-detail');if(d)d.classList.toggle('active')" style="border-left:4px solid {color}">
            <div class="row-main">
                <span class="row-icon">{icon}</span>
                <span class="row-level" style="color:{color}">{label}</span>
                <span class="row-name">{asset_name}</span>
                <span class="row-score" style="color:{color}">{score:+.2f}</span>
                <span class="row-pe">{val_display} <span class="row-range">({val_range_str})</span></span>
                <span class="row-ret">{ret_3m}</span>
                <span class="row-tool">{tool_display}</span>
                <span class="row-pos">{pos_pct}</span>
            </div>
            <div class="row-detail">
                <div class="row-detail-inner">
                    <div class="rd-col"><b>四维评分</b> 估值{v_score:+.2f} | 动量{m_score:+.2f} | 情绪{s_score_val:+.2f} | 叙事{n_score:+.2f}</div>
                    <div class="rd-col"><b>{suggestion}</b></div>
                    <div class="rd-col"><b>{val_label}分位 {val_pct} (正常{val_range_str}) | PE分位 {pe_pct} | PB分位 {pb_pct}</b></div>
                    <div class="rd-col"><b>确认条件</b> {confirmations}</div>
                </div>
            </div>
        </div>'''

    trading_html = ""
    if trading_suggestions:
        for ts in trading_suggestions:
            action = ts.get("action", "")
            asset = ts.get("asset", "")
            suggestion_text = ts.get("suggestion", "")
            action_color = {"新开": "#4CAF50", "加仓": "#2196F3", "减仓": "#FF9800", "平仓": "#F44336", "转向": "#9C27B0"}.get(action, "#757575")
            trading_html += f'''
            <div class="trade-item" style="border-left: 4px solid {action_color}">
                <span class="trade-action" style="color: {action_color}">{action}</span>
                <span class="trade-asset">{asset}</span>
                <span class="trade-desc">{suggestion_text}</span>
            </div>'''

    # 市场环境HTML
    macro = market_data.get("macro", {})
    overview = market_data.get("market_overview", {})

    erp_data = macro.get("cn_premium_value", {})
    # ERP从不同字段名提取
    erp_value = (erp_data.get("EquityPremium") or erp_data.get("value") or erp_data.get("erp") or "")
    erp_10y_pct = erp_data.get("EprPct10Y") or erp_data.get("DprPct10Y")
    if erp_10y_pct:
        erp_10y_pct = float(erp_10y_pct) if erp_10y_pct else None

    erp_status = _erp_status(erp_value)
    erp_status_text = erp_status["interpret"] if isinstance(erp_status, dict) else str(erp_status)
    erp_style = erp_status.get("style", "") if isinstance(erp_status, dict) else ""
    erp_advice = erp_status.get("advice", "") if isinstance(erp_status, dict) else ""
    try:
        erp_value_display = f"{float(erp_value):.2f}%" if erp_value else "N/A"
    except (ValueError, TypeError):
        erp_value_display = str(erp_value) if erp_value else "N/A"

    changedist = overview.get("changedist", {})
    up_count = changedist.get("up_count", "N/A")
    down_count = changedist.get("down_count", "N/A")
    total_count = f"{up_count}/{down_count}" if up_count != "N/A" else "N/A"
    up_ratio_pct = changedist.get("up_ratio_pct") or changedist.get("up_ratio", 0)
    if isinstance(up_ratio_pct, (int, float)):
        up_ratio_pct = up_ratio_pct if up_ratio_pct > 1 else up_ratio_pct * 100
    else:
        up_ratio_pct = 0

    hsgt = overview.get("hsgt", {})
    north_flow_val = hsgt.get("net_flow") or hsgt.get("north_net")
    north_flow_display = _format_flow(north_flow_val)

    # 信号等级分布
    s_count = signal_summary.get("s_plus_count", 0) + signal_summary.get("s_minus_count", 0)
    a_count = signal_summary.get("a_plus_count", 0) + signal_summary.get("a_minus_count", 0)
    total_s = signal_summary.get("total_signals", 0)

    # 板块资金流排名（多维度）
    inflow_html = ""
    outflow_html = ""
    flow_note = ""
    if sector_fund_ranking:
        # 当日TOP5
        for item in sector_fund_ranking.get("inflow_top5", []):
            name = item.get("name", "")
            flow = item.get("1日", 0)
            flow_str = _format_flow(flow)
            inflow_html += f'<span class="fund-chip-inflow">{name} {flow_str}</span> '
        for item in sector_fund_ranking.get("outflow_top5", []):
            name = item.get("name", "")
            flow = item.get("1日", 0)
            flow_str = _format_flow(flow)
            outflow_html += f'<span class="fund-chip-outflow">{name} {flow_str}</span> '

        # 5日趋势TOP5
        in5_html = ""
        out5_html = ""
        for item in sector_fund_ranking.get("inflow_top5_5d", []):
            name = item.get("name", "")
            flow = item.get("5日", 0)
            in5_html += f'<span class="fund-chip-inflow">{name} {_format_flow(flow)}</span> '
        for item in sector_fund_ranking.get("outflow_top5_5d", []):
            name = item.get("name", "")
            flow = item.get("5日", 0)
            out5_html += f'<span class="fund-chip-outflow">{name} {_format_flow(flow)}</span> '

        # 标注持续流入/流出信号
        flow_note = ""
        if in5_html and inflow_html:
            # 比较当日和5日TOP5，找出同时出现在两个列表中的板块
            day1_names = {item.get("name","") for item in sector_fund_ranking.get("inflow_top5",[])}
            day5_names = {item.get("name","") for item in sector_fund_ranking.get("inflow_top5_5d",[])}
            sustained = day1_names & day5_names
            if sustained:
                flow_note += f'🟢 持续流入: {", ".join(sustained)} '
            day1_out = {item.get("name","") for item in sector_fund_ranking.get("outflow_top5",[])}
            day5_out = {item.get("name","") for item in sector_fund_ranking.get("outflow_top5_5d",[])}
            sustained_out = day1_out & day5_out
            if sustained_out:
                flow_note += f'🔴 持续流出: {", ".join(sustained_out)}'

    # 组装完整HTML
    # 板块资金流向卡片HTML（多日）
    sector_fund_card = ""
    if inflow_html:
        sector_fund_card = f'''                <div class="market-card" style="grid-column: span 2;">
                    <div class="label" style="font-size:13px">📈 板块主力资金流向</div>
                    <div class="label" style="margin-top:2px;font-size:12px;line-height:1.8"><b>当日流入TOP</b> {inflow_html}</div>
                    <div class="label" style="font-size:12px;line-height:1.8"><b>当日流出TOP</b> {outflow_html}</div>
                    <details style="margin-top:4px;font-size:12px;color:var(--text-secondary)">
                        <summary style="cursor:pointer">📊 查看5日趋势详情</summary>
                        <div style="margin-top:4px;line-height:1.8"><b>5日流入TOP</b> {in5_html}</div>
                        <div style="line-height:1.8"><b>5日流出TOP</b> {out5_html}</div>
                        <div style="margin-top:4px;color:{'#4CAF50' if flow_note else 'var(--text-secondary)'}">{flow_note}</div>
                    </details>
                </div>
'''

    # 内联条形图HTML

    # 预计算条形图HTML + 资金趋势图
    bar_chart_all = ""
    fund_trend_bars_html = ""
    try:
        # 信号评分条（加等级标签 + 排序）
        def _get_level_label(sc):
            if sc < -0.75: return "S+"
            if sc < -0.50: return "A+"
            if sc < -0.25: return "B+"
            if sc > 0.75: return "S-"
            if sc > 0.50: return "A-"
            if sc > 0.25: return "B-"
            return "N"

        def _get_level_color(sc):
            if sc < -0.75: return "#006400"
            if sc < -0.50: return "#28A745"
            if sc < -0.25: return "#90EE90"
            if sc > 0.75: return "#8B0000"
            if sc > 0.50: return "#DC3545"
            if sc > 0.25: return "#FFB6C1"
            return "#808080"

        sorted_signals = sorted(signals, key=lambda s: s.get("composite_score", 0))
        all_bars = []
        for s in sorted_signals[:12]:
            nm = s.get("asset_name", "")
            sc = s.get("composite_score", 0)
            wdt = min(abs(sc) * 100, 100)
            clr = "#4CAF50" if sc < 0 else "#DC3545"
            lvl = _get_level_label(sc)
            lvl_clr = _get_level_color(sc)
            all_bars.append('<div class="bar-row"><span class="bar-label">' + nm + '</span><span class="bar-level" style="color:' + lvl_clr + ';font-weight:700;font-size:11px;width:28px">' + lvl + '</span><div class="bar-track"><div class="bar-fill" style="width:' + str(round(wdt)) + '%;background:' + clr + '"></div></div><span class="bar-score" style="color:' + clr + '">' + "{:+.2f}".format(sc) + '</span></div>')
        bar_chart_all = "\n".join(all_bars)

        # 资金流向趋势 — 每日竖柱状图（可点击切换行业）
        fund_trend_bars_html = ""
        if sector_fund_ranking:
            # 获取所有行业的每日资金流历史
            sector_daily_data = sector_fund_ranking.get("daily_histories", {})
            if not sector_daily_data:
                # 回退：从mock数据的fund_flow_history取
                sector_daily_data = sector_fund_ranking.get("fund_flow_histories", {})
            
            sector_names = list(sector_daily_data.keys())
            
            if sector_names:
                # 构建标签栏
                tabs_html = " ".join([f'<span class="fund-tab" onclick="showSector(this,\'{s}\')" style="cursor:pointer;padding:2px 10px;margin:2px;border-radius:4px;font-size:12px;display:inline-block;background:rgba(255,255,255,0.06)">{s}</span>' for s in sector_names])
                
                # 为每个行业生成竖柱状图
                first_sector = sector_names[0]
                charts_html = ""
                for nm in sector_names:
                    days_data = sector_daily_data.get(nm, [])
                    max_val = max([abs(d.get("main_flow", 0)) for d in days_data]) if days_data else 1
                    if max_val == 0: max_val = 1
                    
                    bars = ""
                    for d in days_data:
                        date_str = d.get("date", "")[-5:]  # "07-14"格式
                        val = d.get("main_flow", 0)
                        pct = abs(val) / max_val * 100
                        clr = "#4CAF50" if val >= 0 else "#DC3545"
                        val_str = _format_flow(val)
                        bars += f'<div style="display:flex;flex-direction:column;align-items:center;width:36px;flex-shrink:0"><div style="font-size:9px;color:{clr};font-weight:600;margin-bottom:2px">{val_str.replace("亿","")}</div><div style="width:24px;height:{max(4, pct)}px;background:{clr};border-radius:3px 3px 0 0;opacity:0.85"></div><div style="font-size:9px;color:var(--text-secondary);margin-top:2px">{date_str}</div></div>'
                    
                    display = "flex" if nm == first_sector else "none"
                    charts_html += f'<div class="sector-fund-chart" data-sector="{nm}" style="display:{display};justify-content:space-around;align-items:flex-end;padding:10px 0;min-height:160px;overflow-x:auto">{bars}</div>'
                
                fund_trend_bars_html = f'<div style="margin-bottom:6px">{tabs_html}</div>{charts_html}'
                fund_trend_bars_html += '''<script>
function showSector(el, name) {
    document.querySelectorAll('.fund-tab').forEach(function(t) {
        t.style.background = 'rgba(255,255,255,0.06)';
    });
    el.style.background = 'rgba(76,175,80,0.3)';
    document.querySelectorAll('.sector-fund-chart').forEach(function(c) {
        c.style.display = c.getAttribute('data-sector') === name ? 'flex' : 'none';
    });
}
</script>'''
        
        fund_trend_bars_html = fund_trend_bars_html or "暂无资金数据"

    except Exception as e:
        import traceback; traceback.print_exc()
        bar_chart_all = "<!-- 图表渲染异常: " + str(e) + " -->"
        fund_trend_bars_html = "<!-- 资金趋势渲染异常: " + str(e) + " -->"

    html = f'''<!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>全球大类资产极端状态反转策略 — {today}</title>
            <style>
                :root {{
                    --bg: #0f1117;
                    --card-bg: #1a1d2e;
                    --text: #e0e0e0;
                    --text-secondary: #8890a4;
                    --border: #2a2d3e;
                    --accent: #4CAF50;
                    --danger: #F44336;
                    --warning: #FF9800;
                }}
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
                    background: var(--bg);
                    color: var(--text);
                    line-height: 1.6;
                }}
                .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}

                /* Header */
                .header {{
                    text-align: center;
                    padding: 30px 0;
                    border-bottom: 1px solid var(--border);
                    margin-bottom: 30px;
                }}
                .header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
                .header .subtitle {{ color: var(--text-secondary); font-size: 14px; }}

                /* Market Overview */
                .market-overview {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                    gap: 12px;
                    margin-bottom: 30px;
                }}
                .market-card {{
                    background: var(--card-bg);
                    border-radius: 10px;
                    padding: 16px;
                    text-align: center;
                    border: 1px solid var(--border);
                }}
                .market-card .value {{ font-size: 24px; font-weight: 700; margin: 8px 0; }}
                .market-card .label {{ color: var(--text-secondary); font-size: 13px; }}

                /* Section */
                .section {{
                    margin-bottom: 30px;
                }}
                .section-title {{
                    font-size: 20px;
                    font-weight: 700;
                    margin-bottom: 16px;
                    padding-bottom: 8px;
                    border-bottom: 2px solid var(--border);
                }}

                /* Charts */
                .charts-section {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .chart-container {{
                    background: var(--card-bg);
                    border-radius: 12px;
                    padding: 20px;
                    border: 1px solid var(--border);
                }}
                .chart-container canvas {{ max-height: 400px; }}

                /* 内联条形图 */
                .bar-chart {{
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }}
                .bar-row {{
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                .bar-label {{
                    width: 80px;
                    font-size: 12px;
                    text-align: right;
                    flex-shrink: 0;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }}
                .bar-track {{
                    flex: 1;
                    height: 18px;
                    background: rgba(255,255,255,0.06);
                    border-radius: 4px;
                    overflow: hidden;
                    min-width: 60px;
                }}
                .bar-fill {{
                    height: 100%;
                    border-radius: 4px;
                    transition: width 0.3s;
                    opacity: 0.85;
                }}
                .bar-score {{
                    width: 55px;
                    font-size: 12px;
                    font-weight: 600;
                    font-family: 'Courier New', monospace;
                    text-align: right;
                    flex-shrink: 0;
                }}

                /* Signal Table - 紧凑列表 */
                .signal-table {{
                    background: var(--card-bg);
                    border-radius: 10px;
                    border: 1px solid var(--border);
                    overflow: hidden;
                }}
                .st-header {{
                    display: flex;
                    align-items: center;
                    padding: 10px 14px;
                    background: rgba(255,255,255,0.04);
                    border-bottom: 1px solid var(--border);
                    font-size: 12px;
                    color: var(--text-secondary);
                    font-weight: 600;
                    gap: 8px;
                }}
                .st-header span {{ white-space: nowrap; }}
                .sth-icon {{ width: 24px; min-width: 24px; }}
                .sth-level {{ width: 90px; min-width: 90px; }}
                .sth-name {{ width: 90px; min-width: 80px; }}
                .sth-score {{ width: 70px; min-width: 70px; text-align: right; }}
                .sth-pe {{ width: 150px; min-width: 140px; text-align: right; }}
                .sth-ret {{ width: 80px; min-width: 70px; text-align: right; }}
                .sth-tool {{ flex: 1; min-width: 100px; text-align: right; }}
                .sth-pos {{ width: 60px; min-width: 60px; text-align: right; }}
                .signal-row {{
                    display: flex;
                    flex-direction: column;
                    cursor: pointer;
                    transition: background 0.15s;
                    border-bottom: 1px solid rgba(255,255,255,0.04);
                }}
                .signal-row:hover {{ background: rgba(255,255,255,0.03); }}
                .signal-row:last-child {{ border-bottom: none; }}
                .row-main {{
                    display: flex;
                    align-items: center;
                    padding: 10px 14px;
                    gap: 8px;
                    font-size: 14px;
                }}
                .row-main span {{ white-space: nowrap; }}
                .row-icon {{ font-size: 14px; width: 24px; min-width: 24px; text-align: center; }}
                .row-level {{ font-weight: 700; font-size: 12px; width: 90px; min-width: 90px; }}
                .row-name {{ font-weight: 600; width: 90px; min-width: 80px; overflow: hidden; text-overflow: ellipsis; }}
                .row-score {{ font-weight: 700; font-size: 15px; width: 70px; min-width: 70px; text-align: right; font-family: 'Courier New', monospace; }}
                .row-pe {{ width: 150px; min-width: 140px; text-align: right; font-size: 13px; }}
                .row-range {{ font-size: 11px; color: var(--text-secondary); }}
                .row-ret {{ width: 80px; min-width: 70px; text-align: right; font-size: 13px; font-family: 'Courier New', monospace; }}
            .row-tool {{ flex: 1; min-width: 100px; text-align: right; font-size: 13px; font-family: 'Courier New', monospace; font-weight: 600; }}
            .row-pos {{ width: 60px; min-width: 60px; text-align: right; font-size: 13px; font-weight: 600; }}
            .bar-level {{ text-align: center; flex-shrink: 0; }}
                .row-detail {{
                    max-height: 0;
                    overflow: hidden;
                    transition: max-height 0.25s ease;
                    padding: 0 14px;
                    background: rgba(0,0,0,0.15);
                }}
                .row-detail.active {{ max-height: 200px; padding: 10px 14px; }}
                .row-detail-inner {{ font-size: 12px; color: var(--text-secondary); line-height: 1.8; }}
                .rd-col {{ padding: 2px 0; }}
                .section-divider {{
                    display: flex;
                    align-items: center;
                    padding: 0 14px;
                    background: rgba(255,255,255,0.02);
                    border-bottom: 1px solid var(--border);
                    border-top: 1px solid var(--border);
                }}
                .section-divider span {{ font-size: 12px; font-weight: 600; padding: 6px 0; color: var(--text-secondary); }}
                .fund-chip-inflow {{ color: #F44336; padding: 1px 0; }}  /* 流出=红色（负值） */
                .fund-chip-outflow {{ color: #4CAF50; padding: 1px 0; }}  /* 流入=绿色（正值） */
                .empty-state {{
                    text-align: center;
                    padding: 40px;
                    color: var(--text-secondary);
                }}

                @media (max-width: 768px) {{
                    .charts-section {{ grid-template-columns: 1fr; }}
                    .signal-table {{ overflow-x: auto; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Header -->
                <div class="header">
                    <h1>🌐 全球大类资产极端状态反转策略</h1>
                    <div class="subtitle">{today} 收盘日报 | 生成时间 {now_time} CST | 仅供研究参考</div>
                </div>

                <!-- 市场环境速览 -->
                <div class="section">
                    <div class="section-title" style="font-size:16px; margin-bottom:8px">📊 市场环境速览</div>
                    <div class="market-overview">
                        <div class="market-card" style="{erp_style}">
                            <div class="label">股债性价比 (ERP)<span style="font-size:11px;color:var(--text-secondary);font-weight:normal;margin-left:4px;cursor:pointer" onclick="var p=this.parentElement.nextElementSibling.nextElementSibling.nextElementSibling.nextElementSibling;p.style.display=p.style.display=='none'?'block':'none'">[?]</span></div>
                            <div class="value" style="font-size:22px">{erp_value_display}</div>
                            <div class="label" style="font-size:12px; margin-top:4px">{erp_advice}</div>
                            <div class="label" style="font-size:11px">{erp_status_text}{f' | 10年分位{erp_10y_pct:.0f}%' if erp_10y_pct else ''}</div>
                            <div class="label">股债性价比 (ERP)<span style="font-size:11px;color:var(--text-secondary);font-weight:normal;margin-left:4px;cursor:pointer" onclick="var p=this.parentElement.nextElementSibling.nextElementSibling.nextElementSibling.nextElementSibling;p.style.display=p.style.display=='none'?'block':'none'">[?]</span></div>
                            <div class="value" style="font-size:22px">{erp_value_display}</div>
                            <div class="label" style="font-size:12px; margin-top:4px">{erp_advice}</div>
                            <div class="label" style="font-size:11px">{erp_status_text}{f' | 10年分位{erp_10y_pct:.0f}%' if erp_10y_pct else ''}</div>
                        <div style="display:none;margin-top:6px;padding:6px;background:rgba(0,0,0,0.2);border-radius:4px;font-size:11px;line-height:1.6;color:var(--text-secondary);text-align:left">
                            <b>ERP = 1/PE - 10年国债收益率</b><br>
                            ERP越高 → 股票越便宜 → 买股票<br>
                            ERP越低 → 股票越贵 → 买债券<br>
                            <span style="color:#006400">&gt;5% 极度低估 买股票</span><br>
                            <span style="color:#4CAF50">3~5% 有吸引力</span><br>
                            <span style="color:#FFC107">2~3% 中性</span><br>
                            <span style="color:#FF9800">1~2% 偏高估</span><br>
                            <span style="color:#F44336">&lt;1% 极度高估 买债券</span>
                        </div>
                        </div>
                        <div class="market-card">
                            <div class="label">市场情绪 (涨/跌)</div>
                            <div class="value" style="font-size:22px">{total_count}</div>
                            <div class="label" style="font-size:11px">上涨{up_count}/下跌{down_count}</div>
                            <div class="label" style="font-size:11px;color: {'#F44336' if up_count != "N/A" and down_count != "N/A" and int(str(up_count))<int(str(down_count)) else "#4CAF50"}">上涨占比 {up_ratio_pct:.0f}%{' ⚠️ 极弱' if up_ratio_pct and up_ratio_pct<15 else ''}</div>
                        </div>
                        <div class="market-card">
                            <div class="label">主力资金 (替代北向)</div>
                            <div class="value" style="font-size:22px">{north_flow_display}</div>
                            <div class="label" style="font-size:11px">当日主力净流入 | 北向仅季度级别</div>
                        </div>
                        {sector_fund_card}
                        <div class="market-card">
                            <div class="label">信号强度分布</div>
                            <div class="value" style="font-size:20px">{s_count}S / {a_count}A / {total_s}总</div>
                            <div class="label" style="font-size:11px">极端(S) / 显著(A) / 总信号数</div>
                        </div>
                        <div class="market-card">
                            <div class="label">市场方向偏好</div>
                            <div class="value" style="font-size:22px">
                                <span style="color:#4CAF50">{signal_summary.get('long_count', 0)}做多</span>
                                <span style="color:#808080">/</span>
                                <span style="color:#F44336">{signal_summary.get('short_count', 0)}做空</span>
                            </div>
                            <div class="label" style="font-size:11px">做多信号数 / 做空信号数</div>
                        </div>
                    </div>
                </div>

                <!-- 信号等级分布（底部附录） -->
                <div class="section">
                    <details>
                        <summary class="section-title" style="font-size:14px; cursor:pointer; border-bottom:none; display:inline-block">📋 信号等级分布详情</summary>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <div class="stat-value" style="color: #006400">{signal_summary.get('s_plus_count', 0)}</div>
                                <div class="stat-label">S+ 强做多</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value" style="color: #28A745">{signal_summary.get('a_plus_count', 0)}</div>
                                <div class="stat-label">A+ 做多</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value" style="color: #90EE90">{signal_summary.get('b_plus_count', 0)}</div>
                                <div class="stat-label">B+ 观察偏多</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value" style="color: #808080">{signal_summary.get('neutral_count', 0)}</div>
                                <div class="stat-label">N 中性</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value" style="color: #FFB6C1">{signal_summary.get('b_minus_count', 0)}</div>
                                <div class="stat-label">B- 观察偏空</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value" style="color: #DC3545">{signal_summary.get('a_minus_count', 0)}</div>
                                <div class="stat-label">A- 做空</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value" style="color: #8B0000">{signal_summary.get('s_minus_count', 0)}</div>
                                <div class="stat-label">S- 强做空</div>
                            </div>
                        </div>
                    </details>
                </div>

                <!-- Charts -->
                <div class="charts-section">
                    <div class="chart-container">
                        <h3 style="margin-bottom:8px;font-size:15px">📊 信号评分总览</h3>
                        <div class="bar-chart">
                            {bar_chart_all}
                        </div>
                        <div class="chart-legend" style="margin-top:8px;font-size:11px;color:var(--text-secondary);display:flex;flex-wrap:wrap;gap:6px">
                            <span style="color:#006400">■ S+强做多</span>
                            <span style="color:#28A745">■ A+做多</span>
                            <span style="color:#90EE90">■ B+观察偏多</span>
                            <span style="color:#FFB6C1">■ B-观察偏空</span>
                            <span style="color:#DC3545">■ A-做空</span>
                            <span style="color:#8B0000">■ S-强做空</span>
                            <span style="margin-left:8px">| 评分范围: -1.0 ~ +1.0</span>
                            <span>| 正值=高估(做空) 负值=低估(做多)</span>
                        </div>
                    </div>
                    <div class="chart-container">
                        <h3 style="margin-bottom:8px;font-size:15px">📈 板块资金流入趋势</h3>
                        <div class="fund-trend-chart" style="font-size:13px;color:var(--text-secondary);line-height:1.8">
                            {fund_trend_bars_html}
                        </div>
                    </div>
                </div>

                <!-- 信号总览（紧凑列表） -->
                <div class="section">
                    <div class="section-title" style="font-size:16px">📋 信号总览</div>
                    <div class="signal-table">
                        <div class="st-header">
                            <span class="sth-icon"></span>
                            <span class="sth-level">信号</span>
                            <span class="sth-name">资产</span>
                            <span class="sth-score">评分</span>
                            <span class="sth-pe">核心估值(正常区间)</span>
                            <span class="sth-ret">近3月</span>
                            <span class="sth-tool">ETF标的</span>
                            <span class="sth-pos">仓位</span>
                        </div>
                        {'<div class="section-divider"><span>🔴 做空信号区</span></div>' if short_signals else ''}
                        {"".join(build_signal_row(s, "short") for s in short_signals) if short_signals else ''}
                        {'<div class="section-divider"><span>🟢 做多信号区</span></div>' if long_signals else ''}
                        {"".join(build_signal_row(s, "long") for s in long_signals) if long_signals else ''}
                        {'<div class="section-divider"><span>🟡 观察区</span></div>' if watch_signals else ''}
                        {"".join(build_signal_row(s, "watch") for s in watch_signals) if watch_signals else ''}
                        {'<div class="section-divider"><span>🟡 观察区</span></div>' if watch_signals else ''}
                        {'<div class="empty-state" style="padding:20px">暂无信号</div>' if not (short_signals or long_signals or watch_signals) else ''}
                    </div>
                </div>

                <!-- Trading Suggestions -->
                <div class="section">
                    <div class="section-title">📋 今日调仓建议</div>
                    <div class="trade-list">
                        {trading_html if trading_html else '<div class="empty-state">今日无调仓建议</div>'}
                    </div>
                </div>

                <!-- Footer -->
                <div class="footer">
                    <p>⚠️ 本仪表盘仅供研究参考，不构成投资建议。做空风险极高，请谨慎决策。</p>
                    <p>数据来源：腾讯自选股、东方财富、同花顺 | 生成时间：{now_time}</p>
                </div>
            </div>

        </body>
        </html>'''

    return html


def save_dashboard(signals: List[Dict], market_data: Dict,
                   signal_summary: Dict, trading_suggestions: List[Dict] = None,
                   output_path: str = None, sector_fund_ranking: Dict = None) -> str:
    """
    生成并保存HTML仪表盘

    Returns:
        str: 保存的文件路径
    """
    html = generate_dashboard(signals, market_data, signal_summary, trading_suggestions, sector_fund_ranking)

    if output_path is None:
        today = datetime.now().strftime("%Y%m%d")
        output_path = str(OUTPUT_DIR / f"dashboard_{today}.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
