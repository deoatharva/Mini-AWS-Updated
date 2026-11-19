import {
  ArrowLeft,
  Check,
  Copy,
  Eye,
  EyeOff,
  KeyRound,
  ShieldCheck,
  UserPlus,
  Wand2,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../../auth/AuthContext.jsx';
import { api, getErrorMessage } from '../../services/api.js';
import { copyText } from '../../utils/clipboard.js';

const USERNAME_PATTERN = /^[a-z][a-z0-9_-]{2,31}$/;

function generateTemporaryPassword() {
  const alphabet =
    'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%+-_';
  const bytes = new Uint8Array(18);
  globalThis.crypto.getRandomValues(bytes);
  const body = [...bytes].map((value) => alphabet[value % alphabet.length]).join('');
  return `Tmp!${body}9a`;
}

export default function IAMUserCreate() {
  const { user, hasPermission } = useAuth();
  const navigate = useNavigate();
  const [groups, setGroups] = useState([]);
  const [groupsError, setGroupsError] = useState('');
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [consoleAccess, setConsoleAccess] = useState(true);
  const [mustChange, setMustChange] = useState(true);
  const [selectedGroups, setSelectedGroups] = useState([]);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState(null);
  const [createdPassword, setCreatedPassword] = useState('');
  const [copied, setCopied] = useState('');

  useEffect(() => {
    if (!hasPermission('iam:ListGroups')) {
      return;
    }
    api.iam.groups
      .list()
      .then(setGroups)
      .catch((requestError) => setGroupsError(getErrorMessage(requestError)));
  }, [hasPermission]);

  function toggleGroup(groupId) {
    setSelectedGroups((current) =>
      current.includes(groupId)
        ? current.filter((id) => id !== groupId)
        : [...current, groupId],
    );
  }

  function useGeneratedPassword() {
    const generated = generateTemporaryPassword();
    setPassword(generated);
    setConfirmPassword(generated);
    setShowPassword(true);
    setError('');
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    const cleanedUsername = username.trim().toLowerCase();
    if (!USERNAME_PATTERN.test(cleanedUsername)) {
      setError(
        'Username must be 3–32 characters, start with a letter, and use only lowercase letters, numbers, hyphens, or underscores.',
      );
      return;
    }
    if (password.length < 12) {
      setError('The temporary password must be at least 12 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('The temporary passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      const result = await api.iam.users.create({
        username: cleanedUsername,
        display_name: displayName.trim() || null,
        password,
        confirm_password: confirmPassword,
        console_access_enabled: consoleAccess,
        must_change_password: mustChange,
        group_ids: selectedGroups,
      });
      setCreated(result);
      setCreatedPassword(password);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCopy(kind, value) {
    if (await copyText(value)) {
      setCopied(kind);
      window.setTimeout(() => setCopied(''), 1800);
    }
  }

  if (created) {
    return (
      <>
        <div className="page-heading">
          <div>
            <div className="eyebrow">IDENTITY &amp; ACCESS</div>
            <h1>IAM user created</h1>
            <p>Share the temporary credentials through a safe channel.</p>
          </div>
        </div>

        <div className="success-panel">
          <span className="success-panel-icon"><Check size={24} aria-hidden="true" /></span>
          <div>
            <strong>{created.username} is ready to sign in</strong>
            <p>
              This temporary password is shown only on this screen. It is stored in
              the backend only as a bcrypt hash.
            </p>
          </div>
        </div>

        <div className="iam-credential-grid">
          <section className="section-panel">
            <h2>Sign-in details</h2>
            <dl className="detail-list iam-credential-list">
              <dt>Local Account ID</dt>
              <dd>
                <code>{created.account_id}</code>
                <button
                  className="icon-text-button"
                  type="button"
                  onClick={() => handleCopy('account', created.account_id)}
                >
                  {copied === 'account' ? <Check size={13} /> : <Copy size={13} />}
                  {copied === 'account' ? 'Copied' : 'Copy'}
                </button>
              </dd>
              <dt>Username</dt>
              <dd>
                <code>{created.username}</code>
                <button
                  className="icon-text-button"
                  type="button"
                  onClick={() => handleCopy('username', created.username)}
                >
                  {copied === 'username' ? <Check size={13} /> : <Copy size={13} />}
                  {copied === 'username' ? 'Copied' : 'Copy'}
                </button>
              </dd>
              <dt>Temporary password</dt>
              <dd>
                <code>{createdPassword}</code>
                <button
                  className="icon-text-button"
                  type="button"
                  onClick={() => handleCopy('password', createdPassword)}
                >
                  {copied === 'password' ? <Check size={13} /> : <Copy size={13} />}
                  {copied === 'password' ? 'Copied' : 'Copy'}
                </button>
              </dd>
              <dt>Console access</dt>
              <dd>{created.console_access_enabled ? 'Enabled' : 'Disabled'}</dd>
              <dt>First sign-in</dt>
              <dd>
                {created.must_change_password
                  ? 'Password change required'
                  : 'No password change required'}
              </dd>
              <dt>Groups</dt>
              <dd>
                {created.groups.length
                  ? created.groups.map((group) => group.name).join(', ')
                  : 'No groups'}
              </dd>
            </dl>
          </section>

          <section className="section-panel">
            <h2>Next steps</h2>
            <ol className="iam-step-list">
              <li>Share the account ID, username, and temporary password.</li>
              <li>Send the user to the IAM sign-in page on this computer.</li>
              <li>
                {created.must_change_password
                  ? 'They must set a new password before any console page opens.'
                  : 'Their current password remains valid until you reset it.'}
              </li>
              <li>
                {created.groups.length
                  ? 'Review the attached group policies; effective access is shown on the user detail page.'
                  : 'Add the user to a group to grant any console permissions.'}
              </li>
            </ol>
            <div className="iam-step-actions">
              <button
                className="primary-button"
                type="button"
                onClick={() => navigate(`/iam/users/${created.id}`)}
              >
                View user details
              </button>
              <Link className="secondary-button" to="/iam/users">
                Back to users
              </Link>
            </div>
          </section>
        </div>

        <p className="auth-note iam-owner-note">
          Signed in as account owner <strong>{user?.name}</strong>. The temporary
          password cannot be retrieved from the API after leaving this screen.
        </p>
      </>
    );
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">IDENTITY &amp; ACCESS</div>
          <h1>Create IAM user</h1>
          <p>Create a separate console identity inside account {user?.account?.account_id}.</p>
        </div>
        <Link className="secondary-button" to="/iam/users">
          <ArrowLeft size={15} aria-hidden="true" />
          Back to users
        </Link>
      </div>

      <div className="notice">
        <strong>A new identity starts with no permissions by default</strong>
        <span>
          Setting console access only lets the user sign in. Access is granted by
          group policies attached later or selected below.
        </span>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Could not create the IAM user</strong>
          <span>{error}</span>
        </div>
      )}

      <form className="iam-form-layout" onSubmit={handleSubmit}>
        <section className="section-panel">
          <div className="panel-heading">
            <div>
              <h2>Identity details</h2>
              <p className="muted">The username and password are used only with this account ID.</p>
            </div>
            <UserPlus size={20} aria-hidden="true" />
          </div>

          <div className="form-field">
            <label htmlFor="new-iam-username">Username</label>
            <input
              id="new-iam-username"
              type="text"
              autoComplete="off"
              autoFocus
              required
              minLength={3}
              maxLength={32}
              value={username}
              onChange={(event) => setUsername(event.target.value.toLowerCase())}
              placeholder="student1"
              disabled={submitting}
            />
            <p className="form-hint">
              Lowercase letters, numbers, hyphen, or underscore. Must start with a letter.
            </p>
          </div>

          <div className="form-field">
            <label htmlFor="new-iam-display-name">Display name</label>
            <input
              id="new-iam-display-name"
              type="text"
              autoComplete="off"
              maxLength={120}
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Optional, for example Student One"
              disabled={submitting}
            />
          </div>

          <div className="form-field">
            <label htmlFor="new-iam-password">Temporary password</label>
            <div className="password-input-row">
              <input
                id="new-iam-password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                required
                minLength={12}
                maxLength={200}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="At least 12 characters"
                disabled={submitting}
              />
              <button
                className="icon-button password-reveal"
                type="button"
                onClick={() => setShowPassword((current) => !current)}
                aria-label={showPassword ? 'Hide temporary password' : 'Show temporary password'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <button
              className="inline-action"
              type="button"
              onClick={useGeneratedPassword}
              disabled={submitting}
            >
              <Wand2 size={13} aria-hidden="true" />
              Generate a strong temporary password
            </button>
          </div>

          <div className="form-field">
            <label htmlFor="new-iam-confirm-password">Confirm temporary password</label>
            <input
              id="new-iam-confirm-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={200}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Repeat the temporary password"
              disabled={submitting}
            />
          </div>
        </section>

        <div className="iam-form-side">
          <section className="section-panel">
            <div className="panel-heading">
              <div>
                <h2>Access settings</h2>
                <p className="muted">Control how the identity signs in.</p>
              </div>
              <ShieldCheck size={19} aria-hidden="true" />
            </div>

            <label className="check-row" htmlFor="new-iam-console">
              <input
                id="new-iam-console"
                type="checkbox"
                checked={consoleAccess}
                onChange={(event) => setConsoleAccess(event.target.checked)}
                disabled={submitting}
              />
              <span>
                <strong>Console access enabled</strong>
                <small>Allow sign-in when the identity is active.</small>
              </span>
            </label>

            <label className="check-row" htmlFor="new-iam-must-change">
              <input
                id="new-iam-must-change"
                type="checkbox"
                checked={mustChange}
                onChange={(event) => setMustChange(event.target.checked)}
                disabled={submitting}
              />
              <span>
                <strong>Require password change at first sign-in</strong>
                <small>Recommended for temporary passwords.</small>
              </span>
            </label>

            <div className="form-field">
              <label>Initial groups</label>
              {groupsError ? (
                <p className="form-hint error-text">{groupsError}</p>
              ) : groups.length === 0 ? (
                <p className="form-hint">No groups exist yet. You can add the user later.</p>
              ) : (
                <div className="checkbox-list">
                  {groups.map((group) => (
                    <label key={group.id} className="check-row compact-check">
                      <input
                        type="checkbox"
                        checked={selectedGroups.includes(group.id)}
                        onChange={() => toggleGroup(group.id)}
                        disabled={submitting}
                      />
                      <span>
                        <strong>{group.name}</strong>
                        <small>
                          {group.user_count} member(s) · {group.policy_count} policy(ies)
                        </small>
                      </span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </section>

          <div className="iam-form-actions">
            <button className="primary-button" type="submit" disabled={submitting}>
              <KeyRound size={15} aria-hidden="true" />
              {submitting ? 'Creating user…' : 'Create IAM user'}
            </button>
            <Link className="secondary-button" to="/iam/users">
              Cancel
            </Link>
          </div>
        </div>
      </form>
    </>
  );
}
