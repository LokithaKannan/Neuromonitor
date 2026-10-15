import './MetricCard.css';

export default function MetricCard({ label, value, unit, status, icon: Icon, size = 'md' }) {
  return (
    <div className={`metric-card metric-card--${size} ${status ? `metric-card--${status}` : ''}`}>
      {Icon && (
        <div className="metric-card__icon">
          <Icon size={20} strokeWidth={1.8} />
        </div>
      )}
      <div className="metric-card__body">
        <span className="metric-card__label">{label}</span>
        <span className="metric-card__value">
          {value !== null && value !== undefined ? value : '—'}
          {unit && <span className="metric-card__unit"> {unit}</span>}
        </span>
      </div>
    </div>
  );
}
