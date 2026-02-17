import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function SelectPages() {
    const navigate = useNavigate();
    const [pages, setPages] = useState([]);
    const [suggestions, setSuggestions] = useState([]);
    const [baseUrl, setBaseUrl] = useState('');
    const [search, setSearch] = useState('');
    const [guidelineSetId, setGuidelineSetId] = useState(null);
    const [guidelineVersion, setGuidelineVersion] = useState(null);
    const [guidelines, setGuidelines] = useState([]);
    const [runAxe, setRunAxe] = useState(true);
    const [runLlm, setRunLlm] = useState(true);
    const [runDeterministic, setRunDeterministic] = useState(true);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        const data = sessionStorage.getItem('discoveryResult');
        const url = sessionStorage.getItem('baseUrl');
        if (data) {
            const result = JSON.parse(data);
            setPages(result.pages || []);
            setSuggestions(result.smart_exclude_suggestions || []);
        }
        if (url) setBaseUrl(url);

        // Load guidelines
        api.listGuidelines().then(r => setGuidelines(r.sets || [])).catch(() => { });
    }, []);

    const filteredPages = useMemo(() => {
        if (!search) return pages;
        const q = search.toLowerCase();
        return pages.filter(p => p.url.toLowerCase().includes(q) || (p.title || '').toLowerCase().includes(q));
    }, [pages, search]);

    const selectedCount = pages.filter(p => p.selected).length;

    const togglePage = (idx) => {
        setPages(prev => prev.map((p, i) => i === idx ? { ...p, selected: !p.selected } : p));
    };

    const selectAll = () => setPages(prev => prev.map(p => ({ ...p, selected: true })));
    const deselectAll = () => setPages(prev => prev.map(p => ({ ...p, selected: false })));

    const handleStartValidation = async () => {
        const selectedUrls = pages.filter(p => p.selected).map(p => p.url);
        if (selectedUrls.length === 0) return;

        setLoading(true);
        setError(null);

        try {
            const job = await api.startValidation({
                base_url: baseUrl,
                page_urls: selectedUrls,
                guideline_set_id: guidelineSetId,
                guideline_version: guidelineVersion,
                run_axe: runAxe,
                run_llm: runLlm,
                run_deterministic: runDeterministic,
            });
            navigate(`/run/${job.id}`);
        } catch (err) {
            setError(err.message || 'Failed to start validation');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <div className="page-header">
                <h2>📑 Select Pages</h2>
                <p>Choose which pages to validate ({selectedCount} of {pages.length} selected)</p>
            </div>

            {suggestions.length > 0 && (
                <div className="alert alert-warning">
                    💡 <strong>Smart Suggestions:</strong> {suggestions.length} pages may not need validation
                    (e.g., {suggestions.slice(0, 3).map(s => s.reason).join(', ')}).
                </div>
            )}

            <div className="card">
                <div className="filter-bar">
                    <input
                        className="input"
                        placeholder="🔎 Search pages..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                    <button className="btn btn-secondary btn-sm" onClick={selectAll}>Select All</button>
                    <button className="btn btn-secondary btn-sm" onClick={deselectAll}>Deselect All</button>
                </div>

                <div className="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th style={{ width: '40px' }}>✓</th>
                                <th>URL</th>
                                <th>Title</th>
                                <th>Source</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredPages.map((page, idx) => (
                                <tr key={page.url} onClick={() => togglePage(idx)} style={{ cursor: 'pointer' }}>
                                    <td>
                                        <input type="checkbox" checked={page.selected} readOnly />
                                    </td>
                                    <td style={{ maxWidth: '400px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {page.url}
                                    </td>
                                    <td>{page.title || '—'}</td>
                                    <td><span className="badge badge-accent">{page.source}</span></td>
                                </tr>
                            ))}
                            {filteredPages.length === 0 && (
                                <tr><td colSpan="4" className="empty-state"><p>No pages found. Go back to discover pages.</p></td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Validation Options */}
            <div className="card">
                <div className="card-header">
                    <h3>⚙️ Validation Options</h3>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div>
                        <div className="input-group">
                            <label>Guideline Set</label>
                            <select
                                value={guidelineSetId || ''}
                                onChange={(e) => setGuidelineSetId(e.target.value ? parseInt(e.target.value) : null)}
                            >
                                <option value="">None (built-in rules only)</option>
                                {guidelines.map(gs => (
                                    <option key={gs.id} value={gs.id}>{gs.name}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                    <div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', paddingTop: '22px' }}>
                            <label className="checkbox-label">
                                <input type="checkbox" checked={runDeterministic} onChange={(e) => setRunDeterministic(e.target.checked)} />
                                Deterministic Checks
                            </label>
                            <label className="checkbox-label">
                                <input type="checkbox" checked={runLlm} onChange={(e) => setRunLlm(e.target.checked)} />
                                LLM Validation
                            </label>
                            <label className="checkbox-label">
                                <input type="checkbox" checked={runAxe} onChange={(e) => setRunAxe(e.target.checked)} />
                                Accessibility (axe-core)
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            {error && <div className="alert alert-error">⚠️ {error}</div>}

            <div className="action-bar">
                <button className="btn btn-secondary" onClick={() => navigate('/scan')}>← Back</button>
                <button className="btn btn-primary" onClick={handleStartValidation} disabled={loading || selectedCount === 0}>
                    {loading ? (
                        <><span className="spinner"></span> Starting...</>
                    ) : (
                        `🚀 Validate ${selectedCount} Page${selectedCount !== 1 ? 's' : ''}`
                    )}
                </button>
            </div>
        </div>
    );
}
