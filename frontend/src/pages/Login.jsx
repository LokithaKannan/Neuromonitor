import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Activity, ArrowLeft } from 'lucide-react';
import { login } from '../api/auth';
import { getMe } from '../api/auth';
import { useAuth } from '../contexts/AuthContext';
import InputField from '../components/InputField';
import Button from '../components/Button';
import ErrorMessage from '../components/ErrorMessage';
import './Auth.css';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { loginUser } = useAuth();

  const from = location.state?.from?.pathname || '/dashboard';

  const [form, setForm] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState('');
  const [loading, setLoading] = useState(false);

  const set = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    setErrors((er) => ({ ...er, [field]: '' }));
    setApiError('');
  };

  const validate = () => {
    const errs = {};
    if (!form.email.trim()) errs.email = 'Email is required';
    if (!form.password) errs.password = 'Password is required';
    return errs;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setLoading(true);
    setApiError('');
    try {
      const res = await login(form);
      // Store token BEFORE calling getMe so the axios interceptor can attach it
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('refresh_token', res.data.refresh_token);
      const meRes = await getMe();
      loginUser(res.data, meRes.data);
      navigate(from, { replace: true });
    } catch (err) {
      // Clean up tokens if anything fails
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      const msg = err.response?.data?.detail;
      if (typeof msg === 'string') setApiError(msg);
      else setApiError('Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <Link to="/" className="auth-back">
        <ArrowLeft size={15} strokeWidth={2} /> Back to home
      </Link>
      <div className="auth-card">
        <div className="auth-card__header">
          <div className="auth-card__logo">
            <Activity size={24} strokeWidth={1.8} />
          </div>
          <h1 className="auth-card__title">Welcome back</h1>
          <p className="auth-card__sub">Sign in to continue your neurological monitoring.</p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="auth-form">
          <ErrorMessage message={apiError} />

          <InputField
            label="Email Address"
            name="email"
            type="email"
            value={form.email}
            onChange={set('email')}
            error={errors.email}
            placeholder="jane@example.com"
            autoComplete="email"
            required
          />

          <InputField
            label="Password"
            name="password"
            type="password"
            value={form.password}
            onChange={set('password')}
            error={errors.password}
            placeholder="Your password"
            autoComplete="current-password"
            required
          />

          <Button type="submit" variant="primary" size="lg" loading={loading} className="auth-btn">
            Sign In
          </Button>
        </form>

        <p className="auth-card__switch">
          Don't have an account? <Link to="/signup">Create one</Link>
        </p>
      </div>
    </div>
  );
}
