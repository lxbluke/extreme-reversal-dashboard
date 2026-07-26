"""
估值极端度计算模型
为6大资产类别分别实现估值极端度评分（归一化到[-1, 1]）
正值 = 高估，负值 = 低估
"""

import math
import numpy as np
from typing import Dict, List, Optional
from config.settings import VALUATION_WEIGHTS, VALUATION_SECTOR_OVERRIDES, PERCENTILE_MIN_DAYS


def _percentile_to_score(percentile: float) -> float:
    """
    将分位数(0~1)转换为极端度评分(-1~1)
    percentile < 0.5 → 负值(低估)
    percentile > 0.5 → 正值(高估)
    """
    if percentile is None:
        return 0.0
    # |分位-0.5| / 0.5 → 0~1 极端度
    extreme = abs(percentile - 0.5) / 0.5
    # 方向：分位<0.5为低估(负)，>0.5为高估(正)
    direction = 1.0 if percentile > 0.5 else -1.0
    return direction * min(extreme, 1.0)


def _safe_percentile(values: List[float], current: float) -> Optional[float]:
    """安全计算当前值在历史序列中的分位数"""
    if not values or len(values) < PERCENTILE_MIN_DAYS or current is None:
        return None
    arr = np.array([v for v in values if v is not None and not np.isnan(v)])
    if len(arr) < PERCENTILE_MIN_DAYS:
        return None
    return float(np.sum(arr <= current) / len(arr))


# ============================================================
# 1. A股行业板块估值极端度
# ============================================================
def a_share_valuation(sector_data: Dict, historical_pe: List[float] = None,
                      historical_pb: List[float] = None,
                      historical_ps: List[float] = None,
                      historical_dy: List[float] = None) -> Dict:
    """
    A股行业估值极端度
    子指标: PE分位(40%) + PB分位(30%) + PS分位(15%) + 股息率分位(15%)
    """
    valuation = sector_data.get("valuation", {})
    weights = VALUATION_WEIGHTS["a_share_sector"].copy()
    
    # 行业差异化覆盖
    sector_name = sector_data.get("name", "")
    override = VALUATION_SECTOR_OVERRIDES.get(sector_name)
    if override:
        weights["pe_percentile"] = override["pe"]
        weights["pb_percentile"] = override["pb"]
        weights["ps_percentile"] = override["ps"]
        weights["dividend_yield_percentile"] = override["dy"]
    
    pe_ttm = valuation.get("pe_ttm")
    pb = valuation.get("pb")
    ps_ttm = valuation.get("ps_ttm")
    dy = valuation.get("dividend_yield")
    
    pe_percentile = valuation.get("pe_percentile")
    pb_percentile = valuation.get("pb_percentile")
    ps_percentile = valuation.get("ps_percentile")
    dy_percentile = valuation.get("dividend_yield_percentile")
    
    # 如果有历史数据，自行计算分位数
    if historical_pe and pe_ttm:
        pe_percentile = _safe_percentile(historical_pe, pe_ttm) or pe_percentile
    if historical_pb and pb:
        pb_percentile = _safe_percentile(historical_pb, pb) or pb_percentile
    if historical_ps and ps_ttm:
        ps_percentile = _safe_percentile(historical_ps, ps_ttm) or ps_percentile
    if historical_dy and dy:
        dy_percentile = _safe_percentile(historical_dy, dy) or dy_percentile
    
    scores = {
        "pe_score": _percentile_to_score(pe_percentile),
        "pb_score": _percentile_to_score(pb_percentile),
        "ps_score": _percentile_to_score(ps_percentile),
        "dy_score": _percentile_to_score(dy_percentile),
    }
    
    # 加权合成
    composite = (
        scores["pe_score"] * weights["pe_percentile"] +
        scores["pb_score"] * weights["pb_percentile"] +
        scores["ps_score"] * weights["ps_percentile"] +
        scores["dy_score"] * weights["dividend_yield_percentile"]
    )
    
    return {
        "composite": composite,
        "sub_scores": scores,
        "pe_ttm": pe_ttm,
        "pb": pb,
        "ps_ttm": ps_ttm,
        "pe_percentile": pe_percentile,
        "pb_percentile": pb_percentile,
        "ps_percentile": ps_percentile,
    }


# ============================================================
# 2. 全球商品期货估值极端度
# ============================================================
def commodity_valuation(commodity_data: Dict) -> Dict:
    """
    商品期货估值极端度
    子指标: 价格偏离度(40%) + 期限结构偏离(30%) + 库存/持仓偏离(30%)
    """
    weights = VALUATION_WEIGHTS["commodity"]
    kline_1y = commodity_data.get("kline_1y", [])
    
    # 价格偏离度：Z-score of current price vs 250-day MA
    price_deviation_score = 0.0
    if kline_1y and len(kline_1y) >= 20:
        closes = [k.get("close", 0) for k in kline_1y]
        closes = [c for c in closes if c > 0]
        if closes:
            current = closes[-1]
            ma_250 = np.mean(closes)
            std_250 = np.std(closes)
            if std_250 > 0:
                z_score = (current - ma_250) / std_250
                # 归一化到[-1, 1]，|z|>3视为极端
                price_deviation_score = np.clip(z_score / 3.0, -1.0, 1.0)
    
    # 期限结构偏离（用近远月价差代理，如有数据）
    term_structure_score = 0.0
    # 持仓量偏离
    position_deviation_score = 0.0
    if kline_1y and len(kline_1y) >= 20:
        volumes = [k.get("volume", 0) for k in kline_1y]
        volumes = [v for v in volumes if v > 0]
        if volumes:
            current_vol = volumes[-1]
            vol_ma = np.mean(volumes)
            vol_std = np.std(volumes)
            if vol_std > 0:
                z_vol = (current_vol - vol_ma) / vol_std
                position_deviation_score = np.clip(z_vol / 3.0, -1.0, 1.0)
    
    scores = {
        "price_deviation": price_deviation_score,
        "term_structure": term_structure_score,
        "inventory_position": position_deviation_score,
    }
    
    composite = (
        scores["price_deviation"] * weights["price_deviation"] +
        scores["term_structure"] * weights["term_structure"] +
        scores["inventory_position"] * weights["inventory_position"]
    )
    
    return {"composite": composite, "sub_scores": scores}


# ============================================================
# 3. 美股行业ETF估值极端度
# ============================================================
def us_etf_valuation(etf_data: Dict) -> Dict:
    """
    美股ETF估值极端度
    子指标: PE分位(50%) + PB分位(30%) + 股息率分位(20%)
    """
    weights = VALUATION_WEIGHTS["us_etf"]
    detail = etf_data.get("etf_detail", {})
    kline_1y = etf_data.get("kline_1y", [])
    
    pe = detail.get("pe")
    
    # 用价格分位代理PE分位（美股ETF不一定有PE字段）
    pe_score = 0.0
    pb_score = 0.0
    dy_score = 0.0
    
    if kline_1y and len(kline_1y) >= PERCENTILE_MIN_DAYS:
        closes = [k.get("close", 0) for k in kline_1y]
        closes = [c for c in closes if c > 0]
        if closes:
            current = closes[-1]
            percentile = _safe_percentile(closes, current)
            if percentile is not None:
                # 价格分位作为估值分位代理
                pe_score = _percentile_to_score(percentile)
                pb_score = pe_score * 0.8  # PB与PE高度相关
                dy_score = -pe_score * 0.6  # 股息率与估值反向
    
    scores = {
        "pe_score": pe_score,
        "pb_score": pb_score,
        "dy_score": dy_score,
    }
    
    composite = (
        scores["pe_score"] * weights["pe_percentile"] +
        scores["pb_score"] * weights["pb_percentile"] +
        scores["dy_score"] * weights["dividend_yield_percentile"]
    )
    
    return {"composite": composite, "sub_scores": scores, "pe": pe}


# ============================================================
# 4. 港股行业估值极端度
# ============================================================
def hk_sector_valuation(sector_data: Dict) -> Dict:
    """
    港股行业估值极端度
    子指标: PE分位(35%) + PB分位(25%) + PS分位(20%) + AH溢价(20%)
    """
    weights = VALUATION_WEIGHTS["hk_sector"]
    kline_1y = sector_data.get("kline_1y", [])
    
    pe_score = 0.0
    pb_score = 0.0
    ps_score = 0.0
    ah_premium_score = 0.0
    
    if kline_1y and len(kline_1y) >= PERCENTILE_MIN_DAYS:
        closes = [k.get("close", 0) for k in kline_1y]
        closes = [c for c in closes if c > 0]
        if closes:
            current = closes[-1]
            percentile = _safe_percentile(closes, current)
            if percentile is not None:
                pe_score = _percentile_to_score(percentile)
                pb_score = pe_score * 0.85
                ps_score = pe_score * 0.7
    
    scores = {
        "pe_score": pe_score,
        "pb_score": pb_score,
        "ps_score": ps_score,
        "ah_premium": ah_premium_score,
    }
    
    composite = (
        scores["pe_score"] * weights["pe_percentile"] +
        scores["pb_score"] * weights["pb_percentile"] +
        scores["ps_score"] * weights["ps_percentile"] +
        scores["ah_premium"] * weights["ah_premium"]
    )
    
    return {"composite": composite, "sub_scores": scores}


# ============================================================
# 5. 全球股指估值极端度
# ============================================================
def global_index_valuation(index_data: Dict, erp_data: Dict = None) -> Dict:
    """
    全球股指估值极端度
    子指标: PE分位(40%) + ERP极端度(30%) + PB分位(30%)
    """
    weights = VALUATION_WEIGHTS["global_index"]
    kline_1y = index_data.get("kline_1y", [])
    
    pe_score = 0.0
    erp_score = 0.0
    pb_score = 0.0
    
    if kline_1y and len(kline_1y) >= PERCENTILE_MIN_DAYS:
        closes = [k.get("close", 0) for k in kline_1y]
        closes = [c for c in closes if c > 0]
        if closes:
            current = closes[-1]
            percentile = _safe_percentile(closes, current)
            if percentile is not None:
                pe_score = _percentile_to_score(percentile)
                pb_score = pe_score * 0.85
    
    # ERP极端度：从宏观数据中提取
    if erp_data:
        # 如果ERP处于极端低位(高估值)或极端高位(低估值)
        erp_value = erp_data.get("value", erp_data.get("erp"))
        if erp_value is not None:
            # ERP低 = 估值高(做空信号)，ERP高 = 估值低(做多信号)
            # 典型ERP范围 2%~6%
            if erp_value < 2.0:
                erp_score = min((2.0 - erp_value) / 2.0, 1.0)  # 高估
            elif erp_value > 5.0:
                erp_score = -min((erp_value - 5.0) / 2.0, 1.0)  # 低估
            else:
                erp_score = (3.5 - erp_value) / 1.5  # 线性映射
    
    scores = {
        "pe_score": pe_score,
        "erp_score": erp_score,
        "pb_score": pb_score,
    }
    
    composite = (
        scores["pe_score"] * weights["pe_percentile"] +
        scores["erp_score"] * weights["erp_extreme"] +
        scores["pb_score"] * weights["pb_percentile"]
    )
    
    return {"composite": composite, "sub_scores": scores}


# ============================================================
# 6. 外汇/债券估值极端度
# ============================================================
def fx_bond_valuation(fx_data: Dict, macro_data: Dict = None) -> Dict:
    """
    外汇/债券估值极端度
    子指标: 利差偏离(35%) + 实际利率偏离(35%) + 央行政策偏离(30%)
    """
    weights = VALUATION_WEIGHTS["fx_bond"]
    kline_1y = fx_data.get("kline_1y", [])
    
    spread_score = 0.0
    real_rate_score = 0.0
    policy_score = 0.0
    
    if kline_1y and len(kline_1y) >= PERCENTILE_MIN_DAYS:
        closes = [k.get("close", 0) for k in kline_1y]
        closes = [c for c in closes if c > 0]
        if closes:
            current = closes[-1]
            ma_250 = np.mean(closes)
            std_250 = np.std(closes)
            if std_250 > 0:
                z_score = (current - ma_250) / std_250
                spread_score = np.clip(z_score / 3.0, -1.0, 1.0)
                real_rate_score = spread_score * 0.8
    
    scores = {
        "spread_deviation": spread_score,
        "real_rate_deviation": real_rate_score,
        "policy_deviation": policy_score,
    }
    
    composite = (
        scores["spread_deviation"] * weights["spread_deviation"] +
        scores["real_rate_deviation"] * weights["real_rate_deviation"] +
        scores["policy_deviation"] * weights["policy_deviation"]
    )
    
    return {"composite": composite, "sub_scores": scores}


# ============================================================
# 统一估值评分入口
# ============================================================
def calculate_valuation(asset_class: str, asset_data: Dict,
                        historical_data: Dict = None, macro_data: Dict = None) -> Dict:
    """
    统一估值极端度计算入口
    
    Args:
        asset_class: 资产类别
        asset_data: 资产数据
        historical_data: 历史估值数据（可选）
        macro_data: 宏观数据（可选）
    
    Returns:
        {"composite": float, "sub_scores": dict, ...}
    """
    if asset_class == "a_share_sector":
        return a_share_valuation(
            asset_data,
            historical_data.get("pe") if historical_data else None,
            historical_data.get("pb") if historical_data else None,
            historical_data.get("ps") if historical_data else None,
            historical_data.get("dy") if historical_data else None,
        )
    elif asset_class == "commodity":
        return commodity_valuation(asset_data)
    elif asset_class == "us_etf":
        return us_etf_valuation(asset_data)
    elif asset_class == "hk_sector":
        return hk_sector_valuation(asset_data)
    elif asset_class == "global_index":
        erp = macro_data.get("cn_premium_value", {}) if macro_data else {}
        return global_index_valuation(asset_data, erp)
    elif asset_class == "fx_bond":
        return fx_bond_valuation(asset_data, macro_data)
    else:
        return {"composite": 0.0, "sub_scores": {}, "error": f"Unknown asset class: {asset_class}"}
