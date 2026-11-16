const LABELS = {
  running: 'Running',
  stopped: 'Stopped',
  starting: 'Starting',
  stopping: 'Stopping',
  error: 'Error',
};

export function StatusBadge({ status }) {
  const normalized = String(status || 'unknown').toLowerCase();
  return (
    <span className={`status-badge status-${normalized}`}>
      {LABELS[normalized] || status || 'Unknown'}
    </span>
  );
}
