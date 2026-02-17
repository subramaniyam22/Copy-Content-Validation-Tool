import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function NewScan() {
    const navigate = useNavigate();
    const [url, setUrl] = useState('');
    const [useSitemap, setUseSitemap] = useState(true);
    const [useNav, setUseNav] = useState(true);
    const [crawlFallback, setCrawlFallback] = useState(true);
    const [maxPages, setMaxPages] = useState(50);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleDiscover = async (e) => {
        e.preventDefault();
        if (!url.trim()) return;

        setLoading(true);
        setError(null);

        try {
            const result = await api.discover({
                base_url: url.trim(),
                use_sitemap: useSitemap,
                use_nav: useNav,
                crawl_fallback: crawlFallback,
                max_pages: parseInt(maxPages),
            });

            // Store results and navigate to page selection
            sessionStorage.setItem('discoveryResult', JSON.stringify(result));
            sessionStorage.setItem('baseUrl', url.trim());
            navigate('/select-pages');
        } catch (err) {
            setError(err.message || 'Discovery failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <div className="page-header">
                <h2>🔍 New Scan</h2>
                <p>Enter a website URL to discover pages and start validation</p>
            </div>

            <form onSubmit={handleDiscover}>
                <div className="card">
                    <div className="card-header">
                        <h3>Website URL</h3>
                    </div>

                    <div className="input-group">
                        <label>Base URL</label>
                        <input
                            className="input"
                            type="url"
                            placeholder="https://example.com"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            required
                        />
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                        <label className="checkbox-label">
                            <input type="checkbox" checked={useSitemap} onChange={(e) => setUseSitemap(e.target.checked)} />
                            Use Sitemap
                        </label>
                        <label className="checkbox-label">
                            <input type="checkbox" checked={useNav} onChange={(e) => setUseNav(e.target.checked)} />
                            Parse Navigation
                        </label>
                        <label className="checkbox-label">
                            <input type="checkbox" checked={crawlFallback} onChange={(e) => setCrawlFallback(e.target.checked)} />
                            Crawl Fallback
                        </label>
                    </div>

                    <div className="input-group" style={{ marginTop: '16px', maxWidth: '200px' }}>
                        <label>Max Pages</label>
                        <input
                            className="input"
                            type="number"
                            min="1"
                            max="200"
                            value={maxPages}
                            onChange={(e) => setMaxPages(e.target.value)}
                        />
                    </div>
                </div>

                {error && <div className="alert alert-error">⚠️ {error}</div>}

                <button className="btn btn-primary" type="submit" disabled={loading || !url.trim()}>
                    {loading ? (
                        <>
                            <span className="spinner"></span>
                            Discovering pages...
                        </>
                    ) : (
                        '🚀 Discover Pages'
                    )}
                </button>
            </form>
        </div>
    );
}
