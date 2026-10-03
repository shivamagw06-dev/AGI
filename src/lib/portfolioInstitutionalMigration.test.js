import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const methodologySql = readFileSync(new URL('../../supabase/migrations/20260827213000_portfolio_institutional_methodology.sql', import.meta.url), 'utf8');
const founderSql = readFileSync(new URL('../../supabase/migrations/20260826030000_founder_portfolio.sql', import.meta.url), 'utf8');

test('research impact UPDATE checks ownership on both existing and resulting rows', () => {
  const policy = methodologySql.match(/create policy "Users can update own portfolio research impacts"[\s\S]*?;\n/i)?.[0] || '';
  assert.match(policy, /using\s*\([\s\S]*?auth\.uid\(\)[\s\S]*?exists\s*\([\s\S]*?portfolio\.id\s*=\s*portfolio_id[\s\S]*?portfolio\.user_id\s*=\s*\(select auth\.uid\(\)\)/i);
  assert.match(policy, /with check\s*\([\s\S]*?auth\.uid\(\)[\s\S]*?exists\s*\([\s\S]*?portfolio\.id\s*=\s*portfolio_id[\s\S]*?portfolio\.user_id\s*=\s*\(select auth\.uid\(\)\)/i);
});

test('anonymous users receive no portfolio research or methodology write grants', () => {
  assert.match(methodologySql, /revoke all on table public\.portfolio_research_impacts from anon/i);
  assert.match(methodologySql, /revoke all on table public\.portfolio_methodology_versions from anon/i);
  assert.doesNotMatch(methodologySql, /grant[\s\S]*?(insert|update|delete)[\s\S]*?portfolio_(research_impacts|methodology_versions)[\s\S]*?to anon/i);
});

test('ordinary authenticated clients cannot write methodology definitions', () => {
  assert.match(methodologySql, /grant select on table public\.portfolio_methodology_versions to authenticated/i);
  assert.doesNotMatch(methodologySql, /grant[\s\S]*?(insert|update|delete)[\s\S]*?portfolio_methodology_versions[\s\S]*?to authenticated/i);
});

test('Founder Portfolio private records remain founder-admin only', () => {
  assert.match(founderSql, /create policy "Founder transactions are private"[\s\S]*?using \(public\.is_founder_portfolio_admin\(\)\)[\s\S]*?with check \(public\.is_founder_portfolio_admin\(\)\)/i);
  assert.match(founderSql, /create policy "Founder snapshots are private"[\s\S]*?using \(public\.is_founder_portfolio_admin\(\)\)[\s\S]*?with check \(public\.is_founder_portfolio_admin\(\)\)/i);
  assert.doesNotMatch(founderSql, /grant[\s\S]*?founder_portfolio_(transactions|snapshots|validation_reports)[\s\S]*?to anon/i);
});
