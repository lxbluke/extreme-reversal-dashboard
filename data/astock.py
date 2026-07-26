"""
数据采集层 — a-stock-data Python库封装
封装 a-stock-data 的独有能力（东财接口需限流）
"""

import time
import random
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 东财接口限流参数
EASTMONEY_QPS = 2
EASTMONEY_INTERVAL = 1.5  # 秒
_last_call_time = 0


def _rate_limit():
    """东财接口限流：确保调用间隔 >= EASTMONEY_INTERVAL 秒"""
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < EASTMONEY_INTERVAL:
        sleep_time = EASTMONEY_INTERVAL - elapsed + random.uniform(0, 0.5)
        time.sleep(sleep_time)
    _last_call_time = time.time()


# ============================================================
# 1. 行业对比数据
# ============================================================
def get_industry_comparison() -> List[Dict]:
    """
    获取A股行业对比数据
    调用 a-stock-data: industry_comparison()
    返回 ~100个行业的涨跌幅、涨跌家数、领涨股
    """
    _rate_limit()
    try:
        from a_stock_data import industry_comparison
        result = industry_comparison()
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "data" in result:
            return result["data"]
        return []
    except ImportError:
        logger.warning("a_stock_data 未安装，跳过 industry_comparison")
        return []
    except Exception as e:
        logger.error(f"industry_comparison 调用失败: {e}")
        return []


# ============================================================
# 2. 强势股 + 题材归因（独家能力）
# ============================================================
def get_hot_reason() -> List[Dict]:
    """
    获取当日强势股 + 同花顺题材归因
    调用 a-stock-data: ths_hot_reason()
    这是最核心的叙事资金数据源：不仅知道"哪些走强"，还知道"为什么走强"
    """
    _rate_limit()
    try:
        from a_stock_data import ths_hot_reason
        result = ths_hot_reason()
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "data" in result:
            return result["data"]
        return []
    except ImportError:
        logger.warning("a_stock_data 未安装，跳过 ths_hot_reason")
        return []
    except Exception as e:
        logger.error(f"ths_hot_reason 调用失败: {e}")
        return []


def extract_theme_heat(hot_reasons: List[Dict]) -> Dict[str, int]:
    """
    从题材归因数据中提取各题材/行业的热度（出现频次）
    
    Returns:
        {"AI芯片": 15, "新能源": 8, ...}
    """
    theme_counts = {}
    for item in hot_reasons:
        reason = item.get("reason", "") or item.get("题材", "") or item.get("reason_tag", "")
        if reason:
            # 按逗号、分号、顿号分割多个题材标签
            themes = [t.strip() for t in reason.replace("、", ",").replace("；", ",").split(",")]
            for theme in themes:
                if theme:
                    theme_counts[theme] = theme_counts.get(theme, 0) + 1
    return theme_counts


# ============================================================
# 3. 北向资金实时流向（分钟级）
# ============================================================
def get_hsgt_realtime() -> Dict:
    """
    获取沪深港通实时资金流向
    调用 a-stock-data: hsgt_realtime()
    """
    _rate_limit()
    try:
        from a_stock_data import hsgt_realtime
        result = hsgt_realtime()
        if isinstance(result, dict):
            return result
        return {}
    except ImportError:
        logger.warning("a_stock_data 未安装，跳过 hsgt_realtime")
        return {}
    except Exception as e:
        logger.error(f"hsgt_realtime 调用失败: {e}")
        return {}


# ============================================================
# 4. 个股资金流向（120日）
# ============================================================
def get_stock_fund_flow_120d(code: str) -> List[Dict]:
    """
    获取个股120日资金流向
    调用 a-stock-data: stock_fund_flow_120d()
    """
    _rate_limit()
    try:
        from a_stock_data import stock_fund_flow_120d
        result = stock_fund_flow_120d(code)
        if isinstance(result, list):
            return result
        return []
    except ImportError:
        logger.warning("a_stock_data 未安装")
        return []
    except Exception as e:
        logger.error(f"stock_fund_flow_120d({code}) 失败: {e}")
        return []


# ============================================================
# 5. 融资融券
# ============================================================
def get_margin_trading(code: str = None) -> Dict:
    """
    获取融资融券数据
    调用 a-stock-data: margin_trading()
    """
    _rate_limit()
    try:
        from a_stock_data import margin_trading
        result = margin_trading(code) if code else margin_trading()
        if isinstance(result, dict):
            return result
        return {}
    except ImportError:
        logger.warning("a_stock_data 未安装")
        return {}
    except Exception as e:
        logger.error(f"margin_trading 调用失败: {e}")
        return {}


# ============================================================
# 6. 龙虎榜（全市场 + 个股席位）
# ============================================================
def get_daily_dragon_tiger() -> List[Dict]:
    """
    获取全市场龙虎榜数据
    调用 a-stock-data: daily_dragon_tiger()
    """
    _rate_limit()
    try:
        from a_stock_data import daily_dragon_tiger
        result = daily_dragon_tiger()
        if isinstance(result, list):
            return result
        return []
    except ImportError:
        logger.warning("a_stock_data 未安装")
        return []
    except Exception as e:
        logger.error(f"daily_dragon_tiger 调用失败: {e}")
        return []


def get_dragon_tiger_board(code: str) -> Dict:
    """
    获取个股龙虎榜席位明细
    调用 a-stock-data: dragon_tiger_board()
    """
    _rate_limit()
    try:
        from a_stock_data import dragon_tiger_board
        result = dragon_tiger_board(code)
        if isinstance(result, dict):
            return result
        return {}
    except ImportError:
        logger.warning("a_stock_data 未安装")
        return {}
    except Exception as e:
        logger.error(f"dragon_tiger_board({code}) 失败: {e}")
        return {}


# ============================================================
# 7. 限售解禁
# ============================================================
def get_lockup_expiry() -> List[Dict]:
    """获取限售解禁日历"""
    _rate_limit()
    try:
        from a_stock_data import lockup_expiry
        result = lockup_expiry()
        if isinstance(result, list):
            return result
        return []
    except ImportError:
        return []
    except Exception as e:
        logger.error(f"lockup_expiry 调用失败: {e}")
        return []


# ============================================================
# 8. 腾讯行情（实时PE/PB）
# ============================================================
def get_tencent_quote(code: str) -> Dict:
    """
    获取腾讯行情实时数据（含PE/PB）
    调用 a-stock-data: tencent_quote()
    """
    _rate_limit()
    try:
        from a_stock_data import tencent_quote
        result = tencent_quote(code)
        if isinstance(result, dict):
            return result
        return {}
    except ImportError:
        return {}
    except Exception as e:
        logger.error(f"tencent_quote({code}) 失败: {e}")
        return {}


# ============================================================
# 9. 概念板块
# ============================================================
def get_baidu_concept_blocks() -> Dict:
    """
    获取百度概念板块三维分类（行业/概念/地域）
    调用 a-stock-data: baidu_concept_blocks()
    """
    _rate_limit()
    try:
        from a_stock_data import baidu_concept_blocks
        result = baidu_concept_blocks()
        if isinstance(result, dict):
            return result
        return {}
    except ImportError:
        return {}
    except Exception as e:
        logger.error(f"baidu_concept_blocks 调用失败: {e}")
        return {}


# ============================================================
# 10. 全球财经快讯
# ============================================================
def get_global_news() -> List[Dict]:
    """获取东方财富全球财经快讯（7x24滚动）"""
    _rate_limit()
    try:
        from a_stock_data import eastmoney_global_news
        result = eastmoney_global_news()
        if isinstance(result, list):
            return result
        return []
    except ImportError:
        return []
    except Exception as e:
        logger.error(f"eastmoney_global_news 调用失败: {e}")
        return []
