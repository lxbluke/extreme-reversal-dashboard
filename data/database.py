"""
数据采集层 — SQLite历史数据库
存储历史信号和评分数据，支持回溯查询
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    asset_name TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    asset_code TEXT,
    composite_score REAL NOT NULL,
    valuation_score REAL,
    momentum_score REAL,
    sentiment_score REAL,
    narrative_score REAL,
    signal_level TEXT NOT NULL,
    direction TEXT,
    pe_percentile REAL,
    pb_percentile REAL,
    ps_percentile REAL,
    return_3m REAL,
    return_1m REAL,
    turnover_rate REAL,
    rsi_14 REAL,
    volume_ratio REAL,
    trade_suggestion TEXT,
    position_pct REAL,
    details TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS daily_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    market_vix REAL,
    north_flow REAL,
    market_turnover REAL,
    up_down_ratio REAL,
    total_signals INTEGER,
    s_signals INTEGER,
    a_signals INTEGER,
    b_signals INTEGER,
    raw_summary TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS backtest_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT NOT NULL,
    exit_date TEXT,
    asset_name TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_score REAL,
    exit_score REAL,
    entry_price REAL,
    exit_price REAL,
    position_pct REAL,
    pnl_pct REAL,
    exit_reason TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(date);
CREATE INDEX IF NOT EXISTS idx_signals_asset ON signals(asset_name, date);
CREATE INDEX IF NOT EXISTS idx_signals_level ON signals(signal_level, date);
CREATE INDEX IF NOT EXISTS idx_trades_entry ON backtest_trades(entry_date);
"""


class SignalDatabase:
    """信号历史数据库"""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _get_conn(self):
        return sqlite3.connect(str(self.db_path))
    
    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript(SCHEMA)
            conn.commit()
    
    def save_signal(self, signal: Dict):
        """保存一条信号记录"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO signals (
                    date, asset_name, asset_class, asset_code,
                    composite_score, valuation_score, momentum_score,
                    sentiment_score, narrative_score,
                    signal_level, direction,
                    pe_percentile, pb_percentile, ps_percentile,
                    return_3m, return_1m, turnover_rate, rsi_14, volume_ratio,
                    trade_suggestion, position_pct, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.get("date", datetime.now().strftime("%Y-%m-%d")),
                signal.get("asset_name", ""),
                signal.get("asset_class", ""),
                signal.get("asset_code", ""),
                signal.get("composite_score", 0.0),
                signal.get("valuation_score"),
                signal.get("momentum_score"),
                signal.get("sentiment_score"),
                signal.get("narrative_score"),
                signal.get("signal_level", "NEUTRAL"),
                signal.get("direction"),
                signal.get("pe_percentile"),
                signal.get("pb_percentile"),
                signal.get("ps_percentile"),
                signal.get("return_3m"),
                signal.get("return_1m"),
                signal.get("turnover_rate"),
                signal.get("rsi_14"),
                signal.get("volume_ratio"),
                signal.get("trade_suggestion"),
                signal.get("position_pct"),
                json.dumps(signal.get("details", {}), ensure_ascii=False),
            ))
            conn.commit()
    
    def save_signals_batch(self, signals: List[Dict]):
        """批量保存信号"""
        with self._get_conn() as conn:
            for signal in signals:
                conn.execute("""
                    INSERT INTO signals (
                        date, asset_name, asset_class, asset_code,
                        composite_score, valuation_score, momentum_score,
                        sentiment_score, narrative_score,
                        signal_level, direction,
                        pe_percentile, pb_percentile, ps_percentile,
                        return_3m, return_1m, turnover_rate, rsi_14, volume_ratio,
                        trade_suggestion, position_pct, details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    signal.get("date", datetime.now().strftime("%Y-%m-%d")),
                    signal.get("asset_name", ""),
                    signal.get("asset_class", ""),
                    signal.get("asset_code", ""),
                    signal.get("composite_score", 0.0),
                    signal.get("valuation_score"),
                    signal.get("momentum_score"),
                    signal.get("sentiment_score"),
                    signal.get("narrative_score"),
                    signal.get("signal_level", "NEUTRAL"),
                    signal.get("direction"),
                    signal.get("pe_percentile"),
                    signal.get("pb_percentile"),
                    signal.get("ps_percentile"),
                    signal.get("return_3m"),
                    signal.get("return_1m"),
                    signal.get("turnover_rate"),
                    signal.get("rsi_14"),
                    signal.get("volume_ratio"),
                    signal.get("trade_suggestion"),
                    signal.get("position_pct"),
                    json.dumps(signal.get("details", {}), ensure_ascii=False),
                ))
            conn.commit()
    
    def save_daily_summary(self, summary: Dict):
        """保存每日汇总"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO daily_summary (
                    date, market_vix, north_flow, market_turnover,
                    up_down_ratio, total_signals, s_signals, a_signals, b_signals, raw_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                summary.get("date", datetime.now().strftime("%Y-%m-%d")),
                summary.get("market_vix"),
                summary.get("north_flow"),
                summary.get("market_turnover"),
                summary.get("up_down_ratio"),
                summary.get("total_signals", 0),
                summary.get("s_signals", 0),
                summary.get("a_signals", 0),
                summary.get("b_signals", 0),
                json.dumps(summary.get("raw", {}), ensure_ascii=False),
            ))
            conn.commit()
    
    def get_today_signals(self) -> List[Dict]:
        """获取今日所有信号"""
        today = datetime.now().strftime("%Y-%m-%d")
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM signals WHERE date = ? ORDER BY ABS(composite_score) DESC",
                (today,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_signals(self, days: int = 30) -> List[Dict]:
        """获取最近N天的信号"""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM signals 
                   WHERE date >= date('now', ?) 
                   ORDER BY date DESC, ABS(composite_score) DESC""",
                (f"-{days} days",)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_extreme_signals(self, threshold: float = 0.5) -> List[Dict]:
        """获取极端信号 (|score| >= threshold)"""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM signals 
                   WHERE ABS(composite_score) >= ? 
                   ORDER BY date DESC, ABS(composite_score) DESC""",
                (threshold,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_signal_history(self, asset_name: str, days: int = 90) -> List[Dict]:
        """获取单个资产的历史信号"""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM signals 
                   WHERE asset_name = ? AND date >= date('now', ?) 
                   ORDER BY date DESC""",
                (asset_name, f"-{days} days")
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_performance_stats(self, days: int = 90) -> Dict:
        """获取信号表现统计"""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            
            # 信号统计
            cursor = conn.execute(
                """SELECT signal_level, COUNT(*) as cnt 
                   FROM signals WHERE date >= date('now', ?) 
                   GROUP BY signal_level""",
                (f"-{days} days",)
            )
            level_counts = {row["signal_level"]: row["cnt"] for row in cursor.fetchall()}
            
            # 平均评分
            cursor = conn.execute(
                """SELECT AVG(composite_score) as avg_score, 
                   AVG(ABS(composite_score)) as avg_abs_score
                   FROM signals WHERE date >= date('now', ?)""",
                (f"-{days} days",)
            )
            score_stats = dict(cursor.fetchone())
            
            return {
                "level_counts": level_counts,
                "score_stats": score_stats,
                "days": days,
            }
