import { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceLine
} from 'recharts';
import { BarChart2 } from 'lucide-react';
import { getTrends } from '../api/trends';
import AppLayout from '../components/AppLayout';
import Card from '../components/Card';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import ErrorMessage from '../components/ErrorMessage';
import './Trends.css';

const METRICS = [
  { key: 'tremor_frequency', label: 'Tremor Frequency',  unit: 'Hz',          color: 'var(--color-primary)' },
  { key: 'tremor_amplitude', label: 'Tremor Amplitude',  unit: 'px',          color: 'var(--color-primary-light)' },
  { key: 'blink_rate',       label: 'Blink Rate',        unit: 'blinks/min',  color: 'var(--color-accent)' },
  { key: 'asym_score',       label: 'Asymmetry Score',   unit: '',            color: 'var(--color-sage)' },
  { key: 'ptosis_fraction',  label: 'Ptosis Fraction',   unit: '%',           color: 'var(--color-error)' },
];

function fmtDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

export default function Trends() {
  const [metric, setMetric]   = useState('tremor_frequency');
  const [limit, setLimit]     = useState(20);
  const [data, setData]       = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  const selected = METRICS.find((m) => m.key === metric);

  const load = async () => {
    setLoading(true); setError('');
    try {
      const res = await getTrends(metric, limit);
      setData(res.data.data_points || []);
    } catch {
      setError('Could not load trend data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [metric, limit]); // eslint-disable-line react-hooks/exhaustive-deps

  const chartData = data.map((d) => ({
    date:  fmtDate(d.date),
    value: d.value != null ? parseFloat(d.value.toFixed(4)) : null,
    session_id: d.session_id,
  }));

  return (
    <AppLayout>
      <div className="trends-page">
        <div className="trends-page__header">
          <h1>Trends &amp; Analytics</h1>
          <p>Longitudinal measurement data across your completed monitoring sessions.</p>
        </div>

        {/* Controls */}
        <div className="trends-page__controls">
          <div className="trends-page__metric-tabs">
            {METRICS.map((m) => (
              <button
                key={m.key}
                className={`trends-page__tab ${metric === m.key ? 'active' : ''}`}
                onClick={() => setMetric(m.key)}
                style={metric === m.key ? { borderBottomColor: m.color, color: m.color } : {}}
              >
                {m.label}
              </button>
            ))}
          </div>
          <div className="trends-page__limit">
            <label htmlFor="limit-select">Sessions:</label>
            <select
              id="limit-select"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="trends-page__select"
            >
              {[10, 20, 50].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
        </div>

        <ErrorMessage message={error} />

        <Card>
          {loading ? (
            <LoadingSpinner message="Loading trend data…" />
          ) : chartData.length < 2 ? (
            <EmptyState
              icon={BarChart2}
              title="Not enough data"
              description="More monitoring sessions are needed to display this trend. Complete at least two sessions of this assessment type."
            />
          ) : (
            <div className="trends-page__chart">
              <div className="trends-page__chart-title">
                {selected?.label}
                {selected?.unit && <span> ({selected.unit})</span>}
              </div>
              <ResponsiveContainer width="100%" height={340}>
                <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-light)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={['auto', 'auto']}
                    tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                    tickLine={false}
                    axisLine={false}
                    width={50}
                  />
                  <Tooltip
                    contentStyle={{
                      fontSize: 12,
                      borderRadius: 8,
                      border: '1px solid var(--color-border)',
                      boxShadow: 'var(--shadow-md)',
                    }}
                    formatter={(v) => [
                      v != null ? `${v}${selected?.unit ? ' ' + selected.unit : ''}` : '—',
                      selected?.label,
                    ]}
                    labelFormatter={(l) => `Session date: ${l}`}
                  />
                  {/* Reference lines for blink rate normal range */}
                  {metric === 'blink_rate' && (
                    <>
                      <ReferenceLine y={10} stroke="var(--color-success)" strokeDasharray="4 2" label={{ value: 'Min normal', fontSize: 10 }} />
                      <ReferenceLine y={20} stroke="var(--color-success)" strokeDasharray="4 2" label={{ value: 'Max normal', fontSize: 10 }} />
                    </>
                  )}
                  {metric === 'asym_score' && (
                    <ReferenceLine y={0.15} stroke="var(--color-warning)" strokeDasharray="4 2" label={{ value: 'Threshold', fontSize: 10 }} />
                  )}
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke={selected?.color || 'var(--color-primary)'}
                    strokeWidth={2}
                    dot={{ r: 4, fill: selected?.color, strokeWidth: 0 }}
                    activeDot={{ r: 6 }}
                    connectNulls={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>
    </AppLayout>
  );
}
