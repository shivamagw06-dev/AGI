import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import {
  buildLoginUrl,
  getFeatureForPath,
  isPathGated,
  resolveAccess,
} from './accessPolicy.js';

describe('accessPolicy', () => {
  it('keeps acquisition surfaces free', () => {
    assert.equal(getFeatureForPath('/'), null);
    assert.equal(getFeatureForPath('/research'), null);
    assert.equal(getFeatureForPath('/article/nse-ipo'), null);
    assert.equal(getFeatureForPath('/markets'), null);
    assert.equal(getFeatureForPath('/markets/stocks'), null);
    assert.equal(isPathGated('/category/economics'), false);
  });

  it('gates proprietary intelligence surfaces', () => {
    assert.equal(getFeatureForPath('/ask'), 'ask_agi');
    assert.equal(getFeatureForPath('/agi/companies/HDFCBANK'), 'agi_workspace');
    assert.equal(getFeatureForPath('/valuation-intelligence'), 'valuation');
    assert.equal(getFeatureForPath('/hedge-fund'), 'hedge_fund');
    assert.equal(getFeatureForPath('/live-alpha'), 'live_alpha');
    assert.equal(getFeatureForPath('/economics'), 'economics');
    assert.equal(getFeatureForPath('/research/stocks/INFY'), 'company_research');
    assert.equal(getFeatureForPath('/workspace'), 'workspace');
  });

  it('builds signup URLs that preserve returnTo', () => {
    assert.equal(
      buildLoginUrl({ returnTo: '/research/stocks/HDFCBANK', mode: 'signup' }),
      '/login?mode=signup&next=%2Fresearch%2Fstocks%2FHDFCBANK'
    );
  });

  it('allows authenticated users on gated paths', () => {
    assert.equal(resolveAccess({ user: { id: '1' }, pathname: '/ask' }).allowed, true);
    assert.equal(resolveAccess({ user: null, pathname: '/ask' }).allowed, false);
    assert.equal(resolveAccess({ user: null, pathname: '/' }).allowed, true);
  });
});
