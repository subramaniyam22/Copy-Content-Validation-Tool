import React from 'react';
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import NewScan from './pages/NewScan';
import SelectPages from './pages/SelectPages';
import Guidelines from './pages/Guidelines';
import RunValidation from './pages/RunValidation';
import Results from './pages/Results';
import ScanHistory from './pages/ScanHistory';

export default function App() {
    return (
        <div className="app-layout">
            <aside className="sidebar">
                <div className="sidebar-logo">
                    <h1>CVT</h1>
                    <span>Content Validation Tool</span>
                </div>
                <nav>
                    <NavLink to="/scan" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <span className="nav-icon">🔍</span>
                        <span>New Scan</span>
                    </NavLink>
                    <NavLink to="/guidelines" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <span className="nav-icon">📋</span>
                        <span>Guidelines</span>
                    </NavLink>
                    <NavLink to="/history" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <span className="nav-icon">📊</span>
                        <span>Scan History</span>
                    </NavLink>
                </nav>
            </aside>
            <main className="main-content">
                <Routes>
                    <Route path="/" element={<Navigate to="/scan" replace />} />
                    <Route path="/scan" element={<NewScan />} />
                    <Route path="/select-pages" element={<SelectPages />} />
                    <Route path="/guidelines" element={<Guidelines />} />
                    <Route path="/run/:jobId" element={<RunValidation />} />
                    <Route path="/results/:jobId" element={<Results />} />
                    <Route path="/history" element={<ScanHistory />} />
                </Routes>
            </main>
        </div>
    );
}
