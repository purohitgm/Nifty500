"""
NSE Nifty Indices and Sector Configuration
Yahoo Finance symbols for Indian stock market
"""

NIFTY_INDICES = {
    "NIFTY 50":          "^NSEI",
    "NIFTY 100":         "^CNX100",
    "NIFTY 200":         "^CNX200",
    "NIFTY 500":         "^CRSLDX",
    "NIFTY BANK":        "^NSEBANK",
    "NIFTY IT":          "^CNXIT",
    "NIFTY PHARMA":      "^CNXPHARMA",
    "NIFTY AUTO":        "^CNXAUTO",
    "NIFTY METAL":       "^CNXMETAL",
    "NIFTY REALTY":      "^CNXREALTY",
    "NIFTY ENERGY":      "^CNXENERGY",
    "NIFTY FMCG":        "^CNXFMCG",
    "NIFTY PSU BANK":    "^CNXPSUBANK",
    "NIFTY MEDIA":       "^CNXMEDIA",
    "NIFTY FIN SERVICE": "^CNXFIN",
}

# Each sector: name, index_symbol, color, stocks list
SECTORS = [
    {
        "name": "Banking",
        "index_symbol": "^NSEBANK",
        "color": "#3b82f6",
        "stocks": [
            {"symbol": "HDFCBANK.NS",  "name": "HDFC Bank",         "industry": "Private Banks"},
            {"symbol": "ICICIBANK.NS", "name": "ICICI Bank",         "industry": "Private Banks"},
            {"symbol": "KOTAKBANK.NS", "name": "Kotak Bank",         "industry": "Private Banks"},
            {"symbol": "AXISBANK.NS",  "name": "Axis Bank",          "industry": "Private Banks"},
            {"symbol": "SBIN.NS",      "name": "SBI",                "industry": "Public Banks"},
            {"symbol": "BANKBARODA.NS","name": "Bank of Baroda",     "industry": "Public Banks"},
            {"symbol": "PNB.NS",       "name": "Punjab National Bank","industry": "Public Banks"},
            {"symbol": "INDUSINDBK.NS","name": "IndusInd Bank",      "industry": "Private Banks"},
            {"symbol": "FEDERALBNK.NS","name": "Federal Bank",       "industry": "Private Banks"},
            {"symbol": "IDFCFIRSTB.NS","name": "IDFC First Bank",    "industry": "Private Banks"},
        ],
    },
    {
        "name": "IT",
        "index_symbol": "^CNXIT",
        "color": "#10b981",
        "stocks": [
            {"symbol": "TCS.NS",       "name": "TCS",                "industry": "IT Services"},
            {"symbol": "INFY.NS",      "name": "Infosys",            "industry": "IT Services"},
            {"symbol": "WIPRO.NS",     "name": "Wipro",              "industry": "IT Services"},
            {"symbol": "HCLTECH.NS",   "name": "HCL Tech",           "industry": "IT Services"},
            {"symbol": "TECHM.NS",     "name": "Tech Mahindra",      "industry": "IT Services"},
            {"symbol": "LTIM.NS",      "name": "LTIMindtree",        "industry": "IT Services"},
            {"symbol": "COFORGE.NS",   "name": "Coforge",            "industry": "IT Services"},
            {"symbol": "MPHASIS.NS",   "name": "Mphasis",            "industry": "IT Services"},
            {"symbol": "PERSISTENT.NS","name": "Persistent Systems", "industry": "IT Services"},
            {"symbol": "LTTS.NS",      "name": "L&T Technology",     "industry": "IT Services"},
        ],
    },
    {
        "name": "Pharma",
        "index_symbol": "^CNXPHARMA",
        "color": "#f59e0b",
        "stocks": [
            {"symbol": "SUNPHARMA.NS", "name": "Sun Pharma",         "industry": "Pharmaceuticals"},
            {"symbol": "DRREDDY.NS",   "name": "Dr Reddy",           "industry": "Pharmaceuticals"},
            {"symbol": "CIPLA.NS",     "name": "Cipla",              "industry": "Pharmaceuticals"},
            {"symbol": "DIVISLAB.NS",  "name": "Divi Labs",          "industry": "Pharmaceuticals"},
            {"symbol": "BIOCON.NS",    "name": "Biocon",             "industry": "Biotechnology"},
            {"symbol": "LUPIN.NS",     "name": "Lupin",              "industry": "Pharmaceuticals"},
            {"symbol": "AUROPHARMA.NS","name": "Aurobindo Pharma",   "industry": "Pharmaceuticals"},
            {"symbol": "ALKEM.NS",     "name": "Alkem Labs",         "industry": "Pharmaceuticals"},
            {"symbol": "TORNTPHARM.NS","name": "Torrent Pharma",     "industry": "Pharmaceuticals"},
            {"symbol": "ZYDUSLIFE.NS", "name": "Zydus Lifesciences", "industry": "Pharmaceuticals"},
        ],
    },
    {
        "name": "Auto",
        "index_symbol": "^CNXAUTO",
        "color": "#8b5cf6",
        "stocks": [
            {"symbol": "TATAMOTORS.NS","name": "Tata Motors",        "industry": "Auto Manufacturers"},
            {"symbol": "M&M.NS",       "name": "M&M",                "industry": "Auto Manufacturers"},
            {"symbol": "MARUTI.NS",    "name": "Maruti Suzuki",      "industry": "Auto Manufacturers"},
            {"symbol": "BAJAJ-AUTO.NS","name": "Bajaj Auto",         "industry": "2-Wheelers"},
            {"symbol": "HEROMOTOCO.NS","name": "Hero MotoCorp",      "industry": "2-Wheelers"},
            {"symbol": "EICHERMOT.NS", "name": "Eicher Motors",      "industry": "2-Wheelers"},
            {"symbol": "TVSMOTOR.NS",  "name": "TVS Motor",          "industry": "2-Wheelers"},
            {"symbol": "ASHOKLEY.NS",  "name": "Ashok Leyland",      "industry": "Commercial Vehicles"},
            {"symbol": "BALKRISIND.NS","name": "Balkrishna Ind",     "industry": "Auto Ancillary"},
            {"symbol": "MOTHERSON.NS", "name": "Motherson Sumi",     "industry": "Auto Ancillary"},
        ],
    },
    {
        "name": "Metal",
        "index_symbol": "^CNXMETAL",
        "color": "#6366f1",
        "stocks": [
            {"symbol": "TATASTEEL.NS", "name": "Tata Steel",         "industry": "Steel"},
            {"symbol": "JSWSTEEL.NS",  "name": "JSW Steel",          "industry": "Steel"},
            {"symbol": "HINDALCO.NS",  "name": "Hindalco",           "industry": "Aluminum"},
            {"symbol": "VEDL.NS",      "name": "Vedanta",            "industry": "Diversified Metals"},
            {"symbol": "COALINDIA.NS", "name": "Coal India",         "industry": "Mining"},
            {"symbol": "NMDC.NS",      "name": "NMDC",               "industry": "Mining"},
            {"symbol": "SAIL.NS",      "name": "SAIL",               "industry": "Steel"},
            {"symbol": "JINDALSTEL.NS","name": "Jindal Steel",       "industry": "Steel"},
            {"symbol": "NATIONALUM.NS","name": "NALCO",              "industry": "Aluminum"},
            {"symbol": "HINDZINC.NS",  "name": "Hindustan Zinc",     "industry": "Zinc"},
        ],
    },
    {
        "name": "Energy",
        "index_symbol": "^CNXENERGY",
        "color": "#ef4444",
        "stocks": [
            {"symbol": "RELIANCE.NS",  "name": "Reliance",           "industry": "Oil & Gas"},
            {"symbol": "ONGC.NS",      "name": "ONGC",               "industry": "Oil Exploration"},
            {"symbol": "NTPC.NS",      "name": "NTPC",               "industry": "Power Generation"},
            {"symbol": "POWERGRID.NS", "name": "Power Grid",         "industry": "Power Transmission"},
            {"symbol": "ADANIGREEN.NS","name": "Adani Green",        "industry": "Renewable Energy"},
            {"symbol": "TATAPOWER.NS", "name": "Tata Power",         "industry": "Power Generation"},
            {"symbol": "BPCL.NS",      "name": "BPCL",               "industry": "Oil Refining"},
            {"symbol": "IOC.NS",       "name": "IOC",                "industry": "Oil Refining"},
            {"symbol": "GAIL.NS",      "name": "GAIL",               "industry": "Gas Distribution"},
            {"symbol": "ADANIPORTS.NS","name": "Adani Ports",        "industry": "Infrastructure"},
        ],
    },
    {
        "name": "FMCG",
        "index_symbol": "^CNXFMCG",
        "color": "#22c55e",
        "stocks": [
            {"symbol": "HINDUNILVR.NS","name": "HUL",                "industry": "Personal Care"},
            {"symbol": "ITC.NS",       "name": "ITC",                "industry": "Tobacco & FMCG"},
            {"symbol": "NESTLEIND.NS", "name": "Nestle India",       "industry": "Food Products"},
            {"symbol": "BRITANNIA.NS", "name": "Britannia",          "industry": "Food Products"},
            {"symbol": "DABUR.NS",     "name": "Dabur",              "industry": "Personal Care"},
            {"symbol": "MARICO.NS",    "name": "Marico",             "industry": "Personal Care"},
            {"symbol": "GODREJCP.NS",  "name": "Godrej Consumer",    "industry": "Personal Care"},
            {"symbol": "COLPAL.NS",    "name": "Colgate",            "industry": "Personal Care"},
            {"symbol": "TATACONSUM.NS","name": "Tata Consumer",      "industry": "Food Products"},
            {"symbol": "VBL.NS",       "name": "Varun Beverages",    "industry": "Beverages"},
        ],
    },
    {
        "name": "Financial Services",
        "index_symbol": "^CNXFIN",
        "color": "#0ea5e9",
        "stocks": [
            {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance",     "industry": "NBFC"},
            {"symbol": "BAJAJFINSV.NS", "name": "Bajaj Finserv",     "industry": "Holding Company"},
            {"symbol": "HDFCLIFE.NS",   "name": "HDFC Life",         "industry": "Insurance"},
            {"symbol": "SBILIFE.NS",    "name": "SBI Life",          "industry": "Insurance"},
            {"symbol": "ICICIPRULI.NS", "name": "ICICI Pru Life",    "industry": "Insurance"},
            {"symbol": "ICICIGI.NS",    "name": "ICICI Lombard",     "industry": "Insurance"},
            {"symbol": "CHOLAFIN.NS",   "name": "Cholamandalam",     "industry": "NBFC"},
            {"symbol": "MUTHOOTFIN.NS", "name": "Muthoot Finance",   "industry": "NBFC"},
            {"symbol": "M&MFIN.NS",     "name": "M&M Finance",       "industry": "NBFC"},
            {"symbol": "SHRIRAMFIN.NS", "name": "Shriram Finance",   "industry": "NBFC"},
        ],
    },
    {
        "name": "Realty",
        "index_symbol": "^CNXREALTY",
        "color": "#f97316",
        "stocks": [
            {"symbol": "DLF.NS",        "name": "DLF",               "industry": "Real Estate"},
            {"symbol": "GODREJPROP.NS", "name": "Godrej Properties", "industry": "Real Estate"},
            {"symbol": "OBEROIRLTY.NS", "name": "Oberoi Realty",     "industry": "Real Estate"},
            {"symbol": "PRESTIGE.NS",   "name": "Prestige Estates",  "industry": "Real Estate"},
            {"symbol": "PHOENIXLTD.NS", "name": "Phoenix Mills",     "industry": "Real Estate"},
            {"symbol": "BRIGADE.NS",    "name": "Brigade Enterprises","industry": "Real Estate"},
            {"symbol": "LODHA.NS",      "name": "Macrotech",         "industry": "Real Estate"},
            {"symbol": "SOBHA.NS",      "name": "Sobha",             "industry": "Real Estate"},
        ],
    },
    {
        "name": "Media",
        "index_symbol": "^CNXMEDIA",
        "color": "#ec4899",
        "stocks": [
            {"symbol": "ZEEL.NS",      "name": "Zee Entertainment",  "industry": "Broadcasting"},
            {"symbol": "SUNTV.NS",     "name": "Sun TV",             "industry": "Broadcasting"},
            {"symbol": "PVRINOX.NS",   "name": "PVR INOX",           "industry": "Entertainment"},
            {"symbol": "NETWORK18.NS", "name": "Network18",          "industry": "Media"},
            {"symbol": "NAZARA.NS",    "name": "Nazara Tech",        "industry": "Gaming"},
        ],
    },
]

NIFTY_50_STOCKS = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
    "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BPCL.NS", "BHARTIARTL.NS",
    "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "DIVISLAB.NS", "DRREDDY.NS",
    "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS",
    "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "ITC.NS",
    "INDUSINDBK.NS", "INFY.NS", "JSWSTEEL.NS", "KOTAKBANK.NS", "LT.NS",
    "M&M.NS", "MARUTI.NS", "NTPC.NS", "NESTLEIND.NS", "ONGC.NS",
    "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS", "SBIN.NS", "SUNPHARMA.NS",
    "TCS.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "TECHM.NS",
    "TITAN.NS", "ULTRACEMCO.NS", "UPL.NS", "WIPRO.NS", "LTIM.NS",
]


def get_all_stocks():
    """Return flat list of all stocks across all sectors."""
    stocks = []
    for sector in SECTORS:
        for s in sector["stocks"]:
            stocks.append({**s, "sector": sector["name"]})
    return stocks


def get_sector_for_symbol(symbol: str) -> dict | None:
    for sector in SECTORS:
        if any(s["symbol"] == symbol for s in sector["stocks"]):
            return sector
    return None
