import {
  ExternalLink,
  KeyRound,
  Plus,
  RefreshCw,
  Search,
  Users,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../../auth/AuthContext.jsx';
import { StatusBadge } from '../../components/StatusBadge.jsx';
import { api, getErrorMessage } from '../../services/api.js';
import { formatDateTime } from '../../utils/format.js';

export default function IAMUsers() {
  const { hasPermission } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setUsers(await api.iam.users.list());
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

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return users;
    }
    return users.filter((user) =>
      [
        user.username,
        user.display_name,
        ...user.groups.map((group) => group.name),
      ]
        .join(' ')
        .toLowerCase()
        .includes(needle),
    );
  }, [query, users]);

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">IDENTITY &amp; ACCESS</div>
          <h1>IAM users</h1>
          <p>Create identities that can sign in with this account ID and a username.</p>
        </div>
        <div className="heading-actions">
          <button className="secondary-button" type="button" onClick={load} disabled={loading}>
            <RefreshCw size={15} aria-hidden="true" />
            Refresh
          </button>
          {hasPermission('iam:CreateUser') && (
            <Link className="primary-button" to="/iam/users/new">
              <Plus size={15} aria-hidden="true" />
              Create user
            </Link>
          )}
        </div>
      </div>

      <div className="notice">
        <strong>IAM users are account-scoped identities</strong>
        <span>
          They can operate on this account&apos;s compute, storage, and database
          resources only when an attached policy allows the exact action. They
          cannot view or change another local account&apos;s resources.
        </span>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Could not load IAM users</strong>
          <span>{error}</span>
        </div>
      )}

      <div className="section-panel">
        <div className="panel-heading iam-panel-heading">
          <div>
            <h2>Users ({users.length})</h2>
            <p className="muted">
              Temporary-password identities must change their password at first sign-in.
            </p>
          </div>
          <label className="search-field" htmlFor="iam-user-search">
            <Search size={14} aria-hidden="true" />
            <input
              id="iam-user-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Filter users or groups"
              aria-label="Filter IAM users"
            />
          </label>
        </div>

        {loading ? (
          <div className="empty-state" role="status">
            <p>Loading IAM users…</p>
            <span>Reading identity records from the local database.</span>
          </div>
        ) : users.length === 0 ? (
          <div className="empty-state">
            <Users size={27} aria-hidden="true" />
            <p>No IAM users yet</p>
            <span>Create a separate identity for a student or collaborator.</span>
            {hasPermission('iam:CreateUser') && (
              <Link className="secondary-button" to="/iam/users/new">
                <Plus size={14} aria-hidden="true" />
                Create the first IAM user
              </Link>
            )}
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty-state compact-empty">
            <Search size={23} aria-hidden="true" />
            <p>No matching users</p>
            <span>Try a different username, display name, or group.</span>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="resource-table iam-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Groups</th>
                  <th>Console access</th>
                  <th>Status</th>
                  <th>Password</th>
                  <th>Created</th>
                  <th>Last sign-in</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <div className="table-name">{user.display_name || user.username}</div>
                      <div className="table-subtext">
                        <code>{user.username}</code> · ID {user.id}
                      </div>
                      <div className="table-subtext">Account {user.account_id}</div>
                    </td>
                    <td>
                      {user.groups.length === 0 ? (
                        <span className="muted">No groups</span>
                      ) : (
                        <div className="iam-chip-list">
                          {user.groups.map((group) => (
                            <Link
                              key={group.id}
                              to={`/iam/groups/${group.id}`}
                              className="iam-chip"
                            >
                              {group.name}
                            </Link>
                          ))}
                        </div>
                      )}
                    </td>
                    <td>{user.console_access_enabled ? 'Enabled' : 'Disabled'}</td>
                    <td><StatusBadge status={user.status} /></td>
                    <td>
                      {user.must_change_password ? (
                        <span className="iam-state-label warning">
                          <KeyRound size={12} aria-hidden="true" />
                          Change required
                        </span>
                      ) : (
                        <span className="muted">Permanent</span>
                      )}
                    </td>
                    <td className="nowrap">{formatDateTime(user.created_at)}</td>
                    <td className="nowrap">
                      {user.last_login_at ? formatDateTime(user.last_login_at) : 'Never'}
                    </td>
                    <td>
                      <Link className="table-action" to={`/iam/users/${user.id}`}>
                        View
                        <ExternalLink size={12} aria-hidden="true" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
