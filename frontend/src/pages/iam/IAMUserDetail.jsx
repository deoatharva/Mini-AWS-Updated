import {
  AlertTriangle,
  ArrowLeft,
  Check,
  Copy,
  FolderTree,
  KeyRound,
  Monitor,
  MonitorOff,
  RefreshCw,
  ShieldCheck,
  Trash2,
  UserCheck,
  UserX,
  Wand2,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { useAuth } from '../../auth/AuthContext.jsx';
import { Modal } from '../../components/Modal.jsx';
import { StatusBadge } from '../../components/StatusBadge.jsx';
import { api, getErrorMessage } from '../../services/api.js';
import { copyText } from '../../utils/clipboard.js';
import { formatDateTime } from '../../utils/format.js';
import { categoryLabel, groupActions } from '../../utils/iam.js';

function generateTemporaryPassword() {
  const alphabet =
    'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%+-_';
  const bytes = new Uint8Array(18);
  globalThis.crypto.getRandomValues(bytes);
  return `Tmp!${[...bytes].map((value) => alphabet[value % alphabet.length]).join('')}9a`;
}

export default function IAMUserDetail() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const { user: currentUser, hasPermission } = useAuth();
  const [target, setTarget] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [tab, setTab] = useState('summary');
  const [displayName, setDisplayName] = useState('');
  const [savingName, setSavingName] = useState(false);
  const [busyAction, setBusyAction] = useState('');
  const [modal, setModal] = useState(null);
  const [resetPassword, setResetPassword] = useState('');
  const [resetConfirm, setResetConfirm] = useState('');
  const [resetMustChange, setResetMustChange] = useState(true);
  const [resetError, setResetError] = useState('');
  const [resetting, setResetting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.iam.users.get(userId);
      setTarget(data);
      setDisplayName(data.display_name);
      setError('');
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    load();
  }, [load]);

  const isSelf = Boolean(target && currentUser?.id === target.id);
  const canUpdate = hasPermission('iam:UpdateUser') && !isSelf;
  const canReset = hasPermission('iam:ResetUserPassword') && !isSelf;
  const canDelete = hasPermission('iam:DeleteUser') && !isSelf;

  const permissionSources = useMemo(() => {
    if (!target) {
      return [];
    }
    const sources = new Map();
    for (const entries of Object.values(target.permission_sources || {})) {
      for (const source of entries) {
        const key = `${source.type}:${source.group_id || ''}:${source.policy_id || ''}`;
        if (!sources.has(key)) {
          sources.set(key, { ...source, actionCount: 0 });
        }
        sources.get(key).actionCount += 1;
      }
    }
    return [...sources.values()];
  }, [target]);

  const actionGroups = useMemo(
    () => (target ? groupActions(target.effective_actions) : []),
    [target],
  );

  async function saveDisplayName(event) {
    event.preventDefault();
    if (!target) {
      return;
    }
    setSavingName(true);
    setError('');
    setNotice('');
    try {
      const updated = await api.iam.users.update(target.id, {
        display_name: displayName.trim() || null,
      });
      setTarget(updated);
      setDisplayName(updated.display_name);
      setNotice('Display name updated.');
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSavingName(false);
    }
  }

  async function updateAccess(payload, message) {
    if (!target) {
      return;
    }
    setBusyAction('access');
    setError('');
    setNotice('');
    try {
      const updated = await api.iam.users.update(target.id, payload);
      setTarget(updated);
      setDisplayName(updated.display_name);
      setNotice(message);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyAction('');
    }
  }

  function openReset() {
    setResetPassword('');
    setResetConfirm('');
    setResetMustChange(true);
    setResetError('');
    setModal('reset');
  }

  function fillResetPassword() {
    const generated = generateTemporaryPassword();
    setResetPassword(generated);
    setResetConfirm(generated);
    setResetError('');
  }

  async function handleReset(event) {
    event.preventDefault();
    setResetError('');
    if (resetPassword.length < 12) {
      setResetError('Use at least 12 characters for the temporary password.');
      return;
    }
    if (resetPassword !== resetConfirm) {
      setResetError('The temporary passwords do not match.');
      return;
    }
    setResetting(true);
    try {
      const updated = await api.iam.users.resetPassword(target.id, {
        password: resetPassword,
        confirm_password: resetConfirm,
        must_change_password: resetMustChange,
      });
      setTarget(updated);
      setDisplayName(updated.display_name);
      setModal(null);
      setNotice(
        `Password reset for ${updated.username}. Existing sessions were revoked${
          updated.must_change_password ? '; a change is required at next sign-in' : ''
        }.`,
      );
    } catch (requestError) {
      setResetError(getErrorMessage(requestError));
    } finally {
      setResetting(false);
    }
  }

  async function handleDelete() {
    if (!target) {
      return;
    }
    setDeleting(true);
    setError('');
    try {
      await api.iam.users.remove(target.id);
      navigate('/iam/users', { replace: true });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      setModal(null);
    } finally {
      setDeleting(false);
    }
  }

  async function copyAccountId() {
    if (target && (await copyText(target.account_id))) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    }
  }

  if (loading) {
    return (
      <div className="section-panel empty-state" role="status">
        <p>Loading IAM user…</p>
        <span>Reading groups and effective permissions.</span>
      </div>
    );
  }

  if (!target) {
    return (
      <>
        <div className="page-heading">
          <div>
            <div className="eyebrow">IDENTITY &amp; ACCESS</div>
            <h1>IAM user not found</h1>
            <p>The identity may have been deleted or belong to another account.</p>
          </div>
        </div>
        {error && (
          <div className="form-alert" role="alert">
            <strong>Could not open IAM user</strong>
            <span>{error}</span>
          </div>
        )}
        <Link className="secondary-button" to="/iam/users">
          <ArrowLeft size={15} /> Back to users
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
            <h1>{target.display_name}</h1>
            <StatusBadge status={target.status} />
          </div>
          <p>
            IAM user <code>{target.username}</code> in account {target.account_id}
          </p>
        </div>
        <div className="heading-actions">
          <button className="secondary-button" type="button" onClick={load}>
            <RefreshCw size={15} aria-hidden="true" /> Refresh
          </button>
          {(canUpdate || canReset || canDelete) && (
            <>
              {canReset && (
                <button className="secondary-button" type="button" onClick={openReset}>
                  <KeyRound size={15} aria-hidden="true" /> Reset password
                </button>
              )}
              {canDelete && (
                <button
                  className="danger-button"
                  type="button"
                  onClick={() => setModal('delete')}
                >
                  <Trash2 size={15} aria-hidden="true" /> Delete
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Action failed</strong>
          <span>{error}</span>
        </div>
      )}
      {notice && (
        <div className="success-notice" role="status">{notice}</div>
      )}
      {isSelf && (
        <div className="notice">
          <strong>This is your own IAM identity</strong>
          <span>
            Use Account Settings to change your password. IAM management changes to
            your own identity are blocked by the API.
          </span>
        </div>
      )}

      <div className="iam-summary-strip">
        <div>
          <span>Local Account ID</span>
          <strong><code>{target.account_id}</code></strong>
          <button className="icon-text-button" type="button" onClick={copyAccountId}>
            {copied ? <Check size={13} /> : <Copy size={13} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
        <div>
          <span>Username</span>
          <strong><code>{target.username}</code></strong>
        </div>
        <div>
          <span>Console access</span>
          <strong>{target.console_access_enabled ? 'Enabled' : 'Disabled'}</strong>
        </div>
        <div>
          <span>Last sign-in</span>
          <strong>{target.last_login_at ? formatDateTime(target.last_login_at) : 'Never'}</strong>
        </div>
      </div>

      <div className="iam-tabs" role="tablist" aria-label="IAM user details">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'summary'}
          className={tab === 'summary' ? 'active' : ''}
          onClick={() => setTab('summary')}
        >
          Summary
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'permissions'}
          className={tab === 'permissions' ? 'active' : ''}
          onClick={() => setTab('permissions')}
        >
          Groups &amp; permissions
        </button>
      </div>

      {tab === 'summary' && (
        <div className="iam-detail-grid">
          <section className="section-panel">
            <div className="panel-heading">
              <div>
                <h2>Identity summary</h2>
                <p className="muted">Local account association and status.</p>
              </div>
              <ShieldCheck size={20} aria-hidden="true" />
            </div>
            <dl className="detail-list">
              <dt>User ID</dt><dd>{target.id}</dd>
              <dt>Username</dt><dd><code>{target.username}</code></dd>
              <dt>Display name</dt><dd>{target.display_name}</dd>
              <dt>Account</dt><dd>{target.account_id}</dd>
              <dt>Status</dt><dd><StatusBadge status={target.status} /></dd>
              <dt>Console</dt><dd>{target.console_access_enabled ? 'Enabled' : 'Disabled'}</dd>
              <dt>Password</dt>
              <dd>{target.must_change_password ? 'Change required at next sign-in' : 'Set'}</dd>
              <dt>Created</dt><dd>{formatDateTime(target.created_at)}</dd>
              <dt>Updated</dt><dd>{formatDateTime(target.updated_at)}</dd>
              <dt>Last sign-in</dt>
              <dd>{target.last_login_at ? formatDateTime(target.last_login_at) : 'Never'}</dd>
            </dl>
          </section>

          <div className="iam-side-stack">
            {canUpdate && (
              <section className="section-panel">
                <h2>Access controls</h2>
                <div className="iam-access-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={busyAction === 'access'}
                    onClick={() =>
                      updateAccess(
                        { status: target.status === 'active' ? 'disabled' : 'active' },
                        target.status === 'active'
                          ? 'IAM user deactivated. All active sessions were revoked.'
                          : 'IAM user activated.',
                      )
                    }
                  >
                    {target.status === 'active' ? <UserX size={15} /> : <UserCheck size={15} />}
                    {target.status === 'active' ? 'Deactivate user' : 'Activate user'}
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={busyAction === 'access'}
                    onClick={() =>
                      updateAccess(
                        { console_access_enabled: !target.console_access_enabled },
                        target.console_access_enabled
                          ? 'Console access disabled. Existing sessions were revoked.'
                          : 'Console access enabled.',
                      )
                    }
                  >
                    {target.console_access_enabled ? <MonitorOff size={15} /> : <Monitor size={15} />}
                    {target.console_access_enabled ? 'Disable console access' : 'Enable console access'}
                  </button>
                </div>
                <p className="form-hint">
                  Disabling access immediately invalidates existing bearer sessions.
                </p>
              </section>
            )}

            {canUpdate && (
              <section className="section-panel">
                <h2>Display name</h2>
                <form onSubmit={saveDisplayName}>
                  <div className="form-field">
                    <label htmlFor="iam-display-name">Name shown in the console</label>
                    <input
                      id="iam-display-name"
                      type="text"
                      maxLength={120}
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                      disabled={savingName}
                    />
                  </div>
                  <button className="secondary-button" type="submit" disabled={savingName}>
                    {savingName ? 'Saving…' : 'Save display name'}
                  </button>
                </form>
              </section>
            )}

            <section className="section-panel">
              <div className="panel-heading">
                <div>
                  <h2>Group memberships</h2>
                  <p className="muted">Policies are inherited through these groups.</p>
                </div>
                <FolderTree size={19} aria-hidden="true" />
              </div>
              {target.groups.length === 0 ? (
                <p className="muted iam-muted-block">
                  This user is not in any group and therefore has no IAM permissions.
                </p>
              ) : (
                <div className="iam-chip-list">
                  {target.groups.map((group) => (
                    <Link key={group.id} to={`/iam/groups/${group.id}`} className="iam-chip">
                      {group.name}
                    </Link>
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>
      )}

      {tab === 'permissions' && (
        <div className="iam-detail-grid">
          <section className="section-panel">
            <div className="panel-heading">
              <div>
                <h2>Effective permissions ({target.effective_actions.length})</h2>
                <p className="muted">
                  Union of every Allow action in policies attached to this user&apos;s groups.
                </p>
              </div>
              <KeyRound size={20} aria-hidden="true" />
            </div>
            {actionGroups.length === 0 ? (
              <div className="empty-state compact-empty">
                <ShieldCheck size={24} aria-hidden="true" />
                <p>No permissions granted</p>
                <span>An owner must add this user to a group with an attached policy.</span>
              </div>
            ) : (
              <div className="permission-groups">
                {actionGroups.map(([category, actions]) => (
                  <div key={category} className="permission-group">
                    <h3>{categoryLabel(category)}</h3>
                    <div className="permission-chip-list">
                      {actions.map((action) => (
                        <code key={action} className="permission-chip">{action}</code>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="section-panel">
            <div className="panel-heading">
              <div>
                <h2>Permission sources</h2>
                <p className="muted">Groups and policies contributing allowed actions.</p>
              </div>
            </div>
            {permissionSources.length === 0 ? (
              <p className="muted iam-muted-block">No group policy sources.</p>
            ) : (
              <div className="permission-source-list">
                {permissionSources.map((source) => (
                  <div key={`${source.group_id}-${source.policy_id}`} className="permission-source">
                    <span className="source-icon"><ShieldCheck size={15} /></span>
                    <div>
                      <strong>{source.policy_name || source.policy?.name || 'Policy'}</strong>
                      <span>
                        via{' '}
                        {source.group_id ? (
                          <Link to={`/iam/groups/${source.group_id}`}>{source.group_name}</Link>
                        ) : (
                          source.name
                        )}
                      </span>
                    </div>
                    <span className="source-count">{source.actionCount} actions</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      {modal === 'reset' && (
        <Modal
          title={`Reset password for ${target.username}`}
          onClose={() => !resetting && setModal(null)}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setModal(null)}
                disabled={resetting}
              >
                Cancel
              </button>
              <button
                className="primary-button"
                type="submit"
                form="reset-password-form"
                disabled={resetting}
              >
                <KeyRound size={15} /> {resetting ? 'Resetting…' : 'Reset password'}
              </button>
            </>
          }
        >
          <p className="modal-copy">
            The new temporary password is stored only as a bcrypt hash. Existing
            sessions for this user will be revoked immediately.
          </p>
          {resetError && (
            <div className="form-alert" role="alert">
              <strong>Could not reset the password</strong>
              <span>{resetError}</span>
            </div>
          )}
          <form id="reset-password-form" onSubmit={handleReset}>
            <div className="form-field">
              <label htmlFor="reset-iam-password">Temporary password</label>
              <input
                id="reset-iam-password"
                type="text"
                autoComplete="new-password"
                required
                minLength={12}
                value={resetPassword}
                onChange={(event) => setResetPassword(event.target.value)}
                disabled={resetting}
                placeholder="At least 12 characters"
              />
              <button
                className="inline-action"
                type="button"
                onClick={fillResetPassword}
                disabled={resetting}
              >
                <Wand2 size={13} /> Generate temporary password
              </button>
            </div>
            <div className="form-field">
              <label htmlFor="reset-iam-confirm">Confirm temporary password</label>
              <input
                id="reset-iam-confirm"
                type="text"
                autoComplete="new-password"
                required
                minLength={12}
                value={resetConfirm}
                onChange={(event) => setResetConfirm(event.target.value)}
                disabled={resetting}
              />
            </div>
            <label className="check-row" htmlFor="reset-must-change">
              <input
                id="reset-must-change"
                type="checkbox"
                checked={resetMustChange}
                onChange={(event) => setResetMustChange(event.target.checked)}
                disabled={resetting}
              />
              <span>
                <strong>Require password change at next sign-in</strong>
                <small>Recommended after sharing a temporary password.</small>
              </span>
            </label>
          </form>
        </Modal>
      )}

      {modal === 'delete' && (
        <Modal
          title="Delete IAM user"
          onClose={() => !deleting && setModal(null)}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setModal(null)}
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
                <Trash2 size={15} /> {deleting ? 'Deleting…' : 'Delete IAM user'}
              </button>
            </>
          }
        >
          <div className="danger-callout">
            <AlertTriangle size={20} aria-hidden="true" />
            <div>
              <strong>This action cannot be undone.</strong>
              <p>
                The IAM identity <code>{target.username}</code>, its group
                memberships, and all sessions will be deleted. Account resources
                remain owned by the account owner.
              </p>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
