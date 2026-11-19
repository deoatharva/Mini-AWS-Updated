import {
  ExternalLink,
  FolderTree,
  Plus,
  RefreshCw,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../../auth/AuthContext.jsx';
import { api, getErrorMessage } from '../../services/api.js';
import { formatDateTime } from '../../utils/format.js';

export default function IAMGroups() {
  const { hasPermission } = useAuth();
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setGroups(await api.iam.groups.list());
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

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">IDENTITY &amp; ACCESS</div>
          <h1>IAM groups</h1>
          <p>Assign policies once to a group, then manage its IAM user memberships.</p>
        </div>
        <div className="heading-actions">
          <button className="secondary-button" type="button" onClick={load} disabled={loading}>
            <RefreshCw size={15} aria-hidden="true" /> Refresh
          </button>
          {hasPermission('iam:CreateGroup') && (
            <Link className="primary-button" to="/iam/groups/new">
              <Plus size={15} aria-hidden="true" /> Create group
            </Link>
          )}
        </div>
      </div>

      <div className="notice">
        <strong>Groups are the permission boundary</strong>
        <span>
          A user can belong to multiple groups. Effective permissions are the union
          of all Allow actions in attached policies; removing a policy immediately
          affects every member.
        </span>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Could not load IAM groups</strong>
          <span>{error}</span>
        </div>
      )}

      <div className="section-panel">
        <div className="panel-heading">
          <div>
            <h2>Groups ({groups.length})</h2>
            <p className="muted">Each group can contain users from this local account only.</p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state" role="status">
            <p>Loading IAM groups…</p>
            <span>Reading group and policy attachments.</span>
          </div>
        ) : groups.length === 0 ? (
          <div className="empty-state">
            <FolderTree size={27} aria-hidden="true" />
            <p>No IAM groups yet</p>
            <span>Create a group, attach policies, then add existing IAM users.</span>
            {hasPermission('iam:CreateGroup') && (
              <Link className="secondary-button" to="/iam/groups/new">
                <Plus size={14} aria-hidden="true" /> Create the first group
              </Link>
            )}
          </div>
        ) : (
          <div className="table-wrap">
            <table className="resource-table iam-table">
              <thead>
                <tr>
                  <th>Group</th>
                  <th>Members</th>
                  <th>Policies</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {groups.map((group) => (
                  <tr key={group.id}>
                    <td>
                      <div className="table-name">{group.name}</div>
                      <div className="table-subtext">
                        {group.description || 'No description'} · ID {group.id}
                      </div>
                    </td>
                    <td>
                      <span className="iam-count-label">
                        <Users size={13} aria-hidden="true" /> {group.user_count}
                      </span>
                    </td>
                    <td>
                      <span className="iam-count-label">
                        <ShieldCheck size={13} aria-hidden="true" /> {group.policy_count}
                      </span>
                    </td>
                    <td className="nowrap">{formatDateTime(group.created_at)}</td>
                    <td>
                      <Link className="table-action" to={`/iam/groups/${group.id}`}>
                        View <ExternalLink size={12} aria-hidden="true" />
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
