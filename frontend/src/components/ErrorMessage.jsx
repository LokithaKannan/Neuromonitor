import { AlertCircle } from 'lucide-react';
import './ErrorMessage.css';

export default function ErrorMessage({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="error-msg" role="alert">
      <AlertCircle size={16} strokeWidth={2} />
      <span>{message}</span>
      {onRetry && (
        <button className="error-msg__retry" onClick={onRetry}>Retry</button>
      )}
    </div>
  );
}
