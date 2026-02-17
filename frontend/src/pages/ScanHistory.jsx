import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';

export default function ScanHistory() {
    const [baseUrl, setBaseUrl] = useState('');
    const [scans, setScans] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [diffResult, setDiffResult] = useState(null);
    const [diffing, setDiffing] = useState(false);

    const loadScans = async () => {
        setLoading(true);
        setError(null);
        try {
            let data;
            if (baseUrl.trim()) {
                data = await api.listScans(baseUrl.trim());
            } else {
                data = await api.listRecentScans();
            }
            setScans(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadScans();
    }, []);

    const handleCompare = async (scanId) => {
        setDiffing(true);
        setDiffResult(null);
        try {
            const result = await api.compareToLast(scanId);
            setDiffResult(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setDiffing(false);
        }
    };

    return (
        <div>
            <div className="page-header">
                <h2>📊 Scan History</h2>
                <p>View past scans and compare for regressions</p>
            </div>

            <div className="card">
                <div className="filter-bar">
                    <input
                        className="input"
                        placeholder="Enter base URL to search scans..."
                        value={baseUrl}
                        onChange={(e) => setBaseUrl(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && loadScans()}
                    />
                    <button className="btn btn-primary btn-sm" onClick={loadScans} disabled={loading}>
                        {loading ? <span className="spinner"></span> : '🔎 Search'}
                    </button>
                </div>

                {error && <div className="alert alert-error">⚠️ {error}</div>}

                {scans.length > 0 && (
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Status</th>
                                    <th>Pages</th>
                                    <th>Issues</th>
                                    <th>Created</th>
                                    <th>Completed</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {scans.map(scan => (
                                    <tr key={scan.id}>
                                        <td>#{scan.id}</td>
                                        <td>
                                            <span className={`badge ${scan.status === 'COMPLETED' ? 'badge-low' : scan.status === 'FAILED' ? 'badge-high' : 'badge-accent'}`}>
                                                {scan.status}
                                            </span>
                                        </td>
                                        <td>{scan.total_pages}</td>
                                        <td>{scan.total_issues}</td>
                                        <td>{new Date(scan.created_at).toLocaleString()}</td>
                                        <td>{scan.finished_at ? new Date(scan.finished_at).toLocaleString() : '—'}</td>
                                        <td>
                                            <div style={{ display: 'flex', gap: '6px' }}>
                                                <Link to={`/results/${scan.id}`} className="btn btn-secondary btn-sm">📋 Results</Link>
                                                <button className="btn btn-secondary btn-sm" onClick={() => handleCompare(scan.id)} disabled={diffing}>
                                                    🔄 Diff
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {scans.length === 0 && !loading && (
                    <div className="empty-state">
                        <div className="icon">📊</div>
                        <h3>No scans found</h3>
                        <p>Enter a base URL to see its scan history, or start a new scan.</p>
                    </div>
                )}
            </div>

            {/* Diff Result */}
            {diffResult && (
                <div className="card">
                    <div className="card-header">
                        <h3>🔄 Scan Comparison</h3>
                        <span className="tag">Scan #{diffResult.scan_a_id} → #{diffResult.scan_b_id}</span>
                    </div>
                    <div className="stats-grid">
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: 'var(--danger)' }}>{diffResult.new_issues?.length || 0}</div>
                            <div className="stat-label">New Issues (Regressions)</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: 'var(--success)' }}>{diffResult.resolved_issues?.length || 0}</div>
                            <div className="stat-label">Resolved Issues</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{diffResult.unchanged_count}</div>
                            <div className="stat-label">Unchanged</div>
                        </div>
                    </div>

                    {diffResult.new_issues?.length > 0 && (
                        <div style={{ marginTop: '16px' }}>
                            <h4 style={{ marginBottom: '8px', color: 'var(--danger)' }}>🔴 New Issues</h4>
                            {diffResult.new_issues.slice(0, 10).map((issue, idx) => (
                                <div key={idx} style={{ padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: '0.85rem' }}>
                                    <span className={`badge badge-${String(issue.severity).toLowerCase()}`} style={{ marginRight: '8px' }}>
                                        {String(issue.severity).toUpperCase()}
                                    </span>
                                    <strong>{issue.category}</strong> — {issue.evidence?.substring(0, 100)}
                                </div>
                            ))}
                        </div>
                    )}

                    {diffResult.resolved_issues?.length > 0 && (
                        <div style={{ marginTop: '16px' }}>
                            <h4 style={{ marginBottom: '8px', color: 'var(--success)' }}>🟢 Resolved Issues</h4>
                            {diffResult.resolved_issues.slice(0, 10).map((issue, idx) => (
                                <div key={idx} style={{ padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: '0.85rem' }}>
                                    <span className={`badge badge-${String(issue.severity).toLowerCase()}`} style={{ marginRight: '8px' }}>
                                        {String(issue.severity).toUpperCase()}
                                    </span>
                                    <strong>{issue.category}</strong> — {issue.evidence?.substring(0, 100)}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
