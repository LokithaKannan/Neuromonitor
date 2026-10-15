import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity, Eye, Smile, Hand, Brain,
  CheckCircle, ArrowRight, Lock,
  ChevronDown, User, LayoutDashboard,
  LogOut, ChevronRight, Webcam,
  BarChart2, FileText, Zap, Cpu
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import './Landing.css';

/* ── Data ─────────────────────────────────────────── */
const MODULES = [
  {
    icon: Hand,
    tag: 'Tremor',
    title: 'Hand Tremor Detection',
    desc: 'FFT analysis on MediaPipe hand landmarks classifies tremor from mild physiological to high-frequency severe. Results in real time at 10 fps.',
    color: '#5B2D8E',
    light: 'rgba(91,45,142,0.08)',
  },
  {
    icon: Eye,
    tag: 'Blink',
    title: 'Blink Rate Analysis',
    desc: 'Personal Eye Aspect Ratio baseline calibrated in the first 2 seconds. Counts blinks, measures duration, flags abnormal patterns.',
    color: '#B05A1A',
    light: 'rgba(176,90,26,0.08)',
  },
  {
    icon: Smile,
    tag: 'Asymmetry',
    title: 'Facial Asymmetry',
    desc: 'Weighted composite of eye, mouth and brow disparity. Detects sustained asymmetry events and micro-expression bursts.',
    color: '#1E6E5A',
    light: 'rgba(30,110,90,0.08)',
  },
  {
    icon: Activity,
    tag: 'Ptosis',
    title: 'Ptosis Detection',
    desc: 'Per-eyelid Eye Opening Ratio vs your calibrated baseline. Alerts when either eyelid droops below 70 % of its normal opening.',
    color: '#1A3E7A',
    light: 'rgba(26,62,122,0.08)',
  },
];

const STEPS = [
  { icon: User,       num: '1', title: 'Create an account',    desc: 'Sign up in under a minute — only an email and password needed.' },
  { icon: Cpu,        num: '2', title: 'Pick your modules',    desc: 'Run a single detection or combine all four in one session.' },
  { icon: Zap,        num: '3', title: 'Allow the camera',     desc: 'Your webcam activates for the session only. Nothing is stored.' },
  { icon: BarChart2,  num: '4', title: 'View live metrics',    desc: 'Watch measurements update frame-by-frame on your dashboard.' },
  { icon: FileText,   num: '5', title: 'Export the report',    desc: 'Download a PDF summary and revisit historical trends any time.' },
];

const TRUST = [
  'Raw video frames are never saved to disk or database',
  'Only computed metric values are persisted per session',
  'Camera permission is requested freshly each session',
  'Passwords stored as bcrypt hashes — never plain text',
  'All API routes protected with short-lived JWT tokens',
];

/* ── Component ─────────────────────────────────────── */
export default function Landing() {
  const { user, logoutUser, loading } = useAuth();
  const [scrolled,  setScrolled]  = useState(false);
  const [menuOpen,  setMenuOpen]  = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const menuRef = useRef(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="lp">

      {/* ══════════════════ NAV ══════════════════ */}
      <header className={`lp-nav ${scrolled ? 'lp-nav--solid' : ''}`}>
        <div className="lp-nav__inner">
          <Link to="/" className="lp-nav__brand">
            <div className="lp-nav__brand-icon"><Activity size={18} strokeWidth={2} /></div>
            NeuroMonitor
          </Link>

          <nav className="lp-nav__links">
            <a href="#modules">Modules</a>
            <a href="#how">How it works</a>
            <a href="#trust">Privacy</a>
          </nav>

          <div className="lp-nav__end">
            {!loading && (
              user ? (
                <>
                  <Link to="/dashboard" className="lp-nav__pill">
                    <LayoutDashboard size={14} /> Dashboard
                  </Link>
                  <div className="lp-nav__avatar-wrap" ref={menuRef}>
                    <button
                      className="lp-nav__avatar-btn"
                      onClick={() => setMenuOpen(o => !o)}
                      aria-label="Account menu"
                    >
                      <span className="lp-nav__avatar-letter">
                        {user.full_name?.[0]?.toUpperCase()}
                      </span>
                      <ChevronDown size={12} strokeWidth={2.5} className={menuOpen ? 'flip' : ''} />
                    </button>
                    {menuOpen && (
                      <div className="lp-nav__menu">
                        <div className="lp-nav__menu-header">
                          <p className="lp-nav__menu-name">{user.full_name}</p>
                          <p className="lp-nav__menu-email">{user.email}</p>
                        </div>
                        <Link to="/profile"   className="lp-nav__menu-item" onClick={() => setMenuOpen(false)}><User size={14}/>Profile</Link>
                        <Link to="/dashboard" className="lp-nav__menu-item" onClick={() => setMenuOpen(false)}><LayoutDashboard size={14}/>Dashboard</Link>
                        <button className="lp-nav__menu-item lp-nav__menu-item--red" onClick={() => { logoutUser(); setMenuOpen(false); }}>
                          <LogOut size={14}/>Sign out
                        </button>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <Link to="/login"  className="lp-nav__login">Sign in</Link>
                  <Link to="/signup" className="lp-nav__cta">Get started</Link>
                </>
              )
            )}
          </div>
        </div>
      </header>

      {/* ══════════════════ HERO ══════════════════ */}
      <section className="lp-hero">
        {/* Background blobs */}
        <div className="lp-hero__blob lp-hero__blob--a" aria-hidden />
        <div className="lp-hero__blob lp-hero__blob--b" aria-hidden />
        <div className="lp-hero__blob lp-hero__blob--c" aria-hidden />

        <div className="lp-hero__body">
          {/* Left copy */}
          <div className="lp-hero__copy">
            <div className="lp-hero__badge">
              <Brain size={12} strokeWidth={2.5} />
              Computer-vision neurology screening
            </div>

            <h1 className="lp-hero__h1">
              Monitor your<br />
              <span className="lp-hero__accent">neurological</span><br />
              health — from<br />
              your webcam
            </h1>

            <p className="lp-hero__lead">
              Four real-time detection modules analyse tremor, blink patterns,
              facial symmetry and eyelid function. No wearables. No clinic visit.
              Just your browser.
            </p>

            <div className="lp-hero__actions">
              {user ? (
                <>
                  <Link to="/assessment" className="lp-btn lp-btn--fill">
                    Start assessment <ArrowRight size={15} />
                  </Link>
                  <Link to="/dashboard" className="lp-btn lp-btn--soft">Dashboard</Link>
                </>
              ) : (
                <>
                  <Link to="/signup" className="lp-btn lp-btn--fill">
                    Start free <ArrowRight size={15} />
                  </Link>
                  <Link to="/login" className="lp-btn lp-btn--soft">Sign in</Link>
                </>
              )}
            </div>

            <p className="lp-hero__disclaimer">
              Screening tool only — not a substitute for medical diagnosis.
            </p>
          </div>

          {/* Right panel — module selector */}
          <div className="lp-hero__panel">
            <div className="lp-hero__tabs">
              {MODULES.map((m, i) => (
                <button
                  key={m.tag}
                  className={`lp-hero__tab ${activeTab === i ? 'active' : ''}`}
                  onClick={() => setActiveTab(i)}
                  style={activeTab === i ? { '--tab-color': m.color } : {}}
                >
                  <m.icon size={14} strokeWidth={2} />
                  {m.tag}
                </button>
              ))}
            </div>
            <div className="lp-hero__card" style={{ '--card-color': MODULES[activeTab].color, '--card-light': MODULES[activeTab].light }}>
              <div className="lp-hero__card-icon">
                {(() => { const I = MODULES[activeTab].icon; return <I size={26} strokeWidth={1.6} />; })()}
              </div>
              <h3 className="lp-hero__card-title">{MODULES[activeTab].title}</h3>
              <p className="lp-hero__card-desc">{MODULES[activeTab].desc}</p>
              <div className="lp-hero__card-tag">{MODULES[activeTab].tag}</div>
            </div>
            {/* Stats row */}
            <div className="lp-hero__stats">
              <div className="lp-hero__stat"><strong>4</strong><span>modules</span></div>
              <div className="lp-hero__stat-div" />
              <div className="lp-hero__stat"><strong>10 fps</strong><span>live</span></div>
              <div className="lp-hero__stat-div" />
              <div className="lp-hero__stat"><strong>0 bytes</strong><span>video stored</span></div>
            </div>
          </div>
        </div>

        <a href="#modules" className="lp-hero__scroll" aria-label="Scroll to modules">
          <ChevronDown size={20} strokeWidth={1.8} />
        </a>
      </section>

      {/* ══════════════════ MODULES ══════════════════ */}
      <section id="modules" className="lp-modules">
        <div className="lp-wrap">
          <div className="lp-section-head">
            <span className="lp-label">Four detection modules</span>
            <h2>What NeuroMonitor measures</h2>
            <p>Every module runs a validated signal-processing algorithm on your local frame stream.</p>
          </div>

          <div className="lp-modules__grid">
            {MODULES.map((m, i) => (
              <div className="lp-mcard" key={m.tag} style={{ '--mc': m.color, '--mc-light': m.light }}>
                <div className="lp-mcard__num">0{i + 1}</div>
                <div className="lp-mcard__icon">
                  <m.icon size={24} strokeWidth={1.6} />
                </div>
                <h3 className="lp-mcard__title">{m.title}</h3>
                <p className="lp-mcard__desc">{m.desc}</p>
                <div className="lp-mcard__tag">{m.tag}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════ HOW IT WORKS ══════════════════ */}
      <section id="how" className="lp-how">
        <div className="lp-wrap">
          <div className="lp-section-head lp-section-head--light">
            <span className="lp-label lp-label--light">Simple process</span>
            <h2>From sign-up to report in 5 steps</h2>
            <p>No downloads, no hardware, no technical setup needed.</p>
          </div>

          <div className="lp-how__track">
            {STEPS.map((s, i) => (
              <div className="lp-step" key={s.num}>
                <div className="lp-step__left">
                  <div className="lp-step__circle">
                    <s.icon size={18} strokeWidth={1.8} />
                  </div>
                  {i < STEPS.length - 1 && <div className="lp-step__line" aria-hidden />}
                </div>
                <div className="lp-step__body">
                  <span className="lp-step__num">Step {s.num}</span>
                  <h3>{s.title}</h3>
                  <p>{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════ TRUST / PRIVACY ══════════════════ */}
      <section id="trust" className="lp-trust">
        <div className="lp-wrap lp-trust__inner">
          <div className="lp-trust__copy">
            <span className="lp-label">Built with privacy first</span>
            <h2>Your camera stays yours</h2>
            <p>
              NeuroMonitor processes video on the server and discards each frame immediately.
              Only the computed numbers — frequency, rate, score — are saved.
            </p>
            <Link to={user ? '/assessment' : '/signup'} className="lp-btn lp-btn--fill" style={{ marginTop: '1.5rem', display: 'inline-flex' }}>
              {user ? 'Start a session' : 'Create free account'} <ArrowRight size={15} />
            </Link>
          </div>

          <div className="lp-trust__card">
            <div className="lp-trust__card-top">
              <div className="lp-trust__lock"><Lock size={28} strokeWidth={1.4} /></div>
              <h3>Privacy guarantees</h3>
            </div>
            <ul className="lp-trust__list">
              {TRUST.map(t => (
                <li key={t}>
                  <CheckCircle size={14} strokeWidth={2.5} />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* ══════════════════ BOTTOM CTA ══════════════════ */}
      <section className="lp-bottom">
        <div className="lp-wrap lp-bottom__inner">
          <h2>
            {user
              ? `Ready to run another session, ${user.full_name?.split(' ')[0]}?`
              : 'Start monitoring in under two minutes.'}
          </h2>
          <p>
            {user
              ? 'Your history and trend charts are waiting on the dashboard.'
              : 'Free account. No credit card. No special hardware.'}
          </p>
          <div className="lp-bottom__btns">
            {user ? (
              <>
                <Link to="/assessment" className="lp-btn lp-btn--fill lp-btn--lg">New assessment <ArrowRight size={16}/></Link>
                <Link to="/dashboard"  className="lp-btn lp-btn--outline lp-btn--lg">Dashboard</Link>
              </>
            ) : (
              <>
                <Link to="/signup" className="lp-btn lp-btn--fill lp-btn--lg">Create account <ArrowRight size={16}/></Link>
                <Link to="/login"  className="lp-btn lp-btn--outline lp-btn--lg">Sign in</Link>
              </>
            )}
          </div>
        </div>
      </section>

      {/* ══════════════════ FOOTER ══════════════════ */}
      <footer className="lp-footer">
        <div className="lp-wrap lp-footer__inner">
          <div className="lp-footer__brand">
            <Activity size={16} strokeWidth={2} />
            NeuroMonitor
          </div>
          <p className="lp-footer__note">
            For screening and educational purposes only. Not a medical device.
          </p>
          <div className="lp-footer__links">
            {user ? (
              <>
                <Link to="/dashboard">Dashboard</Link>
                <Link to="/assessment">Assessment</Link>
                <Link to="/profile">Profile</Link>
              </>
            ) : (
              <>
                <Link to="/signup">Get started</Link>
                <Link to="/login">Sign in</Link>
              </>
            )}
          </div>
          <p className="lp-footer__copy">© {new Date().getFullYear()} NeuroMonitor</p>
        </div>
      </footer>

    </div>
  );
}
