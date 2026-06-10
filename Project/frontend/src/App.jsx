import { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import Sidebar from './components/Sidebar';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import AllTicketsPage from './pages/AllTicketsPage';
import SettingsPage from './pages/SettingsPage';

function ProtectedRoute({ isAllowed, children }) {
  if (!isAllowed) return <Navigate to="/login" replace />;
  return children;
}

function App() {
  // Theme state
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'light';
  });

  // Auth state
  const [token, setToken] = useState(() => localStorage.getItem('token') || null);
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });

  // Apply theme to HTML element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const handleLogin = (userData, accessToken) => {
    setUser(userData);
    setToken(accessToken);
    localStorage.setItem('user', JSON.stringify(userData));
    localStorage.setItem('token', accessToken);
  };

  const handleLogout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('user');
    localStorage.removeItem('token');
  };

  return (
    <Routes>
      {/* Auth pages */}
      <Route
        path="/login"
        element={
          user
            ? <Navigate to="/dashboard" replace />
            : <LoginPage onLogin={handleLogin} theme={theme} onToggleTheme={toggleTheme} />
        }
      />
      <Route
        path="/register"
        element={
          user
            ? <Navigate to="/dashboard" replace />
            : <RegisterPage onRegister={handleLogin} theme={theme} onToggleTheme={toggleTheme} />
        }
      />

      {/* Dashboard (protected) */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute isAllowed={Boolean(token && user)}>
            <div className="dashboard-layout">
              <Sidebar
                theme={theme}
                onToggleTheme={toggleTheme}
                user={user}
                onLogout={handleLogout}
              />
              <main className="dashboard-main">
                <DashboardPage token={token} onLogout={handleLogout} />
              </main>
            </div>
          </ProtectedRoute>
        }
      />

      {/* All Tickets (protected) */}
      <Route
        path="/tickets"
        element={
          <ProtectedRoute isAllowed={Boolean(token && user)}>
            <div className="dashboard-layout">
              <Sidebar theme={theme} onToggleTheme={toggleTheme} user={user} onLogout={handleLogout} />
              <main className="dashboard-main">
                <AllTicketsPage token={token} onLogout={handleLogout} />
              </main>
            </div>
          </ProtectedRoute>
        }
      />

      {/* Settings (protected) */}
      <Route
        path="/settings"
        element={
          <ProtectedRoute isAllowed={Boolean(token && user)}>
            <div className="dashboard-layout">
              <Sidebar theme={theme} onToggleTheme={toggleTheme} user={user} onLogout={handleLogout} />
              <main className="dashboard-main">
                <SettingsPage user={user} />
              </main>
            </div>
          </ProtectedRoute>
        }
      />

      {/* Redirects */}
      <Route path="/" element={<Navigate to={user ? '/dashboard' : '/login'} replace />} />
      <Route path="*" element={<Navigate to={user ? '/dashboard' : '/login'} replace />} />
    </Routes>
  );
}

export default App;
