const LABELS = {
  running: 'Running',
  stopped: 'Stopped',
  starting: 'Starting',
  stopping: 'Stopping',
  error: 'Error',
  active: 'Active',
  disabled: 'Disabled',
  available: 'Available',
};

export function StatusBadge({ status }) {
  const normalized = String(status || 'unknown').toLowerCase();
  return (
    <span className={`status-badge status-${normalized}`}>
      {LABELS[normalized] || status || 'Unknown'}
    </span>
  );
}
