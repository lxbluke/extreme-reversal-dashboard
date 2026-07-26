"""
数据采集层 — westock-data CLI封装
封装所有 westock-data CLI 命令，提供统一的数据接口
"""

import subprocess
import json
import re
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

WESTOCK_BIN = "npx"
WESTOCK_ARGS = ["-y", "westock-data-skillhub@1.0.5"]
WESTOCK_TIMEOUT = 60  # 单个CLI命令超时（秒）


def _run_cli(cmd: str, timeout: int = WESTOCK_TIMEOUT) -> str:
    """执行 westock-data CLI 命令并返回输出"""
    full_cmd = [WESTOCK_BIN] + WESTOCK_ARGS + cmd.split()
    try:
        result = subprocess.run(
            full_cmd, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            logger.warning(f"CLI命令返回非零: {cmd}\nstderr: {result.stderr[:200]}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"CLI命令超时: {cmd}")
        return ""
    except Exception as e:
        logger.error(f"CLI命令异常: {cmd}, {e}")
        return ""


def _parse_number(text: str) -> Optional[float]:
    """从文本中提取数字"""
    if not text:
        return None
    # 去除百分号和逗号
    cleaned = text.replace("%", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        # 尝试正则提取
        match = re.search(r'[-+]?\d+\.?\d*', cleaned)
        return float(match.group()) if match else None


def _parse_percentile(text: str) -> Optional[float]:
    """从文本中提取分位数值(0-100)"""
    if not text:
        return None
    val = _parse_number(text)
    if val is not None:
        if val > 1:  # 已经是百分数
            return val / 100.0
        return val
    return None


# ============================================================
# 1. 行业板块估值数据
# ============================================================
def get_sector_valuation(pt_code: str) -> Dict:
    """
    获取行业板块估值数据 (PE/PB/PS + 历史分位)
    命令: sector valuation <pt代码>
    
    新格式表格:
    | DivTTM | DivTTMPct | ... | PeTTM | PeTTMPct | ... | PsTTM | PsTTMPct | ... | PbLF | PbLFPct | ... | code | name |
    """
    output = _run_cli(f"sector valuation {pt_code}")
    if not output:
        return {}
    
    result = {
        "pt_code": pt_code,
        "pe_ttm": None,
        "pb": None,
        "ps_ttm": None,
        "pe_percentile": None,
        "pb_percentile": None,
        "ps_percentile": None,
        "dividend_yield": None,
        "dividend_yield_percentile": None,
        "raw": output,
    }
    
    lines = output.split("\n")
    
    # 寻找表格头行和数据行
    header_line = None
    data_line = None
    for i, line in enumerate(lines):
        if "PeTTM" in line and "PsTTM" in line and line.startswith("|"):
            header_line = line
            if i + 2 < len(lines):
                data_line = lines[i + 2]
            break
    
    if header_line and data_line:
        headers = [h.strip() for h in header_line.split("|") if h.strip()]
        values = [v.strip() for v in data_line.split("|") if v.strip()]
        
        # 字段名映射
        field_map = {
            "PeTTM": "pe_ttm", "PeTTMPct": "pe_percentile",
            "PbLF": "pb", "PbLFPct": "pb_percentile",
            "PsTTM": "ps_ttm", "PsTTMPct": "ps_percentile",
            "DivTTM": "dividend_yield", "DivTTMPct": "dividend_yield_percentile",
            "PcfTTM": "pcf_ttm", "PcfTTMPct": "pcf_percentile",
        }
        
        for h, v in zip(headers, values):
            key = field_map.get(h)
            if key:
                val = _parse_number(v)
                if key.endswith("_percentile") or key.endswith("_pct"):
                    # 分位值: CLI返回的已经是百分比数值(如96.92), 转为0-1
                    result[key] = val / 100.0 if val is not None else None
                else:
                    result[key] = val
    
    return result


def get_sector_ranking() -> List[Dict]:
    """获取全市场行业板块行情排名"""
    output = _run_cli("sector ranking")
    if not output:
        return []
    
    sectors = []
    lines = output.split("\n")
    for line in lines:
        # 解析表格行
        if not line.strip() or "----" in line or "代码" in line or "排名" in line:
            continue
        parts = line.split()
        if len(parts) >= 3:
            sectors.append({
                "name": parts[0] if len(parts) > 0 else "",
                "code": parts[1] if len(parts) > 1 else "",
                "change_pct": _parse_number(parts[2]) if len(parts) > 2 else None,
                "raw": line,
            })
    return sectors


def get_sector_constituent(pt_code: str) -> List[str]:
    """获取板块成份股列表"""
    output = _run_cli(f"sector constituent {pt_code}")
    if not output:
        return []
    
    stocks = []
    for line in output.split("\n"):
        # 匹配股票代码模式
        codes = re.findall(r'(sh|sz|bj)\d{6}', line)
        stocks.extend(codes)
    return stocks


# ============================================================
# 2. K线数据
# ============================================================
def get_kline(code: str, period: str = "day", limit: int = 250) -> List[Dict]:
    """
    获取K线数据
    命令: kline <代码> --period <周期> --limit <数量>
    
    Returns:
        [{"date": "2026-01-01", "open": ..., "close": ..., "high": ..., "low": ..., "volume": ...}, ...]
    """
    output = _run_cli(f"kline {code} --period {period} --limit {limit}")
    if not output:
        return []
    
    klines = []
    lines = output.split("\n")
    for line in lines:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 5:
            try:
                kline = {
                    "date": parts[0],
                    "open": float(parts[1].replace(",", "")),
                    "close": float(parts[2].replace(",", "")),
                    "high": float(parts[3].replace(",", "")),
                    "low": float(parts[4].replace(",", "")),
                    "volume": float(parts[5].replace(",", "")) if len(parts) >= 6 else 0,
                }
                klines.append(kline)
            except (ValueError, IndexError):
                continue
    return klines


def get_technical(code: str, indicator: str = "rsi") -> Dict:
    """
    获取技术指标
    命令: technical <代码> --indicator <指标名>
    """
    output = _run_cli(f"technical {code} --indicator {indicator}")
    if not output:
        return {}
    
    result = {"indicator": indicator, "values": []}
    lines = output.split("\n")
    for line in lines:
        nums = re.findall(r'[\d.]+', line)
        if nums:
            try:
                result["values"].append(float(nums[0]))
            except ValueError:
                continue
    return result


# ============================================================
# 3. ETF数据
# ============================================================
def get_etf_detail(code: str) -> Dict:
    """获取ETF详细信息"""
    output = _run_cli(f"etf detail {code}")
    if not output:
        return {}
    
    result = {"code": code, "raw": output}
    for line in output.split("\n"):
        if "规模" in line or "资产" in line:
            nums = re.findall(r'[\d.]+', line)
            if nums:
                result["aum"] = float(nums[0])
        if "PE" in line or "市盈率" in line:
            nums = re.findall(r'[\d.]+', line)
            if nums:
                result["pe"] = float(nums[0])
    return result


def get_etf_nav(code: str, limit: int = 250) -> List[Dict]:
    """获取ETF净值历史"""
    output = _run_cli(f"etf nav {code}")
    if not output:
        return []
    
    navs = []
    lines = output.split("\n")
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            try:
                navs.append({"date": parts[0], "nav": float(parts[1])})
            except ValueError:
                continue
    return navs[:limit]


# ============================================================
# 4. 资金流向数据
# ============================================================
def get_fund_flow(code: str) -> Dict:
    """
    获取资金流向（个股或板块）
    命令: fund flow <代码>
    
    板块代码(如 pt01801080)会返回多维资金流：
    - MainNetFlow: 当日主力净流入
    - MainNetFlow5D: 5日主力净流入
    - MainNetFlow10D: 10日主力净流入
    - MainNetFlow20D: 20日主力净流入
    - JumboNetFlow: 超大单净流入
    """
    output = _run_cli(f"fund flow {code}")
    if not output:
        return {}
    
    result = {"code": code, "raw": output}
    
    # 解析Markdown表格
    lines = output.split("\n")
    header_line = None
    data_line = None
    
    for i, line in enumerate(lines):
        if line.startswith("|") and "code" in line.lower() and "name" in line.lower():
            header_line = line
            # 数据行通常在header之后2行（中间有|---|---|）
            if i + 2 < len(lines):
                data_line = lines[i + 2]
    
    if header_line and data_line:
        headers = [h.strip() for h in header_line.split("|") if h.strip()]
        values = [v.strip() for v in data_line.split("|") if v.strip()]
        
        # 构建字段名到值的映射
        for h, v in zip(headers, values):
            if h == "MainNetFlow":
                result["main_flow"] = _parse_number(v)
            elif h == "MainNetFlow5D":
                result["main_flow_5d"] = _parse_number(v)
            elif h == "MainNetFlow10D":
                result["main_flow_10d"] = _parse_number(v)
            elif h == "MainNetFlow20D":
                result["main_flow_20d"] = _parse_number(v)
            elif h == "JumboNetFlow":
                result["jumbo_flow"] = _parse_number(v)
            elif h == "MainInFlow":
                result["main_in_flow"] = _parse_number(v)
            elif h == "MainOutFlow":
                result["main_out_flow"] = _parse_number(v)
            elif h == "RetailInFlow":
                result["retail_in_flow"] = _parse_number(v)
            elif h == "RetailOutFlow":
                result["retail_out_flow"] = _parse_number(v)
    
    # 兼容旧格式解析
    if not result.get("main_flow"):
        for line in lines:
            if "主力" in line or "超大单" in line or "大单" in line:
                nums = re.findall(r'[-+]?\d+\.?\d*', line)
                if nums:
                    result["main_flow"] = float(nums[0])
    
    return result


def get_fund_flow_history(pt_code: str, days: int = 12) -> List[Dict]:
    """
    获取板块每日资金流向历史
    命令: fund flow <pt代码> --start <日期> --end <日期>
    
    Returns:
        [{"date": "2026-07-14", "main_flow": -1392389410.0}, ...]
    """
    from datetime import datetime, timedelta
    end = datetime.now()
    # 估算days个交易日（按1.4倍日历日估算周末）
    start = end - timedelta(days=int(days * 1.4) + 5)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    
    output = _run_cli(f"fund flow {pt_code} --start {start_str} --end {end_str}")
    if not output:
        return []
    
    result = []
    lines = output.split("\n")
    header_line = None
    data_start = False
    
    for i, line in enumerate(lines):
        if line.startswith("|") and "date" in line.lower() and "MainNetFlow" in line:
            header_line = line
            headers = [h.strip() for h in header_line.split("|") if h.strip()]
            # 数据行从i+2开始
            for j in range(i + 2, len(lines)):
                row = lines[j]
                if not row.startswith("|"):
                    continue
                values = [v.strip() for v in row.split("|") if v.strip()]
                if len(values) < 2:
                    continue
                row_data = {}
                for h, v in zip(headers, values):
                    if h == "date":
                        row_data["date"] = v
                    elif h == "MainNetFlow":
                        row_data["main_flow"] = _parse_number(v)
                if "date" in row_data and "main_flow" in row_data:
                    result.append(row_data)
            break
    
    # 按日期排序（从旧到新）
    result.sort(key=lambda x: x.get("date", ""))
    return result[-days:]  # 只保留最近days条


def get_north_holding(code: str) -> Dict:
    """
    获取北向资金持仓（个股或行业板块）
    命令: fund north-holding <代码>
    返回北向持仓市值及季度/年度变动
    
    输出格式示例：
    | 行业 | 持股市值 | 市值季变动 | 市值年变动 |
    | --- | --- | --- | --- |
    | 电子 | 783007700547.83 | 9532760278.14 | 35119039091.52 |
    """
    output = _run_cli(f"fund north-holding {code}")
    if not output:
        return {}
    
    result = {"code": code, "raw": output}
    lines = output.split("\n")
    
    # 解析Markdown表格格式
    header_line = None
    data_line = None
    
    for i, line in enumerate(lines):
        if line.startswith("|") and "持股市值" in line:
            header_line = line
            if i + 2 < len(lines):
                data_line = lines[i + 2]
            break
    
    if header_line and data_line:
        headers = [h.strip() for h in header_line.split("|") if h.strip()]
        values = [v.strip() for v in data_line.split("|") if v.strip()]
        
        for h, v in zip(headers, values):
            if h == "持股市值":
                val = _parse_number(v)
                if val:
                    result["holding_value"] = val
            elif h == "市值季变动":
                val = _parse_number(v)
                if val:
                    result["quarterly_change"] = val
            elif h == "市值年变动":
                val = _parse_number(v)
                if val:
                    result["yearly_change"] = val
    
    return result


def get_south_holding(code: str) -> Dict:
    """获取南向资金持仓"""
    output = _run_cli(f"fund south-holding {code}")
    if not output:
        return {}
    
    result = {"code": code, "raw": output}
    for line in output.split("\n"):
        if "持股" in line or "持仓" in line:
            nums = re.findall(r'[\d.]+', line)
            if nums:
                result["holding_value"] = float(nums[0])
    return result


def get_short_data(code: str) -> Dict:
    """获取卖空数据（港股/美股）"""
    output = _run_cli(f"fund short {code}")
    if not output:
        return {}
    
    result = {"code": code, "raw": output}
    for line in output.split("\n"):
        if "卖空" in line or "short" in line.lower():
            nums = re.findall(r'[\d.]+', line)
            if nums:
                result["short_ratio"] = float(nums[0])
    return result


# ============================================================
# 5. 宏观指标
# ============================================================
def get_macro_indicator(indicator: str, date_str: str = None) -> Dict:
    """
    获取宏观经济指标
    命令: macro indicator <指标名> --date <日期>
    
    常用指标:
    - cn_core: 中国核心宏观
    - cn_premium_value: 股债性价比(ERP)
    - cn_premium_curve: 溢价率曲线
    - cn_term_spread: 期限利差
    - cn_yield_curve: 国债收益率曲线
    - cn_mlf: MLF操作
    - us_monetary: 美联储政策
    """
    cmd = f"macro indicator {indicator}"
    if date_str:
        cmd += f" --date {date_str}"
    
    output = _run_cli(cmd)
    if not output:
        return {}
    
    result = {"indicator": indicator, "raw": output}
    lines = output.split("\n")
    for line in lines:
        # 尝试提取数值
        nums = re.findall(r'[-+]?\d+\.?\d*', line)
        if nums and len(nums) >= 1:
            key = line.split(":")[0].strip() if ":" in line else "value"
            result[key] = float(nums[0])
            if len(nums) >= 2:
                result[f"{key}_pct"] = float(nums[1])
    return result


def get_market_overview(view_type: str = "valuation") -> Dict:
    """获取市场总览"""
    output = _run_cli(f"market-overview --type {view_type}")
    if not output:
        return {}
    return {"type": view_type, "raw": output}


def get_changedist() -> Dict:
    """获取全市场涨跌分布"""
    output = _run_cli("changedist")
    if not output:
        return {}
    
    result = {"raw": output}
    lines = output.split("\n")
    for line in lines:
        if line.startswith("|"):
            parts = [p.strip() for p in line.split("|")]
            # 第一行: 上涨|下跌|平盘|涨停|跌停|停牌|上涨占比
            if "上涨" in parts and "下跌" in parts:
                for p in parts:
                    if p.replace(".","").isdigit() or p.endswith("%"):
                        pass
                nums = [p for p in parts if p.replace(".","").replace("%","").isdigit()]
                if len(nums) >= 7:
                    result["up_count"] = int(nums[0])
                    result["down_count"] = int(nums[1])
                    result["flat_count"] = int(nums[2])
                    result["up_limit"] = int(nums[3])
                    result["down_limit"] = int(nums[4])
                    result["suspended"] = int(nums[5])
                    result["up_ratio"] = float(nums[6].replace("%","")) if "%" in nums[6] else float(nums[6])
                    result["up_ratio_pct"] = result.get("up_ratio", 0)
            # 涨跌幅区间行
            if len(parts) >= 3:
                interval = parts[1].strip()
                count = parts[2].strip()
                if interval and count.replace(".","").isdigit() and "区间" not in interval.lower():
                    result[f"range_{interval}"] = int(count)
        
        if "成交额" in line:
            nums = re.findall(r'[\d.]+', line)
            if nums:
                result["total_volume"] = float(nums[0])
    
    # 兼容旧格式
    if not result.get("up_count"):
        for line in lines:
            if "上涨" in line:
                nums = re.findall(r'\d+', line)
                if nums:
                    result["up_count"] = int(nums[0])
            if "下跌" in line:
                nums = re.findall(r'\d+', line)
                if nums:
                    result["down_count"] = int(nums[0])
    
    return result


# ============================================================
# 6. 龙虎榜
# ============================================================
def get_lhb(institution_type: str = "all") -> List[Dict]:
    """获取龙虎榜数据"""
    output = _run_cli(f"lhb --type {institution_type}")
    if not output:
        return []
    
    entries = []
    lines = output.split("\n")
    for line in lines:
        codes = re.findall(r'(sh|sz|bj)\d{6}', line)
        if codes:
            entries.append({"code": codes[0], "raw": line})
    return entries


# ============================================================
# 7. 搜索功能
# ============================================================
def search_assets(keyword: str, asset_type: str = None) -> List[Dict]:
    """
    搜索资产
    命令: search <关键词> --type <类型>
    类型: sector, futures, forex, etf, stock
    """
    cmd = f"search {keyword}"
    if asset_type:
        cmd += f" --type {asset_type}"
    
    output = _run_cli(cmd)
    if not output:
        return []
    
    results = []
    lines = output.split("\n")
    for line in lines:
        codes = re.findall(r'(sh|sz|bj|hk|us|fu|fx|pt)\w*', line)
        if codes:
            results.append({"code": codes[0], "name": keyword, "raw": line})
    return results


# ============================================================
# 复合查询函数
# ============================================================
def get_sector_full_data(pt_code: str, sector_name: str) -> Dict:
    """
    获取行业板块完整数据包
    包含: 估值、资金流向、北向持仓、成份股
    """
    data = {
        "name": sector_name,
        "pt_code": pt_code,
        "valuation": get_sector_valuation(pt_code),
        "fund_flow": get_fund_flow(pt_code),
        "north_holding": get_north_holding(pt_code),
        "constituents": get_sector_constituent(pt_code),
        "timestamp": datetime.now().isoformat(),
    }
    return data


def get_commodity_full_data(code: str, name: str) -> Dict:
    """获取商品期货完整数据包"""
    data = {
        "name": name,
        "code": code,
        "kline_1y": get_kline(code, "day", 250),
        "kline_3m": get_kline(code, "day", 66),
        "kline_1m": get_kline(code, "day", 22),
        "technical_rsi": get_technical(code, "rsi"),
        "timestamp": datetime.now().isoformat(),
    }
    return data


def get_index_full_data(code: str, name: str) -> Dict:
    """获取全球股指完整数据包"""
    data = {
        "name": name,
        "code": code,
        "kline_1y": get_kline(code, "day", 250),
        "kline_3m": get_kline(code, "day", 66),
        "technical_rsi": get_technical(code, "rsi"),
        "timestamp": datetime.now().isoformat(),
    }
    return data
