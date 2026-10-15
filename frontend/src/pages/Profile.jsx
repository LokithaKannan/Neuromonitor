import { useState } from 'react';
import { User, Mail, Lock, Save } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { updateProfile } from '../api/profile';
import AppLayout from '../components/AppLayout';
import Card from '../components/Card';
import InputField from '../components/InputField';
import Button from '../components/Button';
import ErrorMessage from '../components/ErrorMessage';
import './Profile.css';

export default function Profile() {
  const { user, setUser } = useAuth();

  const [nameForm, setNameForm] = useState({ full_name: user?.full_name || '' });
  const [emailForm, setEmailForm] = useState({ email: user?.email || '' });
  const [pwForm, setPwForm]     = useState({ current_password: '', new_password: '', confirm: '' });

  const [nameErr,  setNameErr]  = useState('');
  const [emailErr, setEmailErr] = useState('');
  const [pwErr,    setPwErr]    = useState({});
  const [apiErr,   setApiErr]   = useState('');
  const [success,  setSuccess]  = useState('');

  const [savingName,  setSavingName]  = useState(false);
  const [savingEmail, setSavingEmail] = useState(false);
  const [savingPw,    setSavingPw]    = useState(false);

  const saveField = async (payload, setSaving, clearErr) => {
    setSaving(true); clearErr(''); setApiErr(''); setSuccess('');
    try {
      const res = await updateProfile(payload);
      setUser(res.data);
      setSuccess('Saved successfully.');
    } catch (err) {
      const msg = err.response?.data?.detail;
      setApiErr(typeof msg === 'string' ? msg : 'Update failed.');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveName = () => {
    if (!nameForm.full_name.trim() || nameForm.full_name.trim().length < 2) {
      setNameErr('Name must be at least 2 characters'); return;
    }
    saveField({ full_name: nameForm.full_name.trim() }, setSavingName, setNameErr);
  };

  const handleSaveEmail = () => {
    if (!emailForm.email.trim()) { setEmailErr('Email is required'); return; }
    saveField({ email: emailForm.email.trim() }, setSavingEmail, setEmailErr);
  };

  const handleSavePassword = () => {
    const errs = {};
    if (!pwForm.current_password) errs.current_password = 'Current password required';
    if (!pwForm.new_password || pwForm.new_password.length < 8) errs.new_password = 'Minimum 8 characters';
    if (!/[A-Z]/.test(pwForm.new_password)) errs.new_password = 'Must include uppercase letter';
    if (!/[0-9]/.test(pwForm.new_password)) errs.new_password = 'Must include a digit';
    if (pwForm.confirm !== pwForm.new_password) errs.confirm = 'Passwords do not match';
    if (Object.keys(errs).length) { setPwErr(errs); return; }
    saveField(
      { current_password: pwForm.current_password, new_password: pwForm.new_password },
      setSavingPw,
      () => setPwErr({}),
    );
    setPwForm({ current_password: '', new_password: '', confirm: '' });
  };

  return (
    <AppLayout>
      <div className="profile-page">
        <div className="profile-page__header">
          <h1>Profile &amp; Settings</h1>
          <p>Manage your account information and password.</p>
        </div>

        {apiErr && <ErrorMessage message={apiErr} />}
        {success && <div className="profile-page__success">{success}</div>}

        <div className="profile-page__grid">

          {/* Name */}
          <Card>
            <div className="profile-section">
              <div className="profile-section__heading">
                <User size={18} strokeWidth={1.8} />
                <h2>Display Name</h2>
              </div>
              <InputField
                label="Full Name"
                name="full_name"
                value={nameForm.full_name}
                onChange={(e) => { setNameForm({ full_name: e.target.value }); setNameErr(''); }}
                error={nameErr}
                autoComplete="name"
              />
              <Button variant="primary" size="sm" loading={savingName} onClick={handleSaveName}>
                <Save size={14} /> Save Name
              </Button>
            </div>
          </Card>

          {/* Email */}
          <Card>
            <div className="profile-section">
              <div className="profile-section__heading">
                <Mail size={18} strokeWidth={1.8} />
                <h2>Email Address</h2>
              </div>
              <InputField
                label="Email"
                name="email"
                type="email"
                value={emailForm.email}
                onChange={(e) => { setEmailForm({ email: e.target.value }); setEmailErr(''); }}
                error={emailErr}
                autoComplete="email"
              />
              <Button variant="primary" size="sm" loading={savingEmail} onClick={handleSaveEmail}>
                <Save size={14} /> Save Email
              </Button>
            </div>
          </Card>

          {/* Password */}
          <Card>
            <div className="profile-section">
              <div className="profile-section__heading">
                <Lock size={18} strokeWidth={1.8} />
                <h2>Change Password</h2>
              </div>
              <InputField
                label="Current Password"
                name="current_password"
                type="password"
                value={pwForm.current_password}
                onChange={(e) => setPwForm((f) => ({ ...f, current_password: e.target.value }))}
                error={pwErr.current_password}
                autoComplete="current-password"
              />
              <InputField
                label="New Password"
                name="new_password"
                type="password"
                value={pwForm.new_password}
                onChange={(e) => setPwForm((f) => ({ ...f, new_password: e.target.value }))}
                error={pwErr.new_password}
                autoComplete="new-password"
                hint="Minimum 8 chars, one uppercase, one digit."
              />
              <InputField
                label="Confirm New Password"
                name="confirm"
                type="password"
                value={pwForm.confirm}
                onChange={(e) => setPwForm((f) => ({ ...f, confirm: e.target.value }))}
                error={pwErr.confirm}
                autoComplete="new-password"
              />
              <Button variant="primary" size="sm" loading={savingPw} onClick={handleSavePassword}>
                <Save size={14} /> Update Password
              </Button>
            </div>
          </Card>

        </div>
      </div>
    </AppLayout>
  );
}
