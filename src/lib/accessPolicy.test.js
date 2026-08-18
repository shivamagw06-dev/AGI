import { describe, expect, it } from 'vitest';
import {
  buildLoginUrl,
  getFeatureForPath,
  isPathGated,
  resolveAccess,
} from '@/lib/accessPolicy';

describe('accessPolicy', () => {
  it('keeps acquisition surfaces free', () => {
    expect(getFeatureForPath('/')).toBeNull();
    expect(getFeatureForPath('/research')).toBeNull();
    expect(getFeatureForPath('/article/nse-ipo')).toBeNull();
    expect(getFeatureForPath('/markets')).toBeNull();
    expect(isPathGated('/category/economics')).toBe(false);
  });

  it('gates proprietary intelligence surfaces', () => {
    expect(getFeatureForPath('/ask')).toBe('ask_agi');
    expect(getFeatureForPath('/agi/companies/HDFCBANK')).toBe('agi_workspace');
    expect(getFeatureForPath('/valuation-intelligence')).toBe('valuation');
    expect(getFeatureForPath('/hedge-fund')).toBe('hedge_fund');
    expect(getFeatureForPath('/live-alpha')).toBe('live_alpha');
    expect(getFeatureForPath('/economics')).toBe('economics');
    expect(getFeatureForPath('/research/stocks/INFY')).toBe('company_research');
    expect(getFeatureForPath('/workspace')).toBe('workspace');
  });

  it('builds signup URLs that preserve returnTo', () => {
    expect(buildLoginUrl({ returnTo: '/research/stocks/HDFCBANK', mode: 'signup' })).toBe(
      '/login?mode=signup&next=%2Fresearch%2Fstocks%2FHDFCBANK'
    );
  });

  it('allows authenticated users on gated paths', () => {
    expect(resolveAccess({ user: { id: '1' }, pathname: '/ask' }).allowed).toBe(true);
    expect(resolveAccess({ user: null, pathname: '/ask' }).allowed).toBe(false);
    expect(resolveAccess({ user: null, pathname: '/' }).allowed).toBe(true);
  });
});
