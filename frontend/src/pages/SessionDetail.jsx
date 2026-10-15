import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, Hand, Eye, Smile, Activity,
  FileText, Download, Clock, Calendar
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, CartesianGrid
} from 'recharts';
import { getSession } from '../api/sessions';
import { generateReport } from '../api/reports';
import AppLayout from '../components/AppLayout';
import Card from '../components/Card';
import StatusBadge from '../components/StatusBadge';
import MetricCard from '../components/MetricCard';
import LoadingSpinner from '../components/LoadingSpinner';
import Button from '../components/Button';
import ErrorMessage from '../components/ErrorMessage';
import './SessionDetail.css';

function fmt(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}
function dur(secs) {
  if (!secs) return '—';
  const m = Math.floor(secs / 60);
  const s = Math.round(secs % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export default function SessionDetail() {
  const { id } = useParams();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');
  const [genPdf, setGenPdf]   = useState(false);
  const [pdfErr, setPdfErr]   = useState('');

  useEffect(() => {
    getSession(id)
      .then((r) => setSession(r.data))
      .catch(() => setError('Could not load session details.'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleDownloadPdf = async () => {
    setGenPdf(true); setPdfErr('');
    try {
      const res = await generateReport(id);
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `nms_report_session_${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setPdfErr('Failed to generate PDF report.');
    } finally {
      setGenPdf(false);
    }
  };

  if (loading) return <AppLayout><LoadingSpinner message="Loading session…" size="lg" /></AppLayout>;
  if (error)   return <AppLayout><div style={{ padding: '2rem' }}><ErrorMessage message={error} /></div></AppLayout>;
  if (!session) return null;

  const tremor    = session.tremor_results?.[0];
  const blink     = session.blink_results?.[0];
  const asymmetry = session.asymmetry_results?.[0];
  const ptosis    = session.ptosis_results?.[0];

  return (
    <AppLayout>
      <div className="session-detail">
        {/* Header */}
        <div className="session-detail__header">
          <Link to="/history" className="session-detail__back">
            <ArrowLeft size={16} strokeWidth={2} /> Back to History
          </Link>
          <div className="session-detail__title-row">
            <div>
              <h1>Session Results</h1>
              <div className="session-detail__meta">
                <span><Calendar size={13} strokeWidth={2} /> {fmt(session.started_at)}</span>
                <span><Clock size={13} strokeWidth={2} /> {dur(session.duration_seconds)}</span>
                <StatusBadge status={session.status} />
                <span className="session-detail__type">{session.assessment_type}</span>
              </div>
            </div>
            <div className="session-detail__actions">
              {pdfErr && <ErrorMessage message={pdfErr} />}
              <Button variant="outline" size="sm" loading={genPdf} onClick={handleDownloadPdf}>
                <Download size={15} strokeWidth={2} /> Download PDF
              </Button>
            </div>
          </div>
        </div>

        {/* Results grid */}
        <div className="session-detail__grid">

          {/* Tremor */}
          {tremor && (
            <Card className="session-detail__card">
              <div className="session-detail__card-header">
                <Hand size={18} strokeWidth={1.8} style={{ color: 'var(--color-primary)' }} />
                <h2>Tremor Analysis</h2>
              </div>
              <div className="session-detail__metrics">
                <MetricCard label="Max Frequency"   value={tremor.max_frequency_hz?.toFixed(2)}  unit="Hz"  />
                <MetricCard label="Mean Amplitude"  value={tremor.mean_amplitude_px?.toFixed(2)} unit="px"  />
                <MetricCard label="Dominant Severity" value={tremor.dominant_severity || '—'} />
                <MetricCard label="Frames with Hand"  value={tremor.frames_with_hand ?? '—'} />
              </div>
              {tremor.time_series?.length > 1 && (
                <div className="session-detail__chart-wrap">
                  <h4>Frequency over session</h4>
                  <ResponsiveContainer width="100%" height={160}>
                    <LineChart data={tremor.time_series}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-light)" />
                      <XAxis dataKey="timestamp" hide />
                      <YAxis domain={['auto','auto']} width={40} tick={{ fontSize: 10 }} />
                      <Tooltip formatter={(v) => [v?.toFixed(3), 'Freq (Hz)']} contentStyle={{ fontSize: 11 }} />
                      <Line type="monotone" dataKey="frequency" stroke="var(--color-primary)" dot={false} strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          )}

          {/* Blink */}
          {blink && (
            <Card className="session-detail__card">
              <div className="session-detail__card-header">
                <Eye size={18} strokeWidth={1.8} style={{ color: 'var(--color-accent)' }} />
                <h2>Blink Analysis</h2>
              </div>
              <div className="session-detail__metrics">
                <MetricCard label="Total Blinks"     value={blink.total_blinks ?? '—'} />
                <MetricCard label="Blink Rate"       value={blink.blink_rate?.toFixed(1)} unit="/min" />
                <MetricCard label="Rate Status"      value={blink.rate_status || '—'}
                  status={blink.rate_status === 'normal' ? 'success' : blink.rate_status ? 'warning' : undefined} />
                <MetricCard label="Abnormal Blinks"  value={blink.abnormal_blink_count ?? '—'} />
                <MetricCard label="Duration Std Dev" value={blink.duration_std?.toFixed(4)} unit="s" />
              </div>
              {blink.abnormality_flags?.length > 0 && (
                <div className="session-detail__flags">
                  <h4>Observations</h4>
                  <ul>
                    {blink.abnormality_flags.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </div>
              )}
              {blink.blink_log?.length > 1 && (
                <div className="session-detail__chart-wrap">
                  <h4>Blink durations</h4>
                  <ResponsiveContainer width="100%" height={160}>
                    <BarChart data={blink.blink_log}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-light)" />
                      <XAxis dataKey="blink_id" tick={{ fontSize: 10 }} />
                      <YAxis domain={[0, 'auto']} width={40} tick={{ fontSize: 10 }} />
                      <Tooltip formatter={(v) => [v?.toFixed(3) + ' s', 'Duration']} contentStyle={{ fontSize: 11 }} />
                      <Bar dataKey="duration" fill="var(--color-accent)" radius={[2,2,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          )}

          {/* Asymmetry */}
          {asymmetry && (
            <Card className="session-detail__card">
              <div className="session-detail__card-header">
                <Smile size={18} strokeWidth={1.8} style={{ color: 'var(--color-sage)' }} />
                <h2>Facial Asymmetry</h2>
              </div>
              <div className="session-detail__metrics">
                <MetricCard label="Avg Asym Score"     value={asymmetry.avg_asym_score?.toFixed(4)} />
                <MetricCard label="Asymmetry Events"   value={asymmetry.asym_events_count ?? '—'} />
                <MetricCard label="Microexpressions"   value={asymmetry.micro_events_count ?? '—'} />
                <MetricCard label="Threshold Used"     value={asymmetry.threshold_used?.toFixed(2)} />
              </div>
              {asymmetry.asym_events?.length > 0 && (
                <div className="session-detail__flags">
                  <h4>Asymmetry events</h4>
                  <ul>
                    {asymmetry.asym_events.map((e, i) => (
                      <li key={i}>
                        Duration {e.duration_s?.toFixed(2)}s · Max score {e.max_score?.toFixed(4)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          )}

          {/* Ptosis */}
          {ptosis && (
            <Card className="session-detail__card">
              <div className="session-detail__card-header">
                <Activity size={18} strokeWidth={1.8} style={{ color: 'var(--color-primary-light)' }} />
                <h2>Ptosis Detection</h2>
              </div>
              <div className="session-detail__metrics">
                <MetricCard label="Ptosis Detected"
                  value={ptosis.ptosis_alerted ? 'Yes' : 'No'}
                  status={ptosis.ptosis_alerted ? 'error' : 'success'} />
                <MetricCard label="Detection Fraction"
                  value={ptosis.ptosis_fraction != null ? (ptosis.ptosis_fraction * 100).toFixed(1) : '—'} unit="%" />
                <MetricCard label="Mean Left EOR"   value={ptosis.mean_left_ratio?.toFixed(4)} />
                <MetricCard label="Mean Right EOR"  value={ptosis.mean_right_ratio?.toFixed(4)} />
                <MetricCard label="Baseline Left"   value={ptosis.base_left?.toFixed(4)} />
                <MetricCard label="Baseline Right"  value={ptosis.base_right?.toFixed(4)} />
              </div>
            </Card>
          )}

          {/* Nothing recorded */}
          {!tremor && !blink && !asymmetry && !ptosis && (
            <div className="session-detail__empty">
              <FileText size={40} strokeWidth={1.2} />
              <p>No result data was recorded for this session.</p>
            </div>
          )}

        </div>

        {/* Disclaimer */}
        <p className="session-detail__disclaimer">
          These measurements are provided for monitoring and screening purposes only.
          They do not constitute a medical diagnosis. Consult a qualified healthcare provider
          for clinical evaluation.
        </p>
      </div>
    </AppLayout>
  );
}
