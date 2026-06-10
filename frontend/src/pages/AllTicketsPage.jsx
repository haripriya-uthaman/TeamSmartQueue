import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TicketCheck, ExternalLink, RefreshCw, Search, ChevronUp,
  ChevronDown, ChevronsUpDown, Users, AlertCircle,
} from 'lucide-react';
import './AllTicketsPage.css';

const API_BASE = '/api/v1';

const STATUS_META = {
  pending:             { cls: 'status-pending',    label: 'Pending' },
  processing:          { cls: 'status-processing', label: 'In Progress' },
  needs_clarification: { cls: 'status-clarify',    label: 'Needs Info' },
  completed:           { cls: 'status-done',       label: 'Done' },
  duplicate_found:     { cls: 'status-closed',     label: 'Duplicate' },
  failed:              { cls: 'status-closed',     label: 'Failed' },
  closed:              { cls: 'status-closed',     label: 'Closed' },
};

const PRIORITY_META = {
  Low:      'pri-low',
  Medium:   'pri-medium',
  High:     'pri-high',
  Critical: 'pri-critical',
};

function ScorePill({ score }) {
  if (score == null) return <span className="at-muted">—</span>;
  const pct = Math.min(100, Math.max(0, score));
  const cls = pct >= 80 ? 'score-high' : pct >= 50 ? 'score-mid' : 'score-low';
  return <span className={`at-score ${cls}`}>{pct}/100</span>;
}

function SortIcon({ col, sortKey, sortDir }) {
  if (sortKey !== col) return <ChevronsUpDown size={12} className="at-sort-icon dim" />;
  return sortDir === 'asc'
    ? <ChevronUp size={12} className="at-sort-icon" />
    : <ChevronDown size={12} className="at-sort-icon" />;
}

function TH({ col, label, className = '', sortKey, sortDir, onSort }) {
  return (
    <th className={`at-th sortable ${className}`} onClick={() => onSort(col)}>
      <span>{label}</span>
      <SortIcon col={col} sortKey={sortKey} sortDir={sortDir} />
    </th>
  );
}

export default function AllTicketsPage({ token, onLogout }) {
  const [tickets, setTickets]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [search, setSearch]     = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortKey, setSortKey]   = useState('created_at');
  const [sortDir, setSortDir]   = useState('desc');
  const navigate = useNavigate();

  const apiFetch = useCallback(async (url, options = {}) => {
    const res = await fetch(url, {
      ...options,
      headers: { Authorization: `Bearer ${token}`, ...options.headers },
    });
    if (res.status === 401) { onLogout?.(); throw new Error('Session expired'); }
    return res;
  }, [token, onLogout]);

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`${API_BASE}/tickets/`);
      if (res.ok) setTickets(await res.json());
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [apiFetch]);

  useEffect(() => { fetchTickets(); }, [fetchTickets]);

  // Sort toggle
  const handleSort = (col) => {
    if (sortKey === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(col); setSortDir('asc'); }
  };

  // Filter + search + sort
  const visible = tickets
    .filter(t => statusFilter === 'all' || t.status === statusFilter)
    .filter(t => {
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        t.title?.toLowerCase().includes(q) ||
        t.description?.toLowerCase().includes(q) ||
        String(t.id).includes(q)
      );
    })
    .sort((a, b) => {
      let av = a[sortKey], bv = b[sortKey];
      if (sortKey === 'created_at') { av = new Date(av); bv = new Date(bv); }
      if (sortKey === 'score') { av = av ?? -1; bv = bv ?? -1; }
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

  // Status counts for filter bar
  const counts = tickets.reduce((acc, t) => {
    acc[t.status] = (acc[t.status] || 0) + 1;
    return acc;
  }, {});

  const FILTER_TABS = [
    { key: 'all', label: 'All', count: tickets.length },
    { key: 'pending', label: 'Pending', count: counts.pending || 0 },
    { key: 'needs_clarification', label: 'Needs Info', count: counts.needs_clarification || 0 },
    { key: 'processing', label: 'In Progress', count: counts.processing || 0 },
    { key: 'completed', label: 'Done', count: counts.completed || 0 },
    { key: 'duplicate_found', label: 'Duplicate', count: counts.duplicate_found || 0 },
    { key: 'failed', label: 'Failed', count: (counts.failed || 0) + (counts.closed || 0) },
  ].filter(tab => tab.key === 'all' || tab.count > 0);

  return (
    <div className="at-page">
      {/* ── Top bar ── */}
      <div className="at-topbar">
        <div className="at-topbar-left">
          <TicketCheck size={17} />
          <h2>All Tickets</h2>
          <span className="at-total-badge">{tickets.length}</span>
        </div>
        <button className="btn btn-ghost btn-sm at-refresh" onClick={fetchTickets} title="Refresh" disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spinning' : ''} />
        </button>
      </div>

      {/* ── Toolbar ── */}
      <div className="at-toolbar">
        <div className="at-search-wrap">
          <Search size={14} className="at-search-icon" />
          <input
            className="at-search"
            placeholder="Search tickets…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {search && (
            <button className="at-search-clear" onClick={() => setSearch('')}>×</button>
          )}
        </div>

        <div className="at-filter-tabs">
          {FILTER_TABS.map(tab => (
            <button
              key={tab.key}
              className={`at-filter-tab ${statusFilter === tab.key ? 'active' : ''}`}
              onClick={() => setStatusFilter(tab.key)}
            >
              {tab.label}
              {tab.count > 0 && <span className="at-filter-count">{tab.count}</span>}
            </button>
          ))}
        </div>
      </div>

      {/* ── Table ── */}
      <div className="at-body">
        {loading ? (
          <div className="at-state">
            <div className="spinner" style={{ width: 24, height: 24 }} />
            <span>Loading tickets…</span>
          </div>
        ) : tickets.length === 0 ? (
          <div className="at-state">
            <TicketCheck size={40} className="at-state-icon" />
            <p>No tickets yet.</p>
            <button className="btn btn-primary btn-sm" onClick={() => navigate('/dashboard')}>
              Create first ticket
            </button>
          </div>
        ) : visible.length === 0 ? (
          <div className="at-state">
            <AlertCircle size={32} className="at-state-icon" />
            <p>No tickets match your search.</p>
            <button className="btn btn-ghost btn-sm" onClick={() => { setSearch(''); setStatusFilter('all'); }}>
              Clear filters
            </button>
          </div>
        ) : (
          <div className="at-table-wrap">
            <table className="at-table">
              <thead>
                <tr>
                  <TH col="id"         label="ID"       className="col-id" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <TH col="title"      label="Title"    className="col-title" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <TH col="priority"   label="Priority" className="col-priority" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <TH col="status"     label="Status"   className="col-status" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <TH col="score"      label="Score"    className="col-score" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <TH col="created_at" label="Created"  className="col-date" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <th className="at-th col-issue">GitHub</th>
                </tr>
              </thead>
              <tbody>
                {visible.map(t => {
                  const sm = STATUS_META[t.status] || { cls: 'status-pending', label: t.status };
                  return (
                    <tr
                      key={t.id}
                      className="at-row"
                      onClick={() => navigate('/dashboard', { state: { openTicketId: t.id } })}
                    >
                      <td className="col-id">
                        <span className="at-ticket-id">TK-{String(t.id).padStart(3, '0')}</span>
                      </td>
                      <td className="col-title">
                        <div className="at-title-cell">
                          <span className="at-title-text">{t.title}</span>
                          {t.affected_count > 1 && (
                            <span className="at-affected" title={`${t.affected_count} users affected`}>
                              <Users size={10} /> {t.affected_count}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="col-priority">
                        {t.priority
                          ? <span className={`at-badge ${PRIORITY_META[t.priority] || ''}`}>{t.priority}</span>
                          : <span className="at-muted">—</span>}
                      </td>
                      <td className="col-status">
                        <span className={`at-status ${sm.cls}`}>{sm.label}</span>
                      </td>
                      <td className="col-score"><ScorePill score={t.score} /></td>
                      <td className="col-date at-muted">
                        {new Date(t.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </td>
                      <td className="col-issue">
                        {t.github_issue_url ? (
                          <a
                            href={t.github_issue_url}
                            target="_blank"
                            rel="noreferrer"
                            className="at-gh-link"
                            onClick={e => e.stopPropagation()}
                          >
                            #{t.github_issue_number} <ExternalLink size={11} />
                          </a>
                        ) : <span className="at-muted">—</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Footer count ── */}
      {!loading && visible.length > 0 && (
        <div className="at-footer">
          Showing {visible.length} of {tickets.length} ticket{tickets.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}
