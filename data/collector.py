"""
数据采集层 — 数据采集调度器
协调所有数据源的采集流程，处理错误和限流
"""

import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from config.settings import (
    DATA_DIR, EASTMONEY_INTERVAL, LOOKBACK_1Y, LOOKBACK_3M, LOOKBACK_1M
)
from config.asset_mapping import (
    A_SHARE_SECTORS, GLOBAL_COMMODITIES, US_SECTOR_ETFS,
    HK_SECTORS, GLOBAL_INDICES, FX_BOND_ASSETS, get_all_assets
)
from data.westock import (
    get_sector_valuation, get_sector_ranking, get_sector_full_data,
    get_kline, get_technical, get_etf_detail, get_fund_flow,
    get_north_holding, get_south_holding, get_short_data,
    get_macro_indicator, get_market_overview, get_changedist, get_lhb,
    get_commodity_full_data, get_index_full_data
)
from data.astock import (
    get_industry_comparison, get_hot_reason, extract_theme_heat,
    get_hsgt_realtime, get_daily_dragon_tiger, get_margin_trading,
    get_global_news, get_tencent_quote
)
from data.cache import DataCache

logger = logging.getLogger(__name__)

# 全局缓存
cache = DataCache(DATA_DIR, ttl_hours=6)


class DataCollector:
    """数据采集总调度器"""
    
    def __init__(self):
        self.cache = cache
        self.collection_errors = []
        self.collection_stats = {}
    
    def collect_all(self) -> Dict:
        """
        执行全量数据采集，返回统一数据结构
        采集顺序：宏观 → A股行业 → 商品期货 → 美股ETF → 港股 → 全球股指 → 外汇债券
        """
        start_time = time.time()
        all_data = {
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "macro": {},
            "a_share_sectors": {},
            "commodities": {},
            "us_etfs": {},
            "hk_sectors": {},
            "global_indices": {},
            "fx_bonds": {},
            "market_overview": {},
            "errors": [],
        }
        
        logger.info("=" * 60)
        logger.info("开始全量数据采集...")
        
        # Step 1: 宏观数据（最先采集，为后续提供市场环境）
        logger.info("[1/7] 采集宏观数据...")
        all_data["macro"] = self._collect_macro()
        
        # Step 2: 市场总览
        logger.info("[2/7] 采集市场总览...")
        all_data["market_overview"] = self._collect_market_overview()
        
        # Step 3: A股行业板块
        logger.info("[3/7] 采集A股行业数据...")
        all_data["a_share_sectors"] = self._collect_a_share_sectors()
        
        # Step 4: 全球商品期货
        logger.info("[4/7] 采集商品期货数据...")
        all_data["commodities"] = self._collect_commodities()
        
        # Step 5: 美股行业ETF
        logger.info("[5/7] 采集美股ETF数据...")
        all_data["us_etfs"] = self._collect_us_etfs()
        
        # Step 6: 港股行业
        logger.info("[6/7] 采集港股行业数据...")
        all_data["hk_sectors"] = self._collect_hk_sectors()
        
        # Step 7: 全球股指 + 外汇债券
        logger.info("[7/7] 采集全球股指和外汇债券数据...")
        all_data["global_indices"] = self._collect_global_indices()
        all_data["fx_bonds"] = self._collect_fx_bonds()
        
        elapsed = time.time() - start_time
        all_data["collection_time_seconds"] = round(elapsed, 1)
        all_data["errors"] = self.collection_errors
        
        logger.info(f"数据采集完成，耗时 {elapsed:.1f}秒，错误数: {len(self.collection_errors)}")
        
        return all_data
    
    def _collect_macro(self) -> Dict:
        """采集宏观经济指标"""
        macro = {}
        indicators = [
            "cn_core", "cn_premium_value", "cn_premium_curve",
            "cn_term_spread", "cn_yield_curve", "cn_mlf",
            "us_monetary"
        ]
        for ind in indicators:
            try:
                cache_key = f"macro_{ind}"
                data = self.cache.get(cache_key)
                if data is None:
                    data = get_macro_indicator(ind)
                    if data:
                        self.cache.set(cache_key, data)
                macro[ind] = data
                time.sleep(0.2)  # 命令间小间隔
            except Exception as e:
                self.collection_errors.append(f"macro_{ind}: {e}")
                macro[ind] = {}
        return macro
    
    def _collect_market_overview(self) -> Dict:
        """采集市场总览"""
        overview = {}
        try:
            overview["valuation"] = get_market_overview("valuation")
            overview["changedist"] = get_changedist()
            overview["lhb"] = get_lhb("institution")
            overview["hot_reasons"] = get_hot_reason()
            overview["dragon_tiger"] = get_daily_dragon_tiger()
            overview["hsgt"] = get_hsgt_realtime()
            overview["global_news"] = get_global_news()
        except Exception as e:
            self.collection_errors.append(f"market_overview: {e}")
        return overview
    
    def _collect_a_share_sectors(self) -> Dict:
        """采集A股行业板块数据"""
        sectors_data = {}
        
        # 行业排名（一次性获取所有行业）
        try:
            ranking = get_sector_ranking()
            sectors_data["_ranking"] = ranking
            time.sleep(0.3)
        except Exception as e:
            self.collection_errors.append(f"sector_ranking: {e}")
            sectors_data["_ranking"] = []
        
        # 行业对比（a-stock-data）
        try:
            industry_comp = get_industry_comparison()
            sectors_data["_industry_comparison"] = industry_comp
        except Exception as e:
            self.collection_errors.append(f"industry_comparison: {e}")
            sectors_data["_industry_comparison"] = []
        
        # 逐行业采集估值和资金数据
        for sector_name, sector_info in A_SHARE_SECTORS.items():
            pt_code = sector_info["pt_code"]
            try:
                cache_key = f"sector_full_{pt_code}"
                sector_data = self.cache.get(cache_key)
                if sector_data is None:
                    sector_data = get_sector_full_data(pt_code, sector_name)
                    if sector_data.get("valuation"):
                        self.cache.set(cache_key, sector_data)
                sectors_data[sector_name] = sector_data
                time.sleep(0.3)
            except Exception as e:
                self.collection_errors.append(f"sector_{sector_name}: {e}")
                sectors_data[sector_name] = {"name": sector_name, "pt_code": pt_code, "error": str(e)}
        
        # 从sectors_data中提取资金流排名（多维度）
        fund_ranking = {"inflow_top5": [], "outflow_top5": [],
                        "inflow_top5_5d": [], "outflow_top5_5d": [],
                        "inflow_top5_10d": [], "outflow_top5_10d": []}
        
        for period, period_key, top_key_in, top_key_out in [
            ("main_flow", "1日", "inflow_top5", "outflow_top5"),
            ("main_flow_5d", "5日", "inflow_top5_5d", "outflow_top5_5d"),
            ("main_flow_10d", "10日", "inflow_top5_10d", "outflow_top5_10d"),
        ]:
            flows = []
            for name, sd in sectors_data.items():
                if name.startswith("_"):
                    continue
                ff = sd.get("fund_flow", {})
                mf = ff.get(period_key)
                if mf is not None:
                    flows.append({"name": name, period_key: mf, "period": period})
            
            flows.sort(key=lambda x: x[period_key], reverse=True)
            fund_ranking[top_key_in] = flows[:5]
            fund_ranking[top_key_out] = list(reversed(flows[-5:])) if len(flows) >= 5 else list(reversed(flows))
        
        sectors_data["_fund_ranking"] = fund_ranking
        
        return sectors_data
    
    def _collect_commodities(self) -> Dict:
        """采集全球商品期货数据"""
        commodities_data = {}
        for name, info in GLOBAL_COMMODITIES.items():
            code = info["code"]
            try:
                cache_key = f"commodity_{code}"
                data = self.cache.get(cache_key)
                if data is None:
                    data = get_commodity_full_data(code, name)
                    if data.get("kline_1y"):
                        self.cache.set(cache_key, data)
                commodities_data[name] = data
                time.sleep(0.3)
            except Exception as e:
                self.collection_errors.append(f"commodity_{name}: {e}")
                commodities_data[name] = {"name": name, "code": code, "error": str(e)}
        
        return commodities_data
    
    def _collect_us_etfs(self) -> Dict:
        """采集美股行业ETF数据"""
        etfs_data = {}
        for name, info in US_SECTOR_ETFS.items():
            code = info["code"]
            try:
                cache_key = f"us_etf_{code}"
                data = self.cache.get(cache_key)
                if data is None:
                    data = {
                        "name": name,
                        "code": code,
                        "kline_1y": get_kline(code, "day", 250),
                        "kline_3m": get_kline(code, "day", 66),
                        "technical_rsi": get_technical(code, "rsi"),
                        "etf_detail": get_etf_detail(code),
                        "timestamp": datetime.now().isoformat(),
                    }
                    if data.get("kline_1y"):
                        self.cache.set(cache_key, data)
                etfs_data[name] = data
                time.sleep(0.3)
            except Exception as e:
                self.collection_errors.append(f"us_etf_{name}: {e}")
                etfs_data[name] = {"name": name, "code": code, "error": str(e)}
        
        return etfs_data
    
    def _collect_hk_sectors(self) -> Dict:
        """采集港股行业数据"""
        hk_data = {}
        for name, info in HK_SECTORS.items():
            pt_code = info["pt_code"]
            try:
                cache_key = f"hk_sector_{pt_code}"
                data = self.cache.get(cache_key)
                if data is None:
                    data = {
                        "name": name,
                        "pt_code": pt_code,
                        "kline_1y": get_kline(pt_code, "day", 250),
                        "kline_3m": get_kline(pt_code, "day", 66),
                        "technical_rsi": get_technical(pt_code, "rsi"),
                        "south_holding": get_south_holding(pt_code),
                        "short_data": get_short_data(pt_code),
                        "timestamp": datetime.now().isoformat(),
                    }
                    if data.get("kline_1y"):
                        self.cache.set(cache_key, data)
                hk_data[name] = data
                time.sleep(0.3)
            except Exception as e:
                self.collection_errors.append(f"hk_sector_{name}: {e}")
                hk_data[name] = {"name": name, "pt_code": pt_code, "error": str(e)}
        
        return hk_data
    
    def _collect_global_indices(self) -> Dict:
        """采集全球股指数据"""
        indices_data = {}
        for name, info in GLOBAL_INDICES.items():
            code = info["code"]
            try:
                cache_key = f"index_{code}"
                data = self.cache.get(cache_key)
                if data is None:
                    data = get_index_full_data(code, name)
                    if data.get("kline_1y"):
                        self.cache.set(cache_key, data)
                indices_data[name] = data
                time.sleep(0.3)
            except Exception as e:
                self.collection_errors.append(f"index_{name}: {e}")
                indices_data[name] = {"name": name, "code": code, "error": str(e)}
        
        return indices_data
    
    def _collect_fx_bonds(self) -> Dict:
        """采集外汇/债券数据"""
        fx_data = {}
        for name, info in FX_BOND_ASSETS.items():
            code = info["code"]
            try:
                cache_key = f"fx_bond_{code}"
                data = self.cache.get(cache_key)
                if data is None:
                    data = {
                        "name": name,
                        "code": code,
                        "type": info.get("type", "unknown"),
                        "kline_1y": get_kline(code, "day", 250),
                        "kline_3m": get_kline(code, "day", 66),
                        "technical_rsi": get_technical(code, "rsi"),
                        "timestamp": datetime.now().isoformat(),
                    }
                    if data.get("kline_1y"):
                        self.cache.set(cache_key, data)
                fx_data[name] = data
                time.sleep(0.3)
            except Exception as e:
                self.collection_errors.append(f"fx_bond_{name}: {e}")
                fx_data[name] = {"name": name, "code": code, "error": str(e)}
        
        return fx_data


def quick_collect_a_share() -> Dict:
    """
    快速采集A股核心数据（用于快速验证）
    只采集宏观 + A股行业板块 + 市场总览
    """
    collector = DataCollector()
    data = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "macro": collector._collect_macro(),
        "market_overview": collector._collect_market_overview(),
        "a_share_sectors": collector._collect_a_share_sectors(),
        "errors": collector.collection_errors,
    }
    return data
