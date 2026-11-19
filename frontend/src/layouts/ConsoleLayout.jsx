import {
  Cloud,
  Database,
  FolderTree,
  Globe,
  HardDrive,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Monitor,
  ScrollText,
  ShieldCheck,
  UserRound,
  Users,
} from 'lucide-react';
import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';

const serviceLinks = [
  { to: '/', label: 'Console Home', icon: LayoutDashboard, end: true, action: 'dashboard:Read' },
  { to: '/compute/instances', label: 'Compute Instances', icon: Monitor, action: 'compute:ListInstances' },
  { to: '/applications', label: 'App Deployment', icon: Globe, action: 'applications:ListDeployments' },
  { to: '/storage/buckets', label: 'Object Storage', icon: HardDrive, action: 'storage:ListBuckets' },
  { to: '/databases', label: 'Databases', icon: Database, action: 'database:ListDatabases' },
];

const iamLinks = [
  { to: '/iam', label: 'IAM Overview', icon: ShieldCheck, end: true, action: 'iam:ReadOverview' },
  { to: '/iam/users', label: 'IAM Users', icon: Users, action: 'iam:ListUsers' },
  { to: '/iam/groups', label: 'IAM Groups', icon: FolderTree, action: 'iam:ListGroups' },
  { to: '/iam/policies', label: 'IAM Policies', icon: KeyRound, action: 'iam:ListPolicies' },
  { to: '/iam/audit', label: 'Audit Log', icon: ScrollText, action: 'iam:ListAuditLogs' },
];

function SidebarLink({ to, label, icon: Icon, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
    >
      <Icon size={17} aria-hidden="true" />
      <span>{label}</span>
    </NavLink>
  );
}

export function ConsoleLayout() {
  const { user, hasPermission, logout } = useAuth();
  const navigate = useNavigate();
  const [signingOut, setSigningOut] = useState(false);

  const visibleServices = serviceLinks.filter((link) =>
    hasPermission(link.action),
  );
  const visibleIam = iamLinks.filter((link) => hasPermission(link.action));

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
          <span className="topbar-user topbar-identity">
            <span>
              Signed in as <strong>{user?.display_name || user?.name}</strong>
            </span>
            <small>
              {user?.account?.account_id
                ? `Account ${user.account.account_id}`
                : 'Local account'}{' '}
              · {user?.user_type === 'IAM' ? 'IAM user' : 'Owner'}
            </small>
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
          {visibleServices.length > 0 && (
            <>
              <div className="nav-heading">SERVICES</div>
              {visibleServices.map((link) => (
                <SidebarLink key={link.to} {...link} />
              ))}
            </>
          )}
          {visibleIam.length > 0 && (
            <>
              <div className="nav-heading nav-heading-secondary">
                IDENTITY &amp; ACCESS
              </div>
              {visibleIam.map((link) => (
                <SidebarLink key={link.to} {...link} />
              ))}
            </>
          )}
          <div className="nav-heading nav-heading-secondary">ACCOUNT</div>
          <SidebarLink
            to="/account"
            label="Account Settings"
            icon={UserRound}
          />
          <div className="sidebar-note">
            Educational local cloud environment
            {user?.user_type === 'IAM' ? (
              <span className="sidebar-identity-note">
                Permissions: {user.permissions?.length || 0} allowed actions
              </span>
            ) : null}
          </div>
        </aside>
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
