import { Cloud, ShieldOff } from 'lucide-react';
import { Link, Navigate, Outlet, useLocation } from 'react-router-dom';

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
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <SessionLoading />;
  }

  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (
    user?.must_change_password &&
    location.pathname !== '/account/change-password'
  ) {
    return <Navigate to="/account/change-password" replace />;
  }

  return <Outlet />;
}

export function PublicOnlyRoute() {
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <SessionLoading />;
  }

  if (status === 'authenticated') {
    return (
      <Navigate
        to={
          user?.must_change_password
            ? '/account/change-password'
            : getReturnPath(location)
        }
        replace
      />
    );
  }

  return <Outlet />;
}

export function RequirePermission({ action, children }) {
  const { hasPermission } = useAuth();

  if (!hasPermission(action)) {
    return (
      <div className="section-panel access-denied-panel">
        <ShieldOff size={30} aria-hidden="true" />
        <h1>Access denied</h1>
        <p>
          Your IAM permissions do not allow <code>{action}</code>.
        </p>
        <Link to="/">Return to Console Home</Link>
      </div>
    );
  }

  return children;
}
