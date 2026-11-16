import { KeyRound, LogOut, ShieldCheck, UserRound } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';
import { api, getErrorMessage } from '../services/api.js';

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

  useEffect(() => {
    setName(user?.name || '');
  }, [user?.name]);

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

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">ACCOUNT</div>
          <h1>Account settings</h1>
          <p>Review and update the local account used for this console session.</p>
        </div>
        <span className="status-chip">Local account</span>
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
            <dd>{user?.name || 'Unknown'}</dd>
            <dt>Email</dt>
            <dd>{user?.email || 'Unknown'}</dd>
            <dt>Account ID</dt>
            <dd>local-{user?.id ?? 'unknown'}</dd>
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
