import { Inbox } from 'lucide-react';
import './EmptyState.css';

export default function EmptyState({ icon: Icon = Inbox, title, description, action }) {
  return (
    <div className="empty-state">
      <div className="empty-state__icon">
        <Icon size={40} strokeWidth={1.4} />
      </div>
      {title && <h3 className="empty-state__title">{title}</h3>}
      {description && <p className="empty-state__desc">{description}</p>}
      {action && <div className="empty-state__action">{action}</div>}
    </div>
  );
}
