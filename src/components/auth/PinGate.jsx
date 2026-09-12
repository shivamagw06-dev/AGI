import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { shouldChallengePin } from '@/lib/devicePin';

const EXEMPT_PREFIXES = [
  '/login',
  '/verify-email',
  '/forgot-password',
  '/reset-password',
  '/unlock-pin',
  '/account/security',
];

export default function PinGate({ children }) {
  const { user, authReady } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (!authReady || !user) return;
    const path = location.pathname || '/';
    if (EXEMPT_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`))) return;
    if (!shouldChallengePin(user)) return;
    const next = `${path}${location.search || ''}`;
    navigate(`/unlock-pin?next=${encodeURIComponent(next)}`, { replace: true });
  }, [authReady, user, location.pathname, location.search, navigate]);

  return children;
}
