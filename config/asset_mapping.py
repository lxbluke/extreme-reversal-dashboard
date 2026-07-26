"""
全球大类资产极端状态反转策略 — 资产类别映射表
定义6大资产类别的跟踪标的列表
"""

# ============================================================
# 1. A股申万行业板块 (使用申万行业分类)
# ============================================================
A_SHARE_SECTORS = {
    "银行": {
        "pt_code": "pt01801080",
        "etf_long": ["sh512800", "sh512700"],
        "etf_short": [],  # A股行业暂无直接反向ETF
        "futures": [],
        "options": [],
    },
    "医药生物": {
        "pt_code": "pt01801100",
        "etf_long": ["sh512010", "sh512170"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "半导体": {
        "pt_code": "pt01801090",
        "etf_long": ["sh512480", "sh159995"],
        "etf_short": ["sz159995"],  # 芯片ETF有场内ETF期权，可买Put做空
        "futures": [],
        "options": ["sz159995.P"],  # 芯片ETF期权Put
    },
    "食品饮料": {
        "pt_code": "pt01801120",
        "etf_long": ["sh515170", "sh159928"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "新能源": {
        "pt_code": "pt01801110",
        "etf_long": ["sh516160", "sh515790"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "军工": {
        "pt_code": "pt01801070",
        "etf_long": ["sh512660", "sh512670"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "房地产": {
        "pt_code": "pt01801140",
        "etf_long": ["sh512200"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "券商": {
        "pt_code": "pt01801050",
        "etf_long": ["sh512880", "sh512000"],
        "etf_short": ["sh512880"],  # 证券ETF有场内ETF期权，可买Put做空
        "futures": [],
        "options": ["sh512880.P"],  # 证券ETF期权Put
    },
    "煤炭": {
        "pt_code": "pt01801150",
        "etf_long": ["sh515220"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "有色金属": {
        "pt_code": "pt01801130",
        "etf_long": ["sh512400"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "电力设备": {
        "pt_code": "pt01801060",
        "etf_long": ["sh516880", "sh516160"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "计算机": {
        "pt_code": "pt01801160",
        "etf_long": ["sh512720", "sh159998"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "通信": {
        "pt_code": "pt01801170",
        "etf_long": ["sh515880"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "电子": {
        "pt_code": "pt01801180",
        "etf_long": ["sh159997"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "汽车": {
        "pt_code": "pt01801190",
        "etf_long": ["sh516110"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "传媒": {
        "pt_code": "pt01801200",
        "etf_long": ["sh512980", "sh159805"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "基础化工": {
        "pt_code": "pt01801210",
        "etf_long": ["sh516120"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "钢铁": {
        "pt_code": "pt01801220",
        "etf_long": ["sh515210"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "建筑材料": {
        "pt_code": "pt01801230",
        "etf_long": ["sh159745"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
    "公用事业": {
        "pt_code": "pt01801240",
        "etf_long": ["sh159611"],
        "etf_short": [],
        "futures": [],
        "options": [],
    },
}

# ============================================================
# 2. 全球商品期货
# ============================================================
GLOBAL_COMMODITIES = {
    "黄金": {
        "code": "fuGC",
        "exchange": "COMEX",
        "etf_long": ["usGLD"],
        "etf_short": ["usGLL"],
        "futures": ["fuGC"],
        "options": [],
        "unit": "美元/盎司",
    },
    "原油(WTI)": {
        "code": "fuCL",
        "exchange": "NYMEX",
        "etf_long": ["usUSO"],
        "etf_short": ["usSCO"],
        "futures": ["fuCL"],
        "options": [],
        "unit": "美元/桶",
    },
    "布伦特原油": {
        "code": "fuBC",
        "exchange": "ICE",
        "etf_long": ["usBNO"],
        "etf_short": [],
        "futures": ["fuBC"],
        "options": [],
        "unit": "美元/桶",
    },
    "铜": {
        "code": "fuHG",
        "exchange": "COMEX",
        "etf_long": ["usCOPX"],
        "etf_short": [],
        "futures": ["fuHG"],
        "options": [],
        "unit": "美元/磅",
    },
    "白银": {
        "code": "fuSI",
        "exchange": "COMEX",
        "etf_long": ["usSLV"],
        "etf_short": ["usZSL"],
        "futures": ["fuSI"],
        "options": [],
        "unit": "美元/盎司",
    },
    "天然气": {
        "code": "fuNG",
        "exchange": "NYMEX",
        "etf_long": ["usUNG"],
        "etf_short": ["usKOLD"],
        "futures": ["fuNG"],
        "options": [],
        "unit": "美元/百万BTU",
    },
    "大豆": {
        "code": "fuZS",
        "exchange": "CBOT",
        "etf_long": ["usSOYB"],
        "etf_short": [],
        "futures": ["fuZS"],
        "options": [],
        "unit": "美分/蒲式耳",
    },
    "铁矿石": {
        "code": "fuSC",
        "exchange": "DCE",
        "etf_long": [],
        "etf_short": [],
        "futures": ["fuSC"],
        "options": [],
        "unit": "元/吨",
    },
}

# ============================================================
# 3. 美股行业ETF
# ============================================================
US_SECTOR_ETFS = {
    "科技": {
        "code": "usXLK",
        "name": "Technology Select Sector SPDR",
        "etf_short": [],
        "options": "买Put",
    },
    "金融": {
        "code": "usXLF",
        "name": "Financial Select Sector SPDR",
        "etf_short": ["usFAZ"],  # 金融三倍做空ETF
        "options": "买Put",
    },
    "医疗": {
        "code": "usXLV",
        "name": "Health Care Select Sector SPDR",
        "etf_short": [],  # 无直接反向ETF
        "options": "买Put",
    },
    "能源": {
        "code": "usXLE",
        "name": "Energy Select Sector SPDR",
        "etf_short": ["usERY", "usDUG"],  # 能源三倍做空(ERY)/石油天然气两倍做空(DUG)
        "options": "买Put",
    },
    "消费(可选)": {
        "code": "usXLY",
        "name": "Consumer Discretionary SPDR",
        "etf_short": [],
        "options": "买Put",
    },
    "消费(必选)": {
        "code": "usXLP",
        "name": "Consumer Staples Select Sector SPDR",
        "etf_short": [],
        "options": "买Put",
    },
    "工业": {
        "code": "usXLI",
        "name": "Industrial Select Sector SPDR",
        "etf_short": [],
        "options": "买Put",
    },
    "半导体": {
        "code": "usSMH",
        "name": "VanEck Semiconductor ETF",
        "etf_short": ["usSOXS"],
        "options": "买Put",
    },
    "生物科技": {
        "code": "usXBI",
        "name": "SPDR S&P Biotech ETF",
        "etf_short": ["usLABD"],
        "options": "买Put",
    },
    "房地产": {
        "code": "usXLRE",
        "name": "Real Estate Select Sector SPDR",
        "etf_short": [],
        "options": "买Put",
    },
    "公用事业": {
        "code": "usXLU",
        "name": "Utilities Select Sector SPDR",
        "etf_short": [],
        "options": "买Put",
    },
}

# ============================================================
# 4. 港股行业
# ============================================================
HK_SECTORS = {
    "恒生科技": {
        "pt_code": "hkHSTECH",
        "etf_long": ["sh513130", "hk03033"],  # A股+港股双选项
        "etf_short": ["hk07552"],  # XI二南方恒科(-2x)
        "futures": [],
        "options": [],
    },
    "恒生指数": {
        "pt_code": "hkHSI",
        "etf_long": ["hk02800"],
        "etf_short": ["hk07500"],  # FI二南方恒指(-2x)，之前hk07300错误
        "futures": ["r_hdHSImain"],
        "options": [],
    },
    "恒生中国企业": {
        "pt_code": "hkHSCEI",
        "etf_long": ["hk02828"],
        "etf_short": ["hk07588"],
        "futures": ["r_hdHHImain"],
        "options": [],
    },
    "港股银行": {
        "pt_code": "hkHSIFI",
        "etf_long": ["hk03057"],
        "etf_short": [],  # 无直接反向ETF，用恒指反向ETF(07500)近似对冲
        "futures": [],
        "options": [],
    },
    "港股医药": {
        "pt_code": "hkHSHCI",
        "etf_long": ["hk03069", "sh513120"],
        "etf_short": [],  # 无直接反向ETF，用恒科反向ETF(07552)近似对冲
        "futures": [],
        "options": [],
    },
    "港股地产": {
        "pt_code": "hkHSPI",
        "etf_long": ["hk03009"],
        "etf_short": [],  # 无直接反向ETF，用恒指反向ETF(07500)近似对冲
        "futures": [],
        "options": [],
    },
}

# ============================================================
# 5. 全球股指
# ============================================================
GLOBAL_INDICES = {
    "沪深300": {
        "code": "sh000300",
        "etf_long": ["sh510300"],
        "futures": ["IF"],
        "options": ["IO"],
        "currency": "CNY",
    },
    "中证500": {
        "code": "sh000905",
        "etf_long": ["sh510500"],
        "futures": ["IC"],
        "options": [],
        "currency": "CNY",
    },
    "上证50": {
        "code": "sh000016",
        "etf_long": ["sh510050"],
        "futures": ["IH"],
        "options": ["510050.SH"],
        "currency": "CNY",
    },
    "标普500": {
        "code": "usINX",
        "etf_long": ["usSPY", "usVOO"],
        "etf_short": ["usSH", "usSDS", "usSPXU"],  # 做空(SH)/两倍做空(SDS)/三倍做空(SPXU)
        "futures": ["ES"],
        "options": ["SPX"],
        "currency": "USD",
    },
    "纳斯达克100": {
        "code": "usNDX",
        "etf_long": ["usQQQ"],
        "etf_short": ["usPSQ", "usQID", "usSQQQ"],  # 做空(PSQ)/两倍做空(QID)/三倍做空(SQQQ)
        "futures": ["NQ"],
        "options": ["NDX"],
        "currency": "USD",
    },
    "道琼斯": {
        "code": "usDJI",
        "etf_long": ["usDIA"],
        "etf_short": ["usDXD", "usSDOW"],  # 两倍做空(DXD)/三倍做空(SDOW)
        "futures": ["YM"],
        "options": [],
        "currency": "USD",
    },
    "日经225": {
        "code": "jpN225",
        "etf_long": ["usEWJ", "usDXJ"],
        "etf_short": [],  # 无直接反向ETF，用期货空头
        "futures": ["NK"],
        "options": [],
        "currency": "JPY",
    },
    "欧洲斯托克50": {
        "code": "euSX5E",
        "etf_long": ["usFEZ"],
        "etf_short": [],  # 无直接反向ETF，用期货空头
        "futures": ["FESX"],
        "options": [],
        "currency": "EUR",
    },
    "恒生指数": {
        "code": "hkHSI",
        "etf_long": ["hk02800", "sh510900"],
        "etf_short": ["hk07500"],  # FI二南方恒指(-2x)，之前hk07300错误
        "futures": ["r_hdHSImain"],
        "options": [],
        "currency": "HKD",
    },
}

# ============================================================
# 6. 外汇/债券
# ============================================================
FX_BOND_ASSETS = {
    "离岸人民币": {
        "code": "fxCNH",
        "type": "forex",
        "etf_long": [],
        "futures": [],
        "currency_pair": "USD/CNH",
    },
    "美元指数": {
        "code": "fxDINIW",
        "type": "forex",
        "etf_long": ["usUUP"],
        "etf_short": ["usUDN"],
        "futures": ["DX"],
        "currency_pair": "DXY",
    },
    "欧元/美元": {
        "code": "fxEURUSD",
        "type": "forex",
        "etf_long": ["usFXE"],
        "etf_short": ["usEUO"],
        "futures": ["6E"],
    },
    "日元/美元": {
        "code": "fxUSDJPY",
        "type": "forex",
        "etf_long": ["usFXY"],
        "etf_short": ["usYCS"],
        "futures": ["6J"],
    },
    "10年美债": {
        "code": "us10Y",
        "type": "bond",
        "etf_long": ["usTLT", "usIEF"],
        "etf_short": ["usTBT", "usTMV"],
        "futures": ["ZN"],
    },
    "30年美债": {
        "code": "us30Y",
        "type": "bond",
        "etf_long": ["usTLT"],
        "etf_short": ["usTBT"],
        "futures": ["ZB"],
    },
    "中国10年国债": {
        "code": "cn10Y",
        "type": "bond",
        "etf_long": ["sh511010"],
        "etf_short": [],
        "futures": ["T"],
    },
}

# ============================================================
# 聚合函数
# ============================================================
def get_all_assets():
    """获取所有资产类别的跟踪标的"""
    return {
        "a_share_sector": A_SHARE_SECTORS,
        "commodity": GLOBAL_COMMODITIES,
        "us_etf": US_SECTOR_ETFS,
        "hk_sector": HK_SECTORS,
        "global_index": GLOBAL_INDICES,
        "fx_bond": FX_BOND_ASSETS,
    }

def get_asset_class(asset_key: str) -> str:
    """根据资产代码判断资产类别"""
    if asset_key in A_SHARE_SECTORS:
        return "a_share_sector"
    if asset_key in GLOBAL_COMMODITIES:
        return "commodity"
    if asset_key in US_SECTOR_ETFS:
        return "us_etf"
    if asset_key in HK_SECTORS:
        return "hk_sector"
    if asset_key in GLOBAL_INDICES:
        return "global_index"
    if asset_key in FX_BOND_ASSETS:
        return "fx_bond"
    return None

def get_asset_info(asset_key: str):
    """获取资产详细信息"""
    for category, assets in get_all_assets().items():
        if asset_key in assets:
            return {"category": category, **assets[asset_key]}
    return None
