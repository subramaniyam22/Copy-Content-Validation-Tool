import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';

export default function RunValidation() {
    const { jobId } = useParams();
    const navigate = useNavigate();
    const [progress, setProgress] = useState(null);
    const [error, setError] = useState(null);
    const eventSourceRef = useRef(null);

    useEffect(() => {
        // Subscribe to SSE
        const es = api.subscribeJobEvents(jobId);
        eventSourceRef.current = es;

        es.addEventListener('progress', (e) => {
            try {
                const data = JSON.parse(e.data);
                setProgress(data);
            } catch { }
        });

        es.addEventListener('done', (e) => {
            try {
                const data = JSON.parse(e.data);
                setProgress(data);
            } catch { }
            es.close();
            // Navigate to results after a brief delay
            setTimeout(() => navigate(`/results/${jobId}`), 1500);
        });

        es.onerror = () => {
            // Fallback: poll the job status
            es.close();
            pollJob();
        };

        return () => {
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
            }
        };
    }, [jobId]);

    const pollJob = async () => {
        const interval = setInterval(async () => {
            try {
                const job = await api.getJobStatus(jobId);
                if (job.progress) setProgress(job.progress);
                if (['completed', 'COMPLETED'].includes(job.status)) {
                    clearInterval(interval);
                    setTimeout(() => navigate(`/results/${jobId}`), 1000);
                } else if (['failed', 'FAILED'].includes(job.status)) {
                    clearInterval(interval);
                    setError(job.error?.error || 'Job failed');
                }
            } catch (err) {
                setError(err.message);
                clearInterval(interval);
            }
        }, 2000);
    };

    const stage = progress?.stage || 'pending';
    const totalPages = progress?.total_pages || 0;
    const scraped = progress?.scraped || 0;
    const validated = progress?.validated || 0;
    const message = progress?.message || 'Waiting for worker...';

    const scrapePercent = totalPages > 0 ? Math.round((scraped / totalPages) * 100) : 0;
    const validatePercent = totalPages > 0 ? Math.round((validated / totalPages) * 100) : 0;

    const stages = [
        { key: 'scraping', label: '🔍 Scraping', icon: '🌐' },
        { key: 'validating', label: '✅ Validating', icon: '🧪' },
        { key: 'running_tools', label: '🔧 Tools', icon: '⚙️' },
        { key: 'finalizing', label: '📊 Finalizing', icon: '✨' },
    ];

    const currentStageIdx = stages.findIndex(s => s.key === stage);

    return (
        <div>
            <div className="page-header">
                <h2>⏳ Running Validation</h2>
                <p>Job #{jobId} — {message}</p>
            </div>

            {error && <div className="alert alert-error">⚠️ {error}</div>}

            {/* Stage Progress */}
            <div className="card">
                <div className="card-header">
                    <h3>Pipeline Progress</h3>
                </div>

                <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
                    {stages.map((s, idx) => (
                        <div
                            key={s.key}
                            style={{
                                flex: 1,
                                padding: '12px',
                                borderRadius: 'var(--radius-md)',
                                background: idx <= currentStageIdx ? 'var(--accent-glow)' : 'var(--bg-input)',
                                border: idx === currentStageIdx ? '1px solid var(--accent)' : '1px solid var(--border)',
                                textAlign: 'center',
                                transition: 'all 0.3s ease',
                            }}
                        >
                            <div style={{ fontSize: '1.5rem' }}>{s.icon}</div>
                            <div style={{ fontSize: '0.75rem', fontWeight: 600, marginTop: '4px', color: idx <= currentStageIdx ? 'var(--accent-bright)' : 'var(--text-muted)' }}>
                                {s.label}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Detailed Progress */}
                <div className="stats-grid">
                    <div className="stat-card">
                        <div className="stat-value">{totalPages}</div>
                        <div className="stat-label">Total Pages</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value" style={{ color: 'var(--accent-bright)' }}>{scraped}</div>
                        <div className="stat-label">Scraped</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value" style={{ color: 'var(--success)' }}>{validated}</div>
                        <div className="stat-label">Validated</div>
                    </div>
                </div>

                {/* Progress Bars */}
                <div style={{ marginBottom: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Scraping</span>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{scrapePercent}%</span>
                    </div>
                    <div className="progress-bar">
                        <div className="progress-bar-fill" style={{ width: `${scrapePercent}%` }}></div>
                    </div>
                </div>

                <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Validating</span>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{validatePercent}%</span>
                    </div>
                    <div className="progress-bar">
                        <div className="progress-bar-fill" style={{ width: `${validatePercent}%` }}></div>
                    </div>
                </div>
            </div>

            {/* Current Activity */}
            {progress?.current_page && (
                <div className="card">
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        Currently processing: <strong style={{ color: 'var(--text-primary)' }}>{progress.current_page}</strong>
                    </div>
                </div>
            )}

            {stage === 'finalizing' && (
                <div className="alert alert-success">
                    ✅ Validation complete! Redirecting to results...
                </div>
            )}
        </div>
    );
}
