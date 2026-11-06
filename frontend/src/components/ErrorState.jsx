import React from 'react';

/**
 * ErrorState Component
 *
 * Professional error display with retry action and troubleshooting tips.
 */
export default function ErrorState({ error, onRetry }) {
  return (
    <div className="state-card error-card" role="alert">
      <div className="error-icon" aria-hidden="true">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
      </div>

      <h3 className="error-title">Unable to Load Wind Forecast Analysis</h3>
      <p className="error-message">{error || 'An unexpected error occurred while communicating with the backend API.'}</p>

      <div className="error-troubleshooting">
        <h4>Troubleshooting Steps:</h4>
        <ul>
          <li>
            Verify the FastAPI backend is running on <code>http://localhost:8000</code>.
            <pre className="error-command">cd backend && python -m uvicorn main:app --reload --port 8000</pre>
          </li>
          <li>Check that the upstream Elexon BMRS API is accessible.</li>
          <li>Ensure CORS is enabled (automatically allowed for <code>http://localhost:5173</code> in <code>main.py</code>).</li>
        </ul>
      </div>

      {onRetry && (
        <button type="button" className="btn btn-primary btn-retry" onClick={onRetry}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.19" />
          </svg>
          Retry Connection
        </button>
      )}
    </div>
  );
}

