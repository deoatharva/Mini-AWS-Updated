import {
  ExternalLink,
  FileText,
  Monitor,
  Play,
  Plus,
  RefreshCw,
  Square,
  Trash2,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { Modal } from '../../components/Modal.jsx';
import { StatusBadge } from '../../components/StatusBadge.jsx';
import { api, getErrorMessage } from '../../services/api.js';
import { formatDateTime } from '../../utils/format.js';

const emptyLogs = {
  loading: false,
  error: '',
  content: '',
  truncated: false,
};

export default function Instances() {
  const [instances, setInstances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [modal, setModal] = useState(null);
  const [selected, setSelected] = useState(null);
  const [name, setName] = useState('');
  const [createError, setCreateError] = useState('');
  const [creating, setCreating] = useState(false);
  const [action, setAction] = useState(null);
  const [logs, setLogs] = useState(emptyLogs);
  const [deleting, setDeleting] = useState(false);

  const refresh = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) {
      setLoading(true);
    }
    try {
      const data = await api.compute.list();
      setInstances(data);
      setLoadError('');
    } catch (requestError) {
      setLoadError(getErrorMessage(requestError));
    } finally {
      if (!quiet) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function closeModal() {
    if (creating || deleting) {
      return;
    }
    setModal(null);
    setSelected(null);
    setCreateError('');
  }

  async function handleCreate(event) {
    event.preventDefault();
    const cleanedName = name.trim();
    if (!cleanedName) {
      setCreateError('Enter an instance name.');
      return;
    }

    setCreating(true);
    setCreateError('');
    try {
      const created = await api.compute.create({ name: cleanedName });
      setInstances((current) => [created, ...current]);
      setModal(null);
      setName('');
      setNotice(
        `Instance "${created.name}" created. Start it to run a real local worker process.`,
      );
    } catch (requestError) {
      setCreateError(getErrorMessage(requestError));
    } finally {
      setCreating(false);
    }
  }

  async function runAction(instance, type) {
    setAction({ id: instance.id, type });
    setError('');
    setNotice('');
    try {
      const updated =
        type === 'start'
          ? await api.compute.start(instance.id)
          : await api.compute.stop(instance.id);
      setInstances((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setNotice(
        updated.status === 'running'
          ? `"${updated.name}" is running at ${updated.local_url}.`
          : `"${updated.name}" is stopped.`,
      );
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      await refresh({ quiet: true });
    } finally {
      setAction(null);
    }
  }

  async function openLogs(instance) {
    setSelected(instance);
    setModal('logs');
    setLogs({ ...emptyLogs, loading: true });
    try {
      const data = await api.compute.logs(instance.id);
      setLogs({
        loading: false,
        error: '',
        content: data.content,
        truncated: data.truncated,
      });
    } catch (requestError) {
      setLogs({
        ...emptyLogs,
        error: getErrorMessage(requestError),
      });
    }
  }

  async function refreshLogs() {
    if (!selected) {
      return;
    }
    setLogs((current) => ({ ...current, loading: true, error: '' }));
    try {
      const data = await api.compute.logs(selected.id);
      setLogs({
        loading: false,
        error: '',
        content: data.content,
        truncated: data.truncated,
      });
    } catch (requestError) {
      setLogs({
        ...emptyLogs,
        error: getErrorMessage(requestError),
      });
    }
  }

  function openDelete(instance) {
    setSelected(instance);
    setModal('delete');
    setError('');
  }

  async function handleDelete() {
    if (!selected) {
      return;
    }
    setDeleting(true);
    setError('');
    try {
      await api.compute.remove(selected.id);
      setInstances((current) =>
        current.filter((instance) => instance.id !== selected.id),
      );
      setNotice(`Instance "${selected.name}" was deleted.`);
      setModal(null);
      setSelected(null);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      setModal(null);
      setSelected(null);
      await refresh({ quiet: true });
    } finally {
      setDeleting(false);
    }
  }

  const actionBusy = (instanceId) => action?.id === instanceId;

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">COMPUTE</div>
          <h1>Instances</h1>
          <p>Create and manage real Python worker processes on this computer.</p>
        </div>
        <div className="heading-actions">
          <button
            className="secondary-button"
            type="button"
            onClick={() => refresh()}
            disabled={loading}
          >
            <RefreshCw size={15} aria-hidden="true" />
            Refresh
          </button>
          <button
            className="primary-button"
            type="button"
            onClick={() => {
              setName('');
              setCreateError('');
              setModal('create');
            }}
          >
            <Plus size={15} aria-hidden="true" />
            Launch instance
          </button>
        </div>
      </div>

      <div className="notice">
        <strong>Process-based compute, not a VM</strong>
        <span>
          Each running instance is a managed Python worker bound to
          127.0.0.1. State is verified from the real process, heartbeat, and
          health endpoint. These are not EC2 instances or virtual machines.
        </span>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Action failed</strong>
          <span>{error}</span>
        </div>
      )}
      {notice && (
        <div className="success-notice" role="status">
          {notice}
        </div>
      )}

      {loadError && (
        <div className="form-alert" role="alert">
          <strong>Could not load instances</strong>
          <span>{loadError}</span>
        </div>
      )}

      <div className="section-panel">
        <div className="panel-heading">
          <div>
            <h2>Instances ({instances.length})</h2>
            <p className="muted">
              Only instances owned by your local account are shown.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state" role="status">
            <p>Loading instances…</p>
            <span>Checking local worker metadata.</span>
          </div>
        ) : instances.length === 0 ? (
          <div className="empty-state">
            <Monitor size={26} aria-hidden="true" />
            <p>No compute instances yet</p>
            <span>
              Launch an instance, then start it to run a real local process.
            </span>
            <button
              className="secondary-button"
              type="button"
              onClick={() => setModal('create')}
            >
              <Plus size={14} aria-hidden="true" />
              Launch your first instance
            </button>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="resource-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>State</th>
                  <th>Endpoint</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {instances.map((instance) => {
                  const busy = actionBusy(instance.id);
                  const canStart =
                    instance.status === 'stopped' || instance.status === 'error';
                  const canStop =
                    instance.status === 'running' || instance.status === 'starting';

                  return (
                    <tr key={instance.id}>
                      <td>
                        <div className="table-name">{instance.name}</div>
                        <div className="table-subtext">
                          ID {instance.id}
                          {instance.pid ? ` · PID ${instance.pid}` : ''}
                        </div>
                        {instance.last_error && (
                          <div className="table-error">{instance.last_error}</div>
                        )}
                      </td>
                      <td>
                        <div>Local process</div>
                        <div className="table-subtext">Not a virtual machine</div>
                      </td>
                      <td>
                        <StatusBadge status={instance.status} />
                      </td>
                      <td>
                        {instance.local_url ? (
                          <a
                            className="endpoint-link"
                            href={instance.local_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {instance.local_url}
                            <ExternalLink size={12} aria-hidden="true" />
                          </a>
                        ) : (
                          <span className="muted">
                            {instance.port ? `Last port ${instance.port}` : 'Not started'}
                          </span>
                        )}
                      </td>
                      <td className="nowrap">{formatDateTime(instance.created_at)}</td>
                      <td>
                        <div className="row-actions">
                          {canStart && (
                            <button
                              className="table-action"
                              type="button"
                              disabled={busy}
                              onClick={() => runAction(instance, 'start')}
                            >
                              <Play size={13} aria-hidden="true" />
                              {busy && action?.type === 'start' ? 'Starting…' : 'Start'}
                            </button>
                          )}
                          {canStop && (
                            <button
                              className="table-action"
                              type="button"
                              disabled={busy || instance.status === 'starting'}
                              onClick={() => runAction(instance, 'stop')}
                            >
                              <Square size={12} aria-hidden="true" />
                              {busy && action?.type === 'stop' ? 'Stopping…' : 'Stop'}
                            </button>
                          )}
                          <button
                            className="table-action"
                            type="button"
                            onClick={() => openLogs(instance)}
                          >
                            <FileText size={13} aria-hidden="true" />
                            Logs
                          </button>
                          <button
                            className="table-action danger"
                            type="button"
                            disabled={busy || deleting}
                            onClick={() => openDelete(instance)}
                          >
                            <Trash2 size={13} aria-hidden="true" />
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modal === 'create' && (
        <Modal
          title="Launch local instance"
          onClose={closeModal}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={closeModal}
                disabled={creating}
              >
                Cancel
              </button>
              <button
                className="primary-button"
                type="submit"
                form="create-instance-form"
                disabled={creating}
              >
                {creating ? 'Creating…' : 'Create instance'}
              </button>
            </>
          }
        >
          <p className="modal-copy">
            This creates metadata for a managed Python worker. The process does
            not start until you choose Start.
          </p>
          {createError && (
            <div className="form-alert" role="alert">
              <strong>Could not create the instance</strong>
              <span>{createError}</span>
            </div>
          )}
          <form id="create-instance-form" onSubmit={handleCreate}>
            <div className="form-field">
              <label htmlFor="instance-name">Name</label>
              <input
                id="instance-name"
                name="name"
                type="text"
                autoFocus
                required
                maxLength={80}
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Practical 12 worker"
                disabled={creating}
              />
            </div>
            <p className="form-hint">
              The name is a label only. No shell command or uploaded code is
              executed.
            </p>
          </form>
        </Modal>
      )}

      {modal === 'logs' && selected && (
        <Modal
          title={`Logs — ${selected.name}`}
          onClose={closeModal}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={refreshLogs}
                disabled={logs.loading}
              >
                <RefreshCw size={14} aria-hidden="true" />
                {logs.loading ? 'Refreshing…' : 'Refresh logs'}
              </button>
              <button className="secondary-button" type="button" onClick={closeModal}>
                Close
              </button>
            </>
          }
        >
          <p className="modal-copy">
            Output from the real local worker process. Paths and commands are
            controlled by the backend.
          </p>
          {logs.error && (
            <div className="form-alert" role="alert">
              <strong>Could not load logs</strong>
              <span>{logs.error}</span>
            </div>
          )}
          {logs.loading ? (
            <div className="empty-state" role="status">
              <p>Loading logs…</p>
            </div>
          ) : (
            <pre className="log-view">{logs.content || 'No logs yet.'}</pre>
          )}
          {logs.truncated && (
            <p className="form-hint">Showing the most recent 64 KB of output.</p>
          )}
        </Modal>
      )}

      {modal === 'delete' && selected && (
        <Modal
          title="Delete instance"
          onClose={closeModal}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={closeModal}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                className="danger-button"
                type="button"
                onClick={handleDelete}
                disabled={deleting}
              >
                <Trash2 size={14} aria-hidden="true" />
                {deleting ? 'Deleting…' : 'Delete instance'}
              </button>
            </>
          }
        >
          <p className="modal-copy">
            Delete <strong>{selected.name}</strong>? If it is running, the local
            worker is stopped first. Its metadata and logs are removed.
          </p>
          <p className="muted">This action cannot be undone.</p>
        </Modal>
      )}
    </>
  );
}
