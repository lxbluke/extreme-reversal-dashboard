"""
综合评分引擎 — 极端状态反转策略的核心
整合估值、动量、情绪、叙事资金四维度评分，生成信号
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from config.settings import (
    ASSET_WEIGHTS, SIGNAL_LEVELS, CONFIRMATION, SIGNAL_VALIDITY_DAYS
)
from config.asset_mapping import get_asset_class as _get_asset_class, get_asset_info
from config.symbols import get_trade_tool
from models.valuation import calculate_valuation
from models.momentum import calculate_momentum
from models.sentiment import calculate_sentiment
from models.narrative import calculate_narrative

logger = logging.getLogger(__name__)


@dataclass
class SignalResult:
    """信号结果"""
    asset_name: str
    asset_class: str
    asset_code: str
    composite_score: float
    signal_level: str
    signal_label: str
    direction: Optional[str]  # 'long' / 'short' / None
    color: str
    position_multiplier: float
    
    # 子评分
    valuation_score: float = 0.0
    momentum_score: float = 0.0
    sentiment_score: float = 0.0
    narrative_score: float = 0.0
    
    # 详细数据
    pe_percentile: Optional[float] = None
    pb_percentile: Optional[float] = None
    ps_percentile: Optional[float] = None
    return_3m: Optional[float] = None
    return_1m: Optional[float] = None
    rsi_14: Optional[float] = None
    turnover_rate: Optional[float] = None
    volume_ratio: Optional[float] = None
    
    # 交易建议
    trade_tool: Dict = field(default_factory=dict)
    trade_suggestion: str = ""
    position_pct: float = 0.0
    
    # 确认条件
    confirmations: List[str] = field(default_factory=list)
    confirmation_count: int = 0
    
    # 元数据
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: Dict = field(default_factory=dict)
    
    # 历史对比
    previous_signal: Optional[str] = None
    signal_change: str = "new"  # new / upgraded / downgraded / unchanged
    
    def to_dict(self) -> Dict:
        return {
            "date": self.date,
            "asset_name": self.asset_name,
            "asset_class": self.asset_class,
            "asset_code": self.asset_code,
            "composite_score": round(self.composite_score, 4),
            "signal_level": self.signal_level,
            "signal_label": self.signal_label,
            "direction": self.direction,
            "color": self.color,
            "position_multiplier": self.position_multiplier,
            "valuation_score": round(self.valuation_score, 4),
            "momentum_score": round(self.momentum_score, 4),
            "sentiment_score": round(self.sentiment_score, 4),
            "narrative_score": round(self.narrative_score, 4),
            "pe_percentile": self.pe_percentile,
            "pb_percentile": self.pb_percentile,
            "ps_percentile": self.ps_percentile,
            "return_3m": self.return_3m,
            "return_1m": self.return_1m,
            "rsi_14": self.rsi_14,
            "turnover_rate": self.turnover_rate,
            "volume_ratio": self.volume_ratio,
            "trade_suggestion": self.trade_suggestion,
            "trade_tool": self.trade_tool,  # 完整交易工具信息
            "position_pct": round(self.position_pct, 4),
            "confirmations": self.confirmations,
            "confirmation_count": self.confirmation_count,
            "signal_change": self.signal_change,
            "details": self.details,
        }


class ExtremeReversalScorer:
    """极端状态反转综合评分引擎"""
    
    def __init__(self, asset_class: str):
        """
        Args:
            asset_class: 'a_share_sector' | 'commodity' | 'us_etf' | 
                         'hk_sector' | 'global_index' | 'fx_bond'
        """
        self.asset_class = asset_class
        self.weights = ASSET_WEIGHTS.get(asset_class, ASSET_WEIGHTS["a_share_sector"])
    
    def score(self, asset_data: Dict, market_overview: Dict = None,
              macro_data: Dict = None, historical_data: Dict = None) -> SignalResult:
        """
        计算综合评分并生成信号
        
        Args:
            asset_data: 资产数据（从DataCollector采集）
            market_overview: 市场总览数据
            macro_data: 宏观数据
            historical_data: 历史数据（用于分位数计算）
        
        Returns:
            SignalResult: 完整的信号结果
        """
        asset_name = asset_data.get("name", "Unknown")
        asset_code = asset_data.get("code", asset_data.get("pt_code", ""))
        
        # Step 1: 计算四个维度的评分
        v_result = calculate_valuation(self.asset_class, asset_data, historical_data, macro_data)
        m_result = calculate_momentum(self.asset_class, asset_data)
        s_result = calculate_sentiment(self.asset_class, asset_data, market_overview)
        n_result = calculate_narrative(self.asset_class, asset_data, market_overview)
        
        v_score = v_result.get("composite", 0.0)
        m_score = m_result.get("composite", 0.0)
        s_score = s_result.get("composite", 0.0)
        n_score = n_result.get("composite", 0.0)
        
        # Step 2: 处理缺失指标（优雅降级：缺失维度重新归一化权重）
        valid_weights = {}
        total_valid_weight = 0.0
        
        if abs(v_score) > 0.001 or v_result.get("sub_scores"):
            valid_weights["valuation"] = self.weights["valuation"]
            total_valid_weight += self.weights["valuation"]
        if abs(m_score) > 0.001 or m_result.get("sub_scores"):
            valid_weights["momentum"] = self.weights["momentum"]
            total_valid_weight += self.weights["momentum"]
        if abs(s_score) > 0.001 or s_result.get("sub_scores"):
            valid_weights["sentiment"] = self.weights["sentiment"]
            total_valid_weight += self.weights["sentiment"]
        if abs(n_score) > 0.001 or n_result.get("sub_scores"):
            valid_weights["narrative"] = self.weights["narrative"]
            total_valid_weight += self.weights["narrative"]
        
        if total_valid_weight > 0:
            # 重新归一化
            scale = 1.0 / total_valid_weight
            v_w = valid_weights.get("valuation", 0) * scale
            m_w = valid_weights.get("momentum", 0) * scale
            s_w = valid_weights.get("sentiment", 0) * scale
            n_w = valid_weights.get("narrative", 0) * scale
        else:
            v_w = self.weights["valuation"]
            m_w = self.weights["momentum"]
            s_w = self.weights["sentiment"]
            n_w = self.weights["narrative"]
        
        # Step 3: 综合评分
        composite = v_score * v_w + m_score * m_w + s_score * s_w + n_score * n_w
        composite = max(-1.0, min(1.0, composite))  # 封顶
        
        # Step 4: 信号等级判定
        signal_level, signal_info = self._classify(composite)
        
        # Step 5: 确认条件检查
        confirmations = self._check_confirmations(asset_data, v_result, m_result, s_result, composite)
        
        # Step 6: 交易建议
        direction = signal_info["direction"]
        trade_tool = get_trade_tool(asset_name, direction, self.asset_class) if direction else {}
        
        # 仓位计算
        base_pos = 0.05  # 5%
        pos_pct = base_pos * signal_info["position_multiplier"]
        if direction == "short":
            pos_pct *= 0.7  # 做空折减
        
        # 生成交易建议文本
        trade_suggestion = self._generate_suggestion(asset_name, direction, trade_tool, pos_pct)
        
        # Step 7: 提取详细数据
        pe_pct = v_result.get("pe_percentile")
        pb_pct = v_result.get("pb_percentile")
        ps_pct = v_result.get("ps_percentile")
        ret_3m = m_result.get("return_3m_pct")
        ret_1m = m_result.get("return_1m_pct")
        rsi = m_result.get("rsi_14")
        
        return SignalResult(
            asset_name=asset_name,
            asset_class=self.asset_class,
            asset_code=asset_code,
            composite_score=composite,
            signal_level=signal_level,
            signal_label=signal_info["label"],
            direction=direction,
            color=signal_info["color"],
            position_multiplier=signal_info["position_multiplier"],
            valuation_score=v_score,
            momentum_score=m_score,
            sentiment_score=s_score,
            narrative_score=n_score,
            pe_percentile=pe_pct,
            pb_percentile=pb_pct,
            ps_percentile=ps_pct,
            return_3m=ret_3m,
            return_1m=ret_1m,
            rsi_14=rsi,
            trade_tool=trade_tool,
            trade_suggestion=trade_suggestion,
            position_pct=pos_pct,
            confirmations=confirmations,
            confirmation_count=len(confirmations),
            details={
                "valuation_detail": v_result,
                "momentum_detail": m_result,
                "sentiment_detail": s_result,
                "narrative_detail": n_result,
                "valid_weights": {"valuation": v_w, "momentum": m_w, "sentiment": s_w, "narrative": n_w},
            }
        )
    
    def _classify(self, score: float) -> tuple:
        """根据综合评分判定信号等级"""
        for level, info in SIGNAL_LEVELS.items():
            if info["min"] <= score < info["max"] or (info["max"] == 1.0 and score == 1.0):
                return level, info
        # fallback
        return "NEUTRAL", SIGNAL_LEVELS["NEUTRAL"]
    
    def _check_confirmations(self, asset_data: Dict, v_result: Dict, m_result: Dict,
                             s_result: Dict, composite: float) -> List[str]:
        """检查确认条件，防止假信号"""
        confirmations = []
        
        # 1. 估值确认
        pe_pct = v_result.get("pe_percentile")
        if pe_pct is not None:
            if pe_pct < CONFIRMATION["valuation_oversold"] and composite < -0.25:
                confirmations.append(f"估值确认：PE分位{pe_pct*100:.0f}% < {CONFIRMATION['valuation_oversold']*100:.0f}%（极度低估）")
            elif pe_pct > CONFIRMATION["valuation_overbought"] and composite > 0.25:
                confirmations.append(f"估值确认：PE分位{pe_pct*100:.0f}% > {CONFIRMATION['valuation_overbought']*100:.0f}%（极度高估）")
        
        # 2. RSI背离确认
        rsi = m_result.get("rsi_14")
        if rsi is not None:
            if rsi < 30 and composite < -0.25:
                confirmations.append(f"RSI确认：RSI(14)={rsi:.1f} < 30（超卖区域）")
            elif rsi > 70 and composite > 0.25:
                confirmations.append(f"RSI确认：RSI(14)={rsi:.1f} > 70（超买区域）")
        
        # 3. 量价背离确认（简化版）
        ret_1m = m_result.get("return_1m_pct", 0)
        vol_score = s_result.get("sub_scores", {}).get("turnover_rate", 0)
        if ret_1m is not None and vol_score is not None:
            # 价格下跌但换手率从极端开始回落 = 做多确认
            if ret_1m < -15 and vol_score > -0.3 and composite < -0.25:
                confirmations.append("量价确认：急跌后换手率开始回落，恐慌情绪见顶")
            # 价格上涨但换手率从极端开始回落 = 做空确认
            elif ret_1m > 15 and vol_score < 0.3 and composite > 0.25:
                confirmations.append("量价确认：急涨后换手率开始回落，追涨情绪衰竭")
        
        return confirmations
    
    def _generate_suggestion(self, asset_name: str, direction: str,
                             trade_tool: Dict, position_pct: float) -> str:
        """
        生成交易建议文本（含具体ETF代码）
        
        格式：
        做多 → 买入银行ETF(sh512800) 建议仓位5.0%
        做空 → 芯片ETF期权Put(sz159995) 建议仓位3.5%
        """
        if direction == "long":
            tool_type = trade_tool.get("type", "ETF")
            tool_code = trade_tool.get("code", "")
            tool_name = trade_tool.get("name", "")
            alt_code = trade_tool.get("alt_code", "")
            
            parts = [f"做多{asset_name}"]
            
            if tool_code:
                desc = f"买入{tool_type} {tool_code}"
                if tool_name:
                    desc += f"({tool_name})"
                if alt_code:
                    desc += f" 备选: {alt_code}"
                parts.append(desc)
            else:
                parts.append(f"买入ETF做多")
            
            parts.append(f"仓位{position_pct*100:.1f}%")
            return "，".join(parts)
        
        elif direction == "short":
            tool_type = trade_tool.get("type", "期权")
            tool_code = trade_tool.get("code", "")
            tool_name = trade_tool.get("name", "")
            note = trade_tool.get("note", "")
            alt_code = trade_tool.get("alt_code", "")
            leverage = trade_tool.get("leverage")
            
            parts = [f"做空{asset_name}"]
            
            if tool_type == "ETF期权Put" and tool_code:
                parts.append(f"买Put {tool_code}({tool_name})")
            elif "反向ETF" in tool_type and tool_code:
                lev_str = f"{abs(leverage)}x" if leverage else ""
                parts.append(f"买入{lev_str}反向ETF {tool_code}({tool_name})")
            elif tool_type == "ETF融券" and tool_code:
                parts.append(f"融券ETF {tool_code}({tool_name})")
                if note:
                    parts.append(f"替代: {note}")
            elif tool_type == "期货空头" and tool_code:
                parts.append(f"期货空头 {tool_code}")
            elif tool_code:
                parts.append(f"{tool_type} {tool_code}")
            else:
                parts.append(f"{note or '买Put/反向ETF'}")
            
            if alt_code:
                parts.append(f"备选: {alt_code}")
            
            parts.append(f"仓位{position_pct*100:.1f}%")
            return "，".join(parts)
        else:
            return f"{asset_name}当前无明确方向信号，建议观望"


class BatchScorer:
    """批量评分器：对所有资产类别批量计算评分"""
    
    def __init__(self):
        self.scorers = {}
        for asset_class in ASSET_WEIGHTS:
            self.scorers[asset_class] = ExtremeReversalScorer(asset_class)
    
    def score_all(self, collected_data: Dict) -> List[SignalResult]:
        """
        对所有采集的数据批量评分
        
        Args:
            collected_data: DataCollector.collect_all() 返回的数据
        
        Returns:
            List[SignalResult]: 所有信号结果，按|评分|降序排列
        """
        all_signals = []
        macro_data = collected_data.get("macro", {})
        market_overview = collected_data.get("market_overview", {})
        
        # A股行业板块
        for name, sector_data in collected_data.get("a_share_sectors", {}).items():
            if name.startswith("_"):  # 跳过元数据
                continue
            try:
                scorer = self.scorers["a_share_sector"]
                signal = scorer.score(sector_data, market_overview, macro_data)
                all_signals.append(signal)
            except Exception as e:
                logger.error(f"评分失败 A股/{name}: {e}")
        
        # 全球商品期货
        for name, commodity_data in collected_data.get("commodities", {}).items():
            try:
                scorer = self.scorers["commodity"]
                signal = scorer.score(commodity_data, market_overview, macro_data)
                all_signals.append(signal)
            except Exception as e:
                logger.error(f"评分失败 商品/{name}: {e}")
        
        # 美股行业ETF
        for name, etf_data in collected_data.get("us_etfs", {}).items():
            try:
                scorer = self.scorers["us_etf"]
                signal = scorer.score(etf_data, market_overview, macro_data)
                all_signals.append(signal)
            except Exception as e:
                logger.error(f"评分失败 美股ETF/{name}: {e}")
        
        # 港股行业
        for name, hk_data in collected_data.get("hk_sectors", {}).items():
            try:
                scorer = self.scorers["hk_sector"]
                signal = scorer.score(hk_data, market_overview, macro_data)
                all_signals.append(signal)
            except Exception as e:
                logger.error(f"评分失败 港股/{name}: {e}")
        
        # 全球股指
        for name, index_data in collected_data.get("global_indices", {}).items():
            try:
                scorer = self.scorers["global_index"]
                signal = scorer.score(index_data, market_overview, macro_data)
                all_signals.append(signal)
            except Exception as e:
                logger.error(f"评分失败 股指/{name}: {e}")
        
        # 外汇/债券
        for name, fx_data in collected_data.get("fx_bonds", {}).items():
            try:
                scorer = self.scorers["fx_bond"]
                signal = scorer.score(fx_data, market_overview, macro_data)
                all_signals.append(signal)
            except Exception as e:
                logger.error(f"评分失败 外汇债券/{name}: {e}")
        
        # 按 |评分| 降序排列
        all_signals.sort(key=lambda s: abs(s.composite_score), reverse=True)
        
        return all_signals


def get_extreme_signals(signals: List[SignalResult], threshold: float = 0.5) -> List[SignalResult]:
    """过滤出极端信号（|评分| >= threshold）"""
    return [s for s in signals if abs(s.composite_score) >= threshold]


def get_signals_by_direction(signals: List[SignalResult], direction: str) -> List[SignalResult]:
    """按方向过滤信号"""
    return [s for s in signals if s.direction == direction]


def generate_signal_summary(signals: List[SignalResult]) -> Dict:
    """生成信号摘要统计"""
    long_signals = get_signals_by_direction(signals, "long")
    short_signals = get_signals_by_direction(signals, "short")
    
    s_plus = [s for s in signals if s.signal_level == "S_PLUS"]
    s_minus = [s for s in signals if s.signal_level == "S_MINUS"]
    a_plus = [s for s in signals if s.signal_level == "A_PLUS"]
    a_minus = [s for s in signals if s.signal_level == "A_MINUS"]
    
    return {
        "total_signals": len(signals),
        "extreme_signals": len(get_extreme_signals(signals, 0.5)),
        "long_count": len(long_signals),
        "short_count": len(short_signals),
        "s_plus_count": len(s_plus),
        "s_minus_count": len(s_minus),
        "a_plus_count": len(a_plus),
        "a_minus_count": len(a_minus),
        "top_long": [s.to_dict() for s in long_signals[:5]],
        "top_short": [s.to_dict() for s in short_signals[:5]],
    }
