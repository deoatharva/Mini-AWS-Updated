import {
  ArrowUpRight,
  Database,
  Globe,
  HardDrive,
  Monitor,
  RefreshCw,
  Upload,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';
import { api, getErrorMessage } from '../services/api.js';
import { formatBytes, formatDateTime } from '../utils/format.js';

const services = [
  {
    title: 'Compute instances',
    desc: 'Create and manage local compute resources.',
    to: '/compute/instances',
    icon: Monitor,
  },
  {
    title: 'App deployment',
    desc: 'Run a controlled sample web application locally.',
    to: '/applications',
    icon: Globe,
  },
  {
    title: 'Object storage',
    desc: 'Manage buckets and local file objects.',
    to: '/storage/buckets',
    icon: HardDrive,
  },
  {
    title: 'Database service',
    desc: 'Create local databases and run SQL.',
    to: '/databases',
    icon: Database,
  },
];

const serviceRoutes = {
  compute: '/compute/instances',
  applications: '/applications',
  storage: '/storage/buckets',
  databases: '/databases',
};

const serviceIcons = {
  compute: Monitor,
  applications: Globe,
  storage: HardDrive,
  databases: Database,
};

const actionLabels = {
  created: 'Created',
  started: 'Started',
  stopped: 'Stopped',
  failed: 'Failed',
  deployed: 'Deployed',
  uploaded: 'Uploaded',
  deleted: 'Deleted',
  starting: 'Starting',
  stopping: 'Stopping',
};

const resourceLabels = {
  compute_instance: 'compute instance',
  application: 'application',
  bucket: 'bucket',
  object: 'object',
  database: 'database',
};

export default function Dashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.dashboard.get();
      setSummary(data);
      setError('');
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const counts = summary?.counts;
  const activity = summary?.recent_activity ?? [];

  const statCards = counts
    ? [
        {
          title: 'Compute instances',
          value: `${counts.compute_running} / ${counts.compute_total}`,
          detail: 'running / total',
          to: '/compute/instances',
          icon: Monitor,
        },
        {
          title: 'Applications',
          value: `${counts.applications_running} / ${counts.applications_total}`,
          detail: 'running / total',
          to: '/applications',
          icon: Globe,
        },
        {
          title: 'Object storage',
          value: `${counts.objects_total}`,
          detail: `${counts.buckets_total} bucket${
            counts.buckets_total === 1 ? '' : 's'
          } · ${formatBytes(counts.storage_bytes)}`,
          to: '/storage/buckets',
          icon: Upload,
        },
        {
          title: 'Databases',
          value: `${counts.databases_total}`,
          detail: 'isolated SQLite databases',
          to: '/databases',
          icon: Database,
        },
      ]
    : [];

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">CONSOLE HOME</div>
          <h1>Welcome back, {user?.name}</h1>
          <p>Explore your local cloud lab and manage its resources.</p>
        </div>
        <span className="status-chip">● Running locally</span>
      </div>

      <div className="notice">
        <strong>Local environment</strong>
        <span>
          This is an educational cloud lab. It does not create real AWS
          resources or incur cloud charges.
        </span>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Could not load dashboard data</strong>
          <span>{error}</span>
        </div>
      )}

      <h2 className="section-title">Resource summary</h2>
      <div className="summary-grid">
        {loading && !counts
          ? services.slice(0, 4).map(({ title, icon: Icon }) => (
              <div className="summary-card" key={title}>
                <div className="service-icon">
                  <Icon size={20} aria-hidden="true" />
                </div>
                <span className="summary-title">{title}</span>
                <strong className="summary-value">…</strong>
                <span className="summary-detail">Loading real resource data…</span>
              </div>
            ))
          : statCards.map(({ title, value, detail, to, icon: Icon }) => (
              <Link className="summary-card" to={to} key={title}>
                <div className="service-icon">
                  <Icon size={20} aria-hidden="true" />
                </div>
                <span className="summary-title">{title}</span>
                <strong className="summary-value">{value}</strong>
                <span className="summary-detail">{detail}</span>
              </Link>
            ))}
      </div>

      <div className="section-panel">
        <div className="panel-heading">
          <div>
            <h2>Recent activity</h2>
            <p className="muted">
              Recent actions recorded in your local account.
            </p>
          </div>
          <button
            className="secondary-button"
            type="button"
            onClick={refresh}
            disabled={loading}
          >
            <RefreshCw size={14} aria-hidden="true" />
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>

        {loading && activity.length === 0 ? (
          <div className="empty-state" role="status">
            <p>Loading activity…</p>
            <span>Reading recent resource events.</span>
          </div>
        ) : activity.length === 0 ? (
          <div className="empty-state">
            <p>No activity yet</p>
            <span>
              Create an instance, deployment, bucket, or database to start the
              timeline.
            </span>
          </div>
        ) : (
          <ul className="activity-list">
            {activity.map((item) => {
              const Icon = serviceIcons[item.service] || Monitor;
              const heading =
                actionLabels[item.action] || item.action;
              return (
                <li key={item.id}>
                  <span className="activity-icon">
                    <Icon size={15} aria-hidden="true" />
                  </span>
                  <div className="activity-copy">
                    <p>
                      {heading}{' '}
                      {resourceLabels[item.resource_type] || 'resource'}{' '}
                      <strong>{item.resource_name}</strong>
                    </p>
                    <span className="muted">
                      {formatDateTime(item.timestamp)}
                    </span>
                  </div>
                  <Link
                    className="text-link"
                    to={serviceRoutes[item.service] || '/'}
                  >
                    Open
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <h2 className="section-title">Cloud services</h2>
      <div className="service-grid">
        {services.map(({ title, desc, to, icon: Icon }) => (
          <Link className="service-card" to={to} key={title}>
            <div className="service-icon">
              <Icon size={22} aria-hidden="true" />
            </div>
            <div className="service-card-title">
              {title}
              <ArrowUpRight size={16} aria-hidden="true" />
            </div>
            <p>{desc}</p>
            <span className="text-link">Open service →</span>
          </Link>
        ))}
      </div>

      <div className="section-panel">
        <h2>Getting started</h2>
        <ol>
          <li>Open a service from the navigation menu.</li>
          <li>Create a resource and review its status.</li>
          <li>Complete the practical and verify its real local behavior.</li>
        </ol>
        <p className="muted">
          Compute, deployment, object storage, and database services all run on
          real local processes and files. Disabled actions explain what is
          standing in the way.
        </p>
      </div>
    </>
  );
}
