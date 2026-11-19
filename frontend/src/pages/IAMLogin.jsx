import { Cloud, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';
import { getErrorMessage } from '../services/api.js';
import { getReturnPath } from '../utils/navigation.js';

export default function IAMLogin() {
  const { loginIam } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [accountId, setAccountId] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const destination = getReturnPath(location);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');

    if (!/^\d{12}$/.test(accountId.trim())) {
      setError('Enter the 12-digit Local Account ID.');
      return;
    }

    setSubmitting(true);
    try {
      const user = await loginIam({
        account_id: accountId.trim(),
        username: username.trim(),
        password,
      });
      navigate(
        user.must_change_password ? '/account/change-password' : destination,
        { replace: true },
      );
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card iam-login-card">
        <div className="auth-brand">
          <Cloud size={20} aria-hidden="true" />
          <span>Mini AWS</span>
        </div>
        <div className="auth-kicker">
          <ShieldCheck size={15} aria-hidden="true" />
          IAM IDENTITY
        </div>
        <h1>IAM user sign in</h1>
        <p>
          Use the 12-digit account ID and username supplied by your local account
          owner.
        </p>

        {error && (
          <div className="form-alert" role="alert">
            <strong>Sign-in failed</strong>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="iam-account-id">Local Account ID</label>
            <input
              id="iam-account-id"
              name="accountId"
              type="text"
              inputMode="numeric"
              autoComplete="off"
              autoFocus
              required
              maxLength={12}
              value={accountId}
              onChange={(event) =>
                setAccountId(event.target.value.replace(/\D/g, '').slice(0, 12))
              }
              placeholder="123456789012"
              disabled={submitting}
              className="account-id-input"
            />
            <p className="form-hint">Exactly 12 digits. This is not an AWS account ID.</p>
          </div>

          <div className="form-field">
            <label htmlFor="iam-username">IAM username</label>
            <input
              id="iam-username"
              name="username"
              type="text"
              autoComplete="username"
              required
              minLength={3}
              maxLength={32}
              value={username}
              onChange={(event) => setUsername(event.target.value.toLowerCase())}
              placeholder="student1"
              disabled={submitting}
            />
          </div>

          <div className="form-field">
            <label htmlFor="iam-password">Password</label>
            <input
              id="iam-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Temporary or current password"
              disabled={submitting}
            />
          </div>

          <button
            className="primary-button full-width auth-submit"
            type="submit"
            disabled={submitting}
          >
            {submitting ? 'Signing in…' : 'Sign in as IAM user'}
          </button>
        </form>

        <p className="auth-foot">
          Account owner? <Link to="/login" state={location.state}>Owner sign in</Link>
        </p>
        <p className="auth-note">
          IAM users have only the permissions granted through their account
          groups. Ask your owner if you need access.
        </p>
      </div>
    </div>
  );
}
