import {
  CheckCircle2,
  Filter,
  RefreshCw,
  RotateCcw,
  ScrollText,
  Search,
  XCircle,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { api, getErrorMessage } from '../../services/api.js';
import { formatDateTime } from '../../utils/format.js';
import { EVENT_TYPES, eventLabel } from '../../utils/iam.js';

const EMPTY_FILTERS = {
  q: '',
  event_type: '',
  success: '',
};

export default function IAMAudit() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [q, setQ] = useState('');
  const [eventType, setEventType] = useState('');
  const [successFilter, setSuccessFilter] = useState('');

  const load = useCallback(async (filters) => {
    setLoading(true);
    try {
      const data = await api.iam.auditLogs({
        q: filters.q.trim(),
        event_type: filters.event_type,
        success: filters.success,
        limit: 100,
      });
      setEntries(data);
      setError('');
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(EMPTY_FILTERS);
  }, [load]);

  function applyFilters(event) {
    event.preventDefault();
    load({ q, event_type: eventType, success: successFilter });
  }

  function clearFilters() {
    setQ('');
    setEventType('');
    setSuccessFilter('');
    load(EMPTY_FILTERS);
  }

  const successCount = entries.filter((entry) => entry.success).length;
  const failedCount = entries.length - successCount;

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">IDENTITY &amp; ACCESS</div>
          <h1>Audit log</h1>
          <p>Account-scoped authentication and IAM events, newest first.</p>
        </div>
        <button
          className="secondary-button"
          type="button"
          onClick={() => load({ q, event_type: eventType, success: successFilter })}
          disabled={loading}
        >
          <RefreshCw size={15} aria-hidden="true" /> Refresh
        </button>
      </div>

      <div className="notice">
        <strong>Credential values are never written to the audit log</strong>
        <span>
          Password, token, secret, hash, and credential-like metadata fields are
          recursively redacted by the backend. Events are isolated to your local
          account.
        </span>
      </div>

      <section className="section-panel audit-filter-panel">
        <form className="audit-filters" onSubmit={applyFilters}>
          <div className="form-field">
            <label htmlFor="audit-search">Search actor, target, or details</label>
            <div className="search-input-with-icon">
              <Search size={14} aria-hidden="true" />
              <input
                id="audit-search"
                type="search"
                maxLength={120}
                value={q}
                onChange={(event) => setQ(event.target.value)}
                placeholder="username, group, policy…"
              />
            </div>
          </div>
          <div className="form-field">
            <label htmlFor="audit-event-type">Event type</label>
            <select
              id="audit-event-type"
              value={eventType}
              onChange={(event) => setEventType(event.target.value)}
            >
              <option value="">All events</option>
              {EVENT_TYPES.map((type) => (
                <option key={type} value={type}>{eventLabel(type)}</option>
              ))}
            </select>
          </div>
          <div className="form-field">
            <label htmlFor="audit-result">Result</label>
            <select
              id="audit-result"
              value={successFilter}
              onChange={(event) => setSuccessFilter(event.target.value)}
            >
              <option value="">All results</option>
              <option value="true">Success</option>
              <option value="false">Failed</option>
            </select>
          </div>
          <div className="audit-filter-actions">
            <button className="primary-button" type="submit" disabled={loading}>
              <Filter size={14} aria-hidden="true" /> Apply filters
            </button>
            <button className="secondary-button" type="button" onClick={clearFilters} disabled={loading}>
              <RotateCcw size={14} aria-hidden="true" /> Reset
            </button>
          </div>
        </form>
      </section>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Could not load audit log</strong>
          <span>{error}</span>
        </div>
      )}

      <div className="section-panel">
        <div className="panel-heading iam-panel-heading">
          <div>
            <h2>Events ({entries.length})</h2>
            <p className="muted">
              Showing up to 100 matching events. {successCount} succeeded, {failedCount} failed.
            </p>
          </div>
          <span className="audit-scope"><ScrollText size={14} /> Account-scoped</span>
        </div>

        {loading ? (
          <div className="empty-state" role="status">
            <p>Loading audit events…</p>
            <span>Querying the local account audit trail.</span>
          </div>
        ) : entries.length === 0 ? (
          <div className="empty-state">
            <ScrollText size={27} aria-hidden="true" />
            <p>No matching audit events</p>
            <span>Try clearing the filters or performing an IAM action.</span>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="resource-table audit-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Event</th>
                  <th>Actor</th>
                  <th>Target</th>
                  <th>Result</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id}>
                    <td className="nowrap">{formatDateTime(entry.created_at)}</td>
                    <td>
                      <div className="table-name">{eventLabel(entry.event_type)}</div>
                      <div className="table-subtext"><code>{entry.event_type}</code></div>
                    </td>
                    <td>
                      <div className="table-name">
                        {entry.actor_username || 'Anonymous'}
                      </div>
                      <div className="table-subtext">
                        {entry.actor_display_name || 'No display name'} · {entry.actor_type}
                      </div>
                    </td>
                    <td>
                      <div className="table-name">{entry.target_type}</div>
                      <div className="table-subtext">
                        {entry.target_id ? `ID ${entry.target_id}` : 'No target ID'}
                      </div>
                    </td>
                    <td>
                      <span className={`audit-result ${entry.success ? 'success' : 'failed'}`}>
                        {entry.success ? (
                          <CheckCircle2 size={13} aria-hidden="true" />
                        ) : (
                          <XCircle size={13} aria-hidden="true" />
                        )}
                        {entry.success ? 'Success' : 'Failed'}
                      </span>
                    </td>
                    <td>
                      {Object.keys(entry.metadata || {}).length === 0 ? (
                        <span className="muted">—</span>
                      ) : (
                        <details className="audit-metadata">
                          <summary>Metadata</summary>
                          <pre>{JSON.stringify(entry.metadata, null, 2)}</pre>
                        </details>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
