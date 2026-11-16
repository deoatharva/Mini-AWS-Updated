import {
  Database,
  Play,
  Plus,
  RefreshCw,
  Table2,
  Trash2,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { Modal } from '../../components/Modal.jsx';
import { StatusBadge } from '../../components/StatusBadge.jsx';
import { api, getErrorMessage } from '../../services/api.js';
import { formatDateTime } from '../../utils/format.js';

const emptyResult = null;

function ResultTable({ result }) {
  if (result.columns.length === 0) {
    return (
      <p className="form-hint">
        Statement executed
        {result.rows_affected !== null
          ? ` · ${result.rows_affected} row(s) affected`
          : ''}
        .
      </p>
    );
  }

  if (result.rows.length === 0) {
    return (
      <p className="form-hint">
        The query returned no rows.
      </p>
    );
  }

  return (
    <div className="table-wrap">
      <table className="resource-table">
        <thead>
          <tr>
            {result.columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((value, columnIndex) => (
                <td key={columnIndex}>
                  {value === null ? (
                    <span className="muted">NULL</span>
                  ) : (
                    String(value)
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Databases() {
  const [databases, setDatabases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [modal, setModal] = useState(null);
  const [name, setName] = useState('');
  const [createError, setCreateError] = useState('');
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState(null);
  const [tables, setTables] = useState([]);
  const [tablesLoading, setTablesLoading] = useState(false);
  const [tablesError, setTablesError] = useState('');
  const [sql, setSql] = useState('');
  const [querying, setQuerying] = useState(false);
  const [queryError, setQueryError] = useState('');
  const [result, setResult] = useState(emptyResult);
  const [deleting, setDeleting] = useState(false);

  const refresh = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) {
      setLoading(true);
    }
    try {
      const data = await api.databases.list();
      setDatabases(data);
      setLoadError('');
      setSelected((current) =>
        current ? data.find((item) => item.id === current.id) || null : null,
      );
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

  async function loadTables(databaseId, { quiet = false } = {}) {
    if (!quiet) {
      setTablesLoading(true);
    }
    try {
      const data = await api.databases.tables(databaseId);
      setTables(data);
      setTablesError('');
    } catch (requestError) {
      setTablesError(getErrorMessage(requestError));
    } finally {
      if (!quiet) {
        setTablesLoading(false);
      }
    }
  }

  async function openDatabase(database) {
    setSelected(database);
    setTables([]);
    setTablesError('');
    setQueryError('');
    setResult(emptyResult);
    setSql('');
    setError('');
    setNotice('');
    await loadTables(database.id);
  }

  function closeDatabase() {
    if (querying) {
      return;
    }
    setSelected(null);
    setTables([]);
    setTablesError('');
    setQueryError('');
    setResult(emptyResult);
  }

  async function handleCreate(event) {
    event.preventDefault();
    const cleaned = name.trim();
    if (!cleaned) {
      setCreateError('Enter a database name.');
      return;
    }

    setCreating(true);
    setCreateError('');
    setError('');
    setNotice('');
    try {
      const created = await api.databases.create({ name: cleaned });
      setDatabases((current) => [created, ...current]);
      setModal(null);
      setName('');
      setNotice(`Database "${created.name}" was created.`);
    } catch (requestError) {
      setCreateError(getErrorMessage(requestError));
    } finally {
      setCreating(false);
    }
  }

  async function handleRunQuery(event) {
    event.preventDefault();
    if (!selected) {
      return;
    }
    const statement = sql.trim();
    if (!statement) {
      setQueryError('Enter a SQL statement to execute.');
      return;
    }

    setQuerying(true);
    setQueryError('');
    setError('');
    setNotice('');
    try {
      const data = await api.databases.query(selected.id, statement);
      setResult(data);
      await refresh({ quiet: true });
      await loadTables(selected.id, { quiet: true });
    } catch (requestError) {
      setResult(emptyResult);
      setQueryError(getErrorMessage(requestError));
    } finally {
      setQuerying(false);
    }
  }

  function openDelete(database) {
    setSelected(database);
    setModal('delete');
    setError('');
  }

  async function confirmDelete() {
    if (!selected) {
      return;
    }
    setDeleting(true);
    setError('');
    try {
      const target = selected;
      await api.databases.remove(target.id);
      setDatabases((current) => current.filter((item) => item.id !== target.id));
      if (selected?.id === target.id) {
        setSelected(null);
        setTables([]);
        setResult(emptyResult);
        setQueryError('');
      }
      setNotice(`Database "${target.name}" was deleted.`);
      setModal(null);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      setModal(null);
      await refresh({ quiet: true });
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">DATABASES</div>
          <h1>Databases</h1>
          <p>Create and query isolated local SQLite databases.</p>
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
            Create database
          </button>
        </div>
      </div>

      <div className="notice">
        <strong>Isolated local SQLite</strong>
        <span>
          Each database is a separate SQLite file under the local data directory,
          owned by your account. Queries run with a result limit, and ATTACH,
          DETACH, PRAGMA, VACUUM, and file-reading functions are rejected.
        </span>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Database action failed</strong>
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
          <strong>Could not load databases</strong>
          <span>{loadError}</span>
        </div>
      )}

      <div className="section-panel">
        <div className="panel-heading">
          <div>
            <h2>Databases ({databases.length})</h2>
            <p className="muted">
              Engine, table counts, and availability come from real local files.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state" role="status">
            <p>Loading databases…</p>
            <span>Checking isolated SQLite files.</span>
          </div>
        ) : databases.length === 0 ? (
          <div className="empty-state">
            <Database size={26} aria-hidden="true" />
            <p>No databases to display</p>
            <span>Create a database, then run SQL against it.</span>
            <button
              className="secondary-button"
              type="button"
              onClick={() => setModal('create')}
            >
              <Plus size={14} aria-hidden="true" />
              Create your first database
            </button>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="resource-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Engine</th>
                  <th>Status</th>
                  <th>Tables</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {databases.map((database) => (
                  <tr key={database.id}>
                    <td>
                      <div className="table-name">{database.name}</div>
                      <div className="table-subtext">
                        Database ID {database.id}
                      </div>
                      {database.last_error && (
                        <div className="table-error">{database.last_error}</div>
                      )}
                    </td>
                    <td>{database.engine}</td>
                    <td>
                      <StatusBadge status={database.status} />
                    </td>
                    <td>{database.table_count}</td>
                    <td className="nowrap">
                      {formatDateTime(database.created_at)}
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="table-action"
                          type="button"
                          onClick={() => openDatabase(database)}
                        >
                          <Play size={12} aria-hidden="true" />
                          Open SQL
                        </button>
                        <button
                          className="table-action danger"
                          type="button"
                          disabled={deleting}
                          aria-label={`Delete database ${database.name}`}
                          onClick={() => openDelete(database)}
                        >
                          <Trash2 size={13} aria-hidden="true" />
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="section-panel" aria-live="polite">
        <div className="panel-heading">
          <div>
            <h2>
              SQL editor
              {selected ? ` — ${selected.name}` : ''}
            </h2>
            <p className="muted">
              {selected
                ? 'Run one statement at a time. Results are limited to 200 rows.'
                : 'Open a database to inspect its schema and run SQL.'}
            </p>
          </div>
          {selected && (
            <button
              className="secondary-button"
              type="button"
              onClick={closeDatabase}
              disabled={querying}
            >
              <X size={14} aria-hidden="true" />
              Close editor
            </button>
          )}
        </div>

        {!selected ? (
          <div className="empty-state">
            <Table2 size={24} aria-hidden="true" />
            <p>Select a database</p>
            <span>Its schema and SQL editor will appear here.</span>
          </div>
        ) : (
          <>
            <div className="schema-summary">
              {tablesLoading ? (
                <p className="muted">Loading schema…</p>
              ) : tablesError ? (
                <div className="form-alert" role="alert">
                  <strong>Could not load the schema</strong>
                  <span>{tablesError}</span>
                </div>
              ) : tables.length === 0 ? (
                <p className="muted">
                  No tables yet. Run a CREATE TABLE statement to get started.
                </p>
              ) : (
                <>
                  <p className="muted">
                    Schema ({tables.length}{' '}
                    {tables.length === 1 ? 'object' : 'objects'})
                  </p>
                  <ul className="schema-list">
                    {tables.map((table) => (
                      <li key={table.name}>
                        <strong>{table.name}</strong>
                        <span>
                          {table.kind} · {table.columns.length} column
                          {table.columns.length === 1 ? '' : 's'}
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>

            <form onSubmit={handleRunQuery}>
              <div className="form-field">
                <label htmlFor="sql-statement">SQL statement</label>
                <textarea
                  id="sql-statement"
                  name="sql"
                  className="sql-editor"
                  rows={7}
                  spellCheck={false}
                  maxLength={50000}
                  value={sql}
                  onChange={(event) => setSql(event.target.value)}
                  placeholder="SELECT * FROM your_table;"
                  disabled={querying}
                />
              </div>
              {queryError && (
                <div className="form-alert" role="alert">
                  <strong>SQL statement failed</strong>
                  <span>{queryError}</span>
                </div>
              )}
              <div className="sql-actions">
                <button
                  className="primary-button"
                  type="submit"
                  disabled={querying || !sql.trim()}
                >
                  <Play size={14} aria-hidden="true" />
                  {querying ? 'Running…' : 'Run query'}
                </button>
              </div>
            </form>

            {result && (
              <div className="sql-result">
                <p className="muted">
                  {result.statement_type} · {result.rows.length} row
                  {result.rows.length === 1 ? '' : 's'} returned ·{' '}
                  {result.duration_ms.toFixed(1)} ms
                </p>
                <ResultTable result={result} />
                {result.truncated && (
                  <p className="form-hint">
                    Showing the first 200 rows of this result.
                  </p>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {modal === 'create' && (
        <Modal
          title="Create database"
          onClose={() => {
            if (!creating) {
              setModal(null);
            }
          }}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setModal(null)}
                disabled={creating}
              >
                Cancel
              </button>
              <button
                className="primary-button"
                type="submit"
                form="create-database-form"
                disabled={creating}
              >
                {creating ? 'Creating…' : 'Create database'}
              </button>
            </>
          }
        >
          <p className="modal-copy">
            This creates a new isolated SQLite file owned by your account.
            Names are unique per account and case-insensitive.
          </p>
          {createError && (
            <div className="form-alert" role="alert">
              <strong>Could not create the database</strong>
              <span>{createError}</span>
            </div>
          )}
          <form id="create-database-form" onSubmit={handleCreate}>
            <div className="form-field">
              <label htmlFor="database-name">Database name</label>
              <input
                id="database-name"
                name="name"
                type="text"
                autoFocus
                required
                maxLength={80}
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Practical 15 SQL"
                disabled={creating}
              />
            </div>
          </form>
        </Modal>
      )}

      {modal === 'delete' && selected && (
        <Modal
          title="Delete database"
          onClose={() => {
            if (!deleting) {
              setModal(null);
            }
          }}
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
                onClick={confirmDelete}
                disabled={deleting}
              >
                <Trash2 size={14} aria-hidden="true" />
                {deleting ? 'Deleting…' : 'Delete database'}
              </button>
            </>
          }
        >
          <p className="modal-copy">
            Delete <strong>{selected.name}</strong>? Its SQLite file and all
            stored tables are removed. This action cannot be undone.
          </p>
        </Modal>
      )}
    </>
  );
}
