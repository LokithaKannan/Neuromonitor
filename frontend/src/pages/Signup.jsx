import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Activity, ArrowLeft } from 'lucide-react';
import { signup } from '../api/auth';
import { getMe } from '../api/auth';
import { useAuth } from '../contexts/AuthContext';
import InputField from '../components/InputField';
import Button from '../components/Button';
import ErrorMessage from '../components/ErrorMessage';
import './Auth.css';

function passwordStrength(pw) {
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 1) return { level: 'weak',   label: 'Weak' };
  if (score === 2) return { level: 'fair',   label: 'Fair' };
  if (score === 3) return { level: 'good',   label: 'Good' };
  return               { level: 'strong', label: 'Strong' };
}

export default function Signup() {
  const navigate = useNavigate();
  const { loginUser } = useAuth();

  const [form, setForm] = useState({ full_name: '', email: '', password: '', confirm_password: '' });
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
    if (!form.full_name.trim() || form.full_name.trim().length < 2)
      errs.full_name = 'Full name must be at least 2 characters';
    if (!form.email.trim()) errs.email = 'Email is required';
    if (form.password.length < 8) errs.password = 'Password must be at least 8 characters';
    if (!/[A-Z]/.test(form.password)) errs.password = 'Password must contain an uppercase letter';
    if (!/[0-9]/.test(form.password)) errs.password = 'Password must contain a digit';
    if (form.confirm_password !== form.password) errs.confirm_password = 'Passwords do not match';
    return errs;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setLoading(true);
    setApiError('');
    try {
      const res = await signup(form);
      // Store token BEFORE calling getMe so the axios interceptor can attach it
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('refresh_token', res.data.refresh_token);
      const meRes = await getMe();
      loginUser(res.data, meRes.data);
      navigate('/dashboard');
    } catch (err) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      const msg = err.response?.data?.detail;
      if (typeof msg === 'string') setApiError(msg);
      else if (Array.isArray(msg)) setApiError(msg.map((e) => e.msg).join(', '));
      else setApiError('Signup failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const strength = form.password ? passwordStrength(form.password) : null;

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
          <h1 className="auth-card__title">Create your account</h1>
          <p className="auth-card__sub">Start monitoring neurological indicators from your webcam.</p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="auth-form">
          <ErrorMessage message={apiError} />

          <InputField
            label="Full Name"
            name="full_name"
            value={form.full_name}
            onChange={set('full_name')}
            error={errors.full_name}
            placeholder="Jane Smith"
            autoComplete="name"
            required
          />

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
            placeholder="Minimum 8 characters"
            autoComplete="new-password"
            required
            hint="Must include an uppercase letter and a digit."
          />

          {strength && (
            <div className="password-strength">
              <div className={`password-strength__bar password-strength__bar--${strength.level}`} />
              <span className={`password-strength__label password-strength__label--${strength.level}`}>
                {strength.label}
              </span>
            </div>
          )}

          <InputField
            label="Confirm Password"
            name="confirm_password"
            type="password"
            value={form.confirm_password}
            onChange={set('confirm_password')}
            error={errors.confirm_password}
            placeholder="Repeat your password"
            autoComplete="new-password"
            required
          />

          <Button type="submit" variant="primary" size="lg" loading={loading} className="auth-btn">
            Create Account
          </Button>
        </form>

        <p className="auth-card__switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
