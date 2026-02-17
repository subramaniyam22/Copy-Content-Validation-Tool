import React, { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import api from '../api';

export default function Results() {
    const { jobId } = useParams();
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedIssue, setSelectedIssue] = useState(null);
    const [filter, setFilter] = useState({
        severity: 'all',
        category: 'all',
        source: 'all',
        search: ''
    });

    useEffect(() => {
        api.getJobResults(jobId)
            .then(res => {
                setResults(res);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message || 'Failed to load results');
                setLoading(false);
            });
    }, [jobId]);

    const filteredIssues = useMemo(() => {
        if (!results) return [];
        let all = [];
        results.pages.forEach(p => {
            p.issues.forEach(i => {
                all.push({ ...i, page_url: p.url, page_title: p.title });
            });
        });

        return all.filter(i => {
            if (filter.severity !== 'all' && i.severity !== filter.severity) return false;
            if (filter.category !== 'all' && i.category !== filter.category) return false;
            if (filter.source !== 'all' && String(i.source) !== filter.source) return false;
            if (filter.search) {
                const q = filter.search.toLowerCase();
                return (
                    i.type.toLowerCase().includes(q) ||
                    i.explanation.toLowerCase().includes(q) ||
                    (i.evidence || '').toLowerCase().includes(q)
                );
            }
            return true;
        });
    }, [results, filter]);

    const stats = results?.summary || { total: 0, high: 0, medium: 0, low: 0 };

    if (loading) return <div className="loading-state"><span className="spinner"></span> Loading results...</div>;
    if (error) return <div className="alert alert-error">⚠️ {error}</div>;
    if (!results) return <div className="empty-state">No results found for Job #{jobId}</div>;

    const severityBadge = (s) => {
        switch (s.toLowerCase()) {
            case 'high': return 'badge-error';
            case 'medium': return 'badge-warning';
            case 'low': return 'badge-success';
            default: return 'badge-secondary';
        }
    };

    return (
        <div style={{ maxWidth: '1600px', margin: '0 auto' }}>
            <div className="page-header">
                <h2>📊 Validation Results</h2>
                <p>Job #{jobId} — {stats.total} issues found across {results.pages.length} pages</p>
            </div>

            {/* Summary Cards */}
            <div className="stats-grid" style={{ marginBottom: '24px' }}>
                <div className="stat-card">
                    <div className="stat-value">{stats.total}</div>
                    <div className="stat-label">TOTAL ISSUES</div>
                </div>
                <div className="stat-card" style={{ borderLeft: '4px solid var(--error)' }}>
                    <div className="stat-value" style={{ color: 'var(--error)' }}>{stats.high}</div>
                    <div className="stat-label">HIGH SEVERITY</div>
                </div>
                <div className="stat-card" style={{ borderLeft: '4px solid var(--warning)' }}>
                    <div className="stat-value" style={{ color: 'var(--warning)' }}>{stats.medium}</div>
                    <div className="stat-label">MEDIUM SEVERITY</div>
                </div>
                <div className="stat-card" style={{ borderLeft: '4px solid var(--success)' }}>
                    <div className="stat-value" style={{ color: 'var(--success)' }}>{stats.low}</div>
                    <div className="stat-label">LOW SEVERITY</div>
                </div>
            </div>

            {/* Filters */}
            <div className="card" style={{ marginBottom: '16px' }}>
                <div className="filter-bar">
                    <input
                        className="input"
                        placeholder="🔎 Search issues..."
                        value={filter.search}
                        onChange={(e) => setFilter({ ...filter, search: e.target.value })}
                        style={{ flex: 2 }}
                    />
                    <select value={filter.severity} onChange={(e) => setFilter({ ...filter, severity: e.target.value })}>
                        <option value="all">All Severities</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                    <select value={filter.category} onChange={(e) => setFilter({ ...filter, category: e.target.value })}>
                        <option value="all">All Categories</option>
                        {Object.keys(results.summary.by_category).map(c => (
                            <option key={c} value={c}>{c}</option>
                        ))}
                    </select>
                    <select value={filter.source} onChange={(e) => setFilter({ ...filter, source: e.target.value })}>
                        <option value="all">All Sources</option>
                        {Object.keys(results.summary.by_source).map(s => (
                            <option key={s} value={s}>{s}</option>
                        ))}
                    </select>
                </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                <a href={api.exportCsvUrl(jobId)} className="btn btn-secondary btn-sm" download>📥 CSV</a>
                <a href={api.exportXlsxUrl(jobId)} className="btn btn-secondary btn-sm" download>📥 XLSX</a>
            </div>

            {/* Issues Split View */}
            <div className={`split-view-container ${selectedIssue ? 'has-detail' : ''}`}>
                <div className={`split-view-master ${selectedIssue ? 'shrunk' : ''}`}>
                    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: '600px' }}>
                        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <h3>Issues ({filteredIssues.length})</h3>
                        </div>
                        <div className="table-container" style={{ flex: 1 }}>
                            <table>
                                <thead>
                                    <tr>
                                        <th style={{ width: '80px' }}>SEVERITY</th>
                                        <th>CATEGORY</th>
                                        <th>TYPE</th>
                                        <th>GUIDELINE</th>
                                        <th>PAGE</th>
                                        <th>EVIDENCE</th>
                                        <th style={{ width: '100px' }}>SOURCE</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredIssues.map((issue, idx) => (
                                        <tr
                                            key={issue.id || idx}
                                            className={selectedIssue?.id === issue.id ? 'selected-row' : ''}
                                            onClick={() => setSelectedIssue(issue)}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <td>
                                                <span className={`badge ${severityBadge(issue.severity)}`}>
                                                    {issue.severity.toUpperCase()}
                                                </span>
                                            </td>
                                            <td>{issue.category}</td>
                                            <td>{issue.type.replace(/_/g, ' ')}</td>
                                            <td style={{ color: 'var(--accent-bright)', fontWeight: 600 }}>
                                                {issue.guideline_set_name || '—'}
                                            </td>
                                            <td style={{ maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                {issue.page_url}
                                            </td>
                                            <td style={{ maxWidth: '250px' }}>
                                                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontStyle: 'italic', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                    {issue.evidence ? `"${issue.evidence}"` : 'N/A'}
                                                </div>
                                            </td>
                                            <td><span className="badge badge-secondary">{issue.source}</span></td>
                                        </tr>
                                    ))}
                                    {filteredIssues.length === 0 && (
                                        <tr><td colSpan="7" className="empty-state">No issues found.</td></tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div className="split-view-detail">
                    {selectedIssue ? (
                        <div className="detail-panel-content">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                                <h3 style={{ margin: 0 }}>Issue Details</h3>
                                <button className="btn btn-secondary btn-sm" onClick={() => setSelectedIssue(null)}>✕ Close</button>
                            </div>

                            <div className="detail-section">
                                <label>Guideline Source</label>
                                <div style={{ color: 'var(--accent-bright)', fontSize: '1.2rem', fontWeight: 600, marginBottom: '4px' }}>
                                    {selectedIssue.guideline_set_name || 'General Standard'}
                                </div>
                                {selectedIssue.guideline_source_file && (
                                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                                        File: <span style={{ fontWeight: 500 }}>{selectedIssue.guideline_source_file}</span>
                                    </div>
                                )}
                                {(selectedIssue.guideline_section || selectedIssue.guideline_rule_id) && (
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                        {selectedIssue.guideline_section ? `Section: ${selectedIssue.guideline_section}` : `Rule ID: ${selectedIssue.guideline_rule_id}`}
                                    </div>
                                )}
                            </div>

                            <div className="detail-section">
                                <label>Problem Description</label>
                                <p style={{ lineHeight: '1.6', fontSize: '0.95rem' }}>{selectedIssue.explanation}</p>
                            </div>

                            <div className="detail-section">
                                <label>Evidence Found</label>
                                <div className="code-block" style={{
                                    background: 'var(--bg-input)',
                                    padding: '16px',
                                    borderRadius: 'var(--radius-md)',
                                    borderLeft: '4px solid var(--accent)',
                                    fontSize: '0.9rem',
                                    fontFamily: 'monospace',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-all'
                                }}>
                                    {selectedIssue.evidence || 'No specific snippet available.'}
                                </div>
                            </div>

                            <div className="detail-section">
                                <label>Recommended Fix</label>
                                <div style={{
                                    color: 'var(--success)',
                                    fontWeight: 500,
                                    background: 'rgba(74, 222, 128, 0.1)',
                                    padding: '16px',
                                    borderRadius: 'var(--radius-md)',
                                    border: '1px solid rgba(74, 222, 128, 0.2)',
                                    fontSize: '0.95rem'
                                }}>
                                    {selectedIssue.proposed_fix}
                                </div>
                            </div>

                            <div className="detail-section">
                                <label>Occurrence Location</label>
                                <div style={{ fontSize: '0.85rem', wordBreak: 'break-all' }}>
                                    <a href={selectedIssue.page_url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)', textDecoration: 'underline' }}>
                                        {selectedIssue.page_url}
                                    </a>
                                </div>
                            </div>

                            <div style={{ marginTop: 'auto', paddingTop: '20px', borderTop: '1px solid var(--border)', fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                                <span>Detection Method: {selectedIssue.source.toUpperCase()}</span>
                                <span>Confidence: {(selectedIssue.confidence * 100).toFixed(0)}%</span>
                            </div>
                        </div>
                    ) : (
                        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', color: 'var(--text-muted)', textAlign: 'center', padding: '40px' }}>
                            <div style={{ fontSize: '4rem', marginBottom: '20px', opacity: 0.5 }}>🖱️</div>
                            <h3 style={{ color: 'var(--text-primary)', marginBottom: '12px' }}>Select an issue</h3>
                            <p style={{ maxWidth: '250px' }}>Click any row in the table to view the full evidence and proposed fixes here.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
