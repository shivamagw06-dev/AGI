import test from 'node:test';
import assert from 'node:assert/strict';
import { parseIpoPaste } from '../src/lib/ipoPasteParser.js';
import { buildAiSummary } from '../src/lib/ipoIntelligence.js';
const source = `Example IPO is a book build issue of ₹100 crores.
About Example Ltd.
A company operating in India with a long operating history.
Company Financials
Period Ended\t30 Jun 2026\t31 Mar 2026\t31 Mar 2025\t31 Mar 2024
Assets\t100\t90\t80\t70
Profit After Tax\t5\t20\t15\t10
Key Performance Indicator (KPI)
KPI\tJun 30, 2026\tMar 31, 2026
EBITDA Margin\t10%\t20%
IPO Valuation`;
test('full paste retains four financial columns without comparing quarter PAT or margin to full year', () => {
 const p = parseIpoPaste(source);
 assert.deepEqual(p.financials.rows.profit_after_tax, [5,20,15,10]);
 assert.equal(p.financials.periods.length,4);
 assert.ok(!p.risks.some(r => /declined/.test(r)));
});
test('structured risks never padded with title or review notice', () => {
 const risk='Debt repayment absorbs most of the fresh issue proceeds.';
 const summary=buildAiSummary({title:'Example IPO Intelligence',excerpt:'Automated extraction, analyst review required.',researchMeta:{ipo_facts:{},risks:risk}});
 assert.deepEqual(summary.risks,[risk]);
});
test('unstructured content without risk evidence cannot become a risk', () => {
 const summary=buildAiSummary({title:'Example IPO Intelligence',excerpt:'A company operating across India with a broad product portfolio.'});
 assert.deepEqual(summary.risks,['No explicit risk language detected in excerpt.']);
});
test('latest reported loss is explicit and has no default financial score', () => {
 const p=parseIpoPaste(source.replace('5\t20\t15\t10','-5\t20\t15\t10'));
 assert.ok(p.risks.some(r=>/net loss/.test(r)));
 assert.equal(p.suggestedScores.financial_quality,'');
});
