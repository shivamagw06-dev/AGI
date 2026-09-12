#!/usr/bin/env python3
"""Pull full KKR public portfolio via the bioportfoliosearch JSON endpoint discovered by Playwright."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 AGIB-PE-Probe/1.0"
)

BASE = (
    "https://www.kkr.com/content/kkr/sites/global/en/invest/portfolio/"
    "jcr:content/root/main-par/bioportfoliosearch.bioportfoliosearch.json"
)
PE_URL = "https://www.kkr.com/invest/private-equity"
PORT_URL = "https://www.kkr.com/invest/portfolio"

OUT = Path("/opt/cursor/artifacts/kkr_pe_playwright_pull.json")
SUMMARY = Path("/opt/cursor/artifacts/kkr_pe_playwright_summary.md")
CSV_LIKE = Path("/opt/cursor/artifacts/kkr_portfolio_companies.json")


def fetch_page(page, page_no: int) -> dict:
    qs = urlencode(
        {
            "page": str(page_no),
            "sortParameter": "",
            "sortingOrder": "asc",
            "keyword": "",
            "cfnode": "",
        }
    )
    url = f"{BASE}?{qs}"
    resp = page.request.get(url, headers={"Accept": "application/json, text/plain, */*", "User-Agent": UA})
    if resp.status != 200:
        raise RuntimeError(f"page {page_no} status {resp.status}")
    return resp.json()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=UA, locale="en-US")
        page = context.new_page()

        # Warm session on the real portfolio page first (cookies / CSRF if any)
        print("warming portfolio page...", flush=True)
        page.goto(PORT_URL, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        page.wait_for_timeout(1500)

        first = fetch_page(page, 1)
        total_hits = int(first.get("hits") or 0)
        total_pages = int(first.get("pages") or 1)
        print(f"hits={total_hits} pages={total_pages}", flush=True)

        results = list(first.get("results") or [])
        for page_no in range(2, total_pages + 1):
            data = fetch_page(page, page_no)
            batch = data.get("results") or []
            print(f"  page {page_no}/{total_pages}: {len(batch)}", flush=True)
            results.extend(batch)
            time.sleep(0.15)

        # Also pull PE page text for firm signals
        print("PE page text...", flush=True)
        page.goto(PE_URL, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        pe_text = " ".join((page.locator("body").inner_text() or "").split())
        pe_title = page.title()
        browser.close()

    companies = []
    seen = set()
    for row in results:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        companies.append(
            {
                "company": name,
                "logo": row.get("logo"),
                "hq": row.get("hq"),
                "region": row.get("region"),
                "asset_class": row.get("assetClass"),
                "industry": row.get("industry"),
                "investment_year": row.get("yoi"),
                "company_website": row.get("url"),
                "status": "Active",  # listed on current portfolio page
                "source": "kkr.com bioportfoliosearch",
            }
        )

    # Aggregate firm-level stats from portfolio
    by_asset = {}
    by_industry = {}
    by_region = {}
    by_year = {}
    for c in companies:
        by_asset[c["asset_class"] or "Unknown"] = by_asset.get(c["asset_class"] or "Unknown", 0) + 1
        by_industry[c["industry"] or "Unknown"] = by_industry.get(c["industry"] or "Unknown", 0) + 1
        by_region[c["region"] or "Unknown"] = by_region.get(c["region"] or "Unknown", 0) + 1
        by_year[c["investment_year"] or "Unknown"] = by_year.get(c["investment_year"] or "Unknown", 0) + 1

    firm = {
        "firm_name": "KKR",
        "website": "https://www.kkr.com",
        "strategy_page": PE_URL,
        "portfolio_page": PORT_URL,
        "pe_page_title": pe_title,
        "public_portfolio_count": total_hits,
        "extracted_company_count": len(companies),
        "asset_class_breakdown": dict(sorted(by_asset.items(), key=lambda x: -x[1])),
        "industry_breakdown": dict(sorted(by_industry.items(), key=lambda x: -x[1])),
        "region_breakdown": dict(sorted(by_region.items(), key=lambda x: -x[1])),
        "investment_year_breakdown": dict(sorted(by_year.items(), key=lambda x: x[0] or "")),
        "metrics_from_pe_page": [],
        "focus_keywords": [],
    }

    import re
    for pat in [
        r"\$[\d,.]+ ?[BbTtMm](?:illion)?",
        r"\b\d{2,4}\+? portfolio companies\b",
        r"\bsince \d{4}\b",
        r"\b\d{2,4}\+? countries\b",
    ]:
        for m in re.finditer(pat, pe_text, flags=re.I):
            firm["metrics_from_pe_page"].append(m.group(0))
    firm["metrics_from_pe_page"] = list(dict.fromkeys(firm["metrics_from_pe_page"]))[:20]

    for kw in [
        "buyout", "growth", "core", "impact", "infrastructure", "credit",
        "real estate", "healthcare", "technology", "industrials", "consumer",
        "asia", "europe", "americas", "middle-market", "tech growth",
    ]:
        if re.search(rf"\b{re.escape(kw)}\b", pe_text, flags=re.I):
            firm["focus_keywords"].append(kw)

    payload = {
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "method": "playwright_session + bioportfoliosearch.json pagination",
        "endpoint": BASE,
        "firm": firm,
        "portfolio_companies": companies,
        "notes": [
            "Pulled from KKR's public portfolio search JSON API discovered via Playwright network capture.",
            "KKR discloses a significant portion of PE / Tech Growth / Health Care Growth / Global Impact / Infrastructure / Real Assets holdings; some minority/residual/restructuring names are excluded by KKR.",
            "Feasibility probe — not yet written into AGIB PE schema tables.",
        ],
    }

    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    CSV_LIKE.write_text(json.dumps(companies, indent=2, ensure_ascii=False))

    lines = [
        "# KKR Private Equity — Playwright portfolio pull",
        "",
        f"Pulled at: `{payload['pulled_at']}`",
        "",
        "## Firm",
        f"- **{firm['firm_name']}** — {firm['website']}",
        f"- PE page: {firm['pe_page_title']}",
        f"- Public portfolio disclosed: **{firm['public_portfolio_count']}**",
        f"- Extracted clean company rows: **{firm['extracted_company_count']}**",
        f"- Metrics on PE page: {', '.join(firm['metrics_from_pe_page']) or '—'}",
        f"- Focus keywords: {', '.join(firm['focus_keywords']) or '—'}",
        "",
        "## Asset class breakdown",
    ]
    for k, v in firm["asset_class_breakdown"].items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Industry breakdown"]
    for k, v in list(firm["industry_breakdown"].items())[:15]:
        lines.append(f"- {k}: {v}")
    lines += ["", "## Region breakdown"]
    for k, v in firm["region_breakdown"].items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Sample companies (first 40)"]
    for c in companies[:40]:
        lines.append(
            f"- **{c['company']}** · {c.get('industry') or '—'} · {c.get('region') or '—'} · "
            f"{c.get('asset_class') or '—'} · YOI {c.get('investment_year') or '—'} · {c.get('hq') or ''}"
        )
    lines += [
        "",
        "## Method",
        "1. Playwright opened `kkr.com/invest/portfolio`",
        "2. Captured XHR to `bioportfoliosearch.bioportfoliosearch.json`",
        f"3. Paginated all **{total_pages}** pages through the same browser session",
        "",
        f"Artifacts: `{OUT}`, `{CSV_LIKE}`",
    ]
    SUMMARY.write_text("\n".join(lines))
    print(f"done companies={len(companies)} -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
