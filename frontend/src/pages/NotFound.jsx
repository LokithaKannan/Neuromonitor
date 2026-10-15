import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import AppLayout from '../components/AppLayout';
import './NotFound.css';

export default function NotFound() {
  const { user } = useAuth();
  return (
    <AppLayout>
      <div className="not-found">
        <span className="not-found__code">404</span>
        <h1>Page not found</h1>
        <p>The page you are looking for does not exist or has been moved.</p>
        <Link to={user ? '/dashboard' : '/'} className="not-found__btn">
          {user ? 'Back to Dashboard' : 'Back to Home'}
        </Link>
      </div>
    </AppLayout>
  );
}
