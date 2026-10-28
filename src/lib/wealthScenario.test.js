import test from 'node:test';
import assert from 'node:assert/strict';
import { projectAsset, compareScenarios, fdAsset, breakEvenGrowth } from './wealthScenario.js';
const plan = { capital: 10000000, years: 5, fdRate: 7, incomeTax: 30, inflation: 5, reinvest: true };
const land = { id: 'land', label: 'Land', growth: 8, incomeYield: 0, entryCost: 7, exitCost: 2, annualCost: 0, gainsTax: 15 };
const near = (a, b) => assert.ok(Math.abs(a - b) < 0.001, `${a} != ${b}`);

test('FD matches the analytical after-tax compounding formula', () => {
  const result = projectAsset(plan, fdAsset(plan));
  near(result.netWealth, plan.capital * 1.049 ** 5);
  near(result.firstYearNetIncome, 490000);
  near(result.realWealth, result.netWealth / 1.05 ** 5);
  near(result.totalTax, (result.netWealth - plan.capital) * .3 / .7);
});
test('uninvested cash is retained at zero return and not silently compounded', () => {
  const result = projectAsset({ ...plan, reinvest: false }, fdAsset(plan));
  near(result.netWealth, 12450000);
  near(result.totalTax, 1050000);
});
test('property entry costs consume budget, sale costs reduce gains, no tax on unrealized growth', () => {
  const result = projectAsset(plan, land);
  const invested = 10000000 / 1.07;
  const sale = invested * 1.08 ** 5 * .98;
  near(result.initialAsset, invested);
  near(result.netWealth, sale - (sale - 10000000) * .15);
  near(result.totalTax, result.exitTax);
  near(result.firstYearNetIncome, 0);
});
test('losses never create a fictitious tax refund', () => {
  const result = projectAsset(plan, { ...land, growth: -20 });
  assert.equal(result.totalTax, 0);
  assert.ok(result.netWealth < plan.capital);
});
test('break-even solves against exactly the same budget and horizon', () => {
  const growth = breakEvenGrowth(plan, land);
  near(projectAsset(plan, { ...land, growth }).netWealth, projectAsset(plan, fdAsset(plan)).netWealth);
  const [fd, property] = compareScenarios(plan, [land]);
  near(property.vsFd, property.netWealth - fd.netWealth);
});
test('holding costs create a disclosed funding shortfall for non-income assets', () => {
  const result = projectAsset(plan, { ...land, annualCost: 1 });
  assert.ok(result.cashShortfall > 0);
  assert.ok(result.totalCosts > result.entryCost);
});
test('rejects empty, invalid, non-finite and fractional-year financial inputs', () => {
  for (const capital of ['', null, true, Infinity, -1, 'invalid']) assert.throws(() => projectAsset({ ...plan, capital }, land));
  assert.throws(() => projectAsset({ ...plan, years: 1.5 }, land));
  assert.throws(() => projectAsset(plan, { ...land, gainsTax: 101 }));
});
