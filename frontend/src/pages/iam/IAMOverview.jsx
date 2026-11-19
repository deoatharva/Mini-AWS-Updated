import {
  CheckCircle2,
  ChevronRight,
  FolderPlus,
  FolderTree,
  KeyRound,
  ScrollText,
  ShieldCheck,
  UserCheck,
  UserPlus,
  Users,
  XCircle,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../../auth/AuthContext.jsx';
import { api, getErrorMessage } from '../../services/api.js';
import { formatDateTime } from '../../utils/format.js';
import { eventLabel } from '../../utils/iam.js';

function ActivityIcon({ success }) {
  return success ? (
    <CheckCircle2 size={16} aria-hidden="true" />
  ) : (
    <XCircle size={16} aria-hidden="true" />
  );
}

export default function IAMOverview() {
  const { user, hasPermission } = useAuth();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setSummary(await api.iam.overview());
      setError('');
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const quickLinks = [
    {
      to: '/iam/users/new',
      action: 'iam:CreateUser',
      label: 'Create IAM user',
      detail: 'Add a console identity with a temporary password.',
      icon: UserPlus,
    },
    {
      to: '/iam/groups/new',
      action: 'iam:CreateGroup',
      label: 'Create IAM group',
      detail: 'Attach policies and grant permissions to a team.',
      icon: FolderPlus,
    },
    {
      to: '/iam/policies',
      action: 'iam:ListPolicies',
      label: 'View policies',
      detail: 'Inspect built-in policies and custom allow-lists.',
      icon: KeyRound,
    },
    {
      to: '/iam/audit',
      action: 'iam:ListAuditLogs',
      label: 'Open audit log',
      detail: 'Review sign-in and identity-management events.',
      icon: ScrollText,
    },
  ].filter((link) => hasPermission(link.action));

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">IDENTITY &amp; ACCESS</div>
          <h1>IAM overview</h1>
          <p>
            Manage identities, groups, and enforced permissions for local account{' '}
            <strong>{user?.account?.account_id || '—'}</strong>.
          </p>
        </div>
        <div className="heading-actions">
          <button className="secondary-button" type="button" onClick={load} disabled={loading}>
            Refresh
          </button>
          {hasPermission('iam:CreateUser') && (
            <Link className="primary-button" to="/iam/users/new">
              Create IAM user
            </Link>
          )}
        </div>
      </div>

      <div className="notice iam-notice">
        <strong>Permissions are enforced by the API</strong>
        <span>
          This is a real allow-list IAM implementation for the local lab. Account
          owners can access everything in their own account; IAM users start with
          no permissions and receive the union of policies attached to their
          groups.
        </span>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Could not load IAM overview</strong>
          <span>{error}</span>
        </div>
      )}

      {loading && !summary ? (
        <div className="section-panel empty-state" role="status">
          <p>Loading IAM overview…</p>
          <span>Reading local account identity data.</span>
        </div>
      ) : (
        summary && (
          <>
            <div className="iam-stat-grid">
              <Link className="iam-stat-card" to="/iam/users">
                <span className="iam-stat-icon"><Users size={19} aria-hidden="true" /></span>
                <strong>{summary.total_users}</strong>
                <span>IAM users</span>
                <small>{summary.active_users} active · {summary.disabled_users} disabled</small>
              </Link>
              <Link className="iam-stat-card" to="/iam/users">
                <span className="iam-stat-icon"><UserCheck size={19} aria-hidden="true" /></span>
                <strong>{summary.active_users}</strong>
                <span>Active identities</span>
                <small>Can sign in when console access is enabled</small>
              </Link>
              <Link className="iam-stat-card" to="/iam/groups">
                <span className="iam-stat-icon"><FolderTree size={19} aria-hidden="true" /></span>
                <strong>{summary.total_groups}</strong>
                <span>IAM groups</span>
                <small>Policy assignment and membership</small>
              </Link>
              <Link className="iam-stat-card" to="/iam/policies">
                <span className="iam-stat-icon"><ShieldCheck size={19} aria-hidden="true" /></span>
                <strong>{summary.total_policies}</strong>
                <span>Available policies</span>
                <small>Built-in plus account custom policies</small>
              </Link>
            </div>

            <div className="iam-overview-grid">
              <section className="section-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Quick actions</h2>
                    <p className="muted">Identity workflows available to your role.</p>
                  </div>
                </div>
                <div className="iam-quick-list">
                  {quickLinks.length === 0 ? (
                    <p className="muted">
                      Your permissions do not include identity-management actions.
                    </p>
                  ) : (
                    quickLinks.map(({ to, label, detail, icon: Icon }) => (
                      <Link key={to} to={to} className="iam-quick-link">
                        <span className="iam-quick-icon"><Icon size={17} aria-hidden="true" /></span>
                        <span>
                          <strong>{label}</strong>
                          <small>{detail}</small>
                        </span>
                        <ChevronRight size={16} aria-hidden="true" />
                      </Link>
                    ))
                  )}
                </div>
              </section>

              <section className="section-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Recent identity activity</h2>
                    <p className="muted">Newest audited events for this local account.</p>
                  </div>
                  {hasPermission('iam:ListAuditLogs') && (
                    <Link className="table-action" to="/iam/audit">
                      View all
                    </Link>
                  )}
                </div>
                {summary.recent_activity.length === 0 ? (
                  <div className="empty-state compact-empty">
                    <ScrollText size={23} aria-hidden="true" />
                    <p>No identity activity yet</p>
                    <span>Create an IAM user or group to start the audit trail.</span>
                  </div>
                ) : (
                  <ul className="activity-list iam-activity-list">
                    {summary.recent_activity.map((entry) => (
                      <li key={entry.id}>
                        <span className={`activity-icon iam-event-icon ${entry.success ? 'success' : 'failed'}`}>
                          <ActivityIcon success={entry.success} />
                        </span>
                        <div className="activity-copy">
                          <p>
                            <strong>{eventLabel(entry.event_type)}</strong>
                            {entry.actor_username ? ` · ${entry.actor_username}` : ' · anonymous'}
                          </p>
                          <span>
                            {formatDateTime(entry.created_at)}
                            {entry.target_type ? ` · ${entry.target_type}` : ''}
                          </span>
                        </div>
                        <span className={`audit-result ${entry.success ? 'success' : 'failed'}`}>
                          {entry.success ? 'Success' : 'Failed'}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          </>
        )
      )}
    </>
  );
}
