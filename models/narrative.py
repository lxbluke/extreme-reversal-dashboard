"""
叙事资金极端度计算模型
结合"故事"和"资金"两个驱动因素（归一化到[-1, 1]）
正值 = 叙事过度乐观+资金涌入（做空信号），负值 = 叙事过度悲观+资金逃离（做多信号）
"""

import numpy as np
from typing import Dict, List, Optional
from config.settings import NARRATIVE_WEIGHTS


def _fund_flow_zscore(flow_data: Dict, historical_flows: List[float] = None) -> float:
    """资金流Z-score归一化"""
    net_flow = flow_data.get("net_flow") or flow_data.get("main_flow")
    if net_flow is None:
        return 0.0
    if historical_flows and len(historical_flows) > 5:
        mean = np.mean(historical_flows)
        std = np.std(historical_flows)
        if std > 0:
            z = (net_flow - mean) / std
            return np.clip(z / 3.0, -1.0, 1.0)
    # 无历史数据，用绝对值
    return np.clip(net_flow / 1e9, -1.0, 1.0)  # 10亿为单位


def calculate_narrative(asset_class: str, asset_data: Dict,
                        market_overview: Dict = None) -> Dict:
    """
    统一叙事资金极端度计算入口
    """
    weights = NARRATIVE_WEIGHTS.get(asset_class, NARRATIVE_WEIGHTS["default"])
    
    if asset_class == "a_share_sector":
        return _a_share_narrative(asset_data, market_overview, weights)
    elif asset_class == "commodity":
        return _commodity_narrative(asset_data, weights)
    elif asset_class == "us_etf":
        return _us_etf_narrative(asset_data, weights)
    elif asset_class == "hk_sector":
        return _hk_sector_narrative(asset_data, weights)
    elif asset_class == "global_index":
        return _global_index_narrative(asset_data, market_overview, weights)
    elif asset_class == "fx_bond":
        return _fx_bond_narrative(asset_data, weights)
    else:
        return {"composite": 0.0, "sub_scores": {}}


def _a_share_narrative(sector_data: Dict, market_overview: Dict, weights: Dict) -> Dict:
    """
    A股行业叙事资金极端度（数据最丰富）
    资金流极端度(40%) + 题材热度(30%) + 机构关注度(30%)
    """
    fund_flow = sector_data.get("fund_flow", {})
    sector_name = sector_data.get("name", "")
    kline_3m = sector_data.get("kline_3m", [])
    
    # 资金流极端度
    fund_flow_score = _fund_flow_zscore(fund_flow)
    
    # 题材热度：从同花顺强势股归因中提取
    theme_score = 0.0
    hot_reasons = market_overview.get("hot_reasons", []) if market_overview else []
    if hot_reasons:
        # 统计与该行业相关的题材出现频次
        related_count = 0
        total_count = len(hot_reasons)
        for item in hot_reasons:
            reason = str(item.get("reason", "") or item.get("题材", "") or item.get("reason_tag", ""))
            name = str(item.get("name", "") or item.get("stock_name", ""))
            # 简单匹配：题材标签包含行业关键词
            if sector_name in reason or sector_name in name:
                related_count += 1
        
        if total_count > 0:
            ratio = related_count / total_count
            # 超过30%的热点与该行业相关=极度热门
            theme_score = np.clip(ratio / 0.3 - 0.5, -1.0, 1.0)
    
    # 机构关注度：龙虎榜活跃度 + 成交量趋势
    institution_score = 0.0
    dragon_tiger = market_overview.get("dragon_tiger", []) if market_overview else []
    lhb_data = market_overview.get("lhb", []) if market_overview else []
    
    # 龙虎榜活跃度
    dt_total = len(dragon_tiger) + len(lhb_data)
    if dt_total > 0:
        # 活跃度高=关注度高
        dt_score = min(dt_total / 100, 1.0)  # 100+上榜=极端
        institution_score += dt_score * 0.5
    
    # 成交量趋势（放量=关注度提升）
    if kline_3m and len(kline_3m) >= 20:
        volumes = [k.get("volume", 0) for k in kline_3m if k.get("volume", 0) > 0]
        if volumes:
            vol_5d = np.mean(volumes[-5:])
            vol_20d = np.mean(volumes[-20:])
            if vol_20d > 0:
                vol_trend = (vol_5d / vol_20d - 1.0)
                institution_score += np.clip(vol_trend, -0.5, 0.5)
    
    scores = {
        "fund_flow_extreme": fund_flow_score,
        "theme_heat": theme_score,
        "institution_attention": institution_score,
    }
    
    composite = sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights)
    return {"composite": composite, "sub_scores": scores}


def _commodity_narrative(commodity_data: Dict, weights: Dict) -> Dict:
    """商品期货叙事资金极端度"""
    kline_1y = commodity_data.get("kline_1y", [])
    
    oi_trend_score = 0.0
    vol_trend_score = 0.0
    fund_score = 0.0
    
    if kline_1y and len(kline_1y) >= 20:
        volumes = [k.get("volume", 0) for k in kline_1y if k.get("volume", 0) > 0]
        closes = [k.get("close", 0) for k in kline_1y if k.get("close", 0) > 0]
        
        if volumes:
            vol_5d = np.mean(volumes[-5:])
            vol_20d = np.mean(volumes[-20:])
            if vol_20d > 0:
                vol_trend_score = np.clip((vol_5d / vol_20d - 1.0) * 3, -1.0, 1.0)
                oi_trend_score = vol_trend_score * 0.8
        
        if closes and len(closes) >= 5:
            ret_5d = (closes[-1] - closes[-5]) / closes[-5] if closes[-5] > 0 else 0
            fund_score = np.clip(ret_5d * 10, -1.0, 1.0)
    
    scores = {
        "oi_trend_extreme": oi_trend_score,
        "volume_trend_extreme": vol_trend_score,
        "fund_flow_extreme": fund_score,
    }
    
    composite = sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights)
    return {"composite": composite, "sub_scores": scores}


def _us_etf_narrative(etf_data: Dict, weights: Dict) -> Dict:
    """美股ETF叙事资金极端度"""
    kline_1y = etf_data.get("kline_1y", [])
    
    etf_flow_score = 0.0
    short_trend_score = 0.0
    inst_score = 0.0
    
    if kline_1y and len(kline_1y) >= 20:
        volumes = [k.get("volume", 0) for k in kline_1y if k.get("volume", 0) > 0]
        closes = [k.get("close", 0) for k in kline_1y if k.get("close", 0) > 0]
        
        if volumes and closes:
            vol_5d = np.mean(volumes[-5:])
            vol_20d = np.mean(volumes[-20:])
            ret_5d = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 and closes[-5] > 0 else 0
            
            if vol_20d > 0:
                flow_raw = (vol_5d / vol_20d - 1.0) * (1.0 if ret_5d > 0 else -1.0)
                etf_flow_score = np.clip(flow_raw * 2, -1.0, 1.0)
    
    scores = {
        "etf_flow_extreme": etf_flow_score,
        "short_ratio_trend": short_trend_score,
        "institution_position_change": inst_score,
    }
    
    composite = sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights)
    return {"composite": composite, "sub_scores": scores}


def _hk_sector_narrative(sector_data: Dict, weights: Dict) -> Dict:
    """港股行业叙事资金极端度"""
    kline_1y = sector_data.get("kline_1y", [])
    short_data = sector_data.get("short_data", {})
    
    south_score = 0.0
    short_trend_score = 0.0
    sector_flow_score = 0.0
    
    if kline_1y and len(kline_1y) >= 20:
        volumes = [k.get("volume", 0) for k in kline_1y if k.get("volume", 0) > 0]
        if volumes:
            vol_5d = np.mean(volumes[-5:])
            vol_20d = np.mean(volumes[-20:])
            if vol_20d > 0:
                sector_flow_score = np.clip((vol_5d / vol_20d - 1.0) * 2, -1.0, 1.0)
    
    short_ratio = short_data.get("short_ratio")
    if short_ratio is not None:
        # 卖空比例趋势：高卖空=悲观叙事
        short_trend_score = -np.clip(short_ratio / 25 - 0.5, -1.0, 1.0)
    
    scores = {
        "south_flow_extreme": south_score,
        "short_trend_extreme": short_trend_score,
        "sector_flow_extreme": sector_flow_score,
    }
    
    composite = sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights)
    return {"composite": composite, "sub_scores": scores}


def _global_index_narrative(index_data: Dict, market_overview: Dict, weights: Dict) -> Dict:
    """全球股指叙事资金极端度"""
    kline_1y = index_data.get("kline_1y", [])
    
    global_flow_score = 0.0
    macro_surprise_score = 0.0
    cb_deviation_score = 0.0
    
    if kline_1y and len(kline_1y) >= 20:
        closes = [k.get("close", 0) for k in kline_1y if k.get("close", 0) > 0]
        if closes:
            ret_20d = (closes[-1] - closes[-20]) / closes[-20] if closes[-20] > 0 else 0
            global_flow_score = np.clip(ret_20d * 5, -1.0, 1.0)
    
    scores = {
        "global_flow_extreme": global_flow_score,
        "macro_surprise": macro_surprise_score,
        "cb_policy_deviation": cb_deviation_score,
    }
    
    composite = sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights)
    return {"composite": composite, "sub_scores": scores}


def _fx_bond_narrative(fx_data: Dict, weights: Dict) -> Dict:
    """外汇/债券叙事资金极端度"""
    kline_1y = fx_data.get("kline_1y", [])
    
    spread_trend_score = 0.0
    cb_deviation_score = 0.0
    capital_flow_score = 0.0
    
    if kline_1y and len(kline_1y) >= 20:
        closes = [k.get("close", 0) for k in kline_1y if k.get("close", 0) > 0]
        if closes:
            ret_20d = (closes[-1] - closes[-20]) / closes[-20] if closes[-20] > 0 else 0
            spread_trend_score = np.clip(ret_20d * 5, -1.0, 1.0)
    
    scores = {
        "spread_trend_extreme": spread_trend_score,
        "cb_policy_deviation": cb_deviation_score,
        "capital_flow_extreme": capital_flow_score,
    }
    
    composite = sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights)
    return {"composite": composite, "sub_scores": scores}
