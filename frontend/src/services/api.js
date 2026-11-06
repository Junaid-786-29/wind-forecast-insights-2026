/**
 * API Service for WindForecast Analytics.
 *
 * Centralizes communication with the FastAPI backend.
 * - In local development (Vite port 5173), defaults to 'http://localhost:8000/api/v1'.
 * - In Docker production (Nginx container), defaults to relative '/api/v1'
 *   which is seamlessly reverse-proxied by Nginx to http://backend:8000/api/v1.
 * - Can be overridden via VITE_API_BASE_URL for custom domain or cloud deployment.
 */

export const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;

  if (envUrl !== undefined && envUrl !== null) {
    const trimmed = envUrl.trim();
    if (trimmed === '') return '/api/v1';
    const cleanUrl = trimmed.replace(/\/+$/, '');
    return cleanUrl.endsWith('/api/v1') ? cleanUrl : `${cleanUrl}/api/v1`;
  }

  // Local development default (Vite dev server)
  if (typeof window !== 'undefined' && window.location.port === '5173') {
    return 'http://localhost:8000/api/v1';
  }

  // Production fallback (e.g. Docker Nginx reverse proxy)
  return '/api/v1';
};

export const BASE_URL = getApiBaseUrl();

/**
 * Fetch wind forecast selection and accuracy analysis for a given date range.
 *
 * @param {Object} options
 * @param {string} [options.dateFrom='2026-01-01'] - Start date (yyyy-MM-dd)
 * @param {string} [options.dateTo='2026-01-31'] - End date inclusive (yyyy-MM-dd)
 * @param {number} [options.cutoffHourUtc=10] - Cutoff hour on D-1
 * @param {AbortSignal} [options.signal] - Optional abort signal
 * @returns {Promise<Object>} AnalysisResponse schema from backend
 */
export async function fetchWindAnalysis({
  dateFrom = '2026-01-01',
  dateTo = '2026-01-31',
  cutoffHourUtc = 10,
  signal,
} = {}) {
  const params = new URLSearchParams({
    date_from: dateFrom,
    date_to: dateTo,
    cutoff_hour_utc: cutoffHourUtc.toString(),
  });

  const url = `${BASE_URL}/wind/analysis?${params.toString()}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    signal,
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errorJson = await response.json();
      if (errorJson && errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // Body not JSON
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

/**
 * Check backend health status.
 * @returns {Promise<{ status: string, version: string, service: string }>}
 */
export async function fetchHealth() {
  const response = await fetch(`${BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: HTTP ${response.status}`);
  }
  return response.json();
}

