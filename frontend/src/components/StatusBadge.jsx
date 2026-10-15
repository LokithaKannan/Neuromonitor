import './StatusBadge.css';

const STATUS_MAP = {
  normal:    { label: 'Normal',    cls: 'success' },
  low:       { label: 'Low',       cls: 'warning' },
  high:      { label: 'High',      cls: 'warning' },
  warning:   { label: 'Warning',   cls: 'warning' },
  abnormal:  { label: 'Abnormal',  cls: 'error' },
  error:     { label: 'Error',     cls: 'error' },
  active:    { label: 'Active',    cls: 'info' },
  completed: { label: 'Completed', cls: 'success' },
  aborted:   { label: 'Aborted',   cls: 'error' },
  detected:  { label: 'Detected',  cls: 'error' },
  none:      { label: 'None',      cls: 'success' },
};

export default function StatusBadge({ status, label }) {
  const map = STATUS_MAP[status?.toLowerCase()] || { label: status || 'Unknown', cls: 'neutral' };
  return (
    <span className={`status-badge status-badge--${map.cls}`}>
      {label || map.label}
    </span>
  );
}
