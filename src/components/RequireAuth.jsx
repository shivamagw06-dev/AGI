import { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { supabase } from '@/lib/supabaseClient';
import { buildLoginUrl } from '@/lib/accessPolicy';

export default function RequireAuth({ children }) {
  const location = useLocation();
  const [user, setUser] = useState();
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setUser(data.user || null); setLoading(false);
    });
  }, []);
  if (loading) return null;
  if (user) return children;
  const returnTo = `${location.pathname}${location.search || ''}` || '/';
  return <Navigate to={buildLoginUrl({ returnTo, mode: 'signin' })} replace />;
}