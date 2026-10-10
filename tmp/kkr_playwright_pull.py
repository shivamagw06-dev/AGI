#!/usr/bin/env python3
"""One-shot Playwright pull of KKR public PE pages."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 AGIB-PE-Probe/1.0"
)

URLS = {
    "private_equity": "https://www.kkr.com/invest/private-equity",
    "portfolio": "https://www.kkr.com/invest/portfolio",
    "about": "https://www.kkr.com/about",
    "home": "https://www.kkr.com/",
}

OUT = Path("/opt/cursor/artifacts/kkr_pe_playwright_pull.json")
TXT = Path("/opt/cursor/artifacts/kkr_pe_playwright_summary.md")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def extract_page(page, url: str) -> dict:
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    # Give client-rendered portfolio cards a moment
    page.wait_for_timeout(2500)

    title = clean(page.title())
    h1 = [clean(el.inner_text()) for el in page.locator("h1").all()[:5]]
    h2 = [clean(el.inner_text()) for el in page.locator("h2").all()[:20]]
    h3 = [clean(el.inner_text()) for el in page.locator("h3").all()[:40]]

    body_text = clean(page.locator("body").inner_text())[:12000]

    # Collect candidate portfolio / company anchors
    anchors = []
    for a in page.locator("a[href]").all():
        try:
            href = a.get_attribute("href") or ""
            text = clean(a.inner_text())
            if not href:
                continue
            full = urljoin(url, href)
            anchors.append({"text": text, "href": full})
        except Exception:
            continue

    portfolio_links = []
    seen = set()
    for a in anchors:
        href = a["href"]
        text = a["text"]
        low = href.lower()
        if "portfolio" in low or "cfnode=" in low or "/invest/" in low:
            key = (text.lower(), low)
            if key in seen:
                continue
            seen.add(key)
            if text and len(text) > 1:
                portfolio_links.append(a)

    # Heuristic company cards: links under portfolio with cfnode or company-like text
    companies = []
    company_seen = set()
    for a in anchors:
        href = a["href"]
        text = a["text"]
        if not text or len(text) < 2 or len(text) > 80:
            continue
        if "cfnode=" in href or re.search(r"/invest/portfolio/", href):
            key = text.lower()
            if key in company_seen:
                continue
            # skip nav junk
            if text.lower() in {
                "portfolio", "explore portfolio", "private equity", "invest",
                "learn more", "read more", "here's the deal", "meet the team",
            }:
                continue
            company_seen.add(key)
            companies.append({"company": text, "url": href})

    # Metrics / stats often appear as number + label pairs
    metrics = []
    for pat in [
        r"\$[\d,.]+\s*[BbTtMm]?",
        r"\b\d{2,4}\+?\s+(?:portfolio companies|employees|offices|countries|years)\b",
        r"\bAUM\b[^.]{0,80}",
        r"\bfounded\b[^.]{0,80}",
        r"\bsince\s+\d{4}\b[^.]{0,80}",
        r"\b\d+\s+portfolio companies\b",
    ]:
        for m in re.finditer(pat, body_text, flags=re.I):
            metrics.append(clean(m.group(0)))
    # dedupe metrics
    metrics = list(dict.fromkeys(metrics))[:40]

    # Strategy / focus keywords
    focus_hits = []
    for kw in [
        "buyout", "growth", "infrastructure", "credit", "real estate",
        "healthcare", "technology", "industrials", "consumer", "financial services",
        "energy", "impact", "core", "middle-market", "asia", "europe", "americas",
    ]:
        if re.search(rf"\b{re.escape(kw)}\b", body_text, flags=re.I):
            focus_hits.append(kw)

    return {
        "url": url,
        "final_url": page.url,
        "title": title,
        "h1": [x for x in h1 if x],
        "h2": [x for x in h2 if x],
        "h3": [x for x in h3 if x][:25],
        "metrics_snippets": metrics,
        "focus_keywords": focus_hits,
        "portfolio_or_invest_links": portfolio_links[:80],
        "company_candidates": companies[:120],
        "text_excerpt": body_text[:4000],
        "status": "ok",
    }


def main():
    pages = {}
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=UA,
            viewport={"width": 1440, "height": 1100},
            locale="en-US",
        )
        page = context.new_page()
        for key, url in URLS.items():
            try:
                print(f"fetching {key}: {url}", flush=True)
                pages[key] = extract_page(page, url)
                print(
                    f"  title={pages[key]['title']!r} companies={len(pages[key]['company_candidates'])}",
                    flush=True,
                )
            except Exception as exc:
                pages[key] = {"url": url, "status": "error", "error": str(exc)[:400]}
                errors.append({"page": key, "error": str(exc)[:400]})
                print(f"  ERROR {exc}", flush=True)
        browser.close()

    # Merge company candidates across pages
    merged = {}
    for key, data in pages.items():
        for c in data.get("company_candidates") or []:
            name = c["company"]
            if name not in merged:
                merged[name] = {**c, "sources": [key]}
            else:
                if key not in merged[name]["sources"]:
                    merged[name]["sources"].append(key)

    firm = {
        "firm_name": "KKR",
        "website": "https://www.kkr.com",
        "strategy_page": URLS["private_equity"],
        "portfolio_page": URLS["portfolio"],
        "focus_keywords": sorted(
            {
                kw
                for data in pages.values()
                for kw in (data.get("focus_keywords") or [])
            }
        ),
        "metrics_snippets": list(
            dict.fromkeys(
                m
                for data in pages.values()
                for m in (data.get("metrics_snippets") or [])
            )
        )[:50],
        "portfolio_company_candidates": list(merged.values()),
        "portfolio_company_count_extracted": len(merged),
    }

    result = {
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "method": "playwright_chromium_headless",
        "firm": firm,
        "pages": pages,
        "errors": errors,
        "notes": [
            "Public pages only; KKR portfolio listing is JS-rendered and may paginate/filter.",
            "company_candidates are heuristic extractions from links — not a complete verified portfolio.",
            "This is a feasibility probe, not a production PEI ingestion run.",
        ],
    }

    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    companies = firm["portfolio_company_candidates"][:40]
    lines = [
        "# KKR Private Equity — Playwright pull",
        "",
        f"Pulled at: `{result['pulled_at']}`",
        "",
        "## Firm signals",
        f"- Focus keywords: {', '.join(firm['focus_keywords']) or '—'}",
        f"- Metric snippets: {', '.join(firm['metrics_snippets'][:12]) or '—'}",
        f"- Company candidates extracted: **{firm['portfolio_company_count_extracted']}**",
        "",
        "## Pages",
    ]
    for key, data in pages.items():
        lines.append(f"### {key}")
        lines.append(f"- URL: {data.get('final_url') or data.get('url')}")
        lines.append(f"- Status: {data.get('status')}")
        if data.get("title"):
            lines.append(f"- Title: {data['title']}")
        if data.get("h1"):
            lines.append(f"- H1: {'; '.join(data['h1'][:3])}")
        if data.get("error"):
            lines.append(f"- Error: {data['error']}")
        lines.append("")
    lines.append("## Sample portfolio company candidates")
    if not companies:
        lines.append("_No company candidates extracted — page may be blocked or heavily JS-gated._")
    else:
        for c in companies:
            lines.append(f"- **{c['company']}** — {c['url']}")
    TXT.write_text("\n".join(lines))
    print(f"\nWrote {OUT}")
    print(f"Wrote {TXT}")
    print(f"Companies: {firm['portfolio_company_count_extracted']}")


if __name__ == "__main__":
    main()
