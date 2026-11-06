import React from 'react';

/**
 * LoadingState Component
 *
 * Professional enterprise skeleton loading display.
 */
export default function LoadingState({ message = 'Loading analysis data from Elexon...' }) {
  return (
    <div className="state-card loading-card" role="status" aria-live="polite">
      <div className="loading-spinner" aria-hidden="true"></div>
      <h3 className="loading-title">Generating Wind Forecast Accuracy Analysis</h3>
      <p className="loading-message">{message}</p>
      <div className="loading-details">
        <span>Retrieving FUELHH actuals & WINDFOR day-ahead forecasts for January 2026</span>
      </div>

      <div className="skeleton-grid">
        <div className="skeleton-item skeleton-kpi"></div>
        <div className="skeleton-item skeleton-kpi"></div>
        <div className="skeleton-item skeleton-kpi"></div>
        <div className="skeleton-item skeleton-kpi"></div>
      </div>
      <div className="skeleton-item skeleton-chart"></div>
    </div>
  );
}

