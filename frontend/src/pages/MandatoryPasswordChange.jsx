import { Cloud, KeyRound, LogOut, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';
import { getErrorMessage } from '../services/api.js';

export default function MandatoryPasswordChange() {
  const {
    user,
    completeRequiredPasswordChange,
    logout,
  } = useAuth();
  const navigate = useNavigate();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  if (!user?.must_change_password) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    if (newPassword.length < 12) {
      setError('Use at least 12 characters for the new password.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('The new passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      await completeRequiredPasswordChange({
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      navigate('/', { replace: true });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
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

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <Cloud size={20} aria-hidden="true" />
          <span>Mini AWS</span>
        </div>
        <div className="auth-kicker">
          <ShieldCheck size={15} aria-hidden="true" />
          FIRST-LOGIN SECURITY
        </div>
        <h1>Change temporary password</h1>
        <p>
          Your IAM identity <strong>{user.username}</strong> must replace its
          temporary password before the console can be used.
        </p>

        <div className="auth-context">
          <span>Local Account ID</span>
          <strong>{user.account?.account_id || 'Unavailable'}</strong>
        </div>

        {error && (
          <div className="form-alert" role="alert">
            <strong>Could not change the password</strong>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="required-new-password">New password</label>
            <input
              id="required-new-password"
              type="password"
              autoComplete="new-password"
              autoFocus
              required
              minLength={12}
              maxLength={200}
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="At least 12 characters"
              disabled={submitting || signingOut}
            />
          </div>

          <div className="form-field">
            <label htmlFor="required-confirm-password">Confirm new password</label>
            <input
              id="required-confirm-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={200}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Repeat the new password"
              disabled={submitting || signingOut}
            />
            <p className="form-hint">
              The temporary password will stop working immediately after this
              change.
            </p>
          </div>

          <button
            className="primary-button full-width auth-submit"
            type="submit"
            disabled={submitting || signingOut}
          >
            <KeyRound size={15} aria-hidden="true" />
            {submitting ? 'Changing password…' : 'Set new password'}
          </button>
        </form>

        <button
          className="auth-signout"
          type="button"
          onClick={handleSignOut}
          disabled={submitting || signingOut}
        >
          <LogOut size={14} aria-hidden="true" />
          {signingOut ? 'Signing out…' : 'Sign out instead'}
        </button>

        <p className="auth-note">
          Only password change and sign-out are available until this step is
          complete.
        </p>
      </div>
    </div>
  );
}
