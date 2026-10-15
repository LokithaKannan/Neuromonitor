import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Download, ChevronRight, AlertTriangle } from 'lucide-react';
import { listSessions } from '../api/sessions';
import { generateReport } from '../api/reports';
import AppLayout from '../components/AppLayout';
import Card from '../components/Card';
import StatusBadge from '../components/StatusBadge';
import Button from '../components/Button';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import './Reports.css';

function fmt(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}
function dur(secs) {
  if (!secs) return '—';
  const m = Math.floor(secs / 60); const s = Math.round(secs % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export default function Reports() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');
  const [downloading, setDownloading] = useState({});
  const [dlErrors, setDlErrors]       = useState({});

  useEffect(() => {
    listSessions(0, 50)
      .then((r) => setSessions(r.data.filter((s) => s.status === 'completed')))
      .catch(() => setError('Could not load sessions.'))
      .finally(() => setLoading(false));
  }, []);

  const handleDownload = async (sessionId) => {
    setDownloading((d) => ({ ...d, [sessionId]: true }));
    setDlErrors((e) => ({ ...e, [sessionId]: '' }));
    try {
      const res = await generateReport(sessionId);
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `nms_report_session_${sessionId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setDlErrors((e) => ({ ...e, [sessionId]: 'PDF generation failed.' }));
    } finally {
      setDownloading((d) => ({ ...d, [sessionId]: false }));
    }
  };

  return (
    <AppLayout>
      <div className="reports-page">
        <div className="reports-page__header">
          <h1>Reports</h1>
          <p>Download PDF reports for any completed monitoring session.</p>
        </div>

        {error && (
          <div className="reports-page__error">
            <AlertTriangle size={16} /> {error}
          </div>
        )}

        <Card padding={false}>
          {loading ? (
            <LoadingSpinner message="Loading sessions…" />
          ) : sessions.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No completed sessions"
              description="Complete at least one monitoring assessment to generate a report."
              action={<Link to="/assessment" className="btn btn--primary btn--md">Start Assessment</Link>}
            />
          ) : (
            <table className="reports-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Assessment Type</th>
                  <th>Duration</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.id}>
                    <td>{fmt(s.started_at)}</td>
                    <td className="reports-table__type">{s.assessment_type}</td>
                    <td>{dur(s.duration_seconds)}</td>
                    <td><StatusBadge status={s.status} /></td>
                    <td>
                      <div className="reports-table__actions">
                        <Link to={`/history/${s.id}`} className="reports-table__link">
                          View <ChevronRight size={14} />
                        </Link>
                        <Button
                          variant="outline"
                          size="sm"
                          loading={downloading[s.id]}
                          onClick={() => handleDownload(s.id)}
                        >
                          <Download size={13} strokeWidth={2} /> PDF
                        </Button>
                        {dlErrors[s.id] && (
                          <span className="reports-table__err">{dlErrors[s.id]}</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </AppLayout>
  );
}
