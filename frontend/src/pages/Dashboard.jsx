import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Activity, Eye, Smile, Hand, Plus,
  Clock, ChevronRight, BarChart2, FileText, AlertTriangle
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { listSessions } from '../api/sessions';
import Card from '../components/Card';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import AppLayout from '../components/AppLayout';
import './Dashboard.css';

const MODULE_CARDS = [
  {
    key: 'tremor',
    icon: Hand,
    title: 'Tremor Analysis',
    desc: 'FFT-based hand tremor frequency and amplitude measurement.',
    color: '#4A1942',
    path: '/assessment?module=tremor',
  },
  {
    key: 'blink',
    icon: Eye,
    title: 'Blink Analysis',
    desc: 'Eye Aspect Ratio blink detection with auto-calibration.',
    color: '#C07340',
    path: '/assessment?module=blink',
  },
  {
    key: 'asymmetry',
    icon: Smile,
    title: 'Facial Asymmetry',
    desc: 'Weighted eye, mouth, and brow asymmetry scoring.',
    color: '#7A9E8A',
    path: '/assessment?module=asymmetry',
  },
  {
    key: 'ptosis',
    icon: Activity,
    title: 'Ptosis Detection',
    desc: 'Eyelid Eye Opening Ratio versus calibrated baseline.',
    color: '#6B2C62',
    path: '/assessment?module=ptosis',
  },
];

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

function formatDuration(secs) {
  if (!secs) return '—';
  const m = Math.floor(secs / 60);
  const s = Math.round(secs % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    listSessions(0, 5)
      .then((r) => setSessions(r.data))
      .catch(() => setError('Could not load recent sessions.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppLayout>
      <div className="dashboard">
        <div className="dashboard__header">
          <div>
            <h1>Welcome back, {user?.full_name?.split(' ')[0]}</h1>
            <p>Select a module below or start a complete neurological assessment.</p>
          </div>
          <Link to="/assessment" className="dashboard__new-btn">
            <Plus size={16} strokeWidth={2} /> New Assessment
          </Link>
        </div>

        {/* Module cards */}
        <section className="dashboard__modules" aria-label="Monitoring modules">
          {MODULE_CARDS.map((m) => (
            <button
              key={m.key}
              className="module-card"
              onClick={() => navigate(m.path)}
              aria-label={`Start ${m.title}`}
            >
              <div className="module-card__icon" style={{ color: m.color }}>
                <m.icon size={26} strokeWidth={1.6} />
              </div>
              <div className="module-card__body">
                <h3>{m.title}</h3>
                <p>{m.desc}</p>
              </div>
              <ChevronRight size={18} strokeWidth={1.8} className="module-card__arrow" />
            </button>
          ))}
        </section>

        {/* Quick links */}
        <section className="dashboard__quick">
          {[
            { icon: BarChart2, label: 'View Trends', path: '/trends' },
            { icon: Clock,     label: 'History',     path: '/history' },
            { icon: FileText,  label: 'Reports',      path: '/reports' },
          ].map((q) => (
            <Link key={q.path} to={q.path} className="quick-link">
              <q.icon size={20} strokeWidth={1.8} />
              {q.label}
            </Link>
          ))}
        </section>

        {/* Recent sessions */}
        <section className="dashboard__recent">
          <div className="dashboard__section-head">
            <h2>Recent sessions</h2>
            <Link to="/history" className="dashboard__view-all">View all</Link>
          </div>

          <Card padding={false}>
            {loading ? (
              <LoadingSpinner message="Loading sessions…" />
            ) : error ? (
              <div className="dashboard__error">
                <AlertTriangle size={16} /> {error}
              </div>
            ) : sessions.length === 0 ? (
              <EmptyState
                title="No sessions yet"
                description="Complete your first assessment to see results here."
                action={<Link to="/assessment" className="hero__btn hero__btn--primary" style={{ display: 'inline-flex', gap: 6, alignItems: 'center', padding: '8px 18px', borderRadius: 8, background: 'var(--color-primary)', color: '#fff', textDecoration: 'none', fontSize: 14, fontWeight: 600 }}>Start Assessment</Link>}
              />
            ) : (
              <table className="sessions-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Type</th>
                    <th>Duration</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((s) => (
                    <tr key={s.id}>
                      <td>{formatDate(s.started_at)}</td>
                      <td className="sessions-table__type">{s.assessment_type}</td>
                      <td>{formatDuration(s.duration_seconds)}</td>
                      <td><StatusBadge status={s.status} /></td>
                      <td>
                        <Link to={`/history/${s.id}`} className="sessions-table__link">
                          View <ChevronRight size={14} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </section>
      </div>
    </AppLayout>
  );
}
