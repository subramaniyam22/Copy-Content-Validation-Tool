/* API client module */
const BASE = '';

async function request(path, opts = {}) {
    const res = await fetch(`${BASE}${path}`, {
        headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
        ...opts,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Request failed');
    }
    return res.json();
}

export const api = {
    // Discovery
    discover: (data) => request('/api/discover', { method: 'POST', body: JSON.stringify(data) }),

    // Guidelines
    listGuidelines: () => request('/api/guidelines'),
    uploadGuidelines: (formData) =>
        fetch(`${BASE}/api/guidelines`, { method: 'POST', body: formData }).then(r => r.json()),
    getGuidelineRules: (setId, versionId) =>
        request(`/api/guidelines/${setId}/versions/${versionId}/rules`),

    // Exclusions
    listExclusions: (projectId) =>
        request(`/api/exclusions${projectId ? `?project_id=${projectId}` : ''}`),
    createExclusion: (data) =>
        request('/api/exclusions', { method: 'POST', body: JSON.stringify(data) }),

    // Validation
    startValidation: (data) =>
        request('/api/validate', { method: 'POST', body: JSON.stringify(data) }),
    getJobStatus: (jobId) => request(`/api/jobs/${jobId}`),
    getJobResults: (jobId) => request(`/api/jobs/${jobId}/results`),

    // SSE for job progress
    subscribeJobEvents: (jobId) => new EventSource(`${BASE}/api/jobs/${jobId}/events`),

    // Scans
    listScans: (baseUrl) => request(`/api/scans?base_url=${encodeURIComponent(baseUrl)}`),
    listRecentScans: () => request('/api/scans/recent'),
    compareScan: (scanId, toId) => request(`/api/scans/${scanId}/compare?to=${toId}`),
    compareToLast: (scanId) => request(`/api/scans/${scanId}/compare-to-last`),

    // Exports
    exportCsvUrl: (jobId) => `${BASE}/api/jobs/${jobId}/export.csv`,
    exportXlsxUrl: (jobId) => `${BASE}/api/jobs/${jobId}/export.xlsx`,

    // Health
    health: () => request('/health'),
};

export default api;
