import { Cloud } from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';
import { getErrorMessage } from '../services/api.js';
import { getReturnPath } from '../utils/navigation.js';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const destination = getReturnPath(location);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');

    if (password.length < 12) {
      setError('Password must be at least 12 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      await register({
        name: name.trim(),
        email: email.trim(),
        password,
      });
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
        <h1>Create local account</h1>
        <p>
          This creates an account in this local lab, not an AWS account. Your
          password is stored only as a bcrypt hash.
        </p>

        {error && (
          <div className="form-alert" role="alert">
            <strong>Could not create the account</strong>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="register-name">Name</label>
            <input
              id="register-name"
              name="name"
              type="text"
              autoComplete="name"
              autoFocus
              required
              maxLength={120}
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Your name"
              disabled={submitting}
            />
          </div>

          <div className="form-field">
            <label htmlFor="register-email">Email</label>
            <input
              id="register-email"
              name="email"
              type="email"
              autoComplete="email"
              required
              maxLength={255}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              disabled={submitting}
            />
          </div>

          <div className="form-field">
            <label htmlFor="register-password">Password</label>
            <input
              id="register-password"
              name="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={200}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="At least 12 characters"
              disabled={submitting}
            />
            <p className="form-hint">Use at least 12 characters.</p>
          </div>

          <div className="form-field">
            <label htmlFor="register-confirm-password">Confirm password</label>
            <input
              id="register-confirm-password"
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={200}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Repeat the password"
              disabled={submitting}
            />
          </div>

          <button
            className="primary-button full-width auth-submit"
            type="submit"
            disabled={submitting}
          >
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="auth-foot">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
        <p className="auth-note">
          This account exists only in the local metadata database on this
          computer.
        </p>
      </div>
    </div>
  );
}
