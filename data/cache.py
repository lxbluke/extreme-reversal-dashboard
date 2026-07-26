"""
数据采集层 — 数据缓存模块
提供日频数据缓存，减少重复CLI调用
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DataCache:
    """简单的文件系统缓存，用于日频数据"""
    
    def __init__(self, cache_dir: Path, ttl_hours: int = 6):
        """
        Args:
            cache_dir: 缓存目录
            ttl_hours: 缓存有效期（小时），默认6小时（覆盖盘中到盘后）
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_hours = ttl_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _cache_key(self, key: str) -> str:
        """生成缓存文件名"""
        # 日期作为前缀，保证每天第一次获取时会刷新
        today = datetime.now().strftime("%Y%m%d")
        safe_key = key.replace("/", "_").replace(":", "_").replace(" ", "_")
        return f"{today}_{safe_key}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        cache_file = self.cache_dir / self._cache_key(key)
        if not cache_file.exists():
            return None
        
        # 检查是否过期
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - mtime > timedelta(hours=self.ttl_hours):
            return None
        
        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"缓存读取失败: {cache_file}, {e}")
            return None
    
    def set(self, key: str, value: Any):
        """设置缓存数据"""
        cache_file = self.cache_dir / self._cache_key(key)
        try:
            with open(cache_file, "w") as f:
                json.dump(value, f, ensure_ascii=False, default=str)
        except IOError as e:
            logger.warning(f"缓存写入失败: {cache_file}, {e}")
    
    def invalidate(self, key: str = None):
        """清除缓存"""
        if key:
            cache_file = self.cache_dir / self._cache_key(key)
            if cache_file.exists():
                cache_file.unlink()
        else:
            # 清除今天的所有缓存
            today = datetime.now().strftime("%Y%m%d")
            for f in self.cache_dir.glob(f"{today}_*.json"):
                f.unlink()
    
    def cleanup(self, max_age_days: int = 7):
        """清理过期缓存文件"""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        for f in self.cache_dir.glob("*.json"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
