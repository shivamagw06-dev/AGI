"""AGI Institutional Data Warehouse.

A database-backed institutional warehouse that the admin workspace renders as a
spreadsheet. Collectors write here, intelligence modules read from here, every
imported value keeps provenance, every edit keeps a version, every action is
audited.
"""

from institutional_warehouse.schema import TABS, tab, tab_ids

__all__ = ["TABS", "tab", "tab_ids"]
