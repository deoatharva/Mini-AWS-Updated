import {
  Cloud,
  Database,
  Globe,
  HardDrive,
  LayoutDashboard,
  LogOut,
  Monitor,
  UserRound,
} from 'lucide-react';
import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';

const links = [
  { to: '/', label: 'Console Home', icon: LayoutDashboard, end: true },
  { to: '/compute/instances', label: 'Compute Instances', icon: Monitor },
  { to: '/applications', label: 'App Deployment', icon: Globe },
  { to: '/storage/buckets', label: 'Object Storage', icon: HardDrive },
  { to: '/databases', label: 'Databases', icon: Database },
  { to: '/account', label: 'Account Settings', icon: UserRound },
];

export function ConsoleLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await logout();
      navigate('/login', { replace: true });
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <div className="console-shell">
      <header className="topbar">
        <div className="brand">
          <Cloud size={23} aria-hidden="true" />
          <span>Mini AWS</span>
        </div>
        <div className="topbar-label">Cloud Management Console</div>
        <div className="topbar-account">
          <span className="topbar-user">
            Signed in as <strong>{user?.name}</strong>
          </span>
          <button
            className="topbar-signout"
            type="button"
            onClick={handleSignOut}
            disabled={signingOut}
            aria-label="Sign out of Mini AWS"
          >
            <LogOut size={13} aria-hidden="true" />
            {signingOut ? 'Signing out…' : 'Sign out'}
          </button>
        </div>
        <span className="local-pill">LOCAL LAB</span>
      </header>

      <div className="console-body">
        <aside className="sidebar">
          <div className="nav-heading">SERVICES</div>
          {links.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <Icon size={17} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
          <div className="sidebar-note">Educational local cloud environment</div>
        </aside>
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
