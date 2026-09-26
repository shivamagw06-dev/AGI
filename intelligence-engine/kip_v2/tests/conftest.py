import pytest

from kip_v2.storage.sqlite_store import SqliteKnowledgeStore


@pytest.fixture()
def store():
    return SqliteKnowledgeStore(path=":memory:")


FY25_ANNUAL_REPORT = """
BUSINESS OVERVIEW

Our business model is centred on manufacturing and distributing specialty
chemicals to industrial customers across India and export markets. We operate
three manufacturing plants and a pan-India distribution network.

Our product portfolio includes specialty polymers, industrial adhesives, and
performance coatings sold under the Aravali brand.

RISK FACTORS

Key risks include volatility in crude-oil linked raw material prices, which
directly affects our input cost structure and gross margin.

Regulatory risk from changing environmental compliance norms remains a
material risk for our manufacturing operations.

STRATEGY

Our strategy for FY25 is to expand capacity in the western region and deepen
our relationships with key customers in the automotive sector.

Revenue growth of 12.5% for FY25 was driven by higher volumes in the
industrial adhesives segment and improved realizations.

FINANCIAL STATEMENTS

Revenue for FY25 was Rs. 4,250 crore, up from the prior year. EBITDA for FY25
was Rs. 680 crore with an EBITDA margin of 16.0%. Profit after tax for FY25
was Rs. 340 crore. Earnings per share for FY25 was Rs. 42.50.

Capital expenditure for FY25 was Rs. 310 crore, funded through internal
accruals and term debt. Total debt for FY25 stood at Rs. 1,200 crore.

Dividend per share for FY25 was Rs. 8.00, in line with our stated dividend
policy of paying out 20% of profit after tax.

CAPITAL ALLOCATION

Our capital allocation priorities remain: fund organic capex, maintain a
progressive dividend policy, and evaluate bolt-on acquisitions.

MANAGEMENT COMMENTARY

Suresh Iyer (Managing Director): Our growth priorities for the coming year
are centred on expanding capacity in the western region and strengthening
our customer relationships. Demand outlook remains healthy across our core
end markets, and we expect margin expectations to stay in the mid-teens.

"We remain confident in our pricing strategy for FY25," said Suresh Iyer,
Managing Director, adding that realizations should improve further.
"""

FY26_ANNUAL_REPORT = """
BUSINESS OVERVIEW

Our business model is centred on manufacturing and distributing specialty
chemicals to industrial customers across India and export markets, now
expanded to include specialty coatings for the electronics sector.

RISK FACTORS

Regulatory risk from changing environmental compliance norms remains a
material risk for our manufacturing operations.

Currency risk from expanding export operations is now a key risk given our
growing exposure to the US dollar and the Euro.

STRATEGY

Our strategy for FY26 is to enter the electronics coatings market and
deepen our relationships with key customers in the automotive sector.

FINANCIAL STATEMENTS

Revenue for FY26 was Rs. 5,100 crore, up from the prior year. EBITDA for FY26
was Rs. 900 crore with an EBITDA margin of 17.6%. Profit after tax for FY26
was Rs. 460 crore. Earnings per share for FY26 was Rs. 57.50.

Capital expenditure for FY26 was Rs. 520 crore, funded through internal
accruals and term debt. Total debt for FY26 stood at Rs. 1,050 crore.

Dividend per share for FY26 was Rs. 10.00, in line with our stated dividend
policy of paying out 20% of profit after tax.

MANAGEMENT COMMENTARY

Suresh Iyer (Managing Director): Our growth priorities for the coming year
are centred on the new electronics coatings market. Demand outlook remains
healthy across our core end markets, and hiring in our R&D function remains
a top priority.
"""
