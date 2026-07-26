"""
仓位管理模块
根据信号等级、市场波动率、流动性计算建议仓位
"""

import math
from typing import Dict, List, Optional

from config.settings import POSITION, VOLATILITY


class PositionManager:
    """仓位管理器"""
    
    def __init__(self):
        self.base_position = POSITION["base_position_pct"]  # 5%
    
    def calculate_position(self, signal_result) -> float:
        """
        计算单资产建议仓位
        
        仓位 = 基准仓位 × 信号强度系数 × 波动率调整系数 × 流动性调整系数
        
        Args:
            signal_result: SignalResult 对象
        
        Returns:
            建议仓位比例 (0~0.15)
        """
        base = self.base_position
        
        # 1. 信号强度系数
        signal_mult = signal_result.position_multiplier  # S=1.5, A=1.0, B=0.5
        
        # 2. 波动率调整系数
        vol_mult = self._volatility_adjustment(signal_result)
        
        # 3. 流动性调整系数
        liq_mult = self._liquidity_adjustment(signal_result)
        
        # 4. 做空折减
        direction_mult = POSITION["short_position_discount"] if signal_result.direction == "short" else 1.0
        
        position = base * signal_mult * vol_mult * liq_mult * direction_mult
        
        # 根据市场环境设定上限
        vix = self._get_market_vix(signal_result)
        if vix is None or vix <= VOLATILITY["normal_max"]:
            max_single = POSITION["max_single_asset_normal"]
        elif vix <= VOLATILITY["high_max"]:
            max_single = POSITION["max_single_asset_high_vol"]
        else:
            max_single = POSITION["max_single_asset_extreme"]
        
        return min(position, max_single)
    
    def _volatility_adjustment(self, signal_result) -> float:
        """
        波动率调整系数
        高波动 → 降仓位
        """
        # 从RSI极端度推断波动率
        rsi = signal_result.rsi_14
        if rsi is None:
            return 1.0
        
        # RSI偏离50越远，波动越大
        rsi_deviation = abs(rsi - 50) / 50
        
        # 波动率调整 = min(2.0, 20% / 估算年化波动率)
        # 用RSI偏离度代理波动率
        estimated_vol = 0.15 + rsi_deviation * 0.35  # 估算15%~50%年化波动率
        
        adjustment = min(2.0, POSITION["volatility_cap"] / estimated_vol)
        return adjustment
    
    def _liquidity_adjustment(self, signal_result) -> float:
        """流动性调整系数"""
        # 从成交量异常度推断流动性
        volume_ratio = signal_result.volume_ratio
        if volume_ratio is None:
            return 1.0
        
        # 成交量萎缩 = 流动性下降
        if volume_ratio < 0.3:
            return POSITION["liquidity_discount_critical"]
        elif volume_ratio < 0.5:
            return POSITION["liquidity_discount_low"]
        
        return 1.0
    
    def _get_market_vix(self, signal_result) -> Optional[float]:
        """获取市场VIX水平"""
        # 从信号详情中提取
        details = signal_result.details
        return None  # 需要外部数据
    
    def calculate_total_position(self, positions: List[float],
                                  market_vix: float = None) -> Dict:
        """
        计算总仓位和风险敞口
        
        Returns:
            {
                "total_long": float,
                "total_short": float,
                "net_exposure": float,
                "gross_exposure": float,
                "is_over_limit": bool,
                "warning": str,
            }
        """
        total_long = sum(p for p in positions if p > 0)
        total_short = sum(abs(p) for p in positions if p < 0)
        net_exposure = total_long - total_short
        gross_exposure = total_long + total_short
        
        # 市场环境判断
        if market_vix is None or market_vix <= VOLATILITY["normal_max"]:
            max_total = POSITION["max_total_position_normal"]
            max_same_dir = POSITION["max_same_direction_normal"]
        elif market_vix <= VOLATILITY["high_max"]:
            max_total = POSITION["max_total_position_high_vol"]
            max_same_dir = POSITION["max_same_direction_high_vol"]
        else:
            max_total = POSITION["max_total_position_extreme"]
            max_same_dir = POSITION["max_same_direction_extreme"]
        
        warnings = []
        if gross_exposure > max_total:
            warnings.append(f"总仓位{gross_exposure*100:.1f}%超过上限{max_total*100:.0f}%")
        if total_long > max_same_dir:
            warnings.append(f"多头仓位{total_long*100:.1f}%超过同向上限{max_same_dir*100:.0f}%")
        if total_short > max_same_dir:
            warnings.append(f"空头仓位{total_short*100:.1f}%超过同向上限{max_same_dir*100:.0f}%")
        
        return {
            "total_long": total_long,
            "total_short": total_short,
            "net_exposure": net_exposure,
            "gross_exposure": gross_exposure,
            "max_total": max_total,
            "is_over_limit": len(warnings) > 0,
            "warnings": warnings,
        }
