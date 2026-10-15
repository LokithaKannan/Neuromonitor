import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Activity, Eye, Smile, Hand,
  ChevronRight, CheckCircle, Camera, AlertCircle, Layers
} from 'lucide-react';
import { createSession } from '../api/sessions';
import { useCamera } from '../hooks/useCamera';
import Button from '../components/Button';
import ErrorMessage from '../components/ErrorMessage';
import AppLayout from '../components/AppLayout';
import './NewAssessment.css';

const MODULES = [
  {
    key: 'complete', icon: Layers, label: 'Complete Assessment',
    desc: 'Runs all four modules in sequence — tremor, blink, asymmetry, ptosis.',
    prep: [
      'Find a quiet, evenly lit space.',
      'Ensure your face and both hands are visible to the camera.',
      'Sit approximately 50–80 cm from the screen.',
      'Remove glasses if possible for eye-based measurements.',
      'Keep a neutral expression during calibration phases.',
    ],
  },
  {
    key: 'tremor', icon: Hand, label: 'Tremor Analysis',
    desc: 'Tracks index-finger tip to measure FFT tremor frequency and movement amplitude.',
    prep: [
      'Hold one hand in front of the camera at arm length.',
      'Keep the hand visible within the frame throughout.',
      'Try to hold the hand naturally — do not suppress movement.',
      'Ensure there is sufficient lighting on the hand.',
    ],
  },
  {
    key: 'blink', icon: Eye, label: 'Blink Analysis',
    desc: 'Measures Eye Aspect Ratio; auto-calibrates then counts blinks and computes rate.',
    prep: [
      'Face the camera directly — your full face should be in frame.',
      'Ensure even lighting with no harsh shadows across your face.',
      'During the first 2 seconds, keep your eyes open normally for calibration.',
      'Blink naturally — do not suppress or exaggerate blinking.',
    ],
  },
  {
    key: 'asymmetry', icon: Smile, label: 'Facial Asymmetry',
    desc: 'Computes a weighted eye/mouth/brow asymmetry score with event detection.',
    prep: [
      'Face the camera directly at eye level.',
      'Maintain a neutral face expression during the 3-second calibration.',
      'Ensure even lighting — avoid side lighting that creates shadows.',
      'Keep your head as still as possible.',
    ],
  },
  {
    key: 'ptosis', icon: Activity, label: 'Ptosis Detection',
    desc: 'Measures Eye Opening Ratio and flags eyelid drooping vs your baseline.',
    prep: [
      'Face the camera directly at eye level.',
      'Keep your eyes fully open during the first 5 seconds for baseline calibration.',
      'Ensure good lighting across both eyes.',
      'Avoid blinking excessively during calibration.',
    ],
  },
];

const STEPS = ['Select', 'Prepare', 'Camera', 'Start'];

export default function NewAssessment() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const preselect = params.get('module') || '';

  const [step, setStep] = useState(0);
  const [selected, setSelected] = useState(preselect || '');
  const [creating, setCreating] = useState(false);
  const [apiError, setApiError] = useState('');

  const { attachRef, status: camStatus, error: camError, startCamera, stopCamera } = useCamera();

  // Auto-advance to prepare if module pre-selected
  useEffect(() => {
    if (preselect && MODULES.find((m) => m.key === preselect)) {
      setSelected(preselect);
      setStep(1);
    }
  }, [preselect]);

  const selectedModule = MODULES.find((m) => m.key === selected);

  const handleStartCamera = async () => {
    await startCamera();
  };

  const handleBeginSession = async () => {
    setCreating(true);
    setApiError('');
    try {
      const assessmentType = selected === 'complete' ? 'complete' : selected;
      const res = await createSession({ assessment_type: assessmentType });
      const sessionId = res.data.id;
      const moduleList = selected === 'complete'
        ? ['tremor', 'blink', 'asymmetry', 'ptosis']
        : [selected];
      stopCamera();
      navigate(`/monitoring/${sessionId}?modules=${moduleList.join(',')}`);
    } catch (err) {
      setApiError(err.response?.data?.detail || 'Could not create session. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <AppLayout>
      <div className="assessment">
        {/* Step indicator */}
        <div className="assessment__steps">
          {STEPS.map((s, i) => (
            <div key={s} className={`assessment__step ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}>
              <div className="assessment__step-dot">
                {i < step ? <CheckCircle size={14} strokeWidth={2.5} /> : <span>{i + 1}</span>}
              </div>
              <span>{s}</span>
            </div>
          ))}
        </div>

        <div className="assessment__body">
          {/* Step 0 — Select */}
          {step === 0 && (
            <div className="assessment__panel">
              <h2>Select Assessment</h2>
              <p>Choose a single module or run all four in sequence.</p>
              <div className="assessment__options">
                {MODULES.map((m) => (
                  <button
                    key={m.key}
                    className={`assessment__option ${selected === m.key ? 'selected' : ''}`}
                    onClick={() => setSelected(m.key)}
                  >
                    <div className="assessment__option-icon"><m.icon size={22} strokeWidth={1.6} /></div>
                    <div className="assessment__option-body">
                      <strong>{m.label}</strong>
                      <span>{m.desc}</span>
                    </div>
                    {selected === m.key && <CheckCircle size={18} strokeWidth={2} className="assessment__option-check" />}
                  </button>
                ))}
              </div>
              <Button
                variant="primary" size="lg"
                disabled={!selected}
                onClick={() => setStep(1)}
                className="assessment__next"
              >
                Continue <ChevronRight size={16} />
              </Button>
            </div>
          )}

          {/* Step 1 — Prepare */}
          {step === 1 && selectedModule && (
            <div className="assessment__panel">
              <h2>Preparation — {selectedModule.label}</h2>
              <p>Follow these instructions before starting to ensure accurate measurements.</p>
              <ul className="assessment__prep-list">
                {selectedModule.prep.map((item, i) => (
                  <li key={i}><CheckCircle size={16} strokeWidth={2} /> {item}</li>
                ))}
              </ul>
              <div className="assessment__nav">
                <Button variant="ghost" onClick={() => setStep(0)}>Back</Button>
                <Button variant="primary" size="lg" onClick={() => { handleStartCamera(); setStep(2); }}>
                  Check Camera <ChevronRight size={16} />
                </Button>
              </div>
            </div>
          )}

          {/* Step 2 — Camera */}
          {step === 2 && (
            <div className="assessment__panel">
              <h2>Camera Check</h2>
              <p>Confirm your camera is working before starting the assessment.</p>

              <div className="assessment__camera-box">
                {camStatus === 'idle' || camStatus === 'requesting' ? (
                  <div className="assessment__camera-placeholder">
                    <Camera size={40} strokeWidth={1.4} />
                    <span>
                      {camStatus === 'requesting' ? 'Requesting camera permission…' : 'Camera not started'}
                    </span>
                    {camStatus === 'idle' && (
                      <Button variant="primary" onClick={handleStartCamera}>Allow Camera</Button>
                    )}
                  </div>
                ) : camStatus === 'denied' || camStatus === 'unavailable' || camStatus === 'error' ? (
                  <div className="assessment__camera-error">
                    <AlertCircle size={32} strokeWidth={1.4} />
                    <span>{camError}</span>
                    <Button variant="outline" onClick={handleStartCamera}>Retry</Button>
                  </div>
                ) : (
                  <video
                    ref={attachRef}
                    autoPlay
                    playsInline
                    muted
                    className="assessment__preview"
                    aria-label="Camera preview"
                  />
                )}
              </div>

              {camStatus === 'active' && (
                <div className="assessment__camera-ok">
                  <CheckCircle size={16} strokeWidth={2} /> Camera ready
                </div>
              )}

              <div className="assessment__nav">
                <Button variant="ghost" onClick={() => { stopCamera(); setStep(1); }}>Back</Button>
                <Button
                  variant="primary" size="lg"
                  disabled={camStatus !== 'active'}
                  onClick={() => setStep(3)}
                >
                  Looks Good <ChevronRight size={16} />
                </Button>
              </div>
            </div>
          )}

          {/* Step 3 — Start */}
          {step === 3 && selectedModule && (
            <div className="assessment__panel assessment__panel--center">
              <div className="assessment__ready-icon">
                <selectedModule.icon size={40} strokeWidth={1.4} />
              </div>
              <h2>Ready to Begin</h2>
              <p>
                You are about to start <strong>{selectedModule.label}</strong>.
                The analysis will begin as soon as you click the button below.
              </p>
              <ErrorMessage message={apiError} />
              <div className="assessment__nav assessment__nav--center">
                <Button variant="ghost" onClick={() => setStep(2)}>Back</Button>
                <Button
                  variant="accent" size="lg"
                  loading={creating}
                  onClick={handleBeginSession}
                >
                  Start Assessment
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
