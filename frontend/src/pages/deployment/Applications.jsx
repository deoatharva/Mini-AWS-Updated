import {
  ExternalLink,
  FileText,
  Globe,
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

export default function Applications() {
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [modal, setModal] = useState(null);
  const [selected, setSelected] = useState(null);
  const [name, setName] = useState('');
  const [deployError, setDeployError] = useState('');
  const [deploying, setDeploying] = useState(false);
  const [action, setAction] = useState(null);
  const [logs, setLogs] = useState(emptyLogs);
  const [deleting, setDeleting] = useState(false);

  const refresh = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) {
      setLoading(true);
    }
    try {
      const data = await api.applications.list();
      setDeployments(data);
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
    if (deploying || deleting) {
      return;
    }
    setModal(null);
    setSelected(null);
    setDeployError('');
  }

  async function handleDeploy(event) {
    event.preventDefault();
    const cleanedName = name.trim();
    if (!cleanedName) {
      setDeployError('Enter an application name.');
      return;
    }

    setDeploying(true);
    setDeployError('');
    setError('');
    setNotice('');

    let created;
    try {
      created = await api.applications.create({ name: cleanedName });
    } catch (requestError) {
      setDeployError(getErrorMessage(requestError));
      setDeploying(false);
      return;
    }

    try {
      const started = await api.applications.start(created.id);
      setDeployments((current) => [started, ...current]);
      setModal(null);
      setName('');
      setNotice(
        `"${started.name}" deployed and running at ${started.local_url}.`,
      );
    } catch (requestError) {
      setModal(null);
      setName('');
      setError(getErrorMessage(requestError));
      await refresh({ quiet: true });
    } finally {
      setDeploying(false);
    }
  }

  async function runAction(deployment, type) {
    setAction({ id: deployment.id, type });
    setError('');
    setNotice('');
    try {
      const updated =
        type === 'start'
          ? await api.applications.start(deployment.id)
          : await api.applications.stop(deployment.id);
      setDeployments((current) =>
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

  async function openLogs(deployment) {
    setSelected(deployment);
    setModal('logs');
    setLogs({ ...emptyLogs, loading: true });
    try {
      const data = await api.applications.logs(deployment.id);
      setLogs({
        loading: false,
        error: '',
        content: data.content,
        truncated: data.truncated,
      });
    } catch (requestError) {
      setLogs({ ...emptyLogs, error: getErrorMessage(requestError) });
    }
  }

  async function refreshLogs() {
    if (!selected) {
      return;
    }
    setLogs((current) => ({ ...current, loading: true, error: '' }));
    try {
      const data = await api.applications.logs(selected.id);
      setLogs({
        loading: false,
        error: '',
        content: data.content,
        truncated: data.truncated,
      });
    } catch (requestError) {
      setLogs({ ...emptyLogs, error: getErrorMessage(requestError) });
    }
  }

  function openDelete(deployment) {
    setSelected(deployment);
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
      await api.applications.remove(selected.id);
      setDeployments((current) =>
        current.filter((deployment) => deployment.id !== selected.id),
      );
      setNotice(`Deployment "${selected.name}" was deleted.`);
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

  const actionBusy = (deploymentId) => action?.id === deploymentId;

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">APPLICATION SERVICES</div>
          <h1>App deployment</h1>
          <p>Deploy the controlled sample web app as a real local process.</p>
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
              setDeployError('');
              setModal('create');
            }}
          >
            <Plus size={15} aria-hidden="true" />
            Deploy application
          </button>
        </div>
      </div>

      <div className="notice">
        <strong>Controlled template only</strong>
        <span>
          Deployments use a built-in sample web application template. Uploaded
          archives, custom scripts, and arbitrary user code are never executed.
          Each app runs on a local port bound to 127.0.0.1.
        </span>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Deployment action failed</strong>
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
          <strong>Could not load applications</strong>
          <span>{loadError}</span>
        </div>
      )}

      <div className="section-panel">
        <div className="panel-heading">
          <div>
            <h2>Applications ({deployments.length})</h2>
            <p className="muted">
              URLs and states come from real local worker processes.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state" role="status">
            <p>Loading deployments…</p>
            <span>Checking application metadata and worker state.</span>
          </div>
        ) : deployments.length === 0 ? (
          <div className="empty-state">
            <Globe size={26} aria-hidden="true" />
            <p>No applications deployed</p>
            <span>
              Deploy the controlled sample app to get a real local URL.
            </span>
            <button
              className="secondary-button"
              type="button"
              onClick={() => setModal('create')}
            >
              <Plus size={14} aria-hidden="true" />
              Deploy your first application
            </button>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="resource-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Template</th>
                  <th>State</th>
                  <th>Local URL</th>
                  <th>Deployed</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {deployments.map((deployment) => {
                  const busy = actionBusy(deployment.id);
                  const canStart =
                    deployment.status === 'stopped' || deployment.status === 'error';
                  const canStop =
                    deployment.status === 'running' ||
                    deployment.status === 'starting';

                  return (
                    <tr key={deployment.id}>
                      <td>
                        <div className="table-name">{deployment.name}</div>
                        <div className="table-subtext">
                          ID {deployment.id}
                          {deployment.pid ? ` · PID ${deployment.pid}` : ''}
                        </div>
                        {deployment.last_error && (
                          <div className="table-error">{deployment.last_error}</div>
                        )}
                      </td>
                      <td>
                        <div>Sample web app</div>
                        <div className="table-subtext">Controlled template</div>
                      </td>
                      <td>
                        <StatusBadge status={deployment.status} />
                      </td>
                      <td>
                        {deployment.local_url ? (
                          <a
                            className="endpoint-link"
                            href={deployment.local_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {deployment.local_url}
                            <ExternalLink size={12} aria-hidden="true" />
                          </a>
                        ) : (
                          <span className="muted">
                            {deployment.port
                              ? `Last port ${deployment.port}`
                              : 'Not running'}
                          </span>
                        )}
                      </td>
                      <td className="nowrap">
                        {formatDateTime(deployment.created_at)}
                      </td>
                      <td>
                        <div className="row-actions">
                          {canStart && (
                            <button
                              className="table-action"
                              type="button"
                              disabled={busy}
                              onClick={() => runAction(deployment, 'start')}
                            >
                              <Play size={13} aria-hidden="true" />
                              {busy && action?.type === 'start'
                                ? 'Starting…'
                                : 'Start'}
                            </button>
                          )}
                          {canStop && (
                            <button
                              className="table-action"
                              type="button"
                              disabled={busy || deployment.status === 'starting'}
                              onClick={() => runAction(deployment, 'stop')}
                            >
                              <Square size={12} aria-hidden="true" />
                              {busy && action?.type === 'stop'
                                ? 'Stopping…'
                                : 'Stop'}
                            </button>
                          )}
                          <button
                            className="table-action"
                            type="button"
                            onClick={() => openLogs(deployment)}
                          >
                            <FileText size={13} aria-hidden="true" />
                            Logs
                          </button>
                          <button
                            className="table-action danger"
                            type="button"
                            disabled={busy || deleting}
                            onClick={() => openDelete(deployment)}
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
          title="Deploy sample application"
          onClose={closeModal}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={closeModal}
                disabled={deploying}
              >
                Cancel
              </button>
              <button
                className="primary-button"
                type="submit"
                form="deploy-application-form"
                disabled={deploying}
              >
                {deploying ? 'Deploying…' : 'Deploy application'}
              </button>
            </>
          }
        >
          <p className="modal-copy">
            This creates and starts the controlled <code>sample-web-app</code>{' '}
            template as a real Python process on a local port. No uploaded code
            is executed.
          </p>
          {deployError && (
            <div className="form-alert" role="alert">
              <strong>Could not deploy the application</strong>
              <span>{deployError}</span>
            </div>
          )}
          <form id="deploy-application-form" onSubmit={handleDeploy}>
            <div className="form-field">
              <label htmlFor="application-name">Application name</label>
              <input
                id="application-name"
                name="name"
                type="text"
                autoFocus
                required
                maxLength={80}
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Practical 13 sample"
                disabled={deploying}
              />
            </div>
            <p className="form-hint">
              The name is a label only. The backend chooses the template and
              validates the port and process lifecycle.
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
              <button
                className="secondary-button"
                type="button"
                onClick={closeModal}
              >
                Close
              </button>
            </>
          }
        >
          <p className="modal-copy">
            Output from the real controlled sample app process.
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
          title="Delete application"
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
                {deleting ? 'Deleting…' : 'Delete application'}
              </button>
            </>
          }
        >
          <p className="modal-copy">
            Delete <strong>{selected.name}</strong>? A running app is stopped
            first, then its metadata and logs are removed.
          </p>
          <p className="muted">This action cannot be undone.</p>
        </Modal>
      )}
    </>
  );
}
