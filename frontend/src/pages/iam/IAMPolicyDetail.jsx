import {
  AlertTriangle,
  ArrowLeft,
  KeyRound,
  Lock,
  Pencil,
  RefreshCw,
  Save,
  ShieldCheck,
  Trash2,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';

import { useAuth } from '../../auth/AuthContext.jsx';
import { Modal } from '../../components/Modal.jsx';
import { api, getErrorMessage } from '../../services/api.js';
import { formatDateTime } from '../../utils/format.js';
import { categoryLabel, groupActions } from '../../utils/iam.js';
import { PolicyActionPicker } from './PolicyActionPicker.jsx';

export default function IAMPolicyDetail() {
  const { policyId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const [policy, setPolicy] = useState(null);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(
    location.state?.created ? 'Policy created.' : '',
  );
  const [actionsError, setActionsError] = useState('');
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedActions, setSelectedActions] = useState([]);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.iam.policies.get(policyId);
      setPolicy(data);
      setName(data.name);
      setDescription(data.description);
      setSelectedActions(data.actions);
      setError('');
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [policyId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    api.iam
      .actions()
      .then(setActions)
      .catch((requestError) => setActionsError(getErrorMessage(requestError)));
  }, []);

  const groupedActions = useMemo(
    () => (policy ? groupActions(policy.actions) : []),
    [policy],
  );
  const canUpdate = Boolean(
    policy && !policy.is_managed && hasPermission('iam:UpdatePolicy') && !actionsError,
  );
  const canDelete = Boolean(
    policy && !policy.is_managed && hasPermission('iam:DeletePolicy'),
  );

  function beginEdit() {
    setName(policy.name);
    setDescription(policy.description);
    setSelectedActions(policy.actions);
    setFormError('');
    setEditing(true);
  }

  function cancelEdit() {
    setName(policy.name);
    setDescription(policy.description);
    setSelectedActions(policy.actions);
    setFormError('');
    setEditing(false);
  }

  async function handleSave(event) {
    event.preventDefault();
    setFormError('');
    if (name.trim().length < 3) {
      setFormError('Use at least 3 characters for the policy name.');
      return;
    }
    if (!description.trim()) {
      setFormError('A description is required.');
      return;
    }
    if (selectedActions.length === 0) {
      setFormError('Select at least one allowed action.');
      return;
    }

    setSaving(true);
    try {
      const updated = await api.iam.policies.update(policy.id, {
        name: name.trim(),
        description: description.trim(),
        actions: selectedActions,
      });
      setPolicy(updated);
      setName(updated.name);
      setDescription(updated.description);
      setSelectedActions(updated.actions);
      setEditing(false);
      setNotice('Custom policy updated. The new version applies immediately.');
    } catch (requestError) {
      setFormError(getErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await api.iam.policies.remove(policy.id);
      navigate('/iam/policies', { replace: true });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      setDeleteOpen(false);
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="section-panel empty-state" role="status">
        <p>Loading IAM policy…</p>
        <span>Reading allowed actions and group attachments.</span>
      </div>
    );
  }

  if (!policy) {
    return (
      <>
        <div className="page-heading">
          <div>
            <div className="eyebrow">IDENTITY &amp; ACCESS</div>
            <h1>Policy not found</h1>
            <p>The policy may have been deleted or belong to another account.</p>
          </div>
        </div>
        {error && (
          <div className="form-alert" role="alert">
            <strong>Could not open policy</strong>
            <span>{error}</span>
          </div>
        )}
        <Link className="secondary-button" to="/iam/policies">
          <ArrowLeft size={15} /> Back to policies
        </Link>
      </>
    );
  }

  return (
    <>
      <div className="page-heading iam-detail-heading">
        <div>
          <div className="eyebrow">IDENTITY &amp; ACCESS</div>
          <div className="iam-title-row">
            <h1>{policy.name}</h1>
            <span className={`policy-type ${policy.is_managed ? 'managed' : 'custom'}`}>
              {policy.is_managed ? 'Built-in' : 'Custom'}
            </span>
          </div>
          <p>{policy.description}</p>
        </div>
        <div className="heading-actions">
          <button className="secondary-button" type="button" onClick={load}>
            <RefreshCw size={15} aria-hidden="true" /> Refresh
          </button>
          {canUpdate && !editing && (
            <button className="secondary-button" type="button" onClick={beginEdit}>
              <Pencil size={15} aria-hidden="true" /> Edit policy
            </button>
          )}
          {canDelete && !editing && (
            <button
              className="danger-button"
              type="button"
              onClick={() => setDeleteOpen(true)}
              disabled={policy.group_count > 0}
              title={
                policy.group_count > 0
                  ? 'Detach this policy from all groups before deleting it.'
                  : undefined
              }
            >
              <Trash2 size={15} aria-hidden="true" /> Delete
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Action failed</strong>
          <span>{error}</span>
        </div>
      )}
      {notice && <div className="success-notice" role="status">{notice}</div>}
      {policy.is_managed && (
        <div className="notice">
          <strong>Built-in policy is immutable</strong>
          <span>
            This policy is versioned from the backend action registry. To create a
            different permission set, add a custom policy instead.
          </span>
        </div>
      )}
      {!policy.is_managed && policy.group_count > 0 && (
        <div className="notice">
          <strong>This policy is attached to {policy.group_count} group(s)</strong>
          <span>
            Editing changes effective access immediately. Detach it from every group
            before deleting it.
          </span>
        </div>
      )}
      {actionsError && !editing && (
        <div className="form-alert" role="alert">
          <strong>Action registry unavailable</strong>
          <span>
            {actionsError} Policy details remain readable, but editing is disabled.
          </span>
        </div>
      )}

      <div className="iam-summary-strip">
        <div>
          <span>Policy ID</span>
          <strong>{policy.id}</strong>
        </div>
        <div>
          <span>Allowed actions</span>
          <strong>{policy.actions.length}</strong>
        </div>
        <div>
          <span>Attached groups</span>
          <strong>{policy.group_count}</strong>
        </div>
        <div>
          <span>Version</span>
          <strong>v{policy.version}</strong>
        </div>
      </div>

      {editing ? (
        <form onSubmit={handleSave}>
          {formError && (
            <div className="form-alert" role="alert">
              <strong>Could not update policy</strong>
              <span>{formError}</span>
            </div>
          )}
          <div className="section-panel">
            <div className="panel-heading">
              <div>
                <h2>Policy identity</h2>
                <p className="muted">Saving increments the policy version.</p>
              </div>
              <KeyRound size={20} aria-hidden="true" />
            </div>
            <div className="iam-form-two-column">
              <div className="form-field">
                <label htmlFor="edit-policy-name">Policy name</label>
                <input
                  id="edit-policy-name"
                  type="text"
                  required
                  minLength={3}
                  maxLength={80}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  disabled={saving}
                />
              </div>
              <div className="form-field">
                <label htmlFor="edit-policy-description">Description</label>
                <input
                  id="edit-policy-description"
                  type="text"
                  required
                  maxLength={400}
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  disabled={saving}
                />
              </div>
            </div>
          </div>

          <div className="section-panel policy-editor-panel">
            <div className="panel-heading">
              <div>
                <h2>Allowed actions</h2>
                <p className="muted">
                  Changes apply immediately to every user in attached groups.
                </p>
              </div>
              <ShieldCheck size={20} aria-hidden="true" />
            </div>
            <PolicyActionPicker
              actions={actions}
              selectedActions={selectedActions}
              onChange={setSelectedActions}
              disabled={saving}
            />
          </div>

          <div className="iam-form-footer">
            <p className="form-hint">
              {selectedActions.length} of {actions.length} actions selected.
            </p>
            <div className="heading-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={cancelEdit}
                disabled={saving}
              >
                <X size={15} /> Cancel
              </button>
              <button className="primary-button" type="submit" disabled={saving}>
                <Save size={15} />
                {saving ? 'Saving…' : 'Save policy'}
              </button>
            </div>
          </div>
        </form>
      ) : (
        <div className="iam-detail-grid">
          <section className="section-panel">
            <div className="panel-heading">
              <div>
                <h2>Allowed actions ({policy.actions.length})</h2>
                <p className="muted">Exact API actions granted by this policy.</p>
              </div>
              <ShieldCheck size={20} aria-hidden="true" />
            </div>
            <div className="policy-readonly-groups">
              {groupedActions.map(([category, items]) => (
                <div key={category} className="policy-action-group">
                  <div className="policy-action-group-heading">
                    <div>
                      <h3>{categoryLabel(category)}</h3>
                      <span>{items.length} allowed action(s)</span>
                    </div>
                  </div>
                  <div className="policy-action-list readonly">
                    {items.map((action) => (
                      <div key={action} className="policy-action-row readonly-row">
                        <Lock size={13} aria-hidden="true" />
                        <span>
                          <code>{action}</code>
                          <small>
                            {policy.action_descriptions[action] || 'Protected API action'}
                          </small>
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="iam-side-stack">
            <section className="section-panel">
              <div className="panel-heading">
                <div>
                  <h2>Policy summary</h2>
                  <p className="muted">Version and lifecycle metadata.</p>
                </div>
                <KeyRound size={19} aria-hidden="true" />
              </div>
              <dl className="detail-list">
                <dt>Policy ID</dt><dd>{policy.id}</dd>
                <dt>Name</dt><dd>{policy.name}</dd>
                <dt>Type</dt>
                <dd>{policy.is_managed ? 'Built-in (immutable)' : 'Account custom'}</dd>
                <dt>Version</dt><dd>v{policy.version}</dd>
                <dt>Created</dt><dd>{formatDateTime(policy.created_at)}</dd>
                <dt>Updated</dt><dd>{formatDateTime(policy.updated_at)}</dd>
                <dt>Attached groups</dt><dd>{policy.group_count}</dd>
              </dl>
            </section>

            {policy.is_managed && (
              <section className="section-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Immutable policy</h2>
                    <p className="muted">Managed by the backend registry.</p>
                  </div>
                  <Lock size={19} aria-hidden="true" />
                </div>
                <p className="iam-muted-block">
                  The API rejects updates and deletion for built-in policies. They are
                  automatically refreshed from the action registry when the server
                  starts.
                </p>
              </section>
            )}
          </div>
        </div>
      )}

      {deleteOpen && (
        <Modal
          title="Delete custom policy"
          onClose={() => !deleting && setDeleteOpen(false)}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setDeleteOpen(false)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                className="danger-button"
                type="button"
                onClick={handleDelete}
                disabled={deleting}
              >
                <Trash2 size={15} /> {deleting ? 'Deleting…' : 'Delete policy'}
              </button>
            </>
          }
        >
          <div className="danger-callout">
            <AlertTriangle size={20} aria-hidden="true" />
            <div>
              <strong>This policy is not attached to any group.</strong>
              <p>
                Deleting <code>{policy.name}</code> permanently removes this custom
                allow-list from the local account.
              </p>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
