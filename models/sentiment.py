"""
情绪极端度计算模型
使用客观数据指标替代主观打分（归一化到[-1, 1]）
正值 = 过度乐观（做空信号），负值 = 过度悲观（做多信号）
"""

import numpy as np
from typing import Dict, List, Optional
from config.settings import SENTIMENT_WEIGHTS


def _z_score_normalize(value: float, mean: float, std: float) -> float:
    """Z-score归一化到[-1, 1]"""
    if std == 0:
        return 0.0
    return np.clip((value - mean) / (std * 3), -1.0, 1.0)


def _extreme_from_percentile(percentile: float, reverse: bool = False) -> float:
    """
    分位数 → 极端度评分
    percentile: 0~1
    reverse: True表示高分位=悲观（如换手率低=无人关注=悲观）
    """
    if percentile is None:
        return 0.0
    if reverse:
        # 高分位→悲观(负)，低分位→乐观(正)
        return (0.5 - percentile) / 0.5
    else:
        # 高分位→乐观(正)，低分位→悲观(负)
        return (percentile - 0.5) / 0.5


def calculate_sentiment(asset_class: str, asset_data: Dict, market_overview: Dict = None) -> Dict:
    """
    统一情绪极端度计算入口
    """
    weights = SENTIMENT_WEIGHTS.get(asset_class, {})
    
    if asset_class == "a_share_sector":
        return _a_share_sentiment(asset_data, market_overview, weights)
    elif asset_class == "commodity":
        return _commodity_sentiment(asset_data, weights)
    elif asset_class == "us_etf":
        return _us_etf_sentiment(asset_data, weights)
    elif asset_class == "hk_sector":
        return _hk_sector_sentiment(asset_data, weights)
    elif asset_class == "global_index":
        return _global_index_sentiment(asset_data, market_overview, weights)
    elif asset_class == "fx_bond":
        return _fx_bond_sentiment(asset_data, weights)
    else:
        return {"composite": 0.0, "sub_scores": {}}


def _a_share_sentiment(sector_data: Dict, market_overview: Dict, weights: Dict) -> Dict:
    """
    A股行业情绪极端度
    换手率(25%) + 融资买入占比(20%) + 北向资金偏离(20%) + 行业热度(15%) + 大单净量(20%)
    """
    kline_3m = sector_data.get("kline_3m", [])
    fund_flow = sector_data.get("fund_flow", {})
    north_holding = sector_data.get("north_holding", {})
    
    # 换手率极端度
    turnover_score = 0.0
    if kline_3m and len(kline_3m) >= 20:
        volumes = [k.get("volume", 0) for k in kline_3m]
        if volumes:
            current_vol = volumes[-1]
            vol_mean = np.mean(volumes)
            vol_std = np.std(volumes)
            if vol_std > 0:
                z = (current_vol - vol_mean) / vol_std
                turnover_score = np.clip(z / 3.0, -1.0, 1.0)
    
    # 融资买入占比（用成交量放大代理）
    margin_score = 0.0
    if kline_3m and len(kline_3m) >= 20:
        margin_score = turnover_score * 0.7  # 融资与换手率正相关
    
    # 北向资金偏离
    north_flow_score = 0.0
    north_flow_val = north_holding.get("holding_value")
    if north_flow_val and north_flow_val > 0:
        # 北向持仓增加=乐观，减少=悲观
        north_flow_score = 0.0  # 需要历史对比
    
    # 行业热度：从排名数据中提取
    sector_heat_score = 0.0
    ranking = sector_data.get("_ranking", [])
    if ranking:
        # 该行业在排名中的位置
        for i, item in enumerate(ranking):
            if item.get("code") == sector_data.get("pt_code"):
                # 排名靠前=热度高
                rank_pct = i / max(len(ranking), 1)
                sector_heat_score = (0.5 - rank_pct) / 0.5  # 排名靠前=正值
                break
    
    # 大单净量
    big_order_score = 0.0
    main_flow = fund_flow.get("main_flow") or fund_flow.get("net_flow")
    if main_flow is not None and main_flow != 0:
        big_order_score = np.clip(main_flow / 1e8, -1.0, 1.0)  # 以亿为单位
    
    scores = {
        "turnover_rate": turnover_score,
        "margin_ratio": margin_score,
        "north_flow_deviation": north_flow_score,
        "sector_heat": sector_heat_score,
        "big_order_net": big_order_score,
    }
    
    composite = sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights)
    return {"composite": composite, "sub_scores": scores}


def _commodity_sentiment(commodity_data: Dict, weights: Dict) -> Dict:
    """商品期货情绪极端度"""
    kline_1y = commodity_data.get("kline_1y", [])
    
    oi_change_score = 0.0
    spec_score = 0.0
    vol_extreme_score = 0.0
    vol_score = 0.0
    
    if kline_1y and len(kline_1y) >= 20:
        closes = [k.get("close", 0) for k in kline_1y if k.get("close", 0) > 0]
        volumes = [k.get("volume", 0) for k in kline_1y if k.get("volume", 0) > 0]
        
        if closes:
            returns = np.diff(closes[-20:]) / closes[-20:-1]
            vol_20d = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0
            if vol_20d > 0:
                # 高波动=情绪极端
                vol_score = min(vol_20d / 0.5, 1.0)  # 50%年化波动率=极端
        
        if volumes:
            current_vol = volumes[-1]
            vol_mean = np.mean(volumes)
            vol_std = np.std(volumes)
            if vol_std > 0:
                z = (current_vol - vol_mean) / vol_std
                vol_extreme_score = np.clip(z / 3.0, -1.0, 1.0)
                oi_change_score = vol_extreme_score * 0.8
    
    scores = {
        "oi_change": oi_change_score,
        "spec_net_position": spec_score,
        "volume_extreme": vol_extreme_score,
        "volatility_extreme": vol_score,
    }
    
    composite = sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights)
    return {"composite": composite, "sub_scores": scores}


def _us_etf_sentiment(etf_data: Dict, weights: Dict) -> Dict:
    """美股ETF情绪极端度"""
    kline_1y = etf_data.get("kline_1y", [])
    
    flow_score = 0.0
    put_call_score = 0.0
    vix_score = 0.0
    premium_score = 0.0
    
    if kline_1y and len(kline_1y) >= 20:
        closes = [k.get("close", 0) for k in kline_1y if k.get("close", 0) > 0]
        volumes = [k.get("volume", 0) for k in kline_1y if k.get("volume", 0) > 0]
        
        if closes and volumes:
            # 价量关系：价升量增=乐观，价跌量增=悲观
            price_change = (closes[-1] - closes[-20]) / closes[-20] if closes[-20] > 0 else 0
            vol_change = (volumes[-1] - np.mean(volumes[-20:])) / np.mean(volumes[-20:]) if np.mean(volumes[-20:]) > 0 else 0
            flow_score = np.clip(price_change * 5 + vol_change, -1.0, 1.0)
            
            # 用价格波动率代理VIX极端度
            returns = np.diff(closes[-20:]) / closes[-20:-1]
            vol = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0
            vix_score = min(vol / 0.4, 1.0)  # 40%年化=极端
    
    scores = {
        "flow_deviation": flow_score,
        "put_call_ratio": put_call_score,
        "vix_extreme": vix_score,
        "etf_premium": premium_score,
    }
    
    composite = sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights)
    return {"composite": composite, "sub_scores": scores}


def _hk_sector_sentiment(sector_data: Dict, weights: Dict) -> Dict:
    """港股行业情绪极端度"""
    kline_1y = sector_data.get("kline_1y", [])
    short_data = sector_data.get("short_data", {})
    
    south_score = 0.0
    turnover_score = 0.0
    short_score = 0.0
    ah_score = 0.0
    
    if kline_1y and len(kline_1y) >= 20:
        volumes = [k.get("volume", 0) for k in kline_1y if k.get("volume", 0) > 0]
        if volumes:
            current = volumes[-1]
            mean_v = np.mean(volumes)
            std_v = np.std(volumes)
            if std_v > 0:
                z = (current - mean_v) / std_v
                turnover_score = np.clip(z / 3.0, -1.0, 1.0)
    
    # 卖空比例
    short_ratio = short_data.get("short_ratio")
    if short_ratio is not None:
        # 卖空比例>20%=极端悲观(负)，<5%=极端乐观(正)
        if short_ratio > 20:
            short_score = -min((short_ratio - 20) / 20, 1.0)
        elif short_ratio < 5:
            short_score = min((5 - short_ratio) / 5, 1.0)
    
    scores = {
        "south_flow_deviation": south_score,
        "turnover_rate": turnover_score,
        "short_ratio": short_score,
        "ah_premium_sentiment": ah_score,
    }
    
    composite = sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights)
    return {"composite": composite, "sub_scores": scores}


def _global_index_sentiment(index_data: Dict, market_overview: Dict, weights: Dict) -> Dict:
    """全球股指情绪极端度"""
    kline_1y = index_data.get("kline_1y", [])
    
    vix_score = 0.0
    put_call_score = 0.0
    flow_score = 0.0
    breadth_score = 0.0
    
    if kline_1y and len(kline_1y) >= 20:
        closes = [k.get("close", 0) for k in kline_1y if k.get("close", 0) > 0]
        if closes:
            returns = np.diff(closes[-20:]) / closes[-20:-1]
            vol = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0
            vix_score = min(vol / 0.4, 1.0)
            
            # 短期涨跌幅方向
            ret_5d = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 and closes[-5] > 0 else 0
            flow_score = np.clip(ret_5d * 20, -1.0, 1.0)
    
    scores = {
        "vix_extreme": vix_score,
        "put_call_ratio": put_call_score,
        "flow_deviation": flow_score,
        "breadth_extreme": breadth_score,
    }
    
    composite = sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights)
    return {"composite": composite, "sub_scores": scores}


def _fx_bond_sentiment(fx_data: Dict, weights: Dict) -> Dict:
    """外汇/债券情绪极端度"""
    kline_1y = fx_data.get("kline_1y", [])
    
    spec_score = 0.0
    iv_score = 0.0
    carry_score = 0.0
    cb_score = 0.0
    
    if kline_1y and len(kline_1y) >= 20:
        closes = [k.get("close", 0) for k in kline_1y if k.get("close", 0) > 0]
        if closes:
            returns = np.diff(closes[-20:]) / closes[-20:-1]
            vol = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0
            iv_score = min(vol / 0.3, 1.0)
    
    scores = {
        "spec_position": spec_score,
        "implied_volatility": iv_score,
        "carry_crowdedness": carry_score,
        "cb_sentiment": cb_score,
    }
    
    composite = sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights)
    return {"composite": composite, "sub_scores": scores}
