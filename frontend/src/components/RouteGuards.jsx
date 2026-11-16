import { Cloud } from 'lucide-react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';
import { getReturnPath } from '../utils/navigation.js';

function SessionLoading() {
  return (
    <div className="auth-page">
      <div className="auth-card loading-card" role="status" aria-live="polite">
        <div className="auth-brand">
          <Cloud size={20} aria-hidden="true" />
          <span>Mini AWS</span>
        </div>
        <p>Checking your local session…</p>
        <div className="loading-bar" aria-hidden="true" />
      </div>
    </div>
  );
}

export function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <SessionLoading />;
  }

  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export function PublicOnlyRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <SessionLoading />;
  }

  if (status === 'authenticated') {
    return <Navigate to={getReturnPath(location)} replace />;
  }

  return <Outlet />;
}
