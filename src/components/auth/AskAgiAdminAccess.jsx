import { useEffect } from 'react';
import { Navigate } from 'react-router-dom';

import { useAuth } from '@/contexts/AuthContext';
import { isAdmin } from '@/lib/adminAuth';

export function AskAgiVisibility() {
  const { user, loading } = useAuth();
  const allowed = !loading && isAdmin(user);

  useEffect(() => {
    document.documentElement.dataset.askAgiAccess = allowed ? 'admin' : 'hidden';
    return () => {
      delete document.documentElement.dataset.askAgiAccess;
    };
  }, [allowed]);

  return null;
}

export function AdminOnly({ children, fallback = null }) {
  const { user, loading } = useAuth();
  if (loading || !isAdmin(user)) return fallback;
  return children;
}

export default function RequireAskAgiAdmin({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!isAdmin(user)) return <Navigate to="/" replace />;
  return children;
}
