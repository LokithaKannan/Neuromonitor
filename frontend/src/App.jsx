import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';

import Landing        from './pages/Landing';
import Login          from './pages/Login';
import Signup         from './pages/Signup';
import Dashboard      from './pages/Dashboard';
import NewAssessment  from './pages/NewAssessment';
import Monitoring     from './pages/Monitoring';
import History        from './pages/History';
import SessionDetail  from './pages/SessionDetail';
import Trends         from './pages/Trends';
import Reports        from './pages/Reports';
import Profile        from './pages/Profile';
import NotFound       from './pages/NotFound';
import ProtectedRoute from './components/ProtectedRoute';

// Redirect already-authenticated users away from auth pages
function PublicRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<Landing />} />
      <Route path="/login"  element={<PublicRoute><Login  /></PublicRoute>} />
      <Route path="/signup" element={<PublicRoute><Signup /></PublicRoute>} />

      {/* Protected */}
      <Route path="/dashboard"        element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/assessment"       element={<ProtectedRoute><NewAssessment /></ProtectedRoute>} />
      <Route path="/monitoring/:sessionId" element={<ProtectedRoute><Monitoring /></ProtectedRoute>} />
      <Route path="/history"          element={<ProtectedRoute><History /></ProtectedRoute>} />
      <Route path="/history/:id"      element={<ProtectedRoute><SessionDetail /></ProtectedRoute>} />
      <Route path="/trends"           element={<ProtectedRoute><Trends /></ProtectedRoute>} />
      <Route path="/reports"          element={<ProtectedRoute><Reports /></ProtectedRoute>} />
      <Route path="/profile"          element={<ProtectedRoute><Profile /></ProtectedRoute>} />

      {/* 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
