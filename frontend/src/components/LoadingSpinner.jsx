import './LoadingSpinner.css';

export default function LoadingSpinner({ message = 'Loading…', size = 'md' }) {
  return (
    <div className={`loading loading--${size}`} role="status" aria-live="polite">
      <div className="loading__ring" aria-hidden="true">
        <div /><div /><div /><div />
      </div>
      {message && <span className="loading__text">{message}</span>}
    </div>
  );
}
