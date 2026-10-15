import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Clock, ChevronRight, Filter, AlertTriangle } from 'lucide-react';
import { listSessions } from '../api/sessions';
import AppLayout from '../components/AppLayout';
import Card from '../components/Card';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import Button from '../components/Button';
import './History.css';

const TYPES = ['all', 'complete', 'tremor', 'blink', 'asymmetry', 'ptosis'];

function fmt(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}
function dur(secs) {
  if (!secs) return '—';
  const m = Math.floor(secs / 60);
  const s = Math.round(secs % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export default function History() {
  const [sessions, setSessions]   = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState('');
  const [filter, setFilter]       = useState('all');
  const [page, setPage]           = useState(0);
  const [hasMore, setHasMore]     = useState(true);
  const LIMIT = 20;

  const load = async (reset = false) => {
    const skip = reset ? 0 : page * LIMIT;
    setLoading(true);
    try {
      const res = await listSessions(skip, LIMIT);
      const data = res.data;
      if (reset) setSessions(data);
      else setSessions((prev) => [...prev, ...data]);
      if (data.length < LIMIT) setHasMore(false);
      if (reset) setPage(1);
      else setPage((p) => p + 1);
    } catch {
      setError('Could not load session history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(true); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const filtered = filter === 'all'
    ? sessions
    : sessions.filter((s) => s.assessment_type === filter);

  return (
    <AppLayout>
      <div className="history-page">
        <div className="history-page__header">
          <div>
            <h1>Session History</h1>
            <p>All your past neurological monitoring sessions.</p>
          </div>
          <Link to="/assessment" className="history-page__new-btn">+ New Assessment</Link>
        </div>

        {/* Filter */}
        <div className="history-page__filters">
          <Filter size={14} strokeWidth={2} />
          {TYPES.map((t) => (
            <button
              key={t}
              className={`history-page__filter-btn ${filter === t ? 'active' : ''}`}
              onClick={() => setFilter(t)}
            >
              {t === 'all' ? 'All Types' : t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {error && (
          <div className="history-page__error">
            <AlertTriangle size={16} /> {error}
          </div>
        )}

        <Card padding={false}>
          {loading && sessions.length === 0 ? (
            <LoadingSpinner message="Loading history…" />
          ) : filtered.length === 0 ? (
            <EmptyState
              title="No sessions found"
              description={filter === 'all'
                ? 'You have not completed any monitoring sessions yet.'
                : `No ${filter} sessions found.`}
              action={
                <Link to="/assessment" className="btn btn--primary btn--md">
                  Start Assessment
                </Link>
              }
            />
          ) : (
            <>
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Date &amp; Time</th>
                    <th>Assessment Type</th>
                    <th>Duration</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s) => (
                    <tr key={s.id}>
                      <td>{fmt(s.started_at)}</td>
                      <td className="history-table__type">{s.assessment_type}</td>
                      <td>{dur(s.duration_seconds)}</td>
                      <td><StatusBadge status={s.status} /></td>
                      <td>
                        <Link to={`/history/${s.id}`} className="history-table__link">
                          View Results <ChevronRight size={14} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {hasMore && (
                <div className="history-page__load-more">
                  <Button variant="outline" size="sm" loading={loading} onClick={() => load(false)}>
                    Load more
                  </Button>
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </AppLayout>
  );
}
