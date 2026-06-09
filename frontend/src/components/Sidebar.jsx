import { LayoutDashboard, TicketCheck, Settings, LogOut, User, Bug } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import './Sidebar.css';

export default function Sidebar({ theme, onToggleTheme, user, onLogout }) {
  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <Bug />
        </div>
        <div>
          <div className="sidebar-brand-text">Ticket Auditor</div>
          <div className="sidebar-brand-sub">AI Quality Engine</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="sidebar-nav-label">Navigation</div>
        <button className="sidebar-nav-item active">
          <LayoutDashboard />
          Dashboard
        </button>
        <button className="sidebar-nav-item">
          <TicketCheck />
          All Tickets
        </button>
        <button className="sidebar-nav-item">
          <Settings />
          Settings
        </button>
      </nav>

      <div className="sidebar-spacer" />

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-footer-row">
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
          <button className="btn btn-ghost btn-sm" onClick={onLogout} title="Sign out">
            <LogOut size={16} />
          </button>
        </div>

        {user && (
          <div className="sidebar-user">
            <div className="sidebar-user-avatar">
              <User />
            </div>
            <div className="sidebar-user-info">
              <span className="sidebar-user-name">{user.name}</span>
              <span className="sidebar-user-email">{user.email}</span>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
