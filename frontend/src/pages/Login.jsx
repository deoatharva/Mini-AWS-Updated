import { Cloud } from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';
import { getErrorMessage } from '../services/api.js';
import { getReturnPath } from '../utils/navigation.js';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const destination = getReturnPath(location);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      await login({ email, password });
      navigate(destination, { replace: true });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <Cloud size={20} aria-hidden="true" />
          <span>Mini AWS</span>
        </div>
        <h1>Sign in</h1>
        <p>Use your local Mini AWS account. This is not an AWS account.</p>

        {error && (
          <div className="form-alert" role="alert">
            <strong>Sign-in failed</strong>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              name="email"
              type="email"
              autoComplete="email"
              autoFocus
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              disabled={submitting}
            />
          </div>

          <div className="form-field">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Your password"
              disabled={submitting}
            />
          </div>

          <button
            className="primary-button full-width auth-submit"
            type="submit"
            disabled={submitting}
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="auth-foot">
          New to Mini AWS? <Link to="/register">Create a local account</Link>
        </p>
        <p className="auth-note">
          Accounts and resources stay on this computer. No AWS credentials or
          cloud charges are involved.
        </p>
      </div>
    </div>
  );
}
