import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { Activity, Menu, X, LogOut, User, Home } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { logout } from '../api/auth';
import './Navbar.css';

export default function Navbar() {
  const { user, logoutUser } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = async () => {
    try { await logout(); } catch {}
    logoutUser();
    navigate('/');
  };

  return (
    <header className="navbar">
      <div className="navbar__inner">
        <Link to={user ? '/dashboard' : '/'} className="navbar__brand">
          <Activity size={22} strokeWidth={1.8} />
          <span>NeuroMonitor</span>
        </Link>

        {/* Desktop nav */}
        {!user ? (
          <nav className="navbar__links" aria-label="Public navigation">
            <NavLink to="/" end>Home</NavLink>
            <NavLink to="/#how-it-works">How It Works</NavLink>
            <NavLink to="/#capabilities">Capabilities</NavLink>
            <div className="navbar__actions">
              <Link to="/login" className="navbar__link-btn navbar__link-btn--outline">Sign In</Link>
              <Link to="/signup" className="navbar__link-btn navbar__link-btn--filled">Create Account</Link>
            </div>
          </nav>
        ) : (
          <nav className="navbar__links" aria-label="App navigation">
            <NavLink to="/dashboard">Dashboard</NavLink>
            <NavLink to="/assessment">New Assessment</NavLink>
            <NavLink to="/history">History</NavLink>
            <NavLink to="/trends">Trends</NavLink>
            <NavLink to="/reports">Reports</NavLink>
            <div className="navbar__actions">
              <Link to="/" className="navbar__icon-btn" aria-label="Home" title="Back to home">
                <Home size={17} strokeWidth={1.8} />
              </Link>
              <NavLink to="/profile" className="navbar__icon-btn" aria-label="Profile">
                <User size={18} strokeWidth={1.8} />
              </NavLink>
              <button className="navbar__icon-btn" onClick={handleLogout} aria-label="Logout">
                <LogOut size={18} strokeWidth={1.8} />
              </button>
            </div>
          </nav>
        )}

        {/* Mobile toggle */}
        <button
          className="navbar__mobile-toggle"
          onClick={() => setMenuOpen((o) => !o)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="navbar__mobile-menu" role="navigation" aria-label="Mobile navigation">
          {!user ? (
            <>
              <Link to="/" onClick={() => setMenuOpen(false)}>Home</Link>
              <Link to="/login" onClick={() => setMenuOpen(false)}>Sign In</Link>
              <Link to="/signup" onClick={() => setMenuOpen(false)}>Create Account</Link>
            </>
          ) : (
            <>
              <NavLink to="/dashboard" onClick={() => setMenuOpen(false)}>Dashboard</NavLink>
              <NavLink to="/assessment" onClick={() => setMenuOpen(false)}>New Assessment</NavLink>
              <NavLink to="/history" onClick={() => setMenuOpen(false)}>History</NavLink>
              <NavLink to="/trends" onClick={() => setMenuOpen(false)}>Trends</NavLink>
              <NavLink to="/reports" onClick={() => setMenuOpen(false)}>Reports</NavLink>
              <NavLink to="/profile" onClick={() => setMenuOpen(false)}>Profile</NavLink>
              <Link to="/" onClick={() => setMenuOpen(false)}>Home</Link>
              <button onClick={() => { handleLogout(); setMenuOpen(false); }}>Logout</button>
            </>
          )}
        </div>
      )}
    </header>
  );
}
