import { useState, useCallback, useEffect } from 'react';
import {
  Plus, Inbox, FileText, Search, Eye,
  CheckCircle2, AlertTriangle, XCircle, Loader2,
  Send, ExternalLink, ClipboardList, AlertCircle,
  TriangleAlert, GitBranch
} from 'lucide-react';
import './DashboardPage.css';

const API_BASE = 'http://127.0.0.1:8000/api/v1';

function getStatusBadge(status) {
  const map = {
    pending:               { cls: 'badge-neutral', label: 'Pending' },
    processing:            { cls: 'badge-info',    label: 'Processing' },
    needs_clarification:   { cls: 'badge-warning', label: 'Needs Info' },
    completed:             { cls: 'badge-success', label: 'Completed' },
    duplicate_found:       { cls: 'badge-error',   label: 'Duplicate' },
    failed:                { cls: 'badge-error',   label: 'Failed' },
  };
  const m = map[status] || { cls: 'badge-neutral', label: status };
  return <span className={`badge ${m.cls}`}>{m.label}</span>;
}

export default function DashboardPage({ token }) {
  const [tickets, setTickets] = useState([]);
  const [activeTicket, setActiveTicket] = useState(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [submittingAnswers, setSubmittingAnswers] = useState(false);
  const [error, setError] = useState(null);
  const [answers, setAnswers] = useState({});
  const [showForm, setShowForm] = useState(false);

  const fetchTickets = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/tickets/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) setTickets(await res.json());
    } catch (err) {
      console.error('Error fetching tickets:', err);
    }
  }, [token]);

  const fetchTicketDetails = useCallback(async (id, silent = false) => {
    try {
      if (!silent) setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE}/tickets/${id}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setActiveTicket(data);
        setAnswers(prev => {
          const next = { ...prev };
          if (data.questions) {
            data.questions.forEach(q => {
              if (next[q.question_id] === undefined) next[q.question_id] = '';
            });
          }
          return next;
        });
      }
    } catch (err) {
      console.error('Error fetching details:', err);
    } finally {
      if (!silent) setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    queueMicrotask(fetchTickets);
  }, [fetchTickets]);

  // Polling for processing tickets
  useEffect(() => {
    let intervalId;
    if (activeTicket && (activeTicket.status === 'processing' || activeTicket.status === 'pending')) {
      intervalId = setInterval(() => {
        fetchTicketDetails(activeTicket.id, true);
        fetchTickets();
      }, 2500);
    }
    return () => { if (intervalId) clearInterval(intervalId); };
  }, [activeTicket, fetchTicketDetails, fetchTickets]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title || !description) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/tickets/submit`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ title, description })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Submission failed.');
      }
      const data = await res.json();
      await fetchTickets();
      if (data.ticket_id) await fetchTicketDetails(data.ticket_id);
      setTitle('');
      setDescription('');
      setShowForm(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerSubmit = async (e) => {
    e.preventDefault();
    if (!activeTicket) return;
    const payload = Object.keys(answers).map(qid => ({
      question_id: qid,
      answer_text: answers[qid]
    }));
    setSubmittingAnswers(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/tickets/${activeTicket.id}/clarify`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Clarification failed.');
      }
      await fetchTickets();
      await fetchTicketDetails(activeTicket.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmittingAnswers(false);
    }
  };

  return (
    <>
      {/* Top bar */}
      <div className="dashboard-topbar">
        <h2>Dashboard</h2>
        <div className="topbar-actions">
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm(!showForm)}>
            <Plus size={15} />
            New Ticket
          </button>
        </div>
      </div>

      <div className="dashboard-content">
        {/* Left: Ticket list */}
        <div className="ticket-list-panel">
          <div className="ticket-list-header">
            <h3>Tickets</h3>
            <span className="ticket-list-count">{tickets.length}</span>
          </div>
          <div className="ticket-list-body">
            {tickets.length === 0 ? (
              <div className="ticket-list-empty">
                <Inbox />
                <p>No tickets yet</p>
              </div>
            ) : (
              tickets.map(t => (
                <div
                  key={t.id}
                  className={`ticket-item ${activeTicket?.id === t.id ? 'active' : ''}`}
                  onClick={() => fetchTicketDetails(t.id)}
                >
                  <div className="ticket-item-top">
                    <span className="ticket-item-id">TK-{String(t.id).padStart(3, '0')}</span>
                    {getStatusBadge(t.status)}
                  </div>
                  <div className="ticket-item-title">{t.title}</div>
                  <span className="ticket-item-date">
                    {new Date(t.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Detail panel */}
        <div className="detail-panel">
          {error && (
            <div className="status-block status-block-failed" style={{ marginBottom: '1rem' }}>
              <div className="status-block-title"><AlertCircle /> Error</div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>{error}</p>
            </div>
          )}

          {/* Submit form */}
          {showForm && (
            <div className="card submit-card">
              <div className="detail-section-title" style={{ marginBottom: '1rem' }}>
                <Plus size={15} />
                Audit a New Ticket
              </div>
              <form className="submit-form" onSubmit={handleSubmit}>
                <div className="form-field">
                  <label htmlFor="submit-title">Issue Title</label>
                  <input
                    id="submit-title"
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g., Dashboard button overlaps header text"
                    required
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="submit-desc">Description</label>
                  <textarea
                    id="submit-desc"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Steps to reproduce, environment, expected & actual behavior..."
                    rows="4"
                    required
                  />
                </div>
                <div className="submit-form-actions">
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowForm(false)} style={{ marginRight: '0.5rem' }}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary btn-sm" disabled={loading}>
                    {loading ? <><Loader2 size={14} className="spinner" /> Auditing...</> : <><Send size={14} /> Submit Ticket</>}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* No ticket selected */}
          {!activeTicket && !showForm && (
            <div className="detail-empty">
              <Eye />
              <p>Select a ticket to view details or create a new one</p>
            </div>
          )}

          {/* Active ticket details */}
          {activeTicket && (
            <>
              <div className="detail-header">
                <div className="detail-header-left">
                  <h2>{activeTicket.title}</h2>
                  <div className="detail-meta">
                    <span>TK-{String(activeTicket.id).padStart(3, '0')}</span>
                    {getStatusBadge(activeTicket.status)}
                    {activeTicket.score !== null && activeTicket.score !== undefined && (
                      <span>Score: {activeTicket.score}/100</span>
                    )}
                    <span>{new Date(activeTicket.created_at).toLocaleString()}</span>
                  </div>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={() => setActiveTicket(null)}>
                  <XCircle size={16} />
                </button>
              </div>

              {/* Original description */}
              <div className="detail-section">
                <div className="detail-section-title">
                  <FileText />
                  Original Description
                </div>
                <div className="detail-description">{activeTicket.description}</div>
              </div>

              {/* Findings & Missing info */}
              {((activeTicket.findings?.length > 0) || (activeTicket.missing_information?.length > 0)) && (
                <div className="detail-section">
                  <div className="detail-grid">
                    {activeTicket.findings?.length > 0 && (
                      <div className="detail-list-card">
                        <h4><Search size={14} /> Audit Findings</h4>
                        <ul>
                          {activeTicket.findings.map((f, i) => <li key={i}>{f}</li>)}
                        </ul>
                      </div>
                    )}
                    {activeTicket.missing_information?.length > 0 && (
                      <div className="detail-list-card">
                        <h4><TriangleAlert size={14} /> Missing Details</h4>
                        <ul>
                          {activeTicket.missing_information.map((m, i) => <li key={i}>{m}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Processing */}
              {activeTicket.status === 'processing' && (
                <div className="status-block status-block-processing">
                  <div className="status-block-title"><Loader2 /> Processing</div>
                  <div className="processing-indicator">
                    <div className="spinner"></div>
                    Analyzing ticket, checking duplicates, publishing to GitHub...
                  </div>
                </div>
              )}

              {/* Failed */}
              {activeTicket.status === 'failed' && (
                <div className="status-block status-block-failed">
                  <div className="status-block-title"><XCircle /> Pipeline Failed</div>
                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                    An error occurred during processing. This may be due to API rate limits or service unavailability.
                  </p>
                </div>
              )}

              {/* Needs clarification */}
              {activeTicket.status === 'needs_clarification' && (
                <div className="status-block status-block-clarification">
                  <div className="status-block-title"><AlertTriangle /> Clarification Required</div>
                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                    The auditor identified missing information. Please answer the questions below.
                  </p>
                  <form className="clarification-form" onSubmit={handleAnswerSubmit}>
                    {activeTicket.questions?.map(q => (
                      <div key={q.question_id} className="form-field">
                        <label>{q.question_text}</label>
                        <input
                          type="text"
                          value={answers[q.question_id] || ''}
                          onChange={(e) => setAnswers(prev => ({ ...prev, [q.question_id]: e.target.value }))}
                          placeholder={`Details about ${q.field_or_topic}`}
                          required
                        />
                      </div>
                    ))}
                    <div className="submit-form-actions">
                      <button type="submit" className="btn btn-primary btn-sm" disabled={submittingAnswers}>
                        {submittingAnswers ? <><Loader2 size={14} /> Submitting...</> : <><Send size={14} /> Submit Answers</>}
                      </button>
                    </div>
                  </form>
                </div>
              )}

              {/* Duplicate found */}
              {activeTicket.status === 'duplicate_found' && (
                <div className="status-block status-block-duplicate">
                  <div className="status-block-title"><ClipboardList /> Duplicate Detected</div>
                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                    This ticket closely matches an existing entry. Similarity exceeds the 85% threshold.
                  </p>
                </div>
              )}

              {/* Completed */}
              {activeTicket.status === 'completed' && (
                <div className="status-block status-block-completed">
                  <div className="status-block-title"><CheckCircle2 /> Completed</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                    <span className="badge badge-success" style={{ fontSize: '0.8125rem', padding: '0.25rem 0.625rem' }}>
                      Score: {activeTicket.score}/100
                    </span>
                  </div>
                  {activeTicket.github_issue_url && (
                    <a href={activeTicket.github_issue_url} target="_blank" rel="noreferrer" className="github-link">
                      <GitBranch size={14} />
                      View GitHub Issue #{activeTicket.github_issue_number}
                      <ExternalLink size={12} />
                    </a>
                  )}

                  {activeTicket.rewritten_title && (
                    <div className="rewritten-block">
                      <h4>Rewritten Ticket</h4>
                      <div className="rewritten-body">
                        <h5>{activeTicket.rewritten_title}</h5>
                        <pre>{activeTicket.rewritten_description}</pre>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
