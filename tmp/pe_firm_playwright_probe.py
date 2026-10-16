#!/usr/bin/env python3
"""Probe Blackstone, KKR, Apollo public sites via Playwright — discover pullable data."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 AGIB-PE-Probe/1.0"
)

OUT = Path("/opt/cursor/artifacts/pe_three_firms_playwright_probe.json")
SUMMARY = Path("/opt/cursor/artifacts/pe_three_firms_playwright_summary.md")
RAW = Path("/opt/cursor/artifacts/pe_probe_raw")
RAW.mkdir(parents=True, exist_ok=True)

FIRMS = [
    {
        "id": "blackstone",
        "name": "Blackstone",
        "hq": "New York",
        "claimed_aum": "$1.2T+",
        "home": "https://www.blackstone.com",
        "pages": {
            "home": "https://www.blackstone.com",
            "about": "https://www.blackstone.com/the-firm/",
            "private_equity": "https://www.blackstone.com/our-businesses/private-equity/",
            "portfolio": "https://www.blackstone.com/our-businesses/private-equity/portfolio/",
            "investments": "https://www.blackstone.com/our-businesses/private-equity/portfolio/",
        },
    },
    {
        "id": "kkr",
        "name": "KKR",
        "hq": "New York",
        "claimed_aum": "$650B+",
        "home": "https://www.kkr.com",
        "pages": {
            "home": "https://www.kkr.com/",
            "about": "https://www.kkr.com/about",
            "private_equity": "https://www.kkr.com/invest/private-equity",
            "portfolio": "https://www.kkr.com/invest/portfolio",
        },
        "known_api": (
            "https://www.kkr.com/content/kkr/sites/global/en/invest/portfolio/"
            "jcr:content/root/main-par/bioportfoliosearch.bioportfoliosearch.json"
        ),
    },
    {
        "id": "apollo",
        "name": "Apollo Global Management",
        "hq": "New York",
        "claimed_aum": "$800B+",
        "home": "https://www.apollo.com",
        "pages": {
            "home": "https://www.apollo.com",
            "about": "https://www.apollo.com/about-us",
            "private_equity": "https://www.apollo.com/strategies/private-equity",
            "portfolio": "https://www.apollo.com/strategies/private-equity/portfolio",
            "investments": "https://www.apollo.com/insights-news/portfolio-companies",
        },
    },
]


def clean(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "")).strip()


def is_interesting_json_url(url: str) -> bool:
    u = url.lower()
    if any(x in u for x in ["onetrust", "cookielaw", "googletagmanager", "linkedin", "adobe", "demdex", "apptentive", "contentsquare", "6sense", "heap", "gtm"]):
        return False
    return any(
        x in u
        for x in [
            "portfolio", "company", "companies", "invest", "search", "graphql",
            "api", ".json", "bioportfolio", "content/", "wp-json", "algolia",
        ]
    )


def mine_companies_from_json(data, source_url: str) -> list[dict]:
    found = []
    stack = [data]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            name = cur.get("name") or cur.get("title") or cur.get("companyName") or cur.get("company")
            if isinstance(name, str) and 2 <= len(name.strip()) <= 120:
                row = {"company": clean(name), "source_api": source_url[:200]}
                for k, out in [
                    ("sector", "sector"), ("industry", "industry"), ("region", "region"),
                    ("hq", "hq"), ("headquarters", "hq"), ("assetClass", "asset_class"),
                    ("yoi", "investment_year"), ("year", "investment_year"),
                    ("url", "company_website"), ("website", "company_website"),
                ]:
                    v = cur.get(k)
                    if v and not row.get(out):
                        row[out] = clean(str(v))
                found.append(row)
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur[:800])
    # dedupe
    out, seen = [], set()
    for r in found:
        k = r["company"].lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def extract_metrics(text: str) -> list[str]:
    metrics = []
    for pat in [
        r"\$[\d,.]+ ?[BbTtMm](?:illion)?(?:\+)?",
        r"\b\d{1,4}\+?\s+(?:portfolio companies|companies|employees|offices|countries|years)\b",
        r"\bAUM\b[^.]{0,80}",
        r"\bassets under management\b[^.]{0,80}",
        r"\bfounded\b[^.]{0,60}",
        r"\bsince \d{4}\b",
    ]:
        for m in re.finditer(pat, text, flags=re.I):
            metrics.append(clean(m.group(0)))
    return list(dict.fromkeys(metrics))[:30]


def extract_focus(text: str) -> list[str]:
    focus = []
    for kw in [
        "buyout", "growth", "core", "impact", "infrastructure", "credit", "real estate",
        "healthcare", "technology", "industrials", "consumer", "financial services",
        "asia", "europe", "americas", "middle-market", "private equity", "insurance",
    ]:
        if re.search(rf"\b{re.escape(kw)}\b", text, flags=re.I):
            focus.append(kw)
    return focus


def paginate_kkr_api(page) -> dict:
    base = FIRMS[1]["known_api"]
    first = page.request.get(f"{base}?page=1&sortParameter=&sortingOrder=asc&keyword=&cfnode=", headers={"Accept": "application/json"})
    if first.status != 200:
        return {"error": f"status {first.status}"}
    data = first.json()
    results = list(data.get("results") or [])
    pages = int(data.get("pages") or 1)
    for p in range(2, pages + 1):
        r = page.request.get(
            f"{base}?page={p}&sortParameter=&sortingOrder=asc&keyword=&cfnode=",
            headers={"Accept": "application/json"},
        )
        if r.status == 200:
            results.extend(r.json().get("results") or [])
        time.sleep(0.1)
    companies = []
    for row in results:
        name = clean(row.get("name") or "")
        if not name:
            continue
        companies.append({
            "company": name,
            "hq": row.get("hq"),
            "region": row.get("region"),
            "asset_class": row.get("assetClass"),
            "industry": row.get("industry"),
            "investment_year": row.get("yoi"),
            "company_website": row.get("url"),
            "logo": row.get("logo"),
        })
    return {
        "endpoint": base,
        "total_hits": data.get("hits"),
        "pages": pages,
        "companies": companies,
    }


def probe_firm(page, firm: dict) -> dict:
    api_hits = []
    api_companies = []

    def on_response(resp):
        try:
            url = resp.url
            ct = (resp.headers.get("content-type") or "").lower()
            if resp.status >= 400:
                return
            if "json" not in ct and not is_interesting_json_url(url):
                return
            if not is_interesting_json_url(url) and "application/json" not in ct:
                return
            try:
                data = resp.json()
            except Exception:
                return
            api_hits.append({"url": url, "status": resp.status, "keys": list(data.keys())[:20] if isinstance(data, dict) else "list"})
            mined = mine_companies_from_json(data, url)
            if mined:
                api_companies.extend(mined[:200])
        except Exception:
            pass

    page.on("response", on_response)
    page_results = {}
    all_text = []

    for key, url in firm["pages"].items():
        try:
            print(f"  [{firm['id']}] {key}: {url}", flush=True)
            page.goto(url, wait_until="domcontentloaded", timeout=70000)
            try:
                page.wait_for_load_state("networkidle", timeout=18000)
            except Exception:
                pass
            page.wait_for_timeout(2500)
            for _ in range(6):
                page.mouse.wheel(0, 1800)
                page.wait_for_timeout(500)
            body = clean(page.locator("body").inner_text())
            all_text.append(body)
            h1 = [clean(x) for x in page.locator("h1").all()[:3] if clean(x.inner_text())]
            h2 = [clean(x.inner_text()) for x in page.locator("h2").all()[:12] if clean(x.inner_text())]
            dom_links = []
            for a in page.locator("a[href]").all()[:500]:
                try:
                    href = a.get_attribute("href") or ""
                    text = clean(a.inner_text())
                    if not text or len(text) > 80:
                        continue
                    if any(x in href.lower() for x in ["portfolio", "company", "invest", "cfnode"]):
                        dom_links.append({"text": text, "href": urljoin(url, href)})
                except Exception:
                    pass
            page_results[key] = {
                "url": page.url,
                "title": page.title(),
                "h1": h1,
                "h2": h2[:8],
                "text_excerpt": body[:2500],
                "dom_portfolio_links": dom_links[:40],
                "status": "ok",
            }
            (RAW / f"{firm['id']}_{key}.txt").write_text(body[:15000])
        except Exception as exc:
            page_results[key] = {"url": url, "status": "error", "error": str(exc)[:300]}

    combined = " ".join(all_text)
    firm_info = {
        "firm_name": firm["name"],
        "hq_claimed": firm["hq"],
        "aum_claimed": firm["claimed_aum"],
        "website": firm["home"],
        "metrics_snippets": extract_metrics(combined),
        "focus_keywords": extract_focus(combined),
        "pages_probed": list(firm["pages"].keys()),
    }

    # dedupe api companies
    merged = {}
    for c in api_companies:
        k = c["company"].lower()
        if k not in merged:
            merged[k] = c

    portfolio_pull = None
    if firm["id"] == "kkr":
        try:
            page.goto(firm["pages"]["portfolio"], wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)
            portfolio_pull = paginate_kkr_api(page)
        except Exception as exc:
            portfolio_pull = {"error": str(exc)}

    # classify pullable categories based on what we found
    pullable = {
        "firm_information": {
            "available": bool(firm_info["metrics_snippets"] or firm_info["focus_keywords"]),
            "fields": ["name", "hq_signals", "focus", "strategy_snippets", "metrics_from_public_pages"],
            "sample_metrics": firm_info["metrics_snippets"][:10],
        },
        "portfolio_companies": {
            "available": bool(portfolio_pull and portfolio_pull.get("companies")) or len(merged) >= 5,
            "count_from_api": len(portfolio_pull.get("companies") or []) if portfolio_pull else len(merged),
            "fields_detected": sorted({k for c in (portfolio_pull or {}).get("companies", list(merged.values())[:1]) for k in c.keys()}),
            "sample": (portfolio_pull or {}).get("companies", list(merged.values()))[:5],
        },
        "investment_criteria": {
            "available": bool(re.search(r"revenue|ebitda|enterprise value|equity check|ticket", combined, re.I)),
            "note": "Usually on strategy pages; may require deeper page crawl",
        },
        "team_directory": {
            "available": bool(re.search(r"\b(partner|managing director|operating partner|team)\b", combined, re.I)),
            "note": "Team pages not fully probed in this pass",
        },
        "portfolio_news": {
            "available": bool(re.search(r"press release|news|announcement|acquisition|exit", combined, re.I)),
        },
        "case_studies": {
            "available": bool(re.search(r"case study|investment story|here's the deal|value creation", combined, re.I)),
        },
        "press_releases": {
            "available": bool(re.search(r"press release|media center|newsroom", combined, re.I)),
        },
        "fund_information": {
            "available": bool(re.search(r"fund|vintage|fundraising|fund size", combined, re.I)),
        },
        "esg_reports": {
            "available": bool(re.search(r"esg|sustainability|net zero|diversity", combined, re.I)),
        },
        "documents_pdfs": {
            "available": bool(re.search(r"\.pdf|annual report|download", combined, re.I)),
        },
        "json_api_endpoints": {
            "available": len(api_hits) > 0,
            "count": len(api_hits),
            "endpoints": api_hits[:25],
        },
    }

    return {
        "firm": firm_info,
        "pages": page_results,
        "portfolio_api": portfolio_pull,
        "api_company_candidates": list(merged.values())[:100],
        "pullable_categories": pullable,
    }


def main():
    results = {
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "method": "playwright_chromium_public_site_probe",
        "firms": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=UA, viewport={"width": 1440, "height": 1200}, locale="en-US")
        page = context.new_page()

        for firm in FIRMS:
            print(f"\n=== {firm['name']} ===", flush=True)
            results["firms"][firm["id"]] = probe_firm(page, firm)
            pc = results["firms"][firm["id"]]["pullable_categories"]["portfolio_companies"]
            print(f"  portfolio count: {pc.get('count_from_api', 0)}", flush=True)
            print(f"  json endpoints: {results['firms'][firm['id']]['pullable_categories']['json_api_endpoints']['count']}", flush=True)

        browser.close()

    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False)[:8_000_000])

    lines = [
        "# PE Firm Playwright Probe — Blackstone, KKR, Apollo",
        "",
        f"Pulled at: `{results['pulled_at']}`",
        "",
        "What AGIB can pull from **public firm websites** using Playwright (session + XHR capture + pagination where available).",
        "",
    ]

    category_labels = [
        ("firm_information", "Firm information"),
        ("portfolio_companies", "Portfolio companies"),
        ("investment_criteria", "Investment criteria"),
        ("team_directory", "Team directory"),
        ("portfolio_news", "Portfolio news"),
        ("case_studies", "Case studies"),
        ("press_releases", "Press releases"),
        ("fund_information", "Fund information"),
        ("esg_reports", "ESG / sustainability"),
        ("documents_pdfs", "PDFs / reports"),
        ("json_api_endpoints", "Structured JSON APIs"),
    ]

    for fid in ["blackstone", "kkr", "apollo"]:
        data = results["firms"][fid]
        fi = data["firm"]
        lines += [
            f"## {fi['firm_name']} ({fi['aum_claimed']})",
            "",
            f"- HQ: {fi['hq_claimed']}",
            f"- Website: {fi['website']}",
            f"- Metrics found: {', '.join(fi['metrics_snippets'][:8]) or '—'}",
            f"- Focus: {', '.join(fi['focus_keywords'][:12]) or '—'}",
            "",
            "### Pullable now (this probe)",
        ]
        for key, label in category_labels:
            cat = data["pullable_categories"][key]
            yes = "Yes" if cat.get("available") else "Partial / not in this pass"
            extra = ""
            if key == "portfolio_companies" and cat.get("count_from_api"):
                extra = f" — **{cat['count_from_api']} companies**"
            if key == "json_api_endpoints" and cat.get("count"):
                extra = f" — **{cat['count']} endpoints**"
            lines.append(f"- **{label}:** {yes}{extra}")
        if data.get("portfolio_api") and data["portfolio_api"].get("endpoint"):
            lines.append(f"- Portfolio API: `{data['portfolio_api']['endpoint'][:120]}...`")
        if data["pullable_categories"]["portfolio_companies"].get("sample"):
            lines += ["", "Sample companies:"]
            for c in data["pullable_categories"]["portfolio_companies"]["sample"][:8]:
                bits = [c.get("company", "?")]
                if c.get("industry"):
                    bits.append(c["industry"])
                if c.get("region"):
                    bits.append(c["region"])
                if c.get("investment_year"):
                    bits.append(f"YOI {c['investment_year']}")
                lines.append("- " + " · ".join(bits))
        lines.append("")

    lines += [
        "## Summary table",
        "",
        "| Firm | Portfolio rows | JSON APIs | Firm metrics | Best path |",
        "|------|----------------|-----------|--------------|-----------|",
    ]
    for fid in ["blackstone", "kkr", "apollo"]:
        d = results["firms"][fid]
        pc = d["pullable_categories"]["portfolio_companies"].get("count_from_api", 0)
        apis = d["pullable_categories"]["json_api_endpoints"].get("count", 0)
        metrics = len(d["firm"]["metrics_snippets"])
        best = "Paginated JSON API" if fid == "kkr" and pc >= 100 else ("XHR/JSON mining" if apis else "DOM scrape only")
        lines.append(f"| {d['firm']['firm_name']} | {pc} | {apis} | {metrics} | {best} |")

    SUMMARY.write_text("\n".join(lines))
    print(f"\nWrote {OUT}\nWrote {SUMMARY}")


if __name__ == "__main__":
    main()
