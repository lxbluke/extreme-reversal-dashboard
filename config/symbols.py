"""
全球大类资产极端状态反转策略 — 可交易标的完全映射表
提供6大资产类别的做多/做空ETF、期权、期货和反向ETF代码

数据来源：腾讯自选股(westock-data) 已验证
"""

# ============================================================
# A股行业 → 做多ETF映射
# ============================================================
A_SHARE_ETF_LONG = {
    "银行":     {"primary": "sh512800", "alt": "sh512700", "name": "银行ETF华宝"},
    "医药生物": {"primary": "sh512010", "alt": "sh512170", "name": "医药ETF"},
    "半导体":   {"primary": "sh512480", "alt": "sh159995", "name": "半导体ETF"},
    "食品饮料": {"primary": "sh515170", "alt": "sh159928", "name": "食品饮料ETF"},
    "新能源":   {"primary": "sh516160", "alt": "sh515790", "name": "新能源ETF"},
    "光伏":     {"primary": "sh515790", "alt": "", "name": "光伏ETF"},
    "军工":     {"primary": "sh512660", "alt": "sh512670", "name": "军工ETF"},
    "房地产":   {"primary": "sh512200", "alt": "", "name": "房地产ETF"},
    "券商":     {"primary": "sh512880", "alt": "sh512000", "name": "证券ETF"},
    "煤炭":     {"primary": "sh515220", "alt": "", "name": "煤炭ETF"},
    "有色金属": {"primary": "sh512400", "alt": "", "name": "有色ETF"},
    "电力设备": {"primary": "sh516880", "alt": "sh516160", "name": "电力ETF"},
    "计算机":   {"primary": "sh512720", "alt": "sh159998", "name": "计算机ETF"},
    "通信":     {"primary": "sh515880", "alt": "", "name": "通信ETF"},
    "电子":     {"primary": "sh159997", "alt": "", "name": "电子ETF"},
    "汽车":     {"primary": "sh516110", "alt": "", "name": "汽车ETF"},
    "传媒":     {"primary": "sh512980", "alt": "sh159805", "name": "传媒ETF"},
    "基础化工": {"primary": "sh516120", "alt": "", "name": "化工ETF"},
    "钢铁":     {"primary": "sh515210", "alt": "", "name": "钢铁ETF"},
    "建筑材料": {"primary": "sh159745", "alt": "", "name": "建材ETF"},
    "公用事业": {"primary": "sh159611", "alt": "", "name": "公用事业ETF"},
}

# ============================================================
# A股行业 → 做空工具映射（分层策略）
# Tier 1: 有场内ETF期权的行业 → 直接买Put
# Tier 2: 可通过融券做空行业ETF
# Tier 3: 无直接工具 → 用宽基ETF期权近似对冲
#
# 当前A股场内ETF期权标的（9只）：
#   510050(上证50ETF)、510300/159919(沪深300)、510500/159922(中证500)
#   159915(创业板)、159901(深证100)、588000(科创50)
#   159995(芯片ETF)、512880(证券ETF)
# ============================================================
A_SHARE_SHORT_TOOLS = {
    # Tier 1 — 有场内ETF期权
    "半导体": {
        "type": "ETF期权Put",
        "code": "sz159995",
        "name": "芯片ETF",
        "tier": 1,
        "note": "场内ETF期权，买Put做空"  # sz159995有场内ETF期权
    },
    "券商": {
        "type": "ETF期权Put",
        "code": "sh512880",
        "name": "证券ETF",
        "tier": 1,
        "note": "场内ETF期权，买Put做空"  # sh512880有场内ETF期权
    },
    # Tier 2 — 融券做空行业ETF（需券源）
    "银行": {
        "type": "ETF融券",
        "code": "sh512800",
        "name": "银行ETF",
        "tier": 2,
        "note": "融券做空/替代：上证50ETF期权Put(510050)"
    },
    "医药生物": {
        "type": "ETF融券",
        "code": "sh512010",
        "name": "医药ETF",
        "tier": 2,
        "note": "融券做空/替代：沪深300ETF期权Put(510300)"
    },
    "食品饮料": {
        "type": "ETF融券",
        "code": "sh515170",
        "name": "食品饮料ETF",
        "tier": 2,
        "note": "融券做空/替代：沪深300ETF期权Put(510300)"
    },
    "新能源": {
        "type": "ETF融券",
        "code": "sh516160",
        "name": "新能源ETF",
        "tier": 2,
        "note": "融券做空/替代：创业板ETF期权Put(159915)"
    },
    "电力设备": {
        "type": "ETF融券",
        "code": "sh516880",
        "name": "电力ETF",
        "tier": 2,
        "note": "融券做空/替代：创业板ETF期权Put(159915)"
    },
    "计算机": {
        "type": "ETF融券",
        "code": "sh512720",
        "name": "计算机ETF",
        "tier": 2,
        "note": "融券做空/替代：科创50ETF期权Put(588000)"
    },
    "通信": {
        "type": "ETF融券",
        "code": "sh515880",
        "name": "通信ETF",
        "tier": 2,
        "note": "融券做空/替代：科创50ETF期权Put(588000)"
    },
    "电子": {
        "type": "ETF融券",
        "code": "sz159997",
        "name": "电子ETF",
        "tier": 2,
        "note": "融券做空/替代：科创50ETF期权Put(588000)"
    },
    "汽车": {
        "type": "ETF融券",
        "code": "sh516110",
        "name": "汽车ETF",
        "tier": 2,
        "note": "融券做空/替代：沪深300ETF期权Put(510300)"
    },
    "传媒": {
        "type": "ETF融券",
        "code": "sh512980",
        "name": "传媒ETF",
        "tier": 2,
        "note": "融券做空/替代：中证500ETF期权Put(510500)"
    },
    "军工": {
        "type": "ETF融券",
        "code": "sh512660",
        "name": "军工ETF",
        "tier": 2,
        "note": "融券做空/替代：沪深300ETF期权Put(510300)"
    },
    "有色金属": {
        "type": "ETF融券",
        "code": "sh512400",
        "name": "有色ETF",
        "tier": 2,
        "note": "融券做空/替代：沪深300ETF期权Put(510300)"
    },
    "基础化工": {
        "type": "ETF融券",
        "code": "sh516120",
        "name": "化工ETF",
        "tier": 2,
        "note": "融券做空/替代：中证500ETF期权Put(510500)"
    },
    # Tier 3 — 无直接工具，宽基期权对冲
    "房地产": {
        "type": "宽基期权对冲",
        "code": "sh510300",
        "name": "沪深300ETF期权Put",
        "tier": 3,
        "note": "无直接行业ETF期权，用沪深300ETF期权Put近似对冲"
    },
    "煤炭": {
        "type": "宽基期权对冲",
        "code": "sh510300",
        "name": "沪深300ETF期权Put",
        "tier": 3,
        "note": "无直接行业ETF期权，用沪深300ETF期权Put近似对冲"
    },
    "钢铁": {
        "type": "宽基期权对冲",
        "code": "sh510500",
        "name": "中证500ETF期权Put",
        "tier": 3,
        "note": "无直接行业ETF期权，用中证500ETF期权Put近似对冲"
    },
    "建筑材料": {
        "type": "宽基期权对冲",
        "code": "sh510500",
        "name": "中证500ETF期权Put",
        "tier": 3,
        "note": "无直接行业ETF期权，用中证500ETF期权Put近似对冲"
    },
    "公用事业": {
        "type": "宽基期权对冲",
        "code": "sh510300",
        "name": "沪深300ETF期权Put",
        "tier": 3,
        "note": "无直接行业ETF期权，用沪深300ETF期权Put近似对冲"
    },
}

# ============================================================
# A股宽基ETF做空/对冲工具（通用）
# ============================================================
A_SHARE_BROAD_SHORT = {
    "上证50":     {"type": "期权Put", "code": "sh510050", "name": "上证50ETF期权", "note": "最流动的ETF期权"},
    "沪深300":    {"type": "期权Put", "code": "sh510300", "name": "沪深300ETF期权", "note": "覆盖大盘对冲"},
    "中证500":    {"type": "期权Put", "code": "sh510500", "name": "中证500ETF期权", "note": "覆盖中盘对冲"},
    "创业板":     {"type": "期权Put", "code": "sz159915", "name": "创业板ETF期权", "note": "覆盖成长股对冲"},
    "科创50":     {"type": "期权Put", "code": "sh588000", "name": "科创50ETF期权", "note": "覆盖科技股对冲"},
}

# ============================================================
# 全球商品期货 → ETF做多
# ============================================================
COMMODITY_ETF_LONG = {
    "黄金":     {"primary": "usGLD",   "alt_a": "sh518880", "alt_b": "sz159934", "name": "SPDR黄金ETF/华安黄金ETF"},
    "原油(WTI)": {"primary": "usUSO",  "alt_a": "sh501018", "alt_b": "", "name": "USO原油ETF/南方原油LOF"},
    "布伦特原油": {"primary": "usBNO", "alt_a": "", "alt_b": "", "name": "BNO布伦特原油ETF"},
    "铜":       {"primary": "usCOPX", "alt_a": "", "alt_b": "", "name": "全球铜矿ETF"},
    "白银":     {"primary": "usSLV",  "alt_a": "", "alt_b": "", "name": "iShares白银信托"},
    "天然气":   {"primary": "usUNG",  "alt_a": "", "alt_b": "", "name": "美国天然气ETF"},
    "大豆":     {"primary": "usSOYB", "alt_a": "", "alt_b": "", "name": "Teucrium大豆ETF"},
    "铁矿石":   {"primary": "", "alt_a": "", "alt_b": "", "name": "无直接ETF，用期货"},  # 无直接ETF
}

# ============================================================
# 全球商品期货 → ETF做空/反向
# ============================================================
COMMODITY_ETF_SHORT = {
    "黄金":     {"primary": "usGLL", "alt": "usDZZ", "name": "黄金两倍做空ETF", "leverage": -2},
    "原油(WTI)": {"primary": "usSCO", "alt": "", "name": "原油两倍做空ETF", "leverage": -2},
    "布伦特原油": {"primary": "", "alt": "", "name": "无直接反向ETF，用期货空头", "leverage": 0},
    "铜":       {"primary": "", "alt": "", "name": "无直接反向ETF，用期货空头", "leverage": 0},
    "白银":     {"primary": "usZSL", "alt": "", "name": "白银两倍做空ETF", "leverage": -2},
    "天然气":   {"primary": "usKOLD", "alt": "", "name": "天然气做空ETF", "leverage": -1},
    "大豆":     {"primary": "", "alt": "", "name": "无直接反向ETF，用期货空头", "leverage": 0},
    "铁矿石":   {"primary": "", "alt": "", "name": "无直接反向ETF，用期货空头", "leverage": 0},
}

# ============================================================
# 美股行业ETF → 做多（已在asset_mapping中，这里补全细节）
# ============================================================
US_ETF_LONG = {
    "科技":        {"code": "usXLK", "name": "Technology Select Sector SPDR"},
    "金融":        {"code": "usXLF", "name": "Financial Select Sector SPDR"},
    "医疗":        {"code": "usXLV", "name": "Health Care Select Sector SPDR"},
    "能源":        {"code": "usXLE", "name": "Energy Select Sector SPDR"},
    "消费(可选)":  {"code": "usXLY", "name": "Consumer Discretionary SPDR"},
    "消费(必选)":  {"code": "usXLP", "name": "Consumer Staples Select Sector SPDR"},
    "工业":        {"code": "usXLI", "name": "Industrial Select Sector SPDR"},
    "半导体":      {"code": "usSMH", "name": "VanEck Semiconductor ETF"},
    "生物科技":    {"code": "usXBI", "name": "SPDR S&P Biotech ETF"},
    "房地产":      {"code": "usXLRE", "name": "Real Estate Select Sector SPDR"},
    "公用事业":    {"code": "usXLU", "name": "Utilities Select Sector SPDR"},
}

# ============================================================
# 美股行业ETF → 做空（反向ETF + 期权）
# ============================================================
US_ETF_SHORT = {
    "科技":        {"options": "买Put", "inverse_etf": "", "code": "usXLK", "note": "XLK无直接反向ETF，买Put"},
    "金融":        {"options": "买Put", "inverse_etf": "usFAZ", "code": "usXLF", "note": "Direxion金融三倍做空ETF(FAZ)", "leverage": -3},
    "医疗":        {"options": "买Put", "inverse_etf": "", "code": "usXLV", "note": "XLV无直接反向ETF，买Put"},
    "能源":        {"options": "买Put", "inverse_etf": "usERY", "code": "usXLE", "note": "能源三倍做空ETF(ERY)", "leverage": -3},
    "消费(可选)":  {"options": "买Put", "inverse_etf": "", "code": "usXLY", "note": "XLY无直接反向ETF，买Put"},
    "消费(必选)":  {"options": "买Put", "inverse_etf": "", "code": "usXLP", "note": "XLP无直接反向ETF，买Put"},
    "工业":        {"options": "买Put", "inverse_etf": "", "code": "usXLI", "note": "XLI无直接反向ETF，买Put"},
    "半导体":      {"options": "买Put", "inverse_etf": "usSOXS", "code": "usSMH", "note": "Direxion半导体三倍做空(SOXS)", "leverage": -3},
    "生物科技":    {"options": "买Put", "inverse_etf": "usLABD", "code": "usXBI", "note": "Direxion生物技术三倍做空(LABD)", "leverage": -3},
    "房地产":      {"options": "买Put", "inverse_etf": "", "code": "usXLRE", "note": "XLRE无直接反向ETF，买Put"},
    "公用事业":    {"options": "买Put", "inverse_etf": "", "code": "usXLU", "note": "XLU无直接反向ETF，买Put"},
}

# ============================================================
# 港股行业 → 做多ETF
# ============================================================
HK_ETF_LONG = {
    "恒生科技":     {
        "a_share": "sh513130", "hk_primary": "hk03033", "hk_alt": "hk03032",
        "name": "恒生科技ETF(513130)/南方恒生科技(03033)",
        "note": "A股港股双市场选项"
    },
    "恒生指数":     {
        "hk_primary": "hk02800", "a_share": "sh510900",
        "name": "盈富基金(02800)/H股ETF(510900)",
        "note": ""
    },
    "恒生中国企业": {
        "hk_primary": "hk02828", "a_share": "",
        "name": "恒生中国企业ETF(02828)",
        "note": ""
    },
    "港股银行":     {
        "hk_primary": "hk03057", "a_share": "",
        "name": "恒生银行股ETF(03057)",
        "note": ""
    },
    "港股医药":     {
        "hk_primary": "hk03069", "a_share": "sh513120",
        "name": "恒生医药ETF(03069)/港股创新药ETF(513120)",
        "note": ""
    },
    "港股地产":     {
        "hk_primary": "hk03009", "a_share": "",
        "name": "恒生地产ETF(03009)",
        "note": ""
    },
}

# ============================================================
# 港股行业 → 做空/反向ETF
# ============================================================
HK_ETF_SHORT = {
    "恒生科技": {
        "primary": "hk07552", "name": "XI二南方恒科(07552)",
        "leverage": -2, "note": "南方两倍做空恒科"
    },
    "恒生指数": {
        "primary": "hk07500", "name": "FI二南方恒指(07500)",
        "leverage": -2, "note": "南方两倍做空恒指"
    },
    "恒生中国企业": {
        "primary": "hk07588", "name": "FI二南方国指(07588)",
        "leverage": -2, "note": "南方两倍做空国指"
    },
    "港股银行": {
        "primary": "", "name": "无直接反向ETF",
        "leverage": 0, "note": "用恒指反向ETF(07500)近似对冲"
    },
    "港股医药": {
        "primary": "", "name": "无直接反向ETF",
        "leverage": 0, "note": "用恒生科技反向ETF(07552)近似对冲"
    },
    "港股地产": {
        "primary": "", "name": "无直接反向ETF",
        "leverage": 0, "note": "用恒指反向ETF(07500)近似对冲"
    },
}

# ============================================================
# 全球股指 → 做多ETF
# ============================================================
INDEX_ETF_LONG = {
    "沪深300":      {"primary": "sh510300", "alt": "sz159919", "name": "沪深300ETF"},
    "中证500":      {"primary": "sh510500", "alt": "sz159922", "name": "中证500ETF"},
    "上证50":       {"primary": "sh510050", "alt": "", "name": "上证50ETF"},
    "标普500":      {"primary": "usSPY", "alt": "usVOO", "name": "SPDR标普500ETF/先锋标普500ETF"},
    "纳斯达克100":  {"primary": "usQQQ", "alt": "", "name": "Invesco纳斯达克100ETF"},
    "道琼斯":       {"primary": "usDIA", "alt": "", "name": "SPDR道琼斯ETF"},
    "日经225":      {"primary": "usEWJ", "alt": "usDXJ", "name": "iShares日经225ETF/WisdomTree日经ETF"},
    "欧洲斯托克50": {"primary": "usFEZ", "alt": "", "name": "SPDR欧洲斯托克50ETF"},
    "恒生指数":     {"primary": "hk02800", "alt": "sh510900", "name": "盈富基金/H股ETF"},
}

# ============================================================
# 全球股指 → 做空ETF（反向ETF + 期货）
# ============================================================
INDEX_ETF_SHORT = {
    "沪深300":      {"type": "期货空头", "code": "IF", "name": "IF股指期货空头", "leverage": 0,
                     "note": "A股无直接反向ETF，用IF期货空头"},
    "中证500":      {"type": "期货空头", "code": "IC", "name": "IC股指期货空头", "leverage": 0,
                     "note": "用IC期货空头"},
    "上证50":       {"type": "期货空头", "code": "IH", "name": "IH股指期货空头", "leverage": 0,
                     "note": "或用上证50ETF期权Put(510050)"},
    "标普500":      {"primary": "usSH", "alt_inverse": "usSPXU", "name": "标普500做空ETF(SH)/三倍做空(SPXU)",
                     "leverage": -1, "alt_leverage": -3},
    "纳斯达克100":  {"primary": "usPSQ", "alt_inverse": "usSQQQ", "name": "纳斯达克做空(PSQ)/三倍做空(SQQQ)",
                     "leverage": -1, "alt_leverage": -3},
    "道琼斯":       {"primary": "usDXD", "alt_inverse": "usSDOW", "name": "道琼斯两倍做空(DXD)/三倍做空(SDOW)",
                     "leverage": -2, "alt_leverage": -3},
    "日经225":      {"primary": "", "alt_inverse": "", "name": "无直接反向ETF",
                     "leverage": 0, "note": "用期货空头"},
    "欧洲斯托克50": {"primary": "", "alt_inverse": "", "name": "无直接反向ETF",
                     "leverage": 0, "note": "用欧元区做空ETF或期货"},
    "恒生指数":     {"primary": "hk07500", "alt_inverse": "", "name": "FI二南方恒指(07500)",
                     "leverage": -2, "note": "两倍做空恒指"},
}

# ============================================================
# 外汇/债券 → 做多ETF
# ============================================================
FX_BOND_ETF_LONG = {
    "离岸人民币": {"primary": "", "name": "无直接做多CNH的ETF", "note": "用CNH期货或逆向操作UDN"},
    "美元指数":   {"primary": "usUUP", "name": "做多美元ETF(UUP)", "note": ""},
    "欧元/美元":  {"primary": "usFXE", "name": "做多欧元ETF(FXE)", "note": ""},
    "日元/美元":  {"primary": "usFXY", "name": "做多日元ETF(FXY)", "note": ""},
    "10年美债":   {"primary": "usTLT", "alt": "usIEF", "name": "20+年美债ETF(TLT)/7-10年美债(IEF)", "note": "利率下行=做多"},
    "30年美债":   {"primary": "usTLT", "alt": "usEDV", "name": "20+年美债ETF(TLT)", "note": "利率下行=做多"},
    "中国10年国债": {"primary": "sh511010", "name": "国债ETF(511010)", "note": "利率下行=做多"},
}

# ============================================================
# 外汇/债券 → 做空ETF
# ============================================================
FX_BOND_ETF_SHORT = {
    "离岸人民币": {"primary": "usCNYX", "name": "做空CNH的ETF", "note": "用CNH期货或做多美元反向"},
    "美元指数":   {"primary": "usUDN", "name": "做空美元ETF(UDN)", "note": ""},
    "欧元/美元":  {"primary": "usEUO", "name": "两倍做空欧元(EUO)", "leverage": -2},
    "日元/美元":  {"primary": "usYCS", "name": "两倍做空日元(YCS)", "leverage": -2},
    "10年美债":   {"primary": "usTBT", "alt_inverse": "usTMV", "name": "做空美债(TBT)/三倍做空(TMV)",
                   "leverage": -1, "alt_leverage": -3, "note": "利率上行=做空"},
    "30年美债":   {"primary": "usTMV", "name": "三倍做空20+年美债(TMV)",
                   "leverage": -3, "note": "利率上行=做空"},
    "中国10年国债": {"primary": "", "name": "无直接反向ETF", "note": "用国债期货空头"},
}

# ============================================================
# 全球股指期货（做空/做多均可）
# ============================================================
INDEX_FUTURES = {
    "沪深300":     {"code": "IF", "multiplier": 300, "exchange": "CFFEX", "currency": "CNY"},
    "中证500":     {"code": "IC", "multiplier": 200, "exchange": "CFFEX", "currency": "CNY"},
    "上证50":      {"code": "IH", "multiplier": 300, "exchange": "CFFEX", "currency": "CNY"},
    "标普500":     {"code": "ES", "multiplier": 50,  "exchange": "CME",  "currency": "USD"},
    "纳斯达克100": {"code": "NQ", "multiplier": 20,  "exchange": "CME",  "currency": "USD"},
    "恒生指数":    {"code": "r_hdHSImain", "multiplier": 50, "exchange": "HKEX", "currency": "HKD"},
}

# ============================================================
# 统一查询函数
# ============================================================
def get_trade_tool(asset_name: str, direction: str, asset_class: str = "a_share_sector") -> dict:
    """
    根据资产名称和方向获取可交易工具（完整版）
    
    Args:
        asset_name: 资产名称（支持中英文）
        direction: 'long' 或 'short'
        asset_class: 资产类别
    
    Returns:
        dict: {
            "type": "ETF/反向ETF/期权/期货",
            "code": "代码",
            "name": "名称",
            "note": "说明",
            "leverage": 杠杆倍数(反向ETF为负),
            "alt_code": "备选代码",
        }
    """
    
    if asset_class == "a_share_sector":
        if direction == "long":
            info = A_SHARE_ETF_LONG.get(asset_name)
            if info:
                return {
                    "type": "ETF",
                    "code": info["primary"],
                    "name": info["name"],
                    "alt_code": info.get("alt", ""),
                    "note": "买入ETF做多"
                }
            return {"type": "ETF", "code": "", "name": "", "note": "未找到对应ETF"}
        else:
            info = A_SHARE_SHORT_TOOLS.get(asset_name)
            if info:
                return {
                    "type": info["type"],
                    "code": info["code"],
                    "name": info.get("name", ""),
                    "tier": info.get("tier", 3),
                    "note": info.get("note", ""),
                    "alt_code": "",
                }
            return {"type": "期权Put", "code": "sh510300", "name": "沪深300ETF期权",
                    "note": "默认用沪深300ETF期权Put近似对冲", "tier": 3}
    
    elif asset_class == "commodity":
        if direction == "long":
            info = COMMODITY_ETF_LONG.get(asset_name)
            if info and info.get("primary"):
                return {
                    "type": "ETF/期货",
                    "code": info["primary"],
                    "name": info.get("name", ""),
                    "alt_code": info.get("alt_a", ""),
                    "note": "买入商品ETF做多"
                }
            return {"type": "期货多头", "code": "", "name": f"{asset_name}期货", "note": "用期货多头"}
        else:
            info = COMMODITY_ETF_SHORT.get(asset_name)
            if info and info.get("primary"):
                return {
                    "type": "反向ETF",
                    "code": info["primary"],
                    "name": info.get("name", ""),
                    "leverage": info.get("leverage", 0),
                    "alt_code": info.get("alt", ""),
                    "note": f"做空{asset_name}"
                }
            return {"type": "期货空头", "code": "", "name": f"{asset_name}期货", "note": "用期货空头"}
    
    elif asset_class == "us_etf":
        if direction == "long":
            info = US_ETF_LONG.get(asset_name)
            if info:
                return {
                    "type": "ETF",
                    "code": info["code"],
                    "name": info["name"],
                    "note": "买入美股ETF做多"
                }
            return {"type": "ETF", "code": "", "name": "", "note": "买入对应美股ETF做多"}
        else:
            info = US_ETF_SHORT.get(asset_name)
            if info:
                if info.get("inverse_etf"):
                    return {
                        "type": "反向ETF/期权",
                        "code": info["inverse_etf"],
                        "name": info.get("note", ""),
                        "leverage": info.get("leverage"),
                        "alt_code": info.get("options", ""),
                        "alt_type": "期权Put",
                    }
                else:
                    # 无反向ETF，用期权Put做空
                    return {
                        "type": "期权Put",
                        "code": info.get("code", asset_name),
                        "name": info.get("note", f"买入{asset_name}期权Put做空"),
                        "note": f"买Put做空{asset_name}",
                    }
            return {"type": "期权Put", "code": "", "name": "", "note": f"买{asset_name} Put做空"}
    
    elif asset_class == "hk_sector":
        if direction == "long":
            info = HK_ETF_LONG.get(asset_name)
            if info:
                code = info.get("a_share") or info.get("hk_primary", "")
                return {
                    "type": "ETF(QDII/港股)",
                    "code": code,
                    "name": info.get("name", ""),
                    "alt_code": info.get("hk_primary") if info.get("a_share") else "",
                    "note": info.get("note", "买入港股ETF做多")
                }
            return {"type": "ETF", "code": "", "name": "", "note": "买入对应港股ETF做多"}
        else:
            info = HK_ETF_SHORT.get(asset_name)
            if info and info.get("primary"):
                return {
                    "type": "反向ETF",
                    "code": info["primary"],
                    "name": info.get("name", ""),
                    "leverage": info.get("leverage", -2),
                    "note": info.get("note", "买入港股反向ETF做空")
                }
            return {"type": "期权/卖空", "code": "", "name": "", "note": "借券卖空或买Put做空"}
    
    elif asset_class == "global_index":
        if direction == "long":
            info = INDEX_ETF_LONG.get(asset_name)
            if info:
                return {
                    "type": "ETF",
                    "code": info["primary"],
                    "name": info.get("name", ""),
                    "alt_code": info.get("alt", ""),
                    "note": "买入指数ETF做多"
                }
            return {"type": "期货多头", "code": "", "name": "", "note": "用期货多头"}
        else:
            info = INDEX_ETF_SHORT.get(asset_name)
            if info:
                return {
                    "type": info.get("type", "反向ETF"),
                    "code": info.get("primary") or info.get("code", ""),
                    "name": info.get("name", ""),
                    "leverage": info.get("leverage"),
                    "alt_code": info.get("alt_inverse", ""),
                    "note": info.get("note", ""),
                }
            return {"type": "期货空头", "code": "", "name": "", "note": "用期货空头"}
    
    elif asset_class == "fx_bond":
        if direction == "long":
            info = FX_BOND_ETF_LONG.get(asset_name)
            if info:
                return {
                    "type": "ETF",
                    "code": info.get("primary", ""),
                    "name": info.get("name", ""),
                    "alt_code": info.get("alt", ""),
                    "note": info.get("note", "买入做多"),
                }
            return {"type": "期货", "code": "", "name": "", "note": "用外汇期货"}
        else:
            info = FX_BOND_ETF_SHORT.get(asset_name)
            if info:
                return {
                    "type": "反向ETF/期权",
                    "code": info.get("primary", ""),
                    "name": info.get("name", ""),
                    "leverage": info.get("leverage"),
                    "alt_code": info.get("alt_inverse", ""),
                    "note": info.get("note", "做空"),
                }
            return {"type": "期货空头", "code": "", "name": "", "note": "用外汇期货空头"}
    
    return {"type": "未知", "code": "", "name": "", "note": "未找到可交易工具"}
