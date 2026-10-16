import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { getFeatureForPath } from '@/lib/accessPolicy';
import {
  ensureGoogleAnalytics,
  maybeTrackDay7Return,
  trackFunnelEvent,
  trackReturnedToIntended,
} from '@/lib/funnelAnalytics';

/**
 * Global route-level funnel tracker. Mount once inside the router tree.
 */
export default function FunnelRouteTracker() {
  const location = useLocation();
  const { user, authReady } = useAuth();
  const sessionStarted = useRef(false);
  const lastPath = useRef('');

  useEffect(() => {
    ensureGoogleAnalytics();
  }, []);

  useEffect(() => {
    if (!authReady) return;
    if (!sessionStarted.current) {
      sessionStarted.current = true;
      trackFunnelEvent('visitor_session', {
        authenticated: Boolean(user),
        path: location.pathname,
      });
      maybeTrackDay7Return({ authenticated: Boolean(user) });
    }
  }, [authReady, user, location.pathname]);

  useEffect(() => {
    const path = `${location.pathname}${location.search || ''}`;
    if (path === lastPath.current) return;
    lastPath.current = path;

    if (location.pathname === '/') {
      trackFunnelEvent('public_home', { path: '/' });
    } else if (location.pathname.startsWith('/article/')) {
      trackFunnelEvent('public_article', {
        path: location.pathname,
        slug: location.pathname.replace(/^\/article\//, ''),
      });
    }

    // After signup/login, landing back on the intended gated page
    if (user && getFeatureForPath(location.pathname)) {
      trackReturnedToIntended(location.pathname);
    }
  }, [location.pathname, location.search, user]);

  return null;
}
