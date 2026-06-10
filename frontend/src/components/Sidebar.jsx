import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, TicketCheck, LogOut, User, Bug, ChevronLeft, ChevronRight } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import './Sidebar.css';

export default function Sidebar({ theme, onToggleTheme, user, onLogout }) {
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem('sidebar-collapsed') === 'true'
  );

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem('sidebar-collapsed', String(next));
  };

  return (
    <aside className={`sidebar${collapsed ? ' sidebar-collapsed' : ''}`}>
      {/* Brand + collapse toggle */}
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <Bug />
        </div>
        {!collapsed && (
          <div className="sidebar-brand-text-wrap">
            <div className="sidebar-brand-text">Ticket Auditor</div>
            <div className="sidebar-brand-sub">AI Quality Engine</div>
          </div>
        )}
        <button
          className="sidebar-collapse-btn"
          onClick={toggle}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {!collapsed && <div className="sidebar-nav-label">Navigation</div>}
        <NavLink
          to="/dashboard"
          className={({ isActive }) => `sidebar-nav-item${isActive ? ' active' : ''}`}
          title="Dashboard"
        >
          <LayoutDashboard />
          {!collapsed && 'Dashboard'}
        </NavLink>
        <NavLink
          to="/tickets"
          className={({ isActive }) => `sidebar-nav-item${isActive ? ' active' : ''}`}
          title="All Tickets"
        >
          <TicketCheck />
          {!collapsed && 'All Tickets'}
        </NavLink>
      </nav>

      <div className="sidebar-spacer" />

      {/* Footer */}
      <div className="sidebar-footer">
        <div className={`sidebar-footer-row${collapsed ? ' sidebar-footer-row-col' : ''}`}>
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
          <button className="btn btn-ghost btn-sm" onClick={onLogout} title="Sign out">
            <LogOut size={16} />
          </button>
        </div>

        {user && !collapsed && (
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

        {user && collapsed && (
          <div className="sidebar-user-avatar sidebar-user-avatar-center" title={user.name}>
            <User />
          </div>
        )}
      </div>
    </aside>
  );
}
