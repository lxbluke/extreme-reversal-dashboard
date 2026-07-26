#!/usr/bin/env python3
"""
全球大类资产极端状态反转策略 — 每日主流程
每日收盘后自动运行：数据采集 → 评分计算 → 信号生成 → 输出生成

用法:
    python scripts/daily_run.py                    # 完整运行（所有资产）
    python scripts/daily_run.py --quick            # 快速模式（仅A股+宏观）
    python scripts/daily_run.py --mock             # Mock模式（使用模拟数据测试）
"""

import sys
import os
import logging
import argparse
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import LOG_CONFIG, OUTPUT_DIR, LOG_DIR, DATA_DIR, DB_PATH
GITHUB_PAGES_URL = "https://lxbluke.github.io/extreme-reversal-dashboard/"
from data.collector import DataCollector, quick_collect_a_share
from data.database import SignalDatabase
from models.composite import BatchScorer, generate_signal_summary, get_extreme_signals
from strategy.signals import SignalManager
from strategy.position import PositionManager
from strategy.risk import RiskManager
from output.report import generate_daily_report
from output.dashboard import save_dashboard


def setup_logging():
    """配置日志系统"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, LOG_CONFIG["level"]),
        format=LOG_CONFIG["format"],
        datefmt=LOG_CONFIG["date_format"],
        handlers=[
            logging.FileHandler(LOG_CONFIG["daily_run_log"], encoding="utf-8"),
            logging.StreamHandler(),
        ]
    )


def generate_mock_data() -> dict:
    """生成模拟数据用于测试，包含完整trade_tool映射"""
    import random
    random.seed(42)
    
    from config.symbols import get_trade_tool
    
    # (name, cls, code, score) 元组
    mock_assets = [
        ("银行", "a_share_sector", "pt01801080", -0.82),
        ("医药生物", "a_share_sector", "pt01801100", -0.65),
        ("半导体", "a_share_sector", "pt01801090", 0.78),
        ("新能源", "a_share_sector", "pt01801110", -0.58),
        ("黄金", "commodity", "fuGC", 0.62),
        ("恒生科技", "hk_sector", "hkHSTECH", -0.55),
        ("标普500", "global_index", "usINX", 0.48),
        ("科技", "us_etf", "usXLK", 0.52),
        ("券商", "a_share_sector", "pt01801050", -0.35),
        ("房地产", "a_share_sector", "pt01801140", -0.72),
        ("食品饮料", "a_share_sector", "pt01801120", -0.42),
        ("通信", "a_share_sector", "pt01801170", 0.44),
        ("原油(WTI)", "commodity", "fuCL", 0.55),
        ("10年美债", "fx_bond", "us10Y", -0.38),
        ("美元指数", "fx_bond", "fxDINIW", 0.40),
    ]
    
    mock_signals = []
    for name, cls, code, score in mock_assets:
        direction = "long" if score < -0.25 else ("short" if score > 0.25 else None)
        
        # 获取真实ETF映射
        trade_tool = get_trade_tool(name, direction, cls) if direction else {}
        
        mock_signals.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "asset_name": name,
            "asset_class": cls,
            "asset_code": code,
            "composite_score": score,
            "valuation_score": score * 0.85 + random.uniform(-0.1, 0.1),
            "momentum_score": score * 0.7 + random.uniform(-0.15, 0.15),
            "sentiment_score": score * 0.8 + random.uniform(-0.1, 0.1),
            "narrative_score": score * 0.75 + random.uniform(-0.1, 0.1),
            "signal_level": "S_PLUS" if score < -0.75 else ("S_MINUS" if score > 0.75 else ("A_PLUS" if score < -0.5 else ("A_MINUS" if score > 0.5 else ("B_PLUS" if score < -0.25 else ("B_MINUS" if score > 0.25 else "NEUTRAL"))))),
            "signal_label": "S+ 强做多" if score < -0.75 else ("S- 强做空" if score > 0.75 else ("A+ 做多" if score < -0.5 else ("A- 做空" if score > 0.5 else ("B+ 观察偏多" if score < -0.25 else ("B- 观察偏空" if score > 0.25 else "N 中性"))))),
            "direction": direction,
            "color": "#006400" if score < -0.75 else ("#8B0000" if score > 0.75 else ("#28A745" if score < -0.5 else ("#DC3545" if score > 0.5 else ("#90EE90" if score < -0.25 else ("#FFB6C1" if score > 0.25 else "#808080"))))),
            "position_multiplier": 1.0,
            "pe_percentile": max(0.01, min(0.99, 0.5 - score * 0.45)),
            "pb_percentile": max(0.01, min(0.99, 0.5 - score * 0.4)),
            "ps_percentile": max(0.01, min(0.99, 0.5 - score * 0.35)),
            "return_3m": -score * 35,
            "return_1m": -score * 15,
            "rsi_14": 50 - score * 25,
            "trade_tool": trade_tool,
            "trade_suggestion": "",  # 将在下面用真实ETF代码填充
            "position_pct": 0.05,
            "confirmations": ["估值确认", "RSI确认"],
            "confirmation_count": 2,
            "details": {"valuation_detail": {"pe_ttm": None, "pb": None, "ps_ttm": None}},
        })
    
    # 使用真实的trade_tool生成suggestion
    for s in mock_signals:
        pos_pct = s["position_pct"]
        tt = s.get("trade_tool", {})
        name = s["asset_name"]
        direction = s["direction"]
        
        if direction == "long":
            code = tt.get("code", "")
            t = tt.get("type", "ETF")
            n = tt.get("name", "")
            s["trade_suggestion"] = f"做多{name}，买入{t} {code}({n})，仓位{pos_pct*100:.1f}%"
        elif direction == "short":
            code = tt.get("code", "")
            t = tt.get("type", "期权")
            n = tt.get("name", "")
            note = tt.get("note", "")
            lev = tt.get("leverage")
            if "反向ETF" in t and lev:
                s["trade_suggestion"] = f"做空{name}，买入{abs(lev)}x反向ETF {code}({n})，仓位{pos_pct*100:.1f}%"
            elif "ETF期权Put" in t:
                s["trade_suggestion"] = f"做空{name}，买Put {code}({n})，仓位{pos_pct*100:.1f}%"
            else:
                s["trade_suggestion"] = f"做空{name}，{t} {code}，仓位{pos_pct*100:.1f}%"
        else:
            s["trade_suggestion"] = f"{name}当前无方向信号"
    
    return mock_signals


def run_daily(quick: bool = False, mock: bool = False):
    """
    每日主流程
    
    Args:
        quick: 快速模式（仅A股+宏观）
        mock: Mock模式（使用模拟数据）
    """
    logger = logging.getLogger(__name__)
    start_time = time.time()
    today = datetime.now().strftime("%Y-%m-%d")
    
    logger.info("=" * 60)
    logger.info(f"全球大类资产极端状态反转策略 — 每日运行开始 ({today})")
    logger.info(f"模式: {'Mock' if mock else ('快速' if quick else '完整')}")
    logger.info("=" * 60)
    
    # ============================================================
    # Step 1: 数据采集
    # ============================================================
    logger.info("[Step 1/5] 数据采集...")
    
    if mock:
        logger.info("Mock模式：使用模拟数据")
        collected_data = {
            "timestamp": datetime.now().isoformat(),
            "date": today,
            "macro": {"cn_premium_value": {"EquityPremium": 3.04}},
            "market_overview": {"changedist": {"up_count": 555, "down_count": 4940, "up_ratio_pct": 10}},
            "a_share_sectors": {"_fund_ranking": {
                "inflow_top5": [
                    {"name": "银行", "1日": 12345678901},
                    {"name": "券商", "1日": 9876543210},
                    {"name": "煤炭", "1日": 5678901234},
                    {"name": "公用事业", "1日": 3456789012},
                    {"name": "钢铁", "1日": 1234567890}
                ],
                "outflow_top5": [
                    {"name": "电子", "1日": -55782975790},
                    {"name": "医药生物", "1日": -32109876540},
                    {"name": "半导体", "1日": -28456789010},
                    {"name": "计算机", "1日": -15678901230},
                    {"name": "食品饮料", "1日": -9876543210}
                ],
                "inflow_top5_5d": [
                    {"name": "银行", "5日": 45678901234},
                    {"name": "煤炭", "5日": 21234567890},
                    {"name": "券商", "5日": 12345678901},
                    {"name": "公用事业", "5日": 9876543210},
                    {"name": "钢铁", "5日": 4567890123}
                ],
                "outflow_top5_5d": [
                    {"name": "电子", "5日": -123456789012},
                    {"name": "半导体", "5日": -98765432109},
                    {"name": "医药生物", "5日": -76543210987},
                    {"name": "计算机", "5日": -34567890123},
                    {"name": "通信", "5日": -12345678901}
                ],
                "inflow_top5_10d": [
                    {"name": "银行", "10日": 78901234567},
                    {"name": "煤炭", "10日": 34567890123},
                    {"name": "公用事业", "10日": 12345678901}
                ],
                "outflow_top5_10d": [
                    {"name": "电子", "10日": -234567890123},
                    {"name": "半导体", "10日": -123456789012},
                    {"name": "医药生物", "10日": -98765432109}
                ],
                "daily_histories": {
                    "银行": [{"date":"2026-07-11","main_flow":-5056889945},{"date":"2026-07-14","main_flow":4943852581},{"date":"2026-07-15","main_flow":2871109372},{"date":"2026-07-16","main_flow":23401528412},{"date":"2026-07-17","main_flow":21010659343},{"date":"2026-07-18","main_flow":29629862554},{"date":"2026-07-21","main_flow":-2579766849},{"date":"2026-07-22","main_flow":10819552633},{"date":"2026-07-23","main_flow":-4865431377},{"date":"2026-07-24","main_flow":2688198838},{"date":"2026-07-25","main_flow":14156891370}],
                    "医药生物": [{"date":"2026-07-11","main_flow":-59392897004},{"date":"2026-07-14","main_flow":-41351025520},{"date":"2026-07-15","main_flow":-45548743807},{"date":"2026-07-16","main_flow":-58528778150},{"date":"2026-07-17","main_flow":-43775775677},{"date":"2026-07-18","main_flow":-34969184765},{"date":"2026-07-21","main_flow":-67086452644},{"date":"2026-07-22","main_flow":-35113632958},{"date":"2026-07-23","main_flow":-39420827232},{"date":"2026-07-24","main_flow":-53736382371},{"date":"2026-07-25","main_flow":-61127223039}],
                    "半导体": [{"date":"2026-07-11","main_flow":39185089025},{"date":"2026-07-14","main_flow":29431140956},{"date":"2026-07-15","main_flow":29589962294},{"date":"2026-07-16","main_flow":59621081875},{"date":"2026-07-17","main_flow":49870348475},{"date":"2026-07-18","main_flow":58006438152},{"date":"2026-07-21","main_flow":54910578688},{"date":"2026-07-22","main_flow":47170430879},{"date":"2026-07-23","main_flow":64645937780},{"date":"2026-07-24","main_flow":40862682309},{"date":"2026-07-25","main_flow":47802932472}],
                    "食品饮料": [{"date":"2026-07-11","main_flow":37681256520},{"date":"2026-07-14","main_flow":47408742438},{"date":"2026-07-15","main_flow":36034552236},{"date":"2026-07-16","main_flow":41123339874},{"date":"2026-07-17","main_flow":14773441772},{"date":"2026-07-18","main_flow":22056397451},{"date":"2026-07-21","main_flow":24515984969},{"date":"2026-07-22","main_flow":16132145502},{"date":"2026-07-23","main_flow":22252101880},{"date":"2026-07-24","main_flow":16980523602},{"date":"2026-07-25","main_flow":24059410550}],
                    "新能源": [{"date":"2026-07-11","main_flow":8161731585},{"date":"2026-07-14","main_flow":8375683111},{"date":"2026-07-15","main_flow":1948725657},{"date":"2026-07-16","main_flow":4247557308},{"date":"2026-07-17","main_flow":31034627935},{"date":"2026-07-18","main_flow":19489859836},{"date":"2026-07-21","main_flow":17933684653},{"date":"2026-07-22","main_flow":413990354},{"date":"2026-07-23","main_flow":22733516344},{"date":"2026-07-24","main_flow":104544177},{"date":"2026-07-25","main_flow":8746662097}],
                    "军工": [{"date":"2026-07-11","main_flow":54552325458},{"date":"2026-07-14","main_flow":51230324815},{"date":"2026-07-15","main_flow":56336905103},{"date":"2026-07-16","main_flow":62666411871},{"date":"2026-07-17","main_flow":59992331526},{"date":"2026-07-18","main_flow":38114257942},{"date":"2026-07-21","main_flow":30236344820},{"date":"2026-07-22","main_flow":41570456986},{"date":"2026-07-23","main_flow":39661970103},{"date":"2026-07-24","main_flow":37391648807},{"date":"2026-07-25","main_flow":66668723637}],
                    "房地产": [{"date":"2026-07-11","main_flow":30223877879},{"date":"2026-07-14","main_flow":43854309259},{"date":"2026-07-15","main_flow":33462038690},{"date":"2026-07-16","main_flow":54218666237},{"date":"2026-07-17","main_flow":35990836751},{"date":"2026-07-18","main_flow":28231969307},{"date":"2026-07-21","main_flow":27501862955},{"date":"2026-07-22","main_flow":40091488014},{"date":"2026-07-23","main_flow":28146426988},{"date":"2026-07-24","main_flow":41020202256},{"date":"2026-07-25","main_flow":53549677991}],
                    "券商": [{"date":"2026-07-11","main_flow":-21287119120},{"date":"2026-07-14","main_flow":9841554774},{"date":"2026-07-15","main_flow":-9678897739},{"date":"2026-07-16","main_flow":-26423572999},{"date":"2026-07-17","main_flow":-28175294469},{"date":"2026-07-18","main_flow":-25673984272},{"date":"2026-07-21","main_flow":-4962107818},{"date":"2026-07-22","main_flow":1623225089},{"date":"2026-07-23","main_flow":-13173550814},{"date":"2026-07-24","main_flow":-27518841240},{"date":"2026-07-25","main_flow":-14795178026}],
                    "煤炭": [{"date":"2026-07-11","main_flow":50776711828},{"date":"2026-07-14","main_flow":68455273129},{"date":"2026-07-15","main_flow":64043326113},{"date":"2026-07-16","main_flow":30071378902},{"date":"2026-07-17","main_flow":58441010798},{"date":"2026-07-18","main_flow":56880552785},{"date":"2026-07-21","main_flow":51090951240},{"date":"2026-07-22","main_flow":40285145622},{"date":"2026-07-23","main_flow":55250609967},{"date":"2026-07-24","main_flow":34074224968},{"date":"2026-07-25","main_flow":47002748051}],
                    "有色金属": [{"date":"2026-07-11","main_flow":13525007734},{"date":"2026-07-14","main_flow":10406488248},{"date":"2026-07-15","main_flow":-14092067337},{"date":"2026-07-16","main_flow":-4604184845},{"date":"2026-07-17","main_flow":-17481554146},{"date":"2026-07-18","main_flow":11877484207},{"date":"2026-07-21","main_flow":10193113426},{"date":"2026-07-22","main_flow":-12689837709},{"date":"2026-07-23","main_flow":930350428},{"date":"2026-07-24","main_flow":-268820910},{"date":"2026-07-25","main_flow":-18514058625}],
                    "电力设备": [{"date":"2026-07-11","main_flow":27826241212},{"date":"2026-07-14","main_flow":37396139153},{"date":"2026-07-15","main_flow":27465226895},{"date":"2026-07-16","main_flow":6273955853},{"date":"2026-07-17","main_flow":19217322288},{"date":"2026-07-18","main_flow":7030149703},{"date":"2026-07-21","main_flow":43415024658},{"date":"2026-07-22","main_flow":41399955120},{"date":"2026-07-23","main_flow":39517701182},{"date":"2026-07-24","main_flow":18551645024},{"date":"2026-07-25","main_flow":8568086667}],
                    "计算机": [{"date":"2026-07-11","main_flow":55678937732},{"date":"2026-07-14","main_flow":21227098003},{"date":"2026-07-15","main_flow":37240578453},{"date":"2026-07-16","main_flow":20569460659},{"date":"2026-07-17","main_flow":48225046531},{"date":"2026-07-18","main_flow":48434337093},{"date":"2026-07-21","main_flow":22936618500},{"date":"2026-07-22","main_flow":36812255044},{"date":"2026-07-23","main_flow":39793103660},{"date":"2026-07-24","main_flow":28403225078},{"date":"2026-07-25","main_flow":52698281564}],
                    "通信": [{"date":"2026-07-11","main_flow":-19214277762},{"date":"2026-07-14","main_flow":-6114362429},{"date":"2026-07-15","main_flow":1511036784},{"date":"2026-07-16","main_flow":-19640163444},{"date":"2026-07-17","main_flow":-15217554328},{"date":"2026-07-18","main_flow":12119768287},{"date":"2026-07-21","main_flow":-1691083674},{"date":"2026-07-22","main_flow":-10162202623},{"date":"2026-07-23","main_flow":-6983172338},{"date":"2026-07-24","main_flow":-22846038145},{"date":"2026-07-25","main_flow":-18698312499}],
                    "电子": [{"date":"2026-07-11","main_flow":-12659095047},{"date":"2026-07-14","main_flow":-26986854481},{"date":"2026-07-15","main_flow":-27382748407},{"date":"2026-07-16","main_flow":-33351720345},{"date":"2026-07-17","main_flow":-10947325494},{"date":"2026-07-18","main_flow":-27033772433},{"date":"2026-07-21","main_flow":25356735},{"date":"2026-07-22","main_flow":-1806027775},{"date":"2026-07-23","main_flow":-33357149790},{"date":"2026-07-24","main_flow":-26671258410},{"date":"2026-07-25","main_flow":-9432332653}],
                    "汽车": [{"date":"2026-07-11","main_flow":-43283845314},{"date":"2026-07-14","main_flow":-11155749640},{"date":"2026-07-15","main_flow":-25734595530},{"date":"2026-07-16","main_flow":-29669478210},{"date":"2026-07-17","main_flow":-17191542291},{"date":"2026-07-18","main_flow":-16276439352},{"date":"2026-07-21","main_flow":-40959922688},{"date":"2026-07-22","main_flow":-44699086694},{"date":"2026-07-23","main_flow":-31334271967},{"date":"2026-07-24","main_flow":-31633174342},{"date":"2026-07-25","main_flow":-29895332541}],
                    "传媒": [{"date":"2026-07-11","main_flow":29842166838},{"date":"2026-07-14","main_flow":42274193401},{"date":"2026-07-15","main_flow":6844299792},{"date":"2026-07-16","main_flow":19012436230},{"date":"2026-07-17","main_flow":16479689162},{"date":"2026-07-18","main_flow":37374486400},{"date":"2026-07-21","main_flow":12853838303},{"date":"2026-07-22","main_flow":10515941284},{"date":"2026-07-23","main_flow":20852126859},{"date":"2026-07-24","main_flow":19782850539},{"date":"2026-07-25","main_flow":14049390733}],
                    "基础化工": [{"date":"2026-07-11","main_flow":-8088731241},{"date":"2026-07-14","main_flow":-27294125410},{"date":"2026-07-15","main_flow":-10565391021},{"date":"2026-07-16","main_flow":-23006342714},{"date":"2026-07-17","main_flow":-42995822031},{"date":"2026-07-18","main_flow":-5048056475},{"date":"2026-07-21","main_flow":-11578251809},{"date":"2026-07-22","main_flow":-6259504920},{"date":"2026-07-23","main_flow":-7964675891},{"date":"2026-07-24","main_flow":-11071525835},{"date":"2026-07-25","main_flow":-38366910788}],
                    "钢铁": [{"date":"2026-07-11","main_flow":-12885995487},{"date":"2026-07-14","main_flow":-5394275753},{"date":"2026-07-15","main_flow":-19090471456},{"date":"2026-07-16","main_flow":-6276962696},{"date":"2026-07-17","main_flow":17976466296},{"date":"2026-07-18","main_flow":-10827765128},{"date":"2026-07-21","main_flow":9926936623},{"date":"2026-07-22","main_flow":-3235552761},{"date":"2026-07-23","main_flow":-4515588015},{"date":"2026-07-24","main_flow":16856818179},{"date":"2026-07-25","main_flow":18381020125}],
                    "建筑材料": [{"date":"2026-07-11","main_flow":14313163352},{"date":"2026-07-14","main_flow":-8231294648},{"date":"2026-07-15","main_flow":-2554854640},{"date":"2026-07-16","main_flow":24325206939},{"date":"2026-07-17","main_flow":8744043973},{"date":"2026-07-18","main_flow":7264640396},{"date":"2026-07-21","main_flow":15495854756},{"date":"2026-07-22","main_flow":-12136556743},{"date":"2026-07-23","main_flow":8943936119},{"date":"2026-07-24","main_flow":5690847657},{"date":"2026-07-25","main_flow":19685628022}],
                    "公用事业": [{"date":"2026-07-11","main_flow":-15825571075},{"date":"2026-07-14","main_flow":-51052268596},{"date":"2026-07-15","main_flow":-46823728767},{"date":"2026-07-16","main_flow":-30455322948},{"date":"2026-07-17","main_flow":-27248225062},{"date":"2026-07-18","main_flow":-44848571406},{"date":"2026-07-21","main_flow":-49461262648},{"date":"2026-07-22","main_flow":-18645234641},{"date":"2026-07-23","main_flow":-44408113295},{"date":"2026-07-24","main_flow":-30475961065},{"date":"2026-07-25","main_flow":-29481466793}]
                }
            }},"mock": True,
        }
    elif quick:
        collected_data = quick_collect_a_share()
    else:
        collector = DataCollector()
        collected_data = collector.collect_all()
    
    collection_errors = collected_data.get("errors", [])
    if collection_errors:
        logger.warning(f"数据采集完成，但有 {len(collection_errors)} 个错误")
        for err in collection_errors[:5]:
            logger.warning(f"  - {err}")
    
    logger.info(f"数据采集完成，耗时: {collected_data.get('collection_time_seconds', 'N/A')}秒")
    
    # ============================================================
    # Step 2: 评分计算
    # ============================================================
    logger.info("[Step 2/5] 评分计算...")
    
    if mock:
        signals = generate_mock_data()
    else:
        batch_scorer = BatchScorer()
        signal_results = batch_scorer.score_all(collected_data)
        signals = [s.to_dict() for s in signal_results]
    
    signal_summary = generate_signal_summary_from_dicts(signals)
    extreme_signals = [s for s in signals if abs(s.get("composite_score", 0)) >= 0.5]
    
    logger.info(f"评分完成: 总信号{len(signals)}个, 极端信号{len(extreme_signals)}个")
    logger.info(f"  做多: {signal_summary['long_count']} | 做空: {signal_summary['short_count']}")
    logger.info(f"  S+: {signal_summary['s_plus_count']} | S-: {signal_summary['s_minus_count']}")
    
    # ============================================================
    # Step 3: 信号处理
    # ============================================================
    logger.info("[Step 3/5] 信号处理...")
    
    # 初始化数据库
    db = SignalDatabase(DB_PATH)
    
    # 获取历史信号用于对比
    previous_signals = db.get_today_signals()
    
    # 信号管理（Mock模式跳过对比，直接生成交易建议）
    if mock:
        processed = {
            "new_signals": [s for s in signals if abs(s.get("composite_score", 0)) >= 0.25],
            "upgraded": [],
            "downgraded": [],
            "expired": [],
            "unchanged": [],
            "trading_suggestions": [
                {
                    "action": "新开",
                    "asset": s.get("asset_name", ""),
                    "direction": s.get("direction"),
                    "score": s.get("composite_score", 0),
                    "position_pct": s.get("position_pct", 0),
                    "suggestion": s.get("trade_suggestion", ""),
                }
                for s in signals if abs(s.get("composite_score", 0)) >= 0.5
            ],
            "all_active": [s for s in signals if abs(s.get("composite_score", 0)) >= 0.25],
        }
    else:
        signal_manager = SignalManager(db)
        processed = signal_manager.process_signals(signals, previous_signals)
    
    # 仓位计算
    position_manager = PositionManager()
    trading_suggestions = processed.get("trading_suggestions", [])
    
    # 保存信号到数据库
    if not mock:
        try:
            db.save_signals_batch(signals)
            db.save_daily_summary({
                "date": today,
                "total_signals": len(signals),
                "s_signals": signal_summary["s_plus_count"] + signal_summary["s_minus_count"],
                "a_signals": signal_summary["a_plus_count"] + signal_summary["a_minus_count"],
                "b_signals": len(signals) - signal_summary["s_plus_count"] - signal_summary["s_minus_count"] - signal_summary["a_plus_count"] - signal_summary["a_minus_count"],
            })
        except Exception as e:
            logger.error(f"数据库保存失败: {e}")
    
    logger.info(f"信号处理完成: 新开{len(processed['new_signals'])}, "
                f"升级{len(processed['upgraded'])}, 降级{len(processed['downgraded'])}, "
                f"失效{len(processed['expired'])}")
    
    # ============================================================
    # Step 4: 输出生成
    # ============================================================
    logger.info("[Step 4/5] 输出生成...")
    
    # 4.1 Markdown日报
    market_data = {
        "macro": collected_data.get("macro", {}),
        "market_overview": collected_data.get("market_overview", {}),
    }
    
    report_md = generate_daily_report(signals, market_data, signal_summary, trading_suggestions)
    report_path = OUTPUT_DIR / f"daily_report_{today.replace('-', '')}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    logger.info(f"Markdown日报已保存: {report_path}")
    
    # 提取板块资金流排名
    sector_fund_ranking = collected_data.get("a_share_sectors", {}).get("_fund_ranking")
    
    # 提取每日资金流历史
    if not mock:
        hist_data = {}
        sectors_data = collected_data.get("a_share_sectors", {})
        for name, sd in sectors_data.items():
            if name.startswith("_"):
                continue
            hist = sd.get("fund_flow_history", [])
            if hist:
                hist_data[name] = hist[-12:]
        if hist_data:
            if not sector_fund_ranking:
                sector_fund_ranking = {}
            sector_fund_ranking["daily_histories"] = hist_data
    
    # 4.2 HTML仪表盘
    dashboard_path = save_dashboard(signals, market_data, signal_summary, trading_suggestions, sector_fund_ranking=sector_fund_ranking)
    logger.info(f"HTML仪表盘已保存: {dashboard_path}")
    
    # 4.3 保存摘要JSON供腾讯文档更新使用
    import json
    summary_json = {
        "date": today,
        "dashboard_path": str(dashboard_path),"github_url": GITHUB_PAGES_URL,
        "total_signals": signal_summary.get("total_signals", 0),
        "s_plus": signal_summary.get("s_plus_count", 0),
        "s_minus": signal_summary.get("s_minus_count", 0),
        "a_plus": signal_summary.get("a_plus_count", 0),
        "a_minus": signal_summary.get("a_minus_count", 0),
        "long_count": signal_summary.get("long_count", 0),
        "short_count": signal_summary.get("short_count", 0),
    }
    summary_path = DATA_DIR / "last_run.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_json, f, ensure_ascii=False)
    logger.info(f"运行摘要已保存: {summary_path}")
    
    # 4.4 保存腾讯文档更新行
    s_text = ""
    for level, count in [("S-", signal_summary.get("s_minus_count", 0)), ("A-", signal_summary.get("a_minus_count", 0)),
                          ("A+", signal_summary.get("a_plus_count", 0)), ("S+", signal_summary.get("s_plus_count", 0))]:
        if count > 0:
            s_text += f" {level}{count}"
    if not s_text:
        s_text = " 中性"
    tdocs_row = f"{today}|{GITHUB_PAGES_URL}|{s_text.strip()}"
    tdocs_path = DATA_DIR / "tdocs_row.txt"
    with open(tdocs_path, "w", encoding="utf-8") as f:
        f.write(tdocs_row)
    logger.info(f"腾讯文档更新行已保存: {tdocs_row}")
    
    # ============================================================
    # Step 5: 通知（如果有S级信号）
    # ============================================================
    logger.info("[Step 5/5] 检查通知...")
    
    s_signals = [s for s in signals if s.get("signal_level") in ("S_PLUS", "S_MINUS")]
    if s_signals:
        logger.warning(f"⚠️ 发现 {len(s_signals)} 个S级极端信号!")
        for s in s_signals:
            logger.warning(f"  {s['signal_label']}: {s['asset_name']} (评分: {s['composite_score']:+.2f})")
    
    # ============================================================
    # 完成
    # ============================================================
    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"每日运行完成! 总耗时: {elapsed:.1f}秒")
    logger.info(f"输出文件:")
    logger.info(f"  - 日报: {report_path}")
    logger.info(f"  - 仪表盘: {dashboard_path}")
    logger.info("=" * 60)
    
    return {
        "signals": signals,
        "signal_summary": signal_summary,
        "trading_suggestions": trading_suggestions,
        "report_path": str(report_path),
        "dashboard_path": str(dashboard_path),"github_url": GITHUB_PAGES_URL,
        "elapsed_seconds": elapsed,
        "tdocs_url": "https://docs.qq.com/doc/DR1RqWnN3dGVocUxJ",  # 腾讯文档链接
    }


def generate_signal_summary_from_dicts(signals: list) -> dict:
    """从字典格式的信号列表生成摘要"""
    long_signals = [s for s in signals if s.get("direction") == "long"]
    short_signals = [s for s in signals if s.get("direction") == "short"]
    extreme_signals = [s for s in signals if abs(s.get("composite_score", 0)) >= 0.5]
    
    s_plus = [s for s in signals if s.get("signal_level") == "S_PLUS"]
    s_minus = [s for s in signals if s.get("signal_level") == "S_MINUS"]
    a_plus = [s for s in signals if s.get("signal_level") == "A_PLUS"]
    a_minus = [s for s in signals if s.get("signal_level") == "A_MINUS"]
    b_plus = [s for s in signals if s.get("signal_level") == "B_PLUS"]
    b_minus = [s for s in signals if s.get("signal_level") == "B_MINUS"]
    neutral = [s for s in signals if s.get("signal_level") == "NEUTRAL"]
    
    return {
        "total_signals": len(signals),
        "extreme_signals": len(extreme_signals),
        "long_count": len(long_signals),
        "short_count": len(short_signals),
        "s_plus_count": len(s_plus),
        "s_minus_count": len(s_minus),
        "a_plus_count": len(a_plus),
        "a_minus_count": len(a_minus),
        "b_plus_count": len(b_plus),
        "b_minus_count": len(b_minus),
        "neutral_count": len(neutral),
        "top_long": long_signals[:5],
        "top_short": short_signals[:5],
    }


# ============================================================
# CLI入口
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="全球大类资产极端状态反转策略 — 每日运行")
    parser.add_argument("--quick", action="store_true", help="快速模式（仅A股+宏观）")
    parser.add_argument("--mock", action="store_true", help="Mock模式（使用模拟数据测试）")
    args = parser.parse_args()
    
    setup_logging()
    
    try:
        result = run_daily(quick=args.quick, mock=args.mock)
        print(f"\n✅ 运行完成! 耗时 {result['elapsed_seconds']:.1f}秒")
        print(f"📊 日报: {result['report_path']}")
        print(f"📈 仪表盘: {result['dashboard_path']}")
        print(f"📋 总信号: {result['signal_summary']['total_signals']}")
        print(f"   🔴 极端信号: {result['signal_summary']['extreme_signals']}")
        print(f"   🟢 做多: {result['signal_summary']['long_count']} | 🔴 做空: {result['signal_summary']['short_count']}")
    except Exception as e:
        logging.getLogger(__name__).exception(f"每日运行失败: {e}")
        print(f"\n❌ 运行失败: {e}")
        sys.exit(1)
