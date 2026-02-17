import React, { useState, useEffect } from 'react';
import api from '../api';

export default function Guidelines() {
    const [guidelines, setGuidelines] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [name, setName] = useState('');
    const [files, setFiles] = useState(null);
    const [error, setError] = useState(null);
    const [expandedSet, setExpandedSet] = useState(null);
    const [rules, setRules] = useState([]);

    const loadGuidelines = async () => {
        try {
            const data = await api.listGuidelines();
            setGuidelines(data.sets || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadGuidelines(); }, []);

    const handleUpload = async (e) => {
        e.preventDefault();
        if (!name || !files || files.length === 0) return;

        setUploading(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append('name', name);
            for (const file of files) {
                formData.append('files', file);
            }

            await api.uploadGuidelines(formData);
            setName('');
            setFiles(null);
            await loadGuidelines();
        } catch (err) {
            setError(err.message || 'Upload failed');
        } finally {
            setUploading(false);
        }
    };

    const viewRules = async (setId, versionId) => {
        const key = `${setId}-${versionId}`;
        if (expandedSet === key) {
            setExpandedSet(null);
            return;
        }
        try {
            const data = await api.getGuidelineRules(setId, versionId);
            setRules(data);
            setExpandedSet(key);
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div>
            <div className="page-header">
                <h2>📋 Guidelines</h2>
                <p>Upload style guides to extract validation rules</p>
            </div>

            {/* Upload */}
            <div className="card">
                <div className="card-header">
                    <h3>📁 Upload New Guidelines</h3>
                </div>
                <form onSubmit={handleUpload}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                        <div className="input-group">
                            <label>Guideline Set Name</label>
                            <input
                                className="input"
                                placeholder="e.g., Brand Style Guide 2025"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                required
                            />
                        </div>
                        <div className="input-group">
                            <label>Files (PDF, DOCX, TXT, XLSX, CSV)</label>
                            <input
                                className="input"
                                type="file"
                                accept=".pdf,.docx,.txt,.xlsx,.csv"
                                multiple
                                onChange={(e) => setFiles(e.target.files)}
                                required
                            />
                        </div>
                    </div>
                    <button className="btn btn-primary" type="submit" disabled={uploading}>
                        {uploading ? <><span className="spinner"></span> Processing...</> : '📤 Upload & Extract Rules'}
                    </button>
                </form>
            </div>

            {error && <div className="alert alert-error">⚠️ {error}</div>}

            {/* Existing Guidelines */}
            {loading ? (
                <div className="loading-overlay"><div className="spinner"></div><p>Loading guidelines...</p></div>
            ) : guidelines.length === 0 ? (
                <div className="empty-state">
                    <div className="icon">📋</div>
                    <h3>No guidelines yet</h3>
                    <p>Upload your brand style guide or content guidelines to enable rule-based validation.</p>
                </div>
            ) : (
                guidelines.map(gs => (
                    <div className="card" key={gs.id}>
                        <div className="card-header">
                            <h3>{gs.name}</h3>
                            <span className="tag">Created {new Date(gs.created_at).toLocaleDateString()}</span>
                        </div>
                        {gs.versions && gs.versions.map(v => (
                            <div key={v.id} style={{ padding: '10px 0', borderTop: '1px solid var(--border)' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <div>
                                        <strong>Version {v.version_number}</strong>
                                        <span style={{ marginLeft: '12px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                                            {v.rules_count} rules extracted
                                        </span>
                                        {v.model_used && (
                                            <span className="tag" style={{ marginLeft: '8px' }}>{v.model_used}</span>
                                        )}
                                    </div>
                                    <button
                                        className="btn btn-secondary btn-sm"
                                        onClick={() => viewRules(gs.id, v.id)}
                                    >
                                        {expandedSet === `${gs.id}-${v.id}` ? 'Hide Rules' : 'View Rules'}
                                    </button>
                                </div>
                                {expandedSet === `${gs.id}-${v.id}` && rules.length > 0 && (
                                    <div className="table-container" style={{ marginTop: '12px' }}>
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th>Rule ID</th>
                                                    <th>Category</th>
                                                    <th>Severity</th>
                                                    <th>Source File</th>
                                                    <th>Rule</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {rules.map(r => (
                                                    <tr key={r.id}>
                                                        <td><span className="tag">{r.rule_id}</span></td>
                                                        <td>{r.category}</td>
                                                        <td><span className={`badge badge-${r.severity_default}`}>{r.severity_default}</span></td>
                                                        <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                                            {r.source_file || '—'}
                                                        </td>
                                                        <td style={{ maxWidth: '400px' }}>{r.rule_text}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                ))
            )}
        </div>
    );
}
