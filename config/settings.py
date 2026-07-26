"""
全球大类资产极端状态反转策略 — 全局配置
所有权重、阈值、信号等级均可在此调整
"""

from pathlib import Path
from datetime import time

# ============================================================
# 路径配置
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data_cache"
LOG_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"
TEMPLATE_DIR = OUTPUT_DIR / "templates"
DB_PATH = DATA_DIR / "signals.db"

# ============================================================
# 运行时间配置
# ============================================================
CLOSE_TIME = time(15, 30)  # 收盘后开始运行
DATA_COLLECTION_TIMEOUT = 1800  # 数据采集超时（秒）
EASTMONEY_QPS = 2  # 东财接口QPS限制
EASTMONEY_INTERVAL = 1.5  # 东财接口调用间隔（秒）

# ============================================================
# 分位数计算参数
# ============================================================
PERCENTILE_MIN_DAYS = 250  # 计算分位数最少需要的历史天数
LOOKBACK_1M = 22   # 1个月交易日
LOOKBACK_3M = 66   # 3个月交易日
LOOKBACK_1Y = 250  # 1年交易日
LOOKBACK_5Y = 1250 # 5年交易日

# ============================================================
# 资产类别权重分配矩阵
# 权重顺序: [估值, 动量, 情绪, 叙事资金]
# ============================================================
ASSET_WEIGHTS = {
    "a_share_sector": {  # A股行业板块
        "valuation": 0.30,
        "momentum": 0.20,
        "sentiment": 0.25,
        "narrative": 0.25,
    },
    "commodity": {  # 全球商品期货
        "valuation": 0.20,
        "momentum": 0.30,
        "sentiment": 0.20,
        "narrative": 0.30,
    },
    "us_etf": {  # 美股行业ETF
        "valuation": 0.30,
        "momentum": 0.20,
        "sentiment": 0.30,
        "narrative": 0.20,
    },
    "hk_sector": {  # 港股行业
        "valuation": 0.30,
        "momentum": 0.20,
        "sentiment": 0.25,
        "narrative": 0.25,
    },
    "global_index": {  # 全球股指
        "valuation": 0.35,
        "momentum": 0.15,
        "sentiment": 0.25,
        "narrative": 0.25,
    },
    "fx_bond": {  # 外汇/债券
        "valuation": 0.25,
        "momentum": 0.20,
        "sentiment": 0.15,
        "narrative": 0.40,
    },
}

# ============================================================
# 估值极端度子指标权重（按资产类别）
# ============================================================
VALUATION_WEIGHTS = {
    "a_share_sector": {
        "pe_percentile": 0.40,
        "pb_percentile": 0.30,
        "ps_percentile": 0.15,
        "dividend_yield_percentile": 0.15,
    },
    "commodity": {
        "price_deviation": 0.40,
        "term_structure": 0.30,
        "inventory_position": 0.30,
    },
    "us_etf": {
        "pe_percentile": 0.50,
        "pb_percentile": 0.30,
        "dividend_yield_percentile": 0.20,
    },
    "hk_sector": {
        "pe_percentile": 0.35,
        "pb_percentile": 0.25,
        "ps_percentile": 0.20,
        "ah_premium": 0.20,
    },
    "global_index": {
        "pe_percentile": 0.40,
        "erp_extreme": 0.30,
        "pb_percentile": 0.30,
    },
    "fx_bond": {
        "spread_deviation": 0.35,
        "real_rate_deviation": 0.35,
        "policy_deviation": 0.30,
    },
}

# ============================================================
# 动量极端度子指标权重（通用 + 各资产微调）
# ============================================================
MOMENTUM_WEIGHTS = {
    "default": {
        "return_3m": 0.35,
        "return_1m": 0.20,
        "volatility": 0.15,
        "volume_anomaly": 0.15,
        "rsi_extreme": 0.15,
    },
    "a_share_sector": {
        "return_3m": 0.30,
        "return_1m": 0.18,
        "volatility": 0.14,
        "volume_anomaly": 0.14,
        "rsi_extreme": 0.14,
        "breadth_extreme": 0.10,  # 涨跌比极端度（A股独有）
    },
}

# ============================================================
# 情绪极端度子指标权重（按资产类别）
# ============================================================
SENTIMENT_WEIGHTS = {
    "a_share_sector": {
        "turnover_rate": 0.25,
        "margin_ratio": 0.20,
        "north_flow_deviation": 0.20,
        "sector_heat": 0.15,
        "big_order_net": 0.20,
    },
    "commodity": {
        "oi_change": 0.30,
        "spec_net_position": 0.25,
        "volume_extreme": 0.25,
        "volatility_extreme": 0.20,
    },
    "us_etf": {
        "flow_deviation": 0.30,
        "put_call_ratio": 0.25,
        "vix_extreme": 0.25,
        "etf_premium": 0.20,
    },
    "hk_sector": {
        "south_flow_deviation": 0.30,
        "turnover_rate": 0.25,
        "short_ratio": 0.25,
        "ah_premium_sentiment": 0.20,
    },
    "global_index": {
        "vix_extreme": 0.35,
        "put_call_ratio": 0.25,
        "flow_deviation": 0.20,
        "breadth_extreme": 0.20,
    },
    "fx_bond": {
        "spec_position": 0.30,
        "implied_volatility": 0.30,
        "carry_crowdedness": 0.20,
        "cb_sentiment": 0.20,
    },
}

# ============================================================
# 叙事资金��端度子指标权重
# ============================================================
NARRATIVE_WEIGHTS = {
    "default": {
        "fund_flow_extreme": 0.40,
        "theme_heat": 0.30,
        "institution_attention": 0.30,
    },
    "commodity": {
        "oi_trend_extreme": 0.40,
        "volume_trend_extreme": 0.30,
        "fund_flow_extreme": 0.30,
    },
    "us_etf": {
        "etf_flow_extreme": 0.50,
        "short_ratio_trend": 0.30,
        "institution_position_change": 0.20,
    },
    "hk_sector": {
        "south_flow_extreme": 0.40,
        "short_trend_extreme": 0.30,
        "sector_flow_extreme": 0.30,
    },
    "global_index": {
        "global_flow_extreme": 0.40,
        "macro_surprise": 0.30,
        "cb_policy_deviation": 0.30,
    },
    "fx_bond": {
        "spread_trend_extreme": 0.40,
        "cb_policy_deviation": 0.30,
        "capital_flow_extreme": 0.30,
    },
}

# ============================================================
# 信号等级阈值
# ============================================================
SIGNAL_LEVELS = {
    "S_PLUS":  {"min": -1.00, "max": -0.75, "label": "S+ 强做多", "color": "#006400", "direction": "long", "position_multiplier": 1.5},
    "A_PLUS":  {"min": -0.75, "max": -0.50, "label": "A+ 做多",   "color": "#28A745", "direction": "long", "position_multiplier": 1.0},
    "B_PLUS":  {"min": -0.50, "max": -0.25, "label": "B+ 观察偏多","color": "#90EE90", "direction": "long", "position_multiplier": 0.5},
    "NEUTRAL": {"min": -0.25, "max":  0.25, "label": "N 中性",    "color": "#808080", "direction": None,  "position_multiplier": 0.0},
    "B_MINUS": {"min":  0.25, "max":  0.50, "label": "B- 观察偏空","color": "#FFB6C1", "direction": "short","position_multiplier": 0.5},
    "A_MINUS": {"min":  0.50, "max":  0.75, "label": "A- 做空",   "color": "#DC3545", "direction": "short","position_multiplier": 1.0},
    "S_MINUS": {"min":  0.75, "max":  1.00, "label": "S- 强做空",  "color": "#8B0000", "direction": "short","position_multiplier": 1.5},
}

# ============================================================
# 确认条件阈值
# ============================================================
CONFIRMATION = {
    "valuation_oversold": 0.15,   # 估值分位 < 15% 确认做多
    "valuation_overbought": 0.85, # 估值分位 > 85% 确认做空
    "rsi_divergence_lookback": 10, # RSI背离检测回溯天数
    "volume_price_divergence_days": 3, # 量价背离检测天数
    "sentiment_cooling_threshold": 0.05, # 情绪回落阈值
}

# ============================================================
# 信号时效
# ============================================================
SIGNAL_VALIDITY_DAYS = 5  # 信号有效期（交易日）

# ============================================================
# 仓位管理参数
# ============================================================
POSITION = {
    "base_position_pct": 0.05,      # 基准仓位5%
    "max_total_position_normal": 0.80,  # 正常市场总仓位上限
    "max_total_position_high_vol": 0.60, # 高波动总仓位上限 (VIX>30)
    "max_total_position_extreme": 0.40,  # 极端波动总仓位上限 (VIX>40)
    "max_single_asset_normal": 0.10,     # 单资产上限
    "max_single_asset_high_vol": 0.05,
    "max_single_asset_extreme": 0.03,
    "max_same_direction_normal": 0.30,   # 同向资产上限
    "max_same_direction_high_vol": 0.20,
    "max_same_direction_extreme": 0.15,
    "short_position_discount": 0.70,     # 做空仓位折减系数
    "max_short_holding_weeks": 8,        # 做空最长持仓周数
    "volatility_cap": 0.20,              # 年化波动率基准
    "min_daily_amount": 100_000_000,     # 最小日均成交额(1亿)
    "min_daily_amount_critical": 50_000_000, # 临界成交额(5000万)
    "liquidity_discount_low": 0.50,      # 低流动性折减
    "liquidity_discount_critical": 0.30, # 临界流动性折减
}

# ============================================================
# 止损止盈参数
# ============================================================
RISK = {
    "hard_stop_loss_pct": 0.02,      # 硬止损：单笔亏损>总资产2%
    "time_stop_weeks": 12,           # 时间止损：12周
    "signal_stop_threshold": 0.25,   # 信号止损：评分回到中性区间
    "volatility_double_stop": True,  # 波动率翻倍止损
    "correlation_stop_drop": 0.30,   # 相关性下降>0.3止损
    "take_profit_valuation_min": 0.30, # 估值回归止盈：分位回到30%
    "take_profit_valuation_max": 0.70, # 估值回归止盈：分位回到70%
    "take_profit_rsi_neutral": 50,   # RSI回到50止盈
    "take_profit_long_return": 0.15, # 做多目标收益15%
    "take_profit_short_return": 0.10,# 做空目标收益10%
    "take_profit_first_batch": 0.50, # 首批止盈比例
    "take_profit_second_batch": 0.50,# 第二批止盈比例
}

# ============================================================
# PE/PB/RSI正常区间参考（各行业板块）
# 格式: [PE下限, PE上限, PB下限, PB上限]
# 数据来源：申万行业指数历史均值 ±1σ
# ============================================================
NORMAL_RANGES = {
    "银行":       {"pe": [5, 8], "pb": [0.5, 1.5], "dividend": 4.5, "note": "低估值蓝筹"},
    "医药生物":   {"pe": [25, 40], "pb": [3, 8], "dividend": 1.5, "note": "高成长防御"},
    "半导体":       {"pe": [30, 60], "ps": [4, 10], "pb": [4, 10], "dividend": 0.8, "note": "周期成长"},
    "食品饮料":   {"pe": [25, 45], "pb": [5, 12], "dividend": 2.5, "note": "消费龙头"},
    "新能源":     {"pe": [20, 40], "ps": [2, 6], "pb": [2, 6], "dividend": 1.0, "note": "成长赛道"},
    "光伏":       {"pe": [20, 40], "ps": [2, 6], "pb": [2, 6], "dividend": 1.0, "note": "成长赛道"},
    "军工":       {"pe": [40, 80], "pb": [2, 5], "dividend": 0.5, "note": "高波动主题"},
    "房地产":     {"pe": [6, 15], "pb": [0.6, 1.5], "dividend": 3.5, "note": "周期蓝筹"},
    "券商":       {"pe": [15, 30], "pb": [1, 2.5], "dividend": 2.0, "note": "高贝塔"},
    "煤炭":       {"pe": [6, 15], "pb": [0.8, 2.5], "dividend": 5.0, "note": "红利周期"},
    "有色金属":   {"pe": [15, 35], "pb": [1.5, 4], "dividend": 1.5, "note": "大宗周期"},
    "电力设备":   {"pe": [20, 40], "ps": [2, 5], "pb": [2, 5], "dividend": 1.2, "note": "高端制造"},
    "计算机":     {"pe": [35, 70], "ps": [3, 8], "pb": [3, 8], "dividend": 0.5, "note": "科技成长"},
    "通信":       {"pe": [20, 40], "ps": [2, 5], "pb": [2, 5], "dividend": 1.5, "note": "科技基建"},
    "电子":       {"pe": [30, 60], "ps": [3, 8], "pb": [3, 8], "dividend": 0.8, "note": "科技制造"},
    "汽车":       {"pe": [15, 30], "pb": [1.5, 4], "dividend": 2.0, "note": "可选消费"},
    "传媒":       {"pe": [20, 50], "ps": [2, 6], "pb": [2, 5], "dividend": 1.0, "note": "内容产业"},
    "基础化工":   {"pe": [15, 35], "pb": [1.5, 4], "dividend": 2.0, "note": "周期材料"},
    "钢铁":       {"pe": [8, 20], "pb": [0.6, 1.5], "dividend": 3.0, "note": "周期材料"},
    "建筑材料":   {"pe": [10, 25], "pb": [1, 3], "dividend": 2.5, "note": "基建周期"},
    "公用事业":   {"pe": [15, 30], "pb": [1.5, 3], "dividend": 3.0, "note": "防御红利"},
    "default":    {"pe": [15, 35], "pb": [1.5, 5], "dividend": 2.0, "note": ""},
}

# ============================================================
# ERP(股债性价比)正常区间
# ERP = 1/PE - 10年期国债收益率
# ============================================================
ERP_RANGE = {
    "normal_min": 2.0,
    "normal_max": 5.0,
    "overvalued": 2.0,
    "undervalued": 5.0,
    "extreme_high": 6.0,
    "extreme_low": 1.0,
}
# ============================================================
# RSI参考区间
# ============================================================
RSI_RANGE = {
    "oversold": 30,
    "overbought": 70,
}

# ============================================================
# 各行业核心估值指标（主估值指标映射）
# ============================================================
PRIMARY_VALUATION = {
    "银行": "pb",
    "券商": "pb",
    "保险": "pb",
    "房地产": "pb",
    "钢铁": "pb",
    "煤炭": "pb",
    "半导体": "ps",
    "计算机": "ps",
    "电子": "ps",
    "通信": "ps",
    "传媒": "ps",
    "公用事业": "dividend_yield",
    "建筑材料": "pe",
    "医药生物": "pe",
    "食品饮料": "pe",
    "新能源": "pe",
    "光伏": "pe",
    "军工": "pe",
    "有色金属": "pe",
    "电力设备": "pe",
    "汽车": "pe",
    "基础化工": "pe",
    "commodity": "price_deviation",
    "fx_bond": "spread",
    "global_index": "pe",
    "us_etf": "pe",
    "hk_sector": "pe",
}

# ============================================================
# A股行业差异化估值权重覆盖
# ============================================================
VALUATION_SECTOR_OVERRIDES = {
    "银行":       {"pe": 0.10, "pb": 0.50, "ps": 0.10, "dy": 0.30},
    "券商":       {"pe": 0.10, "pb": 0.55, "ps": 0.15, "dy": 0.20},
    "保险":       {"pe": 0.10, "pb": 0.55, "ps": 0.10, "dy": 0.25},
    "房地产":     {"pe": 0.10, "pb": 0.50, "ps": 0.15, "dy": 0.25},
    "钢铁":       {"pe": 0.15, "pb": 0.50, "ps": 0.15, "dy": 0.20},
    "煤炭":       {"pe": 0.15, "pb": 0.40, "ps": 0.15, "dy": 0.30},
    "半导体":     {"pe": 0.15, "pb": 0.20, "ps": 0.50, "dy": 0.15},
    "计算机":     {"pe": 0.20, "pb": 0.20, "ps": 0.45, "dy": 0.15},
    "电子":       {"pe": 0.20, "pb": 0.20, "ps": 0.45, "dy": 0.15},
    "通信":       {"pe": 0.20, "pb": 0.25, "ps": 0.40, "dy": 0.15},
    "传媒":       {"pe": 0.25, "pb": 0.20, "ps": 0.40, "dy": 0.15},
    "军工":       {"pe": 0.35, "pb": 0.25, "ps": 0.25, "dy": 0.15},
    "公用事业":   {"pe": 0.20, "pb": 0.25, "ps": 0.15, "dy": 0.40},
    "有色金属":   {"pe": 0.30, "pb": 0.35, "ps": 0.20, "dy": 0.15},
    "食品饮料":   {"pe": 0.40, "pb": 0.30, "ps": 0.15, "dy": 0.15},
    "医药生物":   {"pe": 0.35, "pb": 0.30, "ps": 0.20, "dy": 0.15},
    "新能源":     {"pe": 0.30, "pb": 0.25, "ps": 0.30, "dy": 0.15},
    "电力设备":   {"pe": 0.30, "pb": 0.25, "ps": 0.30, "dy": 0.15},
    "汽车":       {"pe": 0.35, "pb": 0.30, "ps": 0.20, "dy": 0.15},
    "基础化工":   {"pe": 0.30, "pb": 0.35, "ps": 0.20, "dy": 0.15},
    "建筑材料":   {"pe": 0.30, "pb": 0.35, "ps": 0.20, "dy": 0.15},
}

# ============================================================
# 波动率阈值
# ============================================================
VOLATILITY = {
    "normal_max": 25,
    "high_min": 25,
    "high_max": 40,
    "extreme_min": 40,
}

# ============================================================
# 日志配置
# ============================================================
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "daily_run_log": LOG_DIR / "daily_run.log",
    "signal_log": LOG_DIR / "signals.log",
    "trade_log": LOG_DIR / "trades.log",
    "error_log": LOG_DIR / "errors.log",
}
