import {
  AlertTriangle,
  ArrowLeft,
  ExternalLink,
  FolderTree,
  KeyRound,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';

import { useAuth } from '../../auth/AuthContext.jsx';
import { Modal } from '../../components/Modal.jsx';
import { StatusBadge } from '../../components/StatusBadge.jsx';
import { api, getErrorMessage } from '../../services/api.js';
import { formatDateTime } from '../../utils/format.js';

export default function IAMGroupDetail() {
  const { groupId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, hasPermission } = useAuth();
  const [group, setGroup] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(
    location.state?.created ? 'IAM group created.' : '',
  );
  const [tab, setTab] = useState('overview');
  const [modal, setModal] = useState(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);
  const [editError, setEditError] = useState('');
  const [allUsers, setAllUsers] = useState([]);
  const [allPolicies, setAllPolicies] = useState([]);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [optionsError, setOptionsError] = useState('');
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [selectedPolicies, setSelectedPolicies] = useState([]);
  const [userSearch, setUserSearch] = useState('');
  const [policySearch, setPolicySearch] = useState('');
  const [modalSubmitting, setModalSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');
  const [busyKey, setBusyKey] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [pendingPolicy, setPendingPolicy] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.iam.groups.get(groupId);
      setGroup(data);
      setEditName(data.name);
      setEditDescription(data.description || '');
      setError('');
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [groupId]);

  useEffect(() => {
    load();
  }, [load]);

  const isSelfMember = useMemo(
    () => Boolean(user?.user_type === 'IAM' && group?.members.some((member) => member.id === user.id)),
    [group, user],
  );
  const selfPolicyRestricted =
    Boolean(user?.user_type === 'IAM') && isSelfMember;
  const canChangePolicies =
    hasPermission('iam:AttachGroupPolicy') &&
    hasPermission('iam:DetachGroupPolicy') &&
    !selfPolicyRestricted;
  const availableUsers = useMemo(
    () =>
      allUsers.filter(
        (candidate) =>
          !group?.members.some((member) => member.id === candidate.id) &&
          !(user?.user_type === 'IAM' && candidate.id === user.id),
      ),
    [allUsers, group, user],
  );
  const availablePolicies = useMemo(
    () =>
      allPolicies.filter(
        (policy) => !group?.policies.some((attached) => attached.id === policy.id),
      ),
    [allPolicies, group],
  );
  const filteredUsers = useMemo(() => {
    const needle = userSearch.trim().toLowerCase();
    if (!needle) {
      return availableUsers;
    }
    return availableUsers.filter((candidate) =>
      `${candidate.username} ${candidate.display_name}`
        .toLowerCase()
        .includes(needle),
    );
  }, [availableUsers, userSearch]);
  const filteredPolicies = useMemo(() => {
    const needle = policySearch.trim().toLowerCase();
    if (!needle) {
      return availablePolicies;
    }
    return availablePolicies.filter((policy) =>
      `${policy.name} ${policy.description}`
        .toLowerCase()
        .includes(needle),
    );
  }, [availablePolicies, policySearch]);

  async function loadUsersForModal() {
    setOptionsLoading(true);
    setOptionsError('');
    try {
      setAllUsers(await api.iam.users.list());
    } catch (requestError) {
      setOptionsError(getErrorMessage(requestError));
    } finally {
      setOptionsLoading(false);
    }
  }

  async function loadPoliciesForModal() {
    setOptionsLoading(true);
    setOptionsError('');
    try {
      setAllPolicies(await api.iam.policies.list());
    } catch (requestError) {
      setOptionsError(getErrorMessage(requestError));
    } finally {
      setOptionsLoading(false);
    }
  }

  function openMembers() {
    setSelectedUsers([]);
    setUserSearch('');
    setOptionsError('');
    setModalError('');
    setModal('members');
    loadUsersForModal();
  }

  function openPolicies() {
    setSelectedPolicies([]);
    setPolicySearch('');
    setOptionsError('');
    setModalError('');
    setModal('policies');
    loadPoliciesForModal();
  }

  function openEdit() {
    setEditName(group.name);
    setEditDescription(group.description || '');
    setEditError('');
    setModal('edit');
  }

  function toggleUser(userId) {
    setSelectedUsers((current) =>
      current.includes(userId)
        ? current.filter((id) => id !== userId)
        : [...current, userId],
    );
  }

  function togglePolicy(policyId) {
    setSelectedPolicies((current) =>
      current.includes(policyId)
        ? current.filter((id) => id !== policyId)
        : [...current, policyId],
    );
  }

  async function saveGroup(event) {
    event.preventDefault();
    setEditError('');
    if (editName.trim().length < 2) {
      setEditError('Use at least 2 characters for the group name.');
      return;
    }
    setSavingEdit(true);
    try {
      const updated = await api.iam.groups.update(group.id, {
        name: editName.trim(),
        description: editDescription.trim() || null,
      });
      setGroup(updated);
      setModal(null);
      setNotice('Group details updated.');
    } catch (requestError) {
      setEditError(getErrorMessage(requestError));
    } finally {
      setSavingEdit(false);
    }
  }

  async function addMembers(event) {
    event.preventDefault();
    if (selectedUsers.length === 0) {
      setModalError('Select at least one IAM user.');
      return;
    }
    setModalSubmitting(true);
    setModalError('');
    try {
      const updated = await api.iam.groups.addUsers(group.id, selectedUsers);
      setGroup(updated);
      setModal(null);
      setNotice(
        `${selectedUsers.length} IAM user(s) added to the group.`,
      );
    } catch (requestError) {
      setModalError(getErrorMessage(requestError));
    } finally {
      setModalSubmitting(false);
    }
  }

  async function removeMember(member) {
    setBusyKey(`member-${member.id}`);
    setError('');
    setNotice('');
    try {
      const updated = await api.iam.groups.removeUser(group.id, member.id);
      setGroup(updated);
      setNotice(`${member.username} removed from the group.`);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyKey('');
    }
  }

  async function attachPolicies(event) {
    event.preventDefault();
    if (selectedPolicies.length === 0) {
      setModalError('Select at least one policy.');
      return;
    }
    setModalSubmitting(true);
    setModalError('');
    try {
      const updated = await api.iam.groups.attachPolicies(
        group.id,
        selectedPolicies,
      );
      setGroup(updated);
      setModal(null);
      setNotice(
        `${selectedPolicies.length} policy(ies) attached. Effective permissions changed immediately.`,
      );
    } catch (requestError) {
      setModalError(getErrorMessage(requestError));
    } finally {
      setModalSubmitting(false);
    }
  }

  async function detachPolicy(policy) {
    setBusyKey(`policy-${policy.id}`);
    setError('');
    setNotice('');
    try {
      const updated = await api.iam.groups.detachPolicy(group.id, policy.id);
      setGroup(updated);
      setModal(null);
      setPendingPolicy(null);
      setNotice(
        `${policy.name} detached. The policy remains available for other groups.`,
      );
    } catch (requestError) {
      setModal(null);
      setPendingPolicy(null);
      setError(getErrorMessage(requestError));
    } finally {
      setBusyKey('');
    }
  }

  async function deleteGroup() {
    setDeleting(true);
    try {
      await api.iam.groups.remove(group.id);
      navigate('/iam/groups', { replace: true });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      setModal(null);
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="section-panel empty-state" role="status">
        <p>Loading IAM group…</p>
        <span>Reading members and attached policies.</span>
      </div>
    );
  }

  if (!group) {
    return (
      <>
        <div className="page-heading">
          <div>
            <div className="eyebrow">IDENTITY &amp; ACCESS</div>
            <h1>IAM group not found</h1>
            <p>The group may have been deleted or belong to another account.</p>
          </div>
        </div>
        {error && (
          <div className="form-alert" role="alert">
            <strong>Could not open IAM group</strong>
            <span>{error}</span>
          </div>
        )}
        <Link className="secondary-button" to="/iam/groups">
          <ArrowLeft size={15} /> Back to groups
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
            <h1>{group.name}</h1>
            <span className="iam-summary-badge">
              <FolderTree size={13} /> IAM group
            </span>
          </div>
          <p>{group.description || 'No description provided.'}</p>
        </div>
        <div className="heading-actions">
          <button className="secondary-button" type="button" onClick={load}>
            <RefreshCw size={15} aria-hidden="true" /> Refresh
          </button>
          {hasPermission('iam:UpdateGroup') && (
            <button className="secondary-button" type="button" onClick={openEdit}>
              <Pencil size={15} aria-hidden="true" /> Edit
            </button>
          )}
          {hasPermission('iam:DeleteGroup') && (
            <button
              className="danger-button"
              type="button"
              onClick={() => setModal('delete')}
            >
              <Trash2 size={15} aria-hidden="true" /> Delete
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Action failed</strong>
          <span>{error}</span>
        </div>
      )}
      {notice && <div className="success-notice" role="status">{notice}</div>}
      {selfPolicyRestricted && (
        <div className="notice">
          <strong>Self-escalation protection is active</strong>
          <span>
            You belong to this group. The API blocks IAM users from attaching or
            detaching its policies, even if permission management is otherwise allowed.
          </span>
        </div>
      )}

      <div className="iam-summary-strip">
        <div>
          <span>Group ID</span>
          <strong>{group.id}</strong>
        </div>
        <div>
          <span>Members</span>
          <strong>{group.user_count}</strong>
        </div>
        <div>
          <span>Attached policies</span>
          <strong>{group.policy_count}</strong>
        </div>
        <div>
          <span>Last updated</span>
          <strong>{formatDateTime(group.updated_at)}</strong>
        </div>
      </div>

      <div className="iam-tabs" role="tablist" aria-label="IAM group details">
        {[
          ['overview', 'Overview'],
          ['members', `Members (${group.members.length})`],
          ['policies', `Policies (${group.policies.length})`],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            className={tab === key ? 'active' : ''}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="iam-detail-grid">
          <section className="section-panel">
            <div className="panel-heading">
              <div>
                <h2>Group summary</h2>
                <p className="muted">Membership and policy attachment counts.</p>
              </div>
              <FolderTree size={20} aria-hidden="true" />
            </div>
            <dl className="detail-list">
              <dt>Group ID</dt><dd>{group.id}</dd>
              <dt>Name</dt><dd>{group.name}</dd>
              <dt>Description</dt><dd>{group.description || '—'}</dd>
              <dt>Created</dt><dd>{formatDateTime(group.created_at)}</dd>
              <dt>Updated</dt><dd>{formatDateTime(group.updated_at)}</dd>
            </dl>
          </section>

          <div className="iam-side-stack">
            <section className="section-panel">
              <div className="panel-heading">
                <div>
                  <h2>Permission model</h2>
                  <p className="muted">Allow-list union across attached policies.</p>
                </div>
                <ShieldCheck size={19} aria-hidden="true" />
              </div>
              <p className="iam-muted-block">
                Every member receives the combined actions allowed by this
                group&apos;s policies. No implicit access exists. Removing a policy
                removes those actions for all members immediately.
              </p>
              <button className="secondary-button" type="button" onClick={() => setTab('policies')}>
                Review attached policies
              </button>
            </section>

            <section className="section-panel">
              <div className="panel-heading">
                <div>
                  <h2>Membership</h2>
                  <p className="muted">Only IAM users from this local account.</p>
                </div>
                <Users size={19} aria-hidden="true" />
              </div>
              <p className="iam-muted-block">
                {group.user_count === 0
                  ? 'No users currently inherit permissions from this group.'
                  : `${group.user_count} IAM user(s) inherit this group's permission union.`}
              </p>
              <button className="secondary-button" type="button" onClick={() => setTab('members')}>
                Review group members
              </button>
            </section>
          </div>
        </div>
      )}

      {tab === 'members' && (
        <section className="section-panel">
          <div className="panel-heading iam-panel-heading">
            <div>
              <h2>Members ({group.members.length})</h2>
              <p className="muted">Add an existing IAM user or remove membership.</p>
            </div>
            {hasPermission('iam:AddUserToGroup') && !isSelfMember && (
              <button className="primary-button" type="button" onClick={openMembers}>
                <UserPlus size={15} aria-hidden="true" /> Add users
              </button>
            )}
          </div>

          {group.members.length === 0 ? (
            <div className="empty-state compact-empty">
              <Users size={24} aria-hidden="true" />
              <p>No members</p>
              <span>This group currently grants permissions to no one.</span>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="resource-table iam-table">
                <thead>
                  <tr>
                    <th>IAM user</th>
                    <th>Status</th>
                    <th>Console access</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {group.members.map((member) => (
                    <tr key={member.id}>
                      <td>
                        <div className="table-name">{member.display_name}</div>
                        <div className="table-subtext"><code>{member.username}</code></div>
                      </td>
                      <td><StatusBadge status={member.status} /></td>
                      <td>{member.console_access_enabled ? 'Enabled' : 'Disabled'}</td>
                      <td>
                        <div className="row-actions">
                          <Link className="table-action" to={`/iam/users/${member.id}`}>
                            View <ExternalLink size={12} aria-hidden="true" />
                          </Link>
                          {hasPermission('iam:RemoveUserFromGroup') && (
                            <button
                              className="table-action danger-text"
                              type="button"
                              onClick={() => removeMember(member)}
                              disabled={busyKey === `member-${member.id}`}
                            >
                              <X size={12} aria-hidden="true" />
                              {busyKey === `member-${member.id}` ? 'Removing…' : 'Remove'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {tab === 'policies' && (
        <section className="section-panel">
          <div className="panel-heading iam-panel-heading">
            <div>
              <h2>Attached policies ({group.policies.length})</h2>
              <p className="muted">
                Built-in policies are immutable. Custom policies can be edited on their detail page.
              </p>
            </div>
            {canChangePolicies && (
              <button className="primary-button" type="button" onClick={openPolicies}>
                <Plus size={15} aria-hidden="true" /> Attach policies
              </button>
            )}
          </div>

          {group.policies.length === 0 ? (
            <div className="empty-state compact-empty">
              <KeyRound size={24} aria-hidden="true" />
              <p>No policies attached</p>
              <span>Members of this group currently have no IAM permissions.</span>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="resource-table iam-table">
                <thead>
                  <tr>
                    <th>Policy</th>
                    <th>Type</th>
                    <th>Allowed actions</th>
                    <th>Used by groups</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {group.policies.map((policy) => (
                    <tr key={policy.id}>
                      <td>
                        <Link className="table-name table-link" to={`/iam/policies/${policy.id}`}>
                          {policy.name}
                        </Link>
                        <div className="table-subtext">{policy.description}</div>
                      </td>
                      <td>
                        <span className={`policy-type ${policy.is_managed ? 'managed' : 'custom'}`}>
                          {policy.is_managed ? 'Built-in' : 'Custom'}
                        </span>
                      </td>
                      <td>{policy.actions.length}</td>
                      <td>{policy.group_count}</td>
                      <td>
                        {canChangePolicies ? (
                          <button
                            className="table-action danger-text"
                            type="button"
                            onClick={() => {
                              setPendingPolicy(policy);
                              setModal('detach');
                            }}
                            disabled={busyKey === `policy-${policy.id}`}
                          >
                            <X size={12} aria-hidden="true" />
                            {busyKey === `policy-${policy.id}` ? 'Detaching…' : 'Detach'}
                          </button>
                        ) : (
                          <Link className="table-action" to={`/iam/policies/${policy.id}`}>
                            View <ExternalLink size={12} aria-hidden="true" />
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {modal === 'edit' && (
        <Modal
          title="Edit IAM group"
          onClose={() => !savingEdit && setModal(null)}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setModal(null)}
                disabled={savingEdit}
              >
                Cancel
              </button>
              <button
                className="primary-button"
                type="submit"
                form="edit-group-form"
                disabled={savingEdit}
              >
                {savingEdit ? 'Saving…' : 'Save changes'}
              </button>
            </>
          }
        >
          {editError && (
            <div className="form-alert" role="alert">
              <strong>Could not update group</strong>
              <span>{editError}</span>
            </div>
          )}
          <form id="edit-group-form" onSubmit={saveGroup}>
            <div className="form-field">
              <label htmlFor="edit-group-name">Group name</label>
              <input
                id="edit-group-name"
                type="text"
                required
                minLength={2}
                maxLength={64}
                value={editName}
                onChange={(event) => setEditName(event.target.value)}
                disabled={savingEdit}
              />
            </div>
            <div className="form-field">
              <label htmlFor="edit-group-description">Description</label>
              <textarea
                id="edit-group-description"
                rows={3}
                maxLength={240}
                value={editDescription}
                onChange={(event) => setEditDescription(event.target.value)}
                disabled={savingEdit}
              />
            </div>
          </form>
        </Modal>
      )}

      {modal === 'members' && (
        <Modal
          title="Add IAM users"
          onClose={() => !modalSubmitting && setModal(null)}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setModal(null)}
                disabled={modalSubmitting}
              >
                Cancel
              </button>
              <button
                className="primary-button"
                type="submit"
                form="add-group-members-form"
                disabled={modalSubmitting}
              >
                <UserPlus size={15} />
                {modalSubmitting
                  ? 'Adding…'
                  : `Add ${selectedUsers.length || ''} user${selectedUsers.length === 1 ? '' : 's'}`}
              </button>
            </>
          }
        >
          {modalError && (
            <div className="form-alert" role="alert">
              <strong>Could not add members</strong>
              <span>{modalError}</span>
            </div>
          )}
          {optionsError && <p className="form-hint error-text">{optionsError}</p>}
          {optionsLoading ? (
            <p className="muted">Loading IAM users…</p>
          ) : availableUsers.length === 0 ? (
            <div className="empty-state compact-empty">
              <Users size={23} aria-hidden="true" />
              <p>No eligible IAM users</p>
              <span>
                All existing users are already members, or none exist yet.
              </span>
              <Link className="secondary-button" to="/iam/users/new" onClick={() => setModal(null)}>
                Create an IAM user
              </Link>
            </div>
          ) : (
            <>
              <label className="search-field modal-search" htmlFor="group-user-search">
                <Search size={14} aria-hidden="true" />
                <input
                  id="group-user-search"
                  type="search"
                  value={userSearch}
                  onChange={(event) => setUserSearch(event.target.value)}
                  placeholder="Search IAM users"
                  aria-label="Search IAM users"
                />
              </label>
              {filteredUsers.length === 0 ? (
                <p className="form-hint">No users match that search.</p>
              ) : (
                <form id="add-group-members-form" onSubmit={addMembers}>
                  <div className="modal-check-list">
                    {filteredUsers.map((candidate) => (
                      <label key={candidate.id} className="check-row compact-check">
                        <input
                          type="checkbox"
                          checked={selectedUsers.includes(candidate.id)}
                          onChange={() => toggleUser(candidate.id)}
                          disabled={modalSubmitting}
                        />
                        <span>
                          <strong>{candidate.display_name}</strong>
                          <small>
                            <code>{candidate.username}</code> · {candidate.status} ·{' '}
                            {candidate.groups.length} group(s)
                          </small>
                        </span>
                      </label>
                    ))}
                  </div>
                </form>
              )}
            </>
          )}
        </Modal>
      )}

      {modal === 'policies' && (
        <Modal
          title="Attach policies"
          onClose={() => !modalSubmitting && setModal(null)}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setModal(null)}
                disabled={modalSubmitting}
              >
                Cancel
              </button>
              <button
                className="primary-button"
                type="submit"
                form="attach-group-policies-form"
                disabled={modalSubmitting || selectedPolicies.length === 0}
              >
                <Plus size={15} />
                {modalSubmitting
                  ? 'Attaching…'
                  : `Attach ${selectedPolicies.length || ''} polic${selectedPolicies.length === 1 ? 'y' : 'ies'}`}
              </button>
            </>
          }
        >
          {modalError && (
            <div className="form-alert" role="alert">
              <strong>Could not attach policies</strong>
              <span>{modalError}</span>
            </div>
          )}
          {optionsError && <p className="form-hint error-text">{optionsError}</p>}
          {optionsLoading ? (
            <p className="muted">Loading policies…</p>
          ) : availablePolicies.length === 0 ? (
            <div className="empty-state compact-empty">
              <ShieldCheck size={23} aria-hidden="true" />
              <p>No eligible policies</p>
              <span>Every available policy is already attached to this group.</span>
            </div>
          ) : (
            <>
              <label
                className="search-field modal-search"
                htmlFor="group-policy-search"
              >
                <Search size={14} aria-hidden="true" />
                <input
                  id="group-policy-search"
                  type="search"
                  value={policySearch}
                  onChange={(event) => setPolicySearch(event.target.value)}
                  placeholder="Search policies by name or description"
                  aria-label="Search policies"
                />
              </label>
              {filteredPolicies.length === 0 ? (
                <p className="form-hint">No policies match that search.</p>
              ) : (
                <form id="attach-group-policies-form" onSubmit={attachPolicies}>
                  <div className="modal-check-list">
                    {filteredPolicies.map((policy) => (
                      <label key={policy.id} className="check-row compact-check">
                        <input
                          type="checkbox"
                          checked={selectedPolicies.includes(policy.id)}
                          onChange={() => togglePolicy(policy.id)}
                          disabled={modalSubmitting}
                        />
                        <span>
                          <strong>{policy.name}</strong>
                          <small>
                            {policy.description} · {policy.actions.length} actions ·{' '}
                            {policy.is_managed ? 'Built-in' : 'Custom'}
                          </small>
                        </span>
                      </label>
                    ))}
                  </div>
                </form>
              )}
            </>
          )}
        </Modal>
      )}

      {modal === 'detach' && pendingPolicy && (
        <Modal
          title="Detach policy"
          onClose={() => !busyKey && setModal(null)}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setModal(null)}
                disabled={Boolean(busyKey)}
              >
                Cancel
              </button>
              <button
                className="danger-button"
                type="button"
                onClick={() => detachPolicy(pendingPolicy)}
                disabled={Boolean(busyKey)}
              >
                <X size={15} />
                {busyKey === `policy-${pendingPolicy.id}`
                  ? 'Detaching…'
                  : 'Detach policy'}
              </button>
            </>
          }
        >
          <div className="danger-callout">
            <AlertTriangle size={20} aria-hidden="true" />
            <div>
              <strong>{pendingPolicy.name} will stop granting access.</strong>
              <p>
                Detaching removes this policy&apos;s actions from every current
                member of <code>{group.name}</code> immediately. The policy remains
                available for other groups.
              </p>
            </div>
          </div>
        </Modal>
      )}

      {modal === 'delete' && (
        <Modal
          title="Delete IAM group"
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
                onClick={deleteGroup}
                disabled={deleting}
              >
                <Trash2 size={15} /> {deleting ? 'Deleting…' : 'Delete group'}
              </button>
            </>
          }
        >
          <div className="danger-callout">
            <AlertTriangle size={20} aria-hidden="true" />
            <div>
              <strong>Permission changes take effect immediately.</strong>
              <p>
                Deleting <code>{group.name}</code> removes its memberships and
                policy attachments. IAM users in this group lose these permissions.
                The policies themselves are not deleted.
              </p>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
