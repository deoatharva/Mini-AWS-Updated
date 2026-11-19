import {
  ExternalLink,
  KeyRound,
  Lock,
  Plus,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../../auth/AuthContext.jsx';
import { api, getErrorMessage } from '../../services/api.js';
import { formatDateTime } from '../../utils/format.js';

export default function IAMPolicies() {
  const { hasPermission } = useAuth();
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setPolicies(await api.iam.policies.list());
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

  const builtinCount = policies.filter((policy) => policy.is_managed).length;
  const customCount = policies.length - builtinCount;

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">IDENTITY &amp; ACCESS</div>
          <h1>IAM policies</h1>
          <p>Explicit allow-lists of protected API actions, attached through groups.</p>
        </div>
        <div className="heading-actions">
          <button className="secondary-button" type="button" onClick={load} disabled={loading}>
            <RefreshCw size={15} aria-hidden="true" /> Refresh
          </button>
          {hasPermission('iam:CreatePolicy') && (
            <Link className="primary-button" to="/iam/policies/new">
              <Plus size={15} aria-hidden="true" /> Create policy
            </Link>
          )}
        </div>
      </div>

      <div className="notice">
        <strong>Built-in policies cannot be modified</strong>
        <span>
          Seven lab policies are versioned from the backend action registry. Custom
          policies belong only to this local account and can be edited or deleted
          when they are not attached to a group.
        </span>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Could not load policies</strong>
          <span>{error}</span>
        </div>
      )}

      <div className="iam-policy-summary">
        <span><ShieldCheck size={15} /> {builtinCount} built-in</span>
        <span><KeyRound size={15} /> {customCount} custom</span>
        <span><Lock size={15} /> Deny by default</span>
      </div>

      <div className="section-panel">
        <div className="panel-heading">
          <div>
            <h2>Policies ({policies.length})</h2>
            <p className="muted">Sorted with built-ins first by the API.</p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state" role="status">
            <p>Loading IAM policies…</p>
            <span>Reading the central action allow-lists.</span>
          </div>
        ) : policies.length === 0 ? (
          <div className="empty-state">
            <ShieldCheck size={27} aria-hidden="true" />
            <p>No policies available</p>
            <span>Built-in policies are seeded when the backend starts.</span>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="resource-table iam-table">
              <thead>
                <tr>
                  <th>Policy</th>
                  <th>Type</th>
                  <th>Allowed actions</th>
                  <th>Attached groups</th>
                  <th>Version</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {policies.map((policy) => (
                  <tr key={policy.id}>
                    <td>
                      <div className="table-name">{policy.name}</div>
                      <div className="table-subtext">{policy.description}</div>
                    </td>
                    <td>
                      <span className={`policy-type ${policy.is_managed ? 'managed' : 'custom'}`}>
                        {policy.is_managed ? 'Built-in' : 'Custom'}
                      </span>
                    </td>
                    <td>{policy.actions.length}</td>
                    <td>{policy.group_count}</td>
                    <td>v{policy.version}</td>
                    <td className="nowrap">{formatDateTime(policy.updated_at)}</td>
                    <td>
                      <Link className="table-action" to={`/iam/policies/${policy.id}`}>
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
