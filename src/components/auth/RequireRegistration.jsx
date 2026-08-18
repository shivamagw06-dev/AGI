import { useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { getFeatureForPath, resolveAccess } from '@/lib/accessPolicy';
import UnlockIntelligenceGate from '@/components/auth/UnlockIntelligenceGate';

/**
 * Soft registration gate for proprietary intelligence surfaces.
 * Home, article lists, and articles stay public (see accessPolicy).
 */
export default function RequireRegistration({ feature, children }) {
  const { user, loading, authReady } = useAuth();
  const location = useLocation();
  const returnTo = `${location.pathname}${location.search || ''}`;
  const resolvedFeature = feature || getFeatureForPath(location.pathname) || 'intelligence';
  const access = resolveAccess({ user, pathname: location.pathname });

  if (!authReady || loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center bg-[#070f16] px-4 text-sm text-slate-400">
        Checking access…
      </div>
    );
  }

  if (access.allowed) {
    return children;
  }

  return <UnlockIntelligenceGate feature={resolvedFeature} returnTo={returnTo} />;
}
