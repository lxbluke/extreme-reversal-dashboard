"""
风险控制模块
止损止盈规则、做空特殊规则
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from config.settings import RISK, SIGNAL_LEVELS

logger = logging.getLogger(__name__)


@dataclass
class RiskCheckResult:
    """风险检查结果"""
    action: str  # "hold" / "reduce" / "close" / "stop_loss"
    reason: str
    close_pct: float  # 平仓比例 (0~1)
    urgency: str  # "normal" / "urgent"


class RiskManager:
    """风险管理器"""
    
    def __init__(self):
        self.risk_params = RISK
    
    def check_position_risk(self, position: Dict, current_data: Dict) -> RiskCheckResult:
        """
        检查持仓风险
        
        Args:
            position: 持仓信息
                {
                    "asset_name": str,
                    "direction": "long"|"short",
                    "entry_date": str,
                    "entry_score": float,
                    "entry_price": float,
                    "current_price": float,
                    "position_pct": float,
                    "pnl_pct": float,
                    "holding_weeks": int,
                }
            current_data: 当前市场数据
        
        Returns:
            RiskCheckResult: 风险检查结果
        """
        pnl_pct = position.get("pnl_pct", 0)
        holding_weeks = position.get("holding_weeks", 0)
        direction = position.get("direction", "long")
        
        # 1. 硬止损：单笔亏损 > 总资产2%
        if abs(pnl_pct) > self.risk_params["hard_stop_loss_pct"] * 100:
            # 注意：pnl_pct是单笔收益率，hard_stop_loss_pct是总资产占比
            # 简化：单笔亏损>15%触发硬止损
            if pnl_pct < -0.15:
                return RiskCheckResult(
                    action="stop_loss",
                    reason=f"硬止损触发：单笔亏损{pnl_pct*100:.1f}%",
                    close_pct=1.0,
                    urgency="urgent",
                )
        
        # 2. 时间止损：持仓超过12周
        if holding_weeks > self.risk_params["time_stop_weeks"]:
            return RiskCheckResult(
                action="reduce",
                reason=f"时间止损：持仓{holding_weeks}周超过{self.risk_params['time_stop_weeks']}周上限",
                close_pct=0.5,
                urgency="normal",
            )
        
        # 3. 信号止损：评分回到中性
        current_score = current_data.get("composite_score", 0)
        if abs(current_score) < self.risk_params["signal_stop_threshold"]:
            return RiskCheckResult(
                action="close",
                reason=f"信号止损：当前评分{current_score:.2f}回到中性区间",
                close_pct=1.0,
                urgency="normal",
            )
        
        # 4. 做空时间限制
        if direction == "short" and holding_weeks > self.risk_params.get("max_short_holding_weeks", 8):
            return RiskCheckResult(
                action="close",
                reason=f"做空时间限制：空头持仓{holding_weeks}周超过上限",
                close_pct=1.0,
                urgency="urgent",
            )
        
        # 无风险
        return RiskCheckResult(
            action="hold",
            reason="风险检查通过",
            close_pct=0.0,
            urgency="normal",
        )
    
    def check_take_profit(self, position: Dict, current_data: Dict) -> RiskCheckResult:
        """
        检查止盈条件
        
        Args:
            position: 持仓信息
            current_data: 当前信号数据
                {
                    "composite_score": float,
                    "pe_percentile": float,
                    "rsi_14": float,
                    "signal_level": str,
                }
        """
        pnl_pct = position.get("pnl_pct", 0)
        direction = position.get("direction", "long")
        pe_pct = current_data.get("pe_percentile")
        rsi = current_data.get("rsi_14")
        
        triggers = []
        
        # 1. 估值回归止盈
        if pe_pct is not None:
            if direction == "long" and pe_pct > self.risk_params["take_profit_valuation_min"]:
                triggers.append(f"估值回归：PE分位回升至{pe_pct*100:.0f}%")
            elif direction == "short" and pe_pct < self.risk_params["take_profit_valuation_max"]:
                triggers.append(f"估值回归：PE分位回落至{pe_pct*100:.0f}%")
        
        # 2. 动量衰竭止盈
        if rsi is not None and 45 <= rsi <= 55:
            triggers.append(f"动量衰竭：RSI={rsi:.1f}回到50附近")
        
        # 3. 目标收益止盈
        target = self.risk_params["take_profit_long_return"] if direction == "long" else self.risk_params["take_profit_short_return"]
        if pnl_pct > target:
            triggers.append(f"目标收益达成：收益{pnl_pct*100:.1f}% > {target*100:.0f}%")
        
        if triggers:
            return RiskCheckResult(
                action="reduce",
                reason="止盈触发：" + "；".join(triggers),
                close_pct=self.risk_params["take_profit_first_batch"],
                urgency="normal",
            )
        
        return RiskCheckResult(
            action="hold",
            reason="未触发止盈条件",
            close_pct=0.0,
            urgency="normal",
        )
    
    def get_stop_loss_price(self, entry_price: float, direction: str) -> float:
        """计算止损价格"""
        if direction == "long":
            # 做多止损：亏损8%
            return entry_price * 0.92
        else:
            # 做空止损：亏损10%（做空风险更大）
            return entry_price * 1.10
    
    def get_take_profit_price(self, entry_price: float, direction: str) -> float:
        """计算止盈价格"""
        if direction == "long":
            return entry_price * (1 + self.risk_params["take_profit_long_return"])
        else:
            return entry_price * (1 - self.risk_params["take_profit_short_return"])
