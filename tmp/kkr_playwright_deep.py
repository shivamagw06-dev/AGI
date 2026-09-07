#!/usr/bin/env python3
"""Deeper KKR portfolio pull: capture XHR JSON + richer DOM card extraction."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 AGIB-PE-Probe/1.0"
)

PORTFOLIO = "https://www.kkr.com/invest/portfolio"
PE = "https://www.kkr.com/invest/private-equity"
OUT = Path("/opt/cursor/artifacts/kkr_pe_playwright_pull.json")
SUMMARY = Path("/opt/cursor/artifacts/kkr_pe_playwright_summary.md")
RAW_DIR = Path("/opt/cursor/artifacts/kkr_raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)


def clean(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "")).strip()


def main():
    api_hits = []
    other_json = []

    def on_response(resp):
        try:
            ct = (resp.headers.get("content-type") or "").lower()
            url = resp.url
            if resp.status >= 400:
                return
            interesting = any(
                x in url.lower()
                for x in ["portfolio", "company", "invest", "graphql", "api", "contentful", "algolia", "search"]
            )
            if "application/json" in ct or interesting and ("json" in ct or url.endswith(".json")):
                try:
                    data = resp.json()
                except Exception:
                    text = resp.text()[:5000]
                    other_json.append({"url": url, "status": resp.status, "text_preview": text[:1000]})
                    return
                api_hits.append({"url": url, "status": resp.status, "data": data})
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=UA, viewport={"width": 1440, "height": 1400}, locale="en-US")
        page = context.new_page()
        page.on("response", on_response)

        # --- Private Equity page ---
        print("PE page...", flush=True)
        page.goto(PE, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        page.wait_for_timeout(2000)
        pe_title = page.title()
        pe_text = clean(page.locator("body").inner_text())
        pe_html = page.content()
        (RAW_DIR / "private_equity.html").write_text(pe_html)
        (RAW_DIR / "private_equity.txt").write_text(pe_text)

        # --- Portfolio page ---
        print("Portfolio page...", flush=True)
        page.goto(PORTFOLIO, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=25000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

        # Scroll to trigger lazy load
        for _ in range(12):
            page.mouse.wheel(0, 2200)
            page.wait_for_timeout(700)

        # Try common "Load more" / filters
        for label in ["Load more", "Show more", "View all", "All"]:
            try:
                btn = page.get_by_role("button", name=re.compile(label, re.I))
                if btn.count():
                    btn.first.click(timeout=2000)
                    page.wait_for_timeout(1500)
            except Exception:
                pass
            try:
                link = page.get_by_role("link", name=re.compile(label, re.I))
                if link.count():
                    # don't navigate away on View all if external
                    pass
            except Exception:
                pass

        # More scrolling after load more
        for _ in range(8):
            page.mouse.wheel(0, 2200)
            page.wait_for_timeout(600)

        port_title = page.title()
        port_text = clean(page.locator("body").inner_text())
        port_html = page.content()
        (RAW_DIR / "portfolio.html").write_text(port_html)
        (RAW_DIR / "portfolio.txt").write_text(port_text)

        # DOM strategies for company cards
        companies = []
        seen = set()

        def add_company(name, href=None, sector=None, region=None, extra=None):
            name = clean(name)
            if not name or len(name) < 2 or len(name) > 100:
                return
            key = name.lower()
            junk = {
                "portfolio", "private equity", "invest", "learn more", "read more",
                "here's the deal", "meet the team", "filter", "all", "apply", "reset",
                "kkr", "explore portfolio", "our approach", "contact", "careers",
            }
            if key in junk:
                return
            if key in seen:
                return
            seen.add(key)
            row = {"company": name}
            if href:
                row["url"] = urljoin(PORTFOLIO, href)
            if sector:
                row["sector"] = clean(sector)
            if region:
                row["region"] = clean(region)
            if extra:
                row.update(extra)
            companies.append(row)

        # 1) links with cfnode
        for a in page.locator("a[href*='cfnode=']").all():
            try:
                add_company(a.inner_text() or a.get_attribute("aria-label") or "", a.get_attribute("href"))
            except Exception:
                pass

        # 2) article/card-like nodes
        for sel in [
            "[class*='portfolio'] a",
            "[class*='Portfolio'] a",
            "[class*='card'] a",
            "[class*='Card'] a",
            "[data-testid*='portfolio'] a",
            "main a",
        ]:
            try:
                locs = page.locator(sel)
                n = min(locs.count(), 400)
                for i in range(n):
                    el = locs.nth(i)
                    href = el.get_attribute("href") or ""
                    text = clean(el.inner_text())
                    if "portfolio" in href or "cfnode" in href:
                        add_company(text, href)
            except Exception:
                pass

        # 3) Parse visible text blocks that look like company tiles
        # Many sites put Company\nSector\nRegion
        for sel in ["[class*='tile']", "[class*='Tile']", "[class*='grid'] > div", "li"]:
            try:
                locs = page.locator(sel)
                n = min(locs.count(), 500)
                for i in range(n):
                    t = clean(locs.nth(i).inner_text())
                    if not t or len(t) > 200:
                        continue
                    parts = [p for p in re.split(r"\s{2,}|\n", locs.nth(i).inner_text()) if clean(p)]
                    if 1 <= len(parts) <= 4 and len(parts[0]) <= 80:
                        # weak signal: short first line + optional sector words
                        if any(k in t.lower() for k in ["technology", "health", "consumer", "industrial", "financial", "energy", "infra", "software", "services"]):
                            add_company(parts[0], sector=parts[1] if len(parts) > 1 else None, region=parts[2] if len(parts) > 2 else None)
            except Exception:
                pass

        # Save screenshot
        page.screenshot(path=str(RAW_DIR / "portfolio.png"), full_page=False)

        browser.close()

    # Persist API hits (truncate large payloads)
    api_compact = []
    extracted_from_api = []
    for hit in api_hits:
        data = hit["data"]
        api_compact.append({
            "url": hit["url"],
            "status": hit["status"],
            "type": type(data).__name__,
            "preview": json.dumps(data, ensure_ascii=False)[:1500],
        })
        # Try to mine company-like objects
        stack = [data]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                name = cur.get("name") or cur.get("title") or cur.get("companyName") or cur.get("company")
                if isinstance(name, str) and 2 <= len(name) <= 100:
                    slug = cur.get("slug") or cur.get("id") or cur.get("cfnode")
                    sector = cur.get("sector") or cur.get("industry") or cur.get("primarySector")
                    country = cur.get("country") or cur.get("region") or cur.get("geography")
                    extracted_from_api.append({
                        "company": clean(name),
                        "sector": clean(str(sector)) if sector else None,
                        "country": clean(str(country)) if country else None,
                        "slug": slug,
                        "source_api": hit["url"][:180],
                    })
                stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur[:500])

    # dedupe api companies
    api_companies = []
    seen_api = set()
    for c in extracted_from_api:
        k = c["company"].lower()
        if k in seen_api:
            continue
        seen_api.add(k)
        api_companies.append(c)

    # Merge companies
    merged = {}
    for c in companies + api_companies:
        k = c["company"].lower()
        if k not in merged:
            merged[k] = c
        else:
            for field in ("sector", "country", "region", "url", "slug"):
                if not merged[k].get(field) and c.get(field):
                    merged[k][field] = c[field]

    # Firm metrics from PE text
    metrics = []
    for pat in [
        r"\$[\d,.]+ ?[BbTtMm](?:illion)?",
        r"\b\d{2,4}\+? portfolio companies\b",
        r"\bsince \d{4}\b",
        r"\bAUM\b[^.]{0,100}",
        r"\b\d{2,4}\+? (?:years|employees|offices|countries)\b",
    ]:
        for m in re.finditer(pat, pe_text, flags=re.I):
            metrics.append(clean(m.group(0)))
    metrics = list(dict.fromkeys(metrics))[:40]

    focus = []
    for kw in [
        "buyout", "growth", "core", "impact", "infrastructure", "credit",
        "real estate", "healthcare", "technology", "industrials", "consumer",
        "asia", "europe", "americas", "middle-market", "tech growth",
    ]:
        if re.search(rf"\b{re.escape(kw)}\b", pe_text + " " + port_text, flags=re.I):
            focus.append(kw)

    result = {
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "method": "playwright_chromium_headless_deep",
        "firm": {
            "firm_name": "KKR",
            "hq_hint": "New York" if re.search(r"new york", pe_text, re.I) else None,
            "website": "https://www.kkr.com",
            "strategy_page": PE,
            "portfolio_page": PORTFOLIO,
            "pe_page_title": pe_title,
            "portfolio_page_title": port_title,
            "metrics_snippets": metrics,
            "focus_keywords": focus,
            "portfolio_company_count_extracted": len(merged),
            "portfolio_companies": list(merged.values()),
        },
        "network": {
            "json_responses_captured": len(api_hits),
            "api_hits": api_compact[:40],
            "companies_from_api": api_companies[:200],
        },
        "dom_companies_raw_count": len(companies),
        "artifacts": {
            "json": str(OUT),
            "summary": str(SUMMARY),
            "pe_html": str(RAW_DIR / "private_equity.html"),
            "portfolio_html": str(RAW_DIR / "portfolio.html"),
            "screenshot": str(RAW_DIR / "portfolio.png"),
        },
        "notes": [
            "Public pages only.",
            "If portfolio_companies is sparse, KKR may serve cards via gated API or anti-bot challenges.",
            "Feasibility probe for PEI / FAA Playwright path.",
        ],
    }

    # Keep previous pages excerpt useful
    result["text_excerpts"] = {
        "private_equity": pe_text[:3500],
        "portfolio": port_text[:3500],
    }

    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    lines = [
        "# KKR Private Equity — Playwright deep pull",
        "",
        f"Pulled at: `{result['pulled_at']}`",
        "",
        "## Result",
        f"- PE page: **{pe_title}**",
        f"- Portfolio page: **{port_title}**",
        f"- JSON/XHR responses captured: **{len(api_hits)}**",
        f"- Companies extracted: **{len(merged)}**",
        f"- Focus: {', '.join(focus) or '—'}",
        f"- Metrics: {', '.join(metrics[:15]) or '—'}",
        "",
        "## Companies",
    ]
    if not merged:
        lines.append("_None extracted from DOM/API. Check raw HTML/screenshot for bot wall or empty shell._")
    else:
        for c in list(merged.values())[:60]:
            bits = [f"**{c['company']}**"]
            if c.get("sector"):
                bits.append(c["sector"])
            if c.get("country") or c.get("region"):
                bits.append(c.get("country") or c.get("region"))
            if c.get("url"):
                bits.append(c["url"])
            lines.append("- " + " · ".join(bits))
    lines += ["", "## Top API endpoints"]
    if not api_compact:
        lines.append("_No JSON responses captured._")
    else:
        for hit in api_compact[:15]:
            lines.append(f"- `{hit['status']}` {hit['url'][:160]}")
    SUMMARY.write_text("\n".join(lines))

    # dump full api payloads separately (truncated)
    (RAW_DIR / "api_hits.json").write_text(json.dumps(api_compact, indent=2, ensure_ascii=False)[:2_000_000])

    print(f"companies={len(merged)} api_hits={len(api_hits)}", flush=True)
    print("sample:", [c['company'] for c in list(merged.values())[:15]], flush=True)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
