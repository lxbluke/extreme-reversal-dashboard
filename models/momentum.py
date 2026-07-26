"""
动量极端度计算模型
计算价格动量的极端程度（归一化到[-1, 1]）
正值 = 过度上涨（做空信号），负值 = 过度下跌（做多信号）
"""

import numpy as np
from typing import Dict, List, Optional
from config.settings import MOMENTUM_WEIGHTS


def _safe_z_score(current: float, historical: List[float]) -> float:
    """安全计算Z-score"""
    if not historical or len(historical) < 5:
        return 0.0
    arr = np.array([v for v in historical if v is not None and not np.isnan(v)])
    if len(arr) < 5:
        return 0.0
    mean = np.mean(arr)
    std = np.std(arr)
    if std == 0:
        return 0.0
    return (current - mean) / std


def _return_extreme_score(return_val: float, benchmark: float = 50.0) -> float:
    """
    涨跌幅极端度评分
    涨跌幅绝对值 / benchmark，封顶1.0
    正值 = 暴涨（高估），负值 = 暴跌（低估）
    """
    if return_val is None:
        return 0.0
    direction = 1.0 if return_val > 0 else -1.0
    extreme = min(abs(return_val) / benchmark, 1.0)
    return direction * extreme


def _rsi_extreme_score(rsi: float) -> float:
    """
    RSI极端度评分
    RSI > 70 → 正分(超买/做空)，RSI < 30 → 负分(超卖/做多)
    """
    if rsi is None:
        return 0.0
    # |RSI - 50| / 50 → 0~1
    extreme = abs(rsi - 50) / 50
    direction = 1.0 if rsi > 50 else -1.0
    return direction * min(extreme, 1.0)


def calculate_momentum(asset_class: str, asset_data: Dict) -> Dict:
    """
    统一动量极端度计算入口
    
    通用子指标:
    - 3月涨跌幅极端度 (35%)
    - 1月涨跌幅极端度 (20%)
    - 波动率极端度 (15%)
    - 成交量异常度 (15%)
    - RSI极端度 (15%)
    - 涨跌比极端度 (10%, A股独有)
    """
    weights = MOMENTUM_WEIGHTS.get(asset_class, MOMENTUM_WEIGHTS["default"])
    kline_1y = asset_data.get("kline_1y", [])
    kline_3m = asset_data.get("kline_3m", [])
    technical = asset_data.get("technical_rsi", {})
    
    # 提取价格序列
    def get_closes(klines):
        return [k.get("close", 0) for k in klines if k.get("close", 0) > 0]
    
    def get_volumes(klines):
        return [k.get("volume", 0) for k in klines if k.get("volume", 0) > 0]
    
    # 3月涨跌幅
    closes = get_closes(kline_1y) if kline_1y else get_closes(kline_3m)
    return_3m = 0.0
    return_1m = 0.0
    volatility_score = 0.0
    volume_anomaly_score = 0.0
    rsi_score = 0.0
    breadth_score = 0.0
    
    if closes and len(closes) >= 66:
        # 3月涨跌幅
        return_3m = (closes[-1] - closes[-min(66, len(closes))]) / closes[-min(66, len(closes))] * 100
        # 1月涨跌幅
        return_1m = (closes[-1] - closes[-min(22, len(closes))]) / closes[-min(22, len(closes))] * 100
    
    # 波动率极端度：20日波动率 vs 250日波动率
    if closes and len(closes) >= 22:
        returns = np.diff(closes[-22:]) / closes[-22:-1]
        vol_20d = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0
        if len(closes) >= 250:
            returns_250 = np.diff(closes[-250:]) / closes[-250:-1]
            vol_250d = np.std(returns_250) * np.sqrt(252) if len(returns_250) > 0 else 0
            if vol_250d > 0:
                vol_ratio = vol_20d / vol_250d
                # 波动率放大=极端，方向由涨跌决定
                extreme = min(vol_ratio - 1.0, 1.0)  # 0~1
                direction = 1.0 if return_1m > 0 else -1.0
                volatility_score = direction * extreme
    
    # 成交量异常度
    volumes = get_volumes(kline_3m) if kline_3m else get_volumes(kline_1y)
    if volumes and len(volumes) >= 20:
        vol_5d = np.mean(volumes[-5:])
        vol_20d = np.mean(volumes[-20:])
        if vol_20d > 0:
            vol_ratio = vol_5d / vol_20d
            # 放量=极端，缩量=正常
            extreme = min(abs(vol_ratio - 1.0), 1.0)
            direction = 1.0 if (vol_ratio > 1.0 and return_1m > 0) else (-1.0 if (vol_ratio > 1.0 and return_1m < 0) else 0.0)
            volume_anomaly_score = direction * extreme
    
    # RSI极端度
    rsi_values = technical.get("values", [])
    if rsi_values:
        rsi = rsi_values[-1]
    else:
        # 自行计算RSI(14)
        if closes and len(closes) >= 15:
            deltas = np.diff(closes[-15:])
            gains = np.sum(deltas[deltas > 0]) if any(deltas > 0) else 0
            losses = -np.sum(deltas[deltas < 0]) if any(deltas < 0) else 0
            if losses == 0:
                rsi = 100.0 if gains > 0 else 50.0
            else:
                rs = gains / losses
                rsi = 100.0 - (100.0 / (1.0 + rs))
        else:
            rsi = 50.0
    rsi_score = _rsi_extreme_score(rsi)
    
    # A股独有：涨跌比极端度
    if asset_class == "a_share_sector" and "breadth_extreme" in weights:
        industry_comp = asset_data.get("_industry_comparison", [])
        if industry_comp:
            # 从行业对比数据中提取涨跌比
            up_count = sum(1 for item in industry_comp if item.get("change_pct", 0) > 0)
            down_count = sum(1 for item in industry_comp if item.get("change_pct", 0) < 0)
            total = up_count + down_count
            if total > 0:
                up_ratio = up_count / total
                # 极端上涨(>80%行业涨)或极端下跌(<20%行业涨)
                if up_ratio > 0.8:
                    breadth_score = (up_ratio - 0.8) / 0.2  # 0~1
                elif up_ratio < 0.2:
                    breadth_score = -(0.2 - up_ratio) / 0.2  # -1~0
                else:
                    breadth_score = 0.0
    
    scores = {
        "return_3m": _return_extreme_score(return_3m),
        "return_1m": _return_extreme_score(return_1m, 30.0),
        "volatility": volatility_score,
        "volume_anomaly": volume_anomaly_score,
        "rsi_extreme": rsi_score,
        "breadth_extreme": breadth_score,
    }
    
    # 加权合成
    composite = sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights)
    
    return {
        "composite": composite,
        "sub_scores": scores,
        "return_3m_pct": return_3m,
        "return_1m_pct": return_1m,
        "rsi_14": rsi,
    }
