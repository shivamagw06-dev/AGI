"""Indian equity universes for corpus coverage — Nifty 50 → Next 50 → Nifty 500 path."""

from __future__ import annotations

# Canonical Nifty 50 tickers (NSE symbols, institutional liquid set).
NIFTY_50: list[dict[str, str]] = [
    {"ticker": "RELIANCE", "name": "Reliance Industries", "sector": "Energy"},
    {"ticker": "TCS", "name": "Tata Consultancy Services", "sector": "IT Services"},
    {"ticker": "HDFCBANK", "name": "HDFC Bank", "sector": "Banking"},
    {"ticker": "BHARTIARTL", "name": "Bharti Airtel", "sector": "Telecom"},
    {"ticker": "ICICIBANK", "name": "ICICI Bank", "sector": "Banking"},
    {"ticker": "INFY", "name": "Infosys", "sector": "IT Services"},
    {"ticker": "SBIN", "name": "State Bank of India", "sector": "Banking"},
    {"ticker": "ITC", "name": "ITC", "sector": "FMCG"},
    {"ticker": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "FMCG"},
    {"ticker": "LT", "name": "Larsen & Toubro", "sector": "Capital Goods"},
    {"ticker": "BAJFINANCE", "name": "Bajaj Finance", "sector": "Financial Services"},
    {"ticker": "HCLTECH", "name": "HCLTech", "sector": "IT Services"},
    {"ticker": "AXISBANK", "name": "Axis Bank", "sector": "Banking"},
    {"ticker": "MARUTI", "name": "Maruti Suzuki", "sector": "Auto"},
    {"ticker": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Pharma"},
    {"ticker": "NTPC", "name": "NTPC", "sector": "Power"},
    {"ticker": "ULTRACEMCO", "name": "UltraTech Cement", "sector": "Capital Goods"},
    {"ticker": "M&M", "name": "Mahindra & Mahindra", "sector": "Auto"},
    {"ticker": "POWERGRID", "name": "Power Grid Corporation", "sector": "Power"},
    {"ticker": "TATAMOTORS", "name": "Tata Motors", "sector": "Auto"},
    {"ticker": "WIPRO", "name": "Wipro", "sector": "IT Services"},
    {"ticker": "ONGC", "name": "Oil and Natural Gas Corporation", "sector": "Energy"},
    {"ticker": "NESTLEIND", "name": "Nestle India", "sector": "FMCG"},
    {"ticker": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Banking"},
    {"ticker": "BAJAJFINSV", "name": "Bajaj Finserv", "sector": "Financial Services"},
    {"ticker": "JSWSTEEL", "name": "JSW Steel", "sector": "Metals"},
    {"ticker": "TITAN", "name": "Titan Company", "sector": "Retail"},
    {"ticker": "ASIANPAINT", "name": "Asian Paints", "sector": "Chemicals"},
    {"ticker": "BEL", "name": "Bharat Electronics", "sector": "Defence"},
    {"ticker": "TECHM", "name": "Tech Mahindra", "sector": "IT Services"},
    {"ticker": "GRASIM", "name": "Grasim Industries", "sector": "Chemicals"},
    {"ticker": "HINDALCO", "name": "Hindalco Industries", "sector": "Metals"},
    {"ticker": "INDUSINDBK", "name": "IndusInd Bank", "sector": "Banking"},
    {"ticker": "CIPLA", "name": "Cipla", "sector": "Pharma"},
    {"ticker": "DRREDDY", "name": "Dr. Reddy's Laboratories", "sector": "Pharma"},
    {"ticker": "TATACONSUM", "name": "Tata Consumer Products", "sector": "FMCG"},
    {"ticker": "EICHERMOT", "name": "Eicher Motors", "sector": "Auto"},
    {"ticker": "HEROMOTOCO", "name": "Hero MotoCorp", "sector": "Auto"},
    {"ticker": "DIVISLAB", "name": "Divi's Laboratories", "sector": "Pharma"},
    {"ticker": "BRITANNIA", "name": "Britannia Industries", "sector": "FMCG"},
    {"ticker": "BPCL", "name": "Bharat Petroleum", "sector": "Energy"},
    {"ticker": "COALINDIA", "name": "Coal India", "sector": "Energy"},
    {"ticker": "ADANIENT", "name": "Adani Enterprises", "sector": "Energy"},
    {"ticker": "ADANIPORTS", "name": "Adani Ports", "sector": "Capital Goods"},
    {"ticker": "TATASTEEL", "name": "Tata Steel", "sector": "Metals"},
    {"ticker": "APOLLOHOSP", "name": "Apollo Hospitals", "sector": "Pharma"},
    {"ticker": "SBILIFE", "name": "SBI Life Insurance", "sector": "Financial Services"},
    {"ticker": "HDFCLIFE", "name": "HDFC Life Insurance", "sector": "Financial Services"},
    {"ticker": "TRENT", "name": "Trent", "sector": "Retail"},
    {"ticker": "BAJAJ-AUTO", "name": "Bajaj Auto", "sector": "Auto"},
]

NIFTY_NEXT_50: list[dict[str, str]] = [
    {"ticker": "DLF", "name": "DLF", "sector": "Real Estate"},
    {"ticker": "DMART", "name": "Avenue Supermarts", "sector": "Retail"},
    {"ticker": "HAL", "name": "Hindustan Aeronautics", "sector": "Defence"},
    {"ticker": "SIEMENS", "name": "Siemens India", "sector": "Capital Goods"},
    {"ticker": "ABB", "name": "ABB India", "sector": "Capital Goods"},
    {"ticker": "PIDILITIND", "name": "Pidilite Industries", "sector": "Chemicals"},
    {"ticker": "PERSISTENT", "name": "Persistent Systems", "sector": "IT Services"},
    {"ticker": "COFORGE", "name": "Coforge", "sector": "IT Services"},
    {"ticker": "MPHASIS", "name": "Mphasis", "sector": "IT Services"},
    {"ticker": "LTTS", "name": "L&T Technology Services", "sector": "IT Services"},
    {"ticker": "LTIM", "name": "LTIMindtree", "sector": "IT Services"},
    {"ticker": "HAVELLS", "name": "Havells India", "sector": "Capital Goods"},
    {"ticker": "DIXON", "name": "Dixon Technologies", "sector": "Capital Goods"},
    {"ticker": "POLYCAB", "name": "Polycab India", "sector": "Capital Goods"},
    {"ticker": "TVSMOTOR", "name": "TVS Motor", "sector": "Auto"},
    {"ticker": "ASHOKLEY", "name": "Ashok Leyland", "sector": "Auto"},
    {"ticker": "BANKBARODA", "name": "Bank of Baroda", "sector": "Banking"},
    {"ticker": "PNB", "name": "Punjab National Bank", "sector": "Banking"},
    {"ticker": "CANBK", "name": "Canara Bank", "sector": "Banking"},
    {"ticker": "FEDERALBNK", "name": "Federal Bank", "sector": "Banking"},
    {"ticker": "IDFCFIRSTB", "name": "IDFC First Bank", "sector": "Banking"},
    {"ticker": "CHOLAFIN", "name": "Cholamandalam Finance", "sector": "Financial Services"},
    {"ticker": "SHRIRAMFIN", "name": "Shriram Finance", "sector": "Financial Services"},
    {"ticker": "MUTHOOTFIN", "name": "Muthoot Finance", "sector": "Financial Services"},
    {"ticker": "ICICIGI", "name": "ICICI Lombard", "sector": "Financial Services"},
    {"ticker": "ICICIPRULI", "name": "ICICI Prudential Life", "sector": "Financial Services"},
    {"ticker": "GODREJCP", "name": "Godrej Consumer", "sector": "FMCG"},
    {"ticker": "DABUR", "name": "Dabur India", "sector": "FMCG"},
    {"ticker": "MARICO", "name": "Marico", "sector": "FMCG"},
    {"ticker": "COLPAL", "name": "Colgate-Palmolive", "sector": "FMCG"},
    {"ticker": "UNITDSPR", "name": "United Spirits", "sector": "FMCG"},
    {"ticker": "TORNTPHARM", "name": "Torrent Pharma", "sector": "Pharma"},
    {"ticker": "AUROPHARMA", "name": "Aurobindo Pharma", "sector": "Pharma"},
    {"ticker": "LUPIN", "name": "Lupin", "sector": "Pharma"},
    {"ticker": "ZYDUSLIFE", "name": "Zydus Lifesciences", "sector": "Pharma"},
    {"ticker": "BIOCON", "name": "Biocon", "sector": "Pharma"},
    {"ticker": "VEDL", "name": "Vedanta", "sector": "Metals"},
    {"ticker": "JINDALSTEL", "name": "Jindal Steel", "sector": "Metals"},
    {"ticker": "NMDC", "name": "NMDC", "sector": "Metals"},
    {"ticker": "SAIL", "name": "Steel Authority of India", "sector": "Metals"},
    {"ticker": "AMBUJACEM", "name": "Ambuja Cements", "sector": "Capital Goods"},
    {"ticker": "SHREECEM", "name": "Shree Cement", "sector": "Capital Goods"},
    {"ticker": "DALBHARAT", "name": "Dalmia Bharat", "sector": "Capital Goods"},
    {"ticker": "INDIGO", "name": "InterGlobe Aviation", "sector": "Retail"},
    {"ticker": "IRCTC", "name": "IRCTC", "sector": "Retail"},
    {"ticker": "PFC", "name": "Power Finance Corporation", "sector": "Financial Services"},
    {"ticker": "RECLTD", "name": "REC", "sector": "Financial Services"},
    {"ticker": "GAIL", "name": "GAIL India", "sector": "Energy"},
    {"ticker": "IOC", "name": "Indian Oil Corporation", "sector": "Energy"},
    {"ticker": "NHPC", "name": "NHPC", "sector": "Power"},
]

# Additional liquid names toward Nifty 500 coverage (expandable).
NIFTY_500_EXTENSION: list[dict[str, str]] = [
    {"ticker": "BHEL", "name": "Bharat Heavy Electricals", "sector": "Capital Goods"},
    {"ticker": "CONCOR", "name": "Container Corporation", "sector": "Capital Goods"},
    {"ticker": "OFSS", "name": "Oracle Financial Services", "sector": "IT Services"},
    {"ticker": "PAGEIND", "name": "Page Industries", "sector": "Retail"},
    {"ticker": "VOLTAS", "name": "Voltas", "sector": "Capital Goods"},
    {"ticker": "CROMPTON", "name": "Crompton Greaves Consumer", "sector": "Capital Goods"},
    {"ticker": "BERGEPAINT", "name": "Berger Paints", "sector": "Chemicals"},
    {"ticker": "ALKEM", "name": "Alkem Laboratories", "sector": "Pharma"},
    {"ticker": "LAURUSLABS", "name": "Laurus Labs", "sector": "Pharma"},
    {"ticker": "SYNGENE", "name": "Syngene International", "sector": "Pharma"},
    {"ticker": "MAXHEALTH", "name": "Max Healthcare", "sector": "Pharma"},
    {"ticker": "FORTIS", "name": "Fortis Healthcare", "sector": "Pharma"},
    {"ticker": "GODREJPROP", "name": "Godrej Properties", "sector": "Real Estate"},
    {"ticker": "OBEROIRLTY", "name": "Oberoi Realty", "sector": "Real Estate"},
    {"ticker": "PRESTIGE", "name": "Prestige Estates", "sector": "Real Estate"},
    {"ticker": "MOTHERSON", "name": "Samvardhana Motherson", "sector": "Auto"},
    {"ticker": "BOSCHLTD", "name": "Bosch", "sector": "Auto"},
    {"ticker": "BALKRISIND", "name": "Balkrishna Industries", "sector": "Auto"},
    {"ticker": "PIIND", "name": "PI Industries", "sector": "Chemicals"},
    {"ticker": "SRF", "name": "SRF", "sector": "Chemicals"},
    {"ticker": "AARTIIND", "name": "Aarti Industries", "sector": "Chemicals"},
    {"ticker": "NAUKRI", "name": "Info Edge", "sector": "IT Services"},
    {"ticker": "POLICYBZR", "name": "PB Fintech", "sector": "Financial Services"},
    {"ticker": "PAYTM", "name": "One 97 Communications", "sector": "Financial Services"},
    {"ticker": "ZOMATO", "name": "Eternal (Zomato)", "sector": "Retail"},
    {"ticker": "NYKAA", "name": "FSN E-Commerce (Nykaa)", "sector": "Retail"},
    {"ticker": "DELHIVERY", "name": "Delhivery", "sector": "Retail"},
    {"ticker": "IDEA", "name": "Vodafone Idea", "sector": "Telecom"},
    {"ticker": "TATAPOWER", "name": "Tata Power", "sector": "Power"},
    {"ticker": "ADANIGREEN", "name": "Adani Green Energy", "sector": "Power"},
]


def all_universe_rows() -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for row in NIFTY_50 + NIFTY_NEXT_50 + NIFTY_500_EXTENSION:
        t = row["ticker"].upper()
        if t in seen:
            continue
        seen.add(t)
        out.append(row)
    return out


def nifty50_tickers() -> set[str]:
    return {r["ticker"].upper() for r in NIFTY_50}


def nifty_next50_tickers() -> set[str]:
    return {r["ticker"].upper() for r in NIFTY_NEXT_50}


def nifty500_path_tickers() -> set[str]:
    return {r["ticker"].upper() for r in all_universe_rows()}
