"""Synthetic statements. No real client CAS is ever committed here.

The ISINs are real listed securities because the parser keys on ISIN format
and a made-up one would not exercise it. Everything identifying is invented:
PANs are structurally valid and belong to nobody, account numbers are
sequential, and the quantities are round.
"""

NSDL_TEXT = """
NATIONAL SECURITIES DEPOSITORY LIMITED
CONSOLIDATED ACCOUNT STATEMENT
Statement for the period AS ON 31-AUG-2026
PAN: ABCDE1234F
DEMAT ACCOUNT IN30001234567890
ISIN                Security                                Quantity      Value
INE002A01018 Reliance Industries Limited 25 16280.00
INE467B01029 Tata Consultancy Services Limited 12 28176.00
INE040A01034 HDFC Bank Limited 100 70080.00
INF090I01239 Franklin India Flexi Cap Fund Growth 512.334 45210.55
"""

NSDL_SECOND_ACCOUNT = """
NATIONAL SECURITIES DEPOSITORY LIMITED
CONSOLIDATED ACCOUNT STATEMENT
AS ON 31-AUG-2026
DEMAT ACCOUNT IN30009876543210
INE002A01018 Reliance Industries Limited 40 26048.00
"""

CDSL_TEXT = """
CENTRAL DEPOSITORY SERVICES (INDIA) LIMITED
CONSOLIDATED ACCOUNT STATEMENT
AS ON 31-AUG-2026
DEMAT ACCOUNT 1201060000123456
INE009A01021 Infosys Limited 60 68400.00
INE030A01027 Hindustan Unilever Limited 15 37500.00
"""

CAMS_TEXT = """
CAMS CONSOLIDATED ACCOUNT STATEMENT - MUTUAL FUND
AS ON 31-AUG-2026
Folio            Scheme                                    Units      NAV     Value
91234567/22 Parag Parikh Flexi Cap Fund Direct Growth 1250.500 78.4200 98064.21
55512345/11 SBI Bluechip Fund Direct Growth 300.250 92.1100 27656.03
"""

MALFORMED_TEXT = """
NATIONAL SECURITIES DEPOSITORY LIMITED
AS ON 31-AUG-2026
DEMAT ACCOUNT IN30001234567890
INE002A01018 Reliance Industries Limited
INE467B01029
"""

EMPTY_TEXT = """
NATIONAL SECURITIES DEPOSITORY LIMITED
CONSOLIDATED ACCOUNT STATEMENT
AS ON 31-AUG-2026
No holdings were reported for this period.
"""
