import {
  ArrowLeft,
  FolderPlus,
  KeyRound,
  ShieldCheck,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { api, getErrorMessage } from '../../services/api.js';

export default function IAMGroupCreate() {
  const navigate = useNavigate();
  const [policies, setPolicies] = useState([]);
  const [policiesError, setPoliciesError] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedPolicies, setSelectedPolicies] = useState([]);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.iam.policies
      .list()
      .then(setPolicies)
      .catch((requestError) => setPoliciesError(getErrorMessage(requestError)));
  }, []);

  const builtins = useMemo(
    () => policies.filter((policy) => policy.is_managed),
    [policies],
  );
  const custom = useMemo(
    () => policies.filter((policy) => !policy.is_managed),
    [policies],
  );

  function togglePolicy(policyId) {
    setSelectedPolicies((current) =>
      current.includes(policyId)
        ? current.filter((id) => id !== policyId)
        : [...current, policyId],
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    if (name.trim().length < 2) {
      setError('Use at least 2 characters for the group name.');
      return;
    }
    setSubmitting(true);
    try {
      const group = await api.iam.groups.create({
        name: name.trim(),
        description: description.trim() || null,
        policy_ids: selectedPolicies,
      });
      navigate(`/iam/groups/${group.id}`, {
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
          <h1>Create IAM group</h1>
          <p>Attach policies now or add them after the group is created.</p>
        </div>
        <Link className="secondary-button" to="/iam/groups">
          <ArrowLeft size={15} aria-hidden="true" />
          Back to groups
        </Link>
      </div>

      <div className="notice">
        <strong>A group is an allow-list container</strong>
        <span>
          Users inherit the union of actions from every attached policy. A new
          group grants nothing until at least one policy is attached and a user is
          added.
        </span>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Could not create the group</strong>
          <span>{error}</span>
        </div>
      )}

      <form className="iam-form-layout" onSubmit={handleSubmit}>
        <section className="section-panel">
          <div className="panel-heading">
            <div>
              <h2>Group details</h2>
              <p className="muted">Choose a clear name such as SupportReadOnly.</p>
            </div>
            <FolderPlus size={20} aria-hidden="true" />
          </div>

          <div className="form-field">
            <label htmlFor="new-group-name">Group name</label>
            <input
              id="new-group-name"
              type="text"
              autoFocus
              required
              minLength={2}
              maxLength={64}
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="SupportReadOnly"
              disabled={submitting}
            />
            <p className="form-hint">
              Letters, numbers, spaces, periods, hyphens, and underscores.
            </p>
          </div>

          <div className="form-field">
            <label htmlFor="new-group-description">Description</label>
            <textarea
              id="new-group-description"
              rows={3}
              maxLength={240}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What this group is for and who should join it."
              disabled={submitting}
            />
          </div>
        </section>

        <div className="iam-form-side">
          <section className="section-panel">
            <div className="panel-heading">
              <div>
                <h2>Initial policies</h2>
                <p className="muted">Optional. Effective only for group members.</p>
              </div>
              <ShieldCheck size={19} aria-hidden="true" />
            </div>

            {policiesError && (
              <p className="form-hint error-text">{policiesError}</p>
            )}

            {[
              ['Built-in policies', builtins],
              ['Custom policies', custom],
            ].map(([label, items]) => (
              <div key={label} className="group-policy-section">
                <h3>{label}</h3>
                {items.length === 0 ? (
                  <p className="form-hint">
                    {label === 'Custom policies'
                      ? 'No account-specific policies exist.'
                      : 'No built-in policies available.'}
                  </p>
                ) : (
                  <div className="policy-select-list">
                    {items.map((policy) => (
                      <label key={policy.id} className="check-row policy-select-row">
                        <input
                          type="checkbox"
                          checked={selectedPolicies.includes(policy.id)}
                          onChange={() => togglePolicy(policy.id)}
                          disabled={submitting}
                        />
                        <span>
                          <strong>{policy.name}</strong>
                          <small>{policy.description}</small>
                          <em>{policy.actions.length} actions</em>
                        </span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </section>

          <div className="iam-form-actions">
            <button className="primary-button" type="submit" disabled={submitting}>
              <KeyRound size={15} aria-hidden="true" />
              {submitting ? 'Creating group…' : 'Create group'}
            </button>
            <Link className="secondary-button" to="/iam/groups">
              Cancel
            </Link>
          </div>
        </div>
      </form>
    </>
  );
}
