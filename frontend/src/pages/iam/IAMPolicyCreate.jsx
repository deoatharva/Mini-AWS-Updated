import { ArrowLeft, KeyRound, Plus, ShieldCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { api, getErrorMessage } from '../../services/api.js';
import { PolicyActionPicker } from './PolicyActionPicker.jsx';

export default function IAMPolicyCreate() {
  const navigate = useNavigate();
  const [actions, setActions] = useState([]);
  const [actionsLoading, setActionsLoading] = useState(true);
  const [actionsError, setActionsError] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedActions, setSelectedActions] = useState([]);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.iam
      .actions()
      .then(setActions)
      .catch((requestError) => setActionsError(getErrorMessage(requestError)))
      .finally(() => setActionsLoading(false));
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    if (name.trim().length < 3) {
      setError('Use at least 3 characters for the policy name.');
      return;
    }
    if (!description.trim()) {
      setError('A description is required.');
      return;
    }
    if (selectedActions.length === 0) {
      setError('Select at least one allowed action.');
      return;
    }

    setSubmitting(true);
    try {
      const policy = await api.iam.policies.create({
        name: name.trim(),
        description: description.trim(),
        actions: selectedActions,
      });
      navigate(`/iam/policies/${policy.id}`, {
        replace: true,
        state: { created: true },
      });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">IDENTITY &amp; ACCESS</div>
          <h1>Create custom policy</h1>
          <p>Build an explicit list of allowed actions for this local account.</p>
        </div>
        <Link className="secondary-button" to="/iam/policies">
          <ArrowLeft size={15} aria-hidden="true" /> Back to policies
        </Link>
      </div>

      <div className="notice">
        <strong>Only selected actions are allowed</strong>
        <span>
          Policies never grant wildcard or owner-level access implicitly. Unknown
          actions are rejected by the API and there are no explicit Deny statements
          in this lab implementation.
        </span>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Could not create the policy</strong>
          <span>{error}</span>
        </div>
      )}
      {actionsError && (
        <div className="form-alert" role="alert">
          <strong>Could not load the action registry</strong>
          <span>{actionsError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="section-panel">
          <div className="panel-heading">
            <div>
              <h2>Policy identity</h2>
              <p className="muted">The name must be unique within this account.</p>
            </div>
            <KeyRound size={20} aria-hidden="true" />
          </div>
          <div className="iam-form-two-column">
            <div className="form-field">
              <label htmlFor="new-policy-name">Policy name</label>
              <input
                id="new-policy-name"
                type="text"
                autoFocus
                required
                minLength={3}
                maxLength={80}
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="StudentStorageOperator"
                disabled={submitting}
              />
            </div>
            <div className="form-field">
              <label htmlFor="new-policy-description">Description</label>
              <input
                id="new-policy-description"
                type="text"
                required
                maxLength={400}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Allows bucket and object operations for labs."
                disabled={submitting}
              />
            </div>
          </div>
        </div>

        <div className="section-panel policy-editor-panel">
          <div className="panel-heading">
            <div>
              <h2>Allowed actions</h2>
              <p className="muted">
                Select exact protected API actions. Each one is enforced server-side.
              </p>
            </div>
            <ShieldCheck size={20} aria-hidden="true" />
          </div>

          {actionsLoading ? (
            <div className="empty-state compact-empty" role="status">
              <p>Loading action registry…</p>
              <span>Reading the backend&apos;s protected action catalog.</span>
            </div>
          ) : (
            <PolicyActionPicker
              actions={actions}
              selectedActions={selectedActions}
              onChange={setSelectedActions}
              disabled={submitting}
            />
          )}
        </div>

        <div className="iam-form-footer">
          <p className="form-hint">
            Selected {selectedActions.length} of {actions.length} available actions.
          </p>
          <div className="heading-actions">
            <Link className="secondary-button" to="/iam/policies">Cancel</Link>
            <button
              className="primary-button"
              type="submit"
              disabled={submitting || actionsLoading}
            >
              <Plus size={15} aria-hidden="true" />
              {submitting ? 'Creating policy…' : 'Create policy'}
            </button>
          </div>
        </div>
      </form>
    </>
  );
}
