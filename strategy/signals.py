"""
信号生成与过滤模块
信号确认、去重、排序、有效期管理
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from config.settings import SIGNAL_LEVELS, SIGNAL_VALIDITY_DAYS
from models.composite import SignalResult

logger = logging.getLogger(__name__)


class SignalManager:
    """信号管理器：负责信号的确认、过滤、去重和生命周期管理"""
    
    def __init__(self, db=None):
        self.db = db  # SignalDatabase 实例
        self.active_signals: Dict[str, SignalResult] = {}  # 当前活跃信号
        self.signal_history: List[Dict] = []  # 信号变更历史
    
    def process_signals(self, signals: List[SignalResult],
                        previous_signals: List[Dict] = None) -> Dict:
        """
        处理新信号：对比历史信号，标记新增/升级/降级/失效
        
        Returns:
            {
                "new_signals": [...],       # 新出现的信号
                "upgraded": [...],          # 信号升级
                "downgraded": [...],        # 信号降级
                "expired": [...],           # 信号失效
                "unchanged": [...],         # 维持不变
                "trading_suggestions": [...],  # 调仓建议
            }
        """
        result = {
            "new_signals": [],
            "upgraded": [],
            "downgraded": [],
            "expired": [],
            "unchanged": [],
            "trading_suggestions": [],
            "all_active": [],
        }
        
        # 构建历史信号映射 (asset_name -> previous signal)
        prev_map = {}
        if previous_signals:
            for ps in previous_signals:
                name = ps.get("asset_name", "")
                if name:
                    prev_map[name] = ps
        
        # 当前信号名称集合
        current_names = set()
        
        for signal in signals:
            name = signal.asset_name
            current_names.add(name)
            
            if abs(signal.composite_score) < 0.25:
                # 中性信号，不处理
                continue
            
            if name not in prev_map:
                # 新信号
                signal.signal_change = "new"
                result["new_signals"].append(signal.to_dict())
                result["trading_suggestions"].append({
                    "action": "新开",
                    "asset": name,
                    "direction": signal.direction,
                    "score": signal.composite_score,
                    "position_pct": signal.position_pct,
                    "suggestion": signal.trade_suggestion,
                })
            else:
                prev = prev_map[name]
                prev_level = prev.get("signal_level", "NEUTRAL")
                current_level = signal.signal_level
                
                # 比较信号等级
                level_order = ["S_PLUS", "A_PLUS", "B_PLUS", "NEUTRAL", "B_MINUS", "A_MINUS", "S_MINUS"]
                prev_idx = level_order.index(prev_level) if prev_level in level_order else 3
                curr_idx = level_order.index(current_level) if current_level in level_order else 3
                
                # 方向是否一致
                prev_dir = prev.get("direction")
                curr_dir = signal.direction
                
                if abs(curr_idx - 3) > abs(prev_idx - 3):  # 偏离中性更多
                    signal.signal_change = "upgraded"
                    signal.previous_signal = prev_level
                    result["upgraded"].append(signal.to_dict())
                    
                    action = "加仓" if curr_dir == prev_dir else "转向"
                    result["trading_suggestions"].append({
                        "action": action,
                        "asset": name,
                        "direction": curr_dir,
                        "score": signal.composite_score,
                        "prev_score": prev.get("composite_score"),
                        "position_pct": signal.position_pct,
                        "suggestion": signal.trade_suggestion,
                    })
                elif abs(curr_idx - 3) < abs(prev_idx - 3):  # 更接近中性
                    signal.signal_change = "downgraded"
                    signal.previous_signal = prev_level
                    result["downgraded"].append(signal.to_dict())
                    
                    action = "减仓" if abs(signal.composite_score) > 0.25 else "平仓"
                    result["trading_suggestions"].append({
                        "action": action,
                        "asset": name,
                        "direction": curr_dir,
                        "score": signal.composite_score,
                        "prev_score": prev.get("composite_score"),
                        "position_pct": signal.position_pct if action == "减仓" else 0,
                        "suggestion": signal.trade_suggestion,
                    })
                else:
                    signal.signal_change = "unchanged"
                    signal.previous_signal = prev_level
                    result["unchanged"].append(signal.to_dict())
            
            result["all_active"].append(signal.to_dict())
        
        # 检查失效信号（历史有但当前没有）
        for name, prev in prev_map.items():
            if name not in current_names:
                prev_level = prev.get("signal_level", "NEUTRAL")
                if prev_level not in ("NEUTRAL",):
                    result["expired"].append({
                        "asset": name,
                        "prev_signal": prev_level,
                        "prev_score": prev.get("composite_score"),
                        "reason": "评分回到中性区间",
                    })
                    result["trading_suggestions"].append({
                        "action": "平仓",
                        "asset": name,
                        "direction": prev.get("direction"),
                        "score": 0,
                        "position_pct": 0,
                        "suggestion": f"{name}信号已失效，建议平仓",
                    })
        
        return result
    
    def filter_by_confirmations(self, signals: List[SignalResult],
                                min_confirmations: int = 1) -> List[SignalResult]:
        """
        按确认条件过滤信号
        至少满足 min_confirmations 个确认条件才保留
        """
        if min_confirmations <= 0:
            return signals
        
        filtered = []
        for s in signals:
            if abs(s.composite_score) < 0.5:
                # A级及以上才需要确认条件
                filtered.append(s)
            elif s.confirmation_count >= min_confirmations:
                filtered.append(s)
            else:
                logger.info(f"信号过滤: {s.asset_name} 评分{s.composite_score:.2f} "
                           f"但确认条件不足({s.confirmation_count}/{min_confirmations})，降级处理")
                # 降级为B级
                s.signal_level = "B_PLUS" if s.composite_score < 0 else "B_MINUS"
                s.signal_label = SIGNAL_LEVELS[s.signal_level]["label"]
                s.position_multiplier = SIGNAL_LEVELS[s.signal_level]["position_multiplier"]
                s.color = SIGNAL_LEVELS[s.signal_level]["color"]
                filtered.append(s)
        
        return filtered
    
    def check_signal_validity(self, signal_date: str) -> bool:
        """检查信号是否在有效期内"""
        try:
            signal_dt = datetime.strptime(signal_date, "%Y-%m-%d")
            expiry = signal_dt + timedelta(days=SIGNAL_VALIDITY_DAYS)
            return datetime.now() <= expiry
        except ValueError:
            return True
    
    def deduplicate(self, signals: List[SignalResult]) -> List[SignalResult]:
        """去重：同一资产保留最新/最强信号"""
        seen = {}
        for s in signals:
            key = s.asset_name
            if key not in seen or abs(s.composite_score) > abs(seen[key].composite_score):
                seen[key] = s
        return list(seen.values())
