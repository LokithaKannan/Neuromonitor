import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  StopCircle, Wifi, WifiOff, Clock,
  Hand, Eye, Smile, Activity, AlertTriangle, Camera
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import { useCamera } from '../hooks/useCamera';
import { useMonitoringWS } from '../hooks/useMonitoringWS';
import {
  saveTremorResult, saveBlinkResult,
  saveAsymmetryResult, savePtosisResult, completeSession
} from '../api/sessions';
import Button from '../components/Button';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';
import AppLayout from '../components/AppLayout';
import './Monitoring.css';

const FRAME_INTERVAL_MS = 100; // capture ~10 fps
const MAX_CHART_POINTS  = 60;

const MODULE_ICON = { tremor: Hand, blink: Eye, asymmetry: Smile, ptosis: Activity };

function useElapsed(running) {
  const [elapsed, setElapsed] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    if (running) {
      ref.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    } else {
      clearInterval(ref.current);
    }
    return () => clearInterval(ref.current);
  }, [running]);
  const reset = () => setElapsed(0);
  return { elapsed, reset };
}

function fmt(secs) {
  const m = Math.floor(secs / 60).toString().padStart(2, '0');
  const s = (secs % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

export default function Monitoring() {
  const { sessionId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const modulesParam = searchParams.get('modules') || 'tremor,blink,asymmetry,ptosis';
  const modules = modulesParam.split(',').filter(Boolean);

  // ── Camera ──
  const { videoRef, attachRef, status: camStatus, error: camError, startCamera, stopCamera, captureFrame } = useCamera();

  // ── State ──
  const [phase, setPhase] = useState('connecting'); // connecting | calibrating | monitoring | stopping | done
  const [wsError, setWsError] = useState('');
  const [frameCount, setFrameCount] = useState(0);

  // Per-module live metrics
  const [tremorData,    setTremorData]    = useState(null);
  const [blinkData,     setBlinkData]     = useState(null);
  const [asymmetryData, setAsymmetryData] = useState(null);
  const [ptosisData,    setPtosisData]    = useState(null);

  // Chart series (rolling window)
  const [tremorChart,    setTremorChart]    = useState([]);
  const [blinkChart,     setBlinkChart]     = useState([]);
  const [asymmetryChart, setAsymmetryChart] = useState([]);

  const intervalRef = useRef(null);
  const summaryRef  = useRef(null);

  const { elapsed, reset: resetElapsed } = useElapsed(phase === 'monitoring');

  // ── Phase ref to avoid stale closure in handleResult ──
  const phaseRef = useRef(phase);
  useEffect(() => { phaseRef.current = phase; }, [phase]);

  // ── WebSocket callbacks ──
  const handleResult = useCallback((msg) => {
    setFrameCount((c) => c + 1);
    const mods = msg.data?.modules || {};

    if (mods.tremor) {
      setTremorData(mods.tremor);
      if (!mods.tremor.is_calibrating) {
        setTremorChart((prev) => {
          const label = fmt(prev.length);
          const next = [...prev, { t: label, freq: mods.tremor.frequency, amp: mods.tremor.amplitude }];
          return next.slice(-MAX_CHART_POINTS);
        });
      }
    }
    if (mods.blink) {
      setBlinkData(mods.blink);
      if (!mods.blink.is_calibrating) {
        setBlinkChart((prev) => {
          const label = fmt(prev.length);
          const next = [...prev, { t: label, ear: mods.blink.ear, rate: mods.blink.blink_rate }];
          return next.slice(-MAX_CHART_POINTS);
        });
      }
    }
    if (mods.asymmetry) {
      setAsymmetryData(mods.asymmetry);
      if (!mods.asymmetry.is_calibrating) {
        setAsymmetryChart((prev) => {
          const label = fmt(prev.length);
          const next = [...prev, { t: label, score: mods.asymmetry.asym_score }];
          return next.slice(-MAX_CHART_POINTS);
        });
      }
    }
    if (mods.ptosis) {
      setPtosisData(mods.ptosis);
    }

    // Move from calibrating → monitoring once all active modules are calibrated
    if (phaseRef.current === 'calibrating') {
      const allCalibrated = modules.every((m) => {
        const d = mods[m];
        return d && !d.is_calibrating;
      });
      if (allCalibrated) setPhase('monitoring');
    }
  }, [modules]);

  const handleSummary = useCallback(async (summary) => {
    summaryRef.current = summary;
    setPhase('done');
    stopCamera();
    clearInterval(intervalRef.current);

    // Persist results to DB
    try {
      const s = summary.summaries || {};
      const id = parseInt(sessionId, 10);
      if (s.tremor)    await saveTremorResult(id,    { max_frequency: s.tremor.max_frequency,    mean_amplitude: s.tremor.mean_amplitude,    dominant_severity: s.tremor.dominant_severity,    frames_with_hand: s.tremor.frames_with_hand, total_frames: s.tremor.total_frames, time_series: s.tremor.time_series });
      if (s.blink)     await saveBlinkResult(id,     s.blink);
      if (s.asymmetry) await saveAsymmetryResult(id, s.asymmetry);
      if (s.ptosis)    await savePtosisResult(id,    s.ptosis);
      await completeSession(id);
    } catch (err) {
      console.error('Failed to save results:', err);
    }

    navigate(`/history/${sessionId}`);
  }, [sessionId, navigate, stopCamera]);

  const handleWsError = useCallback((msg) => {
    setWsError(msg || 'Connection error');
  }, []);

  // ── WebSocket ──
  const { connect, sendFrame, sendStop, connected, connecting } = useMonitoringWS({
    sessionId,
    modules,
    onResult: handleResult,
    onSummary: handleSummary,
    onError: handleWsError,
  });

  // ── On mount: start camera then connect WS ──
  useEffect(() => {
    let cancelled = false;
    (async () => {
      await startCamera();
      if (cancelled) return;
      connect();
      setPhase('calibrating');
    })();
    return () => {
      cancelled = true;
      clearInterval(intervalRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Frame capture loop ──
  useEffect(() => {
    if ((phase === 'calibrating' || phase === 'monitoring') && connected) {
      intervalRef.current = setInterval(() => {
        const frame = captureFrame(0.6);
        if (frame) sendFrame(frame, modules);
      }, FRAME_INTERVAL_MS);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [phase, connected, captureFrame, sendFrame, modules]);

  const handleStop = () => {
    setPhase('stopping');
    clearInterval(intervalRef.current);
    sendStop();
  };

  // ── Camera status label ──
  const camStatusLabel = {
    idle:        'Camera idle',
    requesting:  'Requesting camera…',
    active:      'Camera active',
    denied:      'Camera permission denied',
    unavailable: 'No camera found',
    error:       'Camera error',
  }[camStatus] || 'Camera unknown';

  const isCalibrating = modules.some((m) => {
    const d = { tremor: tremorData, blink: blinkData, asymmetry: asymmetryData, ptosis: ptosisData }[m];
    return d?.is_calibrating;
  });

  return (
    <AppLayout>
      <div className="monitoring">

        {/* ── Top bar ── */}
        <div className="monitoring__topbar">
          <div className="monitoring__topbar-left">
            <span className="monitoring__status-dot" data-status={phase} />
            <span className="monitoring__phase-label">
              {phase === 'calibrating' ? 'Calibrating…'
               : phase === 'monitoring' ? 'Monitoring'
               : phase === 'stopping'   ? 'Finishing…'
               : phase === 'connecting' ? 'Connecting…'
               : 'Done'}
            </span>
            {(phase === 'calibrating' || phase === 'monitoring') && (
              <span className="monitoring__elapsed">
                <Clock size={14} strokeWidth={2} /> {fmt(elapsed)}
              </span>
            )}
          </div>
          <div className="monitoring__topbar-right">
            <span className={`monitoring__ws-indicator ${connected ? 'online' : 'offline'}`}>
              {connected
                ? <><Wifi size={14} strokeWidth={2} /> Connected</>
                : <><WifiOff size={14} strokeWidth={2} /> {connecting ? 'Connecting…' : 'Disconnected'}</>
              }
            </span>
            <Button
              variant="danger"
              size="sm"
              disabled={phase === 'stopping' || phase === 'done'}
              loading={phase === 'stopping'}
              onClick={handleStop}
            >
              <StopCircle size={15} strokeWidth={2} /> Stop
            </Button>
          </div>
        </div>

        {/* ── Errors ── */}
        {(wsError || camError) && (
          <div className="monitoring__error-banner">
            <AlertTriangle size={16} strokeWidth={2} />
            {wsError || camError}
          </div>
        )}

        {/* ── Main grid ── */}
        <div className="monitoring__grid">

          {/* LEFT — Camera feed */}
          <div className="monitoring__camera-panel">
            <div className="monitoring__camera-box">
              {camStatus === 'active' ? (
                <video
                  ref={attachRef}
                  autoPlay playsInline muted
                  className="monitoring__video"
                  aria-label="Live camera feed"
                />
              ) : (
                <div className="monitoring__camera-placeholder">
                  <Camera size={40} strokeWidth={1.4} />
                  <span>{camStatusLabel}</span>
                </div>
              )}
              {isCalibrating && (
                <div className="monitoring__calibrating-overlay">
                  <span className="monitoring__calib-pulse" />
                  Calibrating — hold position
                </div>
              )}
            </div>
            <div className="monitoring__camera-footer">
              <span>Frames processed: <strong>{frameCount}</strong></span>
              <span>Modules: <strong>{modules.join(', ')}</strong></span>
            </div>
          </div>

          {/* RIGHT — Live metrics */}
          <div className="monitoring__metrics-panel">

            {/* Tremor */}
            {modules.includes('tremor') && (
              <div className="monitoring__module-section">
                <div className="monitoring__module-header">
                  <Hand size={16} strokeWidth={1.8} />
                  <h3>Tremor</h3>
                  {tremorData && !tremorData.is_calibrating && (
                    <StatusBadge
                      status={tremorData.severity === 'No tremor' ? 'normal' : 'warning'}
                      label={tremorData.severity || '—'}
                    />
                  )}
                  {tremorData?.is_calibrating && <StatusBadge status="active" label="Calibrating" />}
                </div>
                <div className="monitoring__metrics-row">
                  <MetricCard label="Frequency" value={tremorData?.frequency?.toFixed(2) ?? '—'} unit="Hz" size="sm" />
                  <MetricCard label="Amplitude" value={tremorData?.amplitude?.toFixed(2) ?? '—'} unit="px" size="sm" />
                  <MetricCard
                    label="Hand"
                    value={tremorData ? (tremorData.hand_detected ? 'Detected' : 'Not found') : '—'}
                    size="sm"
                  />
                </div>
                {tremorChart.length > 2 && (
                  <div className="monitoring__chart">
                    <ResponsiveContainer width="100%" height={90}>
                      <LineChart data={tremorChart}>
                        <XAxis dataKey="t" hide />
                        <YAxis hide domain={['auto', 'auto']} />
                        <Tooltip
                          contentStyle={{ fontSize: 11, borderRadius: 6, border: '1px solid var(--color-border)' }}
                          formatter={(v, n) => [v?.toFixed(3), n]}
                        />
                        <Line type="monotone" dataKey="freq" stroke="var(--color-primary)" dot={false} strokeWidth={1.5} name="Freq (Hz)" />
                        <Line type="monotone" dataKey="amp"  stroke="var(--color-accent)"  dot={false} strokeWidth={1.5} name="Amp (px)" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}

            {/* Blink */}
            {modules.includes('blink') && (
              <div className="monitoring__module-section">
                <div className="monitoring__module-header">
                  <Eye size={16} strokeWidth={1.8} />
                  <h3>Blink</h3>
                  {blinkData && !blinkData.is_calibrating && (
                    <StatusBadge
                      status={blinkData.blink_rate > 10 && blinkData.blink_rate < 20 ? 'normal' : 'warning'}
                      label={blinkData.blink_in_progress ? 'Blinking' : 'Open'}
                    />
                  )}
                  {blinkData?.is_calibrating && <StatusBadge status="active" label="Calibrating" />}
                </div>
                <div className="monitoring__metrics-row">
                  <MetricCard label="EAR"         value={blinkData?.ear?.toFixed(3) ?? '—'}              size="sm" />
                  <MetricCard label="Blinks"       value={blinkData?.blink_count ?? '—'}                  size="sm" />
                  <MetricCard label="Rate"         value={blinkData?.blink_rate?.toFixed(1) ?? '—'} unit="/min" size="sm" />
                </div>
                {blinkChart.length > 2 && (
                  <div className="monitoring__chart">
                    <ResponsiveContainer width="100%" height={90}>
                      <LineChart data={blinkChart}>
                        <XAxis dataKey="t" hide />
                        <YAxis hide domain={['auto', 'auto']} />
                        <Tooltip
                          contentStyle={{ fontSize: 11, borderRadius: 6, border: '1px solid var(--color-border)' }}
                          formatter={(v, n) => [v?.toFixed(3), n]}
                        />
                        <ReferenceLine y={blinkData?.ear_threshold} stroke="var(--color-accent)" strokeDasharray="4 2" />
                        <Line type="monotone" dataKey="ear" stroke="var(--color-primary)" dot={false} strokeWidth={1.5} name="EAR" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}

            {/* Asymmetry */}
            {modules.includes('asymmetry') && (
              <div className="monitoring__module-section">
                <div className="monitoring__module-header">
                  <Smile size={16} strokeWidth={1.8} />
                  <h3>Facial Asymmetry</h3>
                  {asymmetryData && !asymmetryData.is_calibrating && (
                    <StatusBadge
                      status={asymmetryData.asym_event_active ? 'error' : asymmetryData.asym_score > 0.15 ? 'warning' : 'normal'}
                      label={asymmetryData.asym_event_active ? 'Event Active' : asymmetryData.asym_score > 0.15 ? 'Asymmetric' : 'Symmetric'}
                    />
                  )}
                  {asymmetryData?.is_calibrating && <StatusBadge status="active" label="Calibrating" />}
                </div>
                <div className="monitoring__metrics-row">
                  <MetricCard label="Score"  value={asymmetryData?.asym_score?.toFixed(3) ?? '—'} size="sm" />
                  <MetricCard label="Eye Δ"  value={asymmetryData?.eye_asym?.toFixed(3) ?? '—'}   size="sm" />
                  <MetricCard label="Mouth Δ" value={asymmetryData?.mouth_asym?.toFixed(3) ?? '—'} size="sm" />
                </div>
                {asymmetryChart.length > 2 && (
                  <div className="monitoring__chart">
                    <ResponsiveContainer width="100%" height={90}>
                      <LineChart data={asymmetryChart}>
                        <XAxis dataKey="t" hide />
                        <YAxis hide domain={[0, 0.5]} />
                        <Tooltip
                          contentStyle={{ fontSize: 11, borderRadius: 6, border: '1px solid var(--color-border)' }}
                          formatter={(v) => [v?.toFixed(4), 'Asym Score']}
                        />
                        <ReferenceLine y={0.15} stroke="var(--color-accent)" strokeDasharray="4 2" />
                        <Line type="monotone" dataKey="score" stroke="var(--color-sage)" dot={false} strokeWidth={1.5} name="Score" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}

            {/* Ptosis */}
            {modules.includes('ptosis') && (
              <div className="monitoring__module-section">
                <div className="monitoring__module-header">
                  <Activity size={16} strokeWidth={1.8} />
                  <h3>Ptosis</h3>
                  {ptosisData && !ptosisData.is_calibrating && (
                    <StatusBadge
                      status={ptosisData.ptosis_detected ? 'error' : 'normal'}
                      label={ptosisData.ptosis_detected ? 'Drooping Detected' : 'Normal'}
                    />
                  )}
                  {ptosisData?.is_calibrating && <StatusBadge status="active" label="Calibrating" />}
                </div>
                <div className="monitoring__metrics-row">
                  <MetricCard label="Left EOR"  value={ptosisData?.left_ratio?.toFixed(3) ?? '—'}  size="sm" />
                  <MetricCard label="Right EOR" value={ptosisData?.right_ratio?.toFixed(3) ?? '—'} size="sm" />
                  <MetricCard
                    label="Detection"
                    value={ptosisData ? (ptosisData.ptosis_detected ? 'Yes' : 'No') : '—'}
                    status={ptosisData?.ptosis_detected ? 'error' : undefined}
                    size="sm"
                  />
                </div>
              </div>
            )}

          </div>
        </div>

        {/* ── No face / no hand warnings ── */}
        <div className="monitoring__warnings">
          {modules.includes('tremor') && tremorData && !tremorData.hand_detected && !tremorData.is_calibrating && (
            <div className="monitoring__warn-pill">
              <AlertTriangle size={13} strokeWidth={2} /> No hand detected — hold your hand in front of the camera
            </div>
          )}
          {modules.some((m) => ['blink','asymmetry','ptosis'].includes(m)) &&
            blinkData && !blinkData.face_detected && !blinkData.is_calibrating && (
            <div className="monitoring__warn-pill">
              <AlertTriangle size={13} strokeWidth={2} /> No face detected — ensure your face is in frame
            </div>
          )}
        </div>

      </div>
    </AppLayout>
  );
}
