import {
  Check,
  Copy,
  FolderTree,
  KeyRound,
  LogOut,
  ShieldCheck,
  UserRound,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';
import { api, getErrorMessage } from '../services/api.js';
import { copyText } from '../utils/clipboard.js';
import { categoryLabel, groupActions } from '../utils/iam.js';

function formatDate(value) {
  if (!value) {
    return 'Unknown';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'Unknown';
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

export default function Account() {
  const { user, logout, updateProfile } = useAuth();
  const navigate = useNavigate();
  const [signingOut, setSigningOut] = useState(false);
  const [name, setName] = useState(user?.name || '');
  const [profileError, setProfileError] = useState('');
  const [profileMessage, setProfileMessage] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordMessage, setPasswordMessage] = useState('');
  const [savingPassword, setSavingPassword] = useState(false);
  const [copiedAccountId, setCopiedAccountId] = useState(false);

  useEffect(() => {
    setName(user?.name || '');
  }, [user?.name]);

  async function handleCopyAccountId() {
    const accountId = user?.account?.account_id;
    if (accountId && (await copyText(accountId))) {
      setCopiedAccountId(true);
      window.setTimeout(() => setCopiedAccountId(false), 1800);
    }
  }

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await logout();
      navigate('/login', { replace: true });
    } finally {
      setSigningOut(false);
    }
  }

  async function handleProfileSubmit(event) {
    event.preventDefault();
    setProfileError('');
    setProfileMessage('');
    setSavingProfile(true);

    try {
      const updated = await updateProfile({ name: name.trim() });
      setName(updated.name);
      setProfileMessage('Display name updated.');
    } catch (requestError) {
      setProfileError(getErrorMessage(requestError));
    } finally {
      setSavingProfile(false);
    }
  }

  async function handlePasswordSubmit(event) {
    event.preventDefault();
    setPasswordError('');
    setPasswordMessage('');

    if (newPassword !== confirmPassword) {
      setPasswordError('The new passwords do not match.');
      return;
    }

    setSavingPassword(true);
    try {
      await api.auth.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setPasswordMessage(
        'Password updated. Any other signed-in sessions were signed out.',
      );
    } catch (requestError) {
      setPasswordError(getErrorMessage(requestError));
    } finally {
      setSavingPassword(false);
    }
  }

  const profileUnchanged = name.trim() === (user?.name || '');
  const isIam = user?.user_type === 'IAM';
  const permissionGroups = groupActions(user?.permissions || []);

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">ACCOUNT</div>
          <h1>Account settings</h1>
          <p>
            Review this local account, identity, group memberships, and effective
            permissions.
          </p>
        </div>
        <span className="status-chip">
          {isIam ? 'IAM identity' : 'Local account owner'}
        </span>
      </div>

      <div className="notice">
        <strong>This is not an AWS account</strong>
        <span>
          Mini AWS accounts exist only in this project&apos;s local metadata
          database. No cloud credentials, billing, or remote identity provider
          are involved.
        </span>
      </div>

      <div className="account-grid">
        <section className="section-panel">
          <h2>
            <UserRound size={18} aria-hidden="true" /> Profile
          </h2>
          <dl className="detail-list">
            <dt>Name</dt>
            <dd>{user?.display_name || user?.name || 'Unknown'}</dd>
            <dt>Username</dt>
            <dd><code>{user?.username || 'Unknown'}</code></dd>
            <dt>Email</dt>
            <dd>
              {user?.email || (isIam ? 'Not used for IAM identities' : 'Unknown')}
            </dd>
            <dt>Account ID</dt>
            <dd className="account-id-row">
              <code>
                {user?.account?.account_id || `local-${user?.id ?? 'unknown'}`}
              </code>
              {user?.account?.account_id && (
                <button
                  className="icon-text-button"
                  type="button"
                  onClick={handleCopyAccountId}
                  aria-label="Copy Local Account ID"
                >
                  {copiedAccountId ? <Check size={13} /> : <Copy size={13} />}
                  {copiedAccountId ? 'Copied' : 'Copy'}
                </button>
              )}
            </dd>
            <dt>Account name</dt>
            <dd>{user?.account?.name || 'Local account'}</dd>
            <dt>Identity type</dt>
            <dd>{isIam ? 'IAM user' : 'Account owner'}</dd>
            <dt>Status</dt>
            <dd>{user?.status || 'active'}</dd>
            <dt>Groups</dt>
            <dd>
              {isIam && user?.groups?.length ? (
                <span className="iam-chip-list">
                  {user.groups.map((group) => (
                    <Link key={group.id} to={`/iam/groups/${group.id}`} className="iam-chip">
                      {group.name}
                    </Link>
                  ))}
                </span>
              ) : isIam ? (
                'No groups'
              ) : (
                'Owner has full account access'
              )}
            </dd>
            <dt>Created</dt>
            <dd>{formatDate(user?.created_at)}</dd>
          </dl>
        </section>

        <section className="section-panel">
          <h2>
            <ShieldCheck size={18} aria-hidden="true" /> Session
          </h2>
          <p className="muted">
            Your session uses an opaque token. Only a keyed hash of the token is
            stored by the API, and signing out deletes the local session.
          </p>
          <dl className="detail-list">
            <dt>Sign-in type</dt>
            <dd>{isIam ? 'IAM account ID + username' : 'Owner email'}</dd>
            <dt>Last sign-in</dt>
            <dd>{formatDate(user?.last_login_at)}</dd>
            <dt>Console access</dt>
            <dd>{user?.console_access_enabled === false ? 'Disabled' : 'Enabled'}</dd>
          </dl>
          <div className="account-actions">
            <button
              className="secondary-button"
              type="button"
              onClick={handleSignOut}
              disabled={signingOut}
            >
              <LogOut size={15} aria-hidden="true" />
              {signingOut ? 'Signing out…' : 'Sign out'}
            </button>
          </div>
        </section>
      </div>

      <section className="section-panel account-permissions-panel">
        <div className="panel-heading">
          <div>
            <h2>
              <KeyRound size={18} aria-hidden="true" /> Effective permissions
            </h2>
            <p className="muted">
              Computed by the API from the union of policies attached to your groups.
            </p>
          </div>
          {isIam && (
            <Link className="table-action" to="/iam">
              IAM overview
            </Link>
          )}
        </div>
        {!isIam ? (
          <div className="notice owner-access-notice">
            <strong>Owner access is implicit</strong>
            <span>
              The account owner can access every supported action in this local
              account. IAM users do not inherit this access automatically.
            </span>
          </div>
        ) : permissionGroups.length === 0 ? (
          <div className="empty-state compact-empty">
            <FolderTree size={24} aria-hidden="true" />
            <p>No permissions granted</p>
            <span>Ask the account owner to add you to a group with attached policies.</span>
          </div>
        ) : (
          <div className="permission-groups">
            {permissionGroups.map(([category, actions]) => (
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

      <div className="account-grid account-forms">
        <section className="section-panel">
          <h2>
            <UserRound size={18} aria-hidden="true" /> Display name
          </h2>
          <p className="muted">This name appears in the console header.</p>

          {profileError && (
            <div className="form-alert" role="alert">
              <strong>Name not updated</strong>
              <span>{profileError}</span>
            </div>
          )}
          {profileMessage && (
            <div className="success-notice" role="status">
              {profileMessage}
            </div>
          )}

          <form onSubmit={handleProfileSubmit}>
            <div className="form-field">
              <label htmlFor="account-name">Name</label>
              <input
                id="account-name"
                name="name"
                type="text"
                autoComplete="name"
                required
                maxLength={120}
                value={name}
                onChange={(event) => setName(event.target.value)}
                disabled={savingProfile}
              />
            </div>
            <button
              className="primary-button"
              type="submit"
              disabled={savingProfile || profileUnchanged || !name.trim()}
            >
              {savingProfile ? 'Saving…' : 'Save name'}
            </button>
          </form>
        </section>

        <section className="section-panel">
          <h2>
            <KeyRound size={18} aria-hidden="true" /> Password
          </h2>
          <p className="muted">
            Changing your password signs out your other sessions. This session
            stays signed in.
          </p>

          {passwordError && (
            <div className="form-alert" role="alert">
              <strong>Password not updated</strong>
              <span>{passwordError}</span>
            </div>
          )}
          {passwordMessage && (
            <div className="success-notice" role="status">
              {passwordMessage}
            </div>
          )}

          <form onSubmit={handlePasswordSubmit}>
            <div className="form-field">
              <label htmlFor="current-password">Current password</label>
              <input
                id="current-password"
                name="current-password"
                type="password"
                autoComplete="current-password"
                required
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                disabled={savingPassword}
              />
            </div>
            <div className="form-field">
              <label htmlFor="new-password">New password</label>
              <input
                id="new-password"
                name="new-password"
                type="password"
                autoComplete="new-password"
                required
                minLength={12}
                maxLength={200}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                disabled={savingPassword}
              />
              <p className="form-hint">At least 12 characters.</p>
            </div>
            <div className="form-field">
              <label htmlFor="confirm-password">Confirm new password</label>
              <input
                id="confirm-password"
                name="confirm-password"
                type="password"
                autoComplete="new-password"
                required
                minLength={12}
                maxLength={200}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                disabled={savingPassword}
              />
            </div>
            <button
              className="primary-button"
              type="submit"
              disabled={savingPassword}
            >
              {savingPassword ? 'Updating…' : 'Update password'}
            </button>
          </form>
        </section>
      </div>
    </>
  );
}
