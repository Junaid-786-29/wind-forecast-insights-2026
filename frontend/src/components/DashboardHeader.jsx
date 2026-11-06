import React from 'react';

/**
 * DashboardHeader Component
 *
 * Displays product title, energy utility branding, January 2026 period badge,
 * cutoff policy, and action buttons.
 */
export default function DashboardHeader({
  dateFrom,
  dateTo,
  cutoffHourUtc,
  cutoffAssumption,
  onRefresh,
  loading,
}) {
  return (
    <header className="dashboard-header">
      <div className="header-brand">
        <div className="header-logo-container">
          <div className="energy-icon" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
            </svg>
          </div>
          <div>
            <div className="header-title-row">
              <h1 className="header-title">WindForecast Analytics</h1>
              <span className="badge period-badge">January 2026</span>
              <span className="badge source-badge">Elexon BMRS (FUELHH & WINDFOR)</span>
            </div>
            <p className="header-subtitle">
              UK National Wind Generation · Day-Ahead Forecast Accuracy & Purchasing Intelligence
            </p>
          </div>
        </div>
      </div>

      <div className="header-actions">
        <div className="cutoff-pill" title={cutoffAssumption || "10:00 UTC D-1 decision cutoff"}>
          <span className="cutoff-label">Gate Closure Cutoff:</span>
          <span className="cutoff-value">{cutoffHourUtc !== undefined ? `${cutoffHourUtc}:00 UTC (D-1)` : '10:00 UTC (D-1)'}</span>
        </div>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onRefresh}
          disabled={loading}
          title="Refresh analysis data from backend"
        >
          <svg className={`btn-icon ${loading ? 'spin' : ''}`} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.19" />
          </svg>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
    </header>
  );
}

