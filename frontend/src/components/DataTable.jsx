import React, { useState, useMemo } from 'react';

function formatDateTime(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    const year = d.getUTCFullYear();
    const month = (d.getUTCMonth() + 1).toString().padStart(2, '0');
    const day = d.getUTCDate().toString().padStart(2, '0');
    const hours = d.getUTCHours().toString().padStart(2, '0');
    const minutes = d.getUTCMinutes().toString().padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes} UTC`;
  } catch {
    return isoString;
  }
}

/**
 * DataTable Component
 *
 * Detailed half-hourly interval inspection table:
 * - Start time
 * - Actual generation
 * - Forecast generation
 * - Forecast publication time
 * - Forecast error (signed + pill)
 * - Absolute error
 * - Absolute percentage error
 *
 * Includes pagination, column sorting, search/filter, and CSV download.
 */
export default function DataTable({ intervals = [] }) {
  const [pageSize, setPageSize] = useState(25);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState('startTime');
  const [sortAsc, setSortAsc] = useState(true);

  // Filter intervals by text search
  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return intervals;
    const q = searchQuery.toLowerCase();
    return intervals.filter((item) => {
      const st = (item.startTime || '').toLowerCase();
      const pt = (item.forecastPublishTime || '').toLowerCase();
      return st.includes(q) || pt.includes(q);
    });
  }, [intervals, searchQuery]);

  // Sort intervals
  const sorted = useMemo(() => {
    const list = [...filtered];
    list.sort((a, b) => {
      let vA = a[sortField];
      let vB = b[sortField];

      if (vA === null || vA === undefined) return 1;
      if (vB === null || vB === undefined) return -1;

      if (typeof vA === 'string') {
        const cmp = vA.localeCompare(vB);
        return sortAsc ? cmp : -cmp;
      }

      return sortAsc ? vA - vB : vB - vA;
    });
    return list;
  }, [filtered, sortField, sortAsc]);

  // Pagination slice
  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const pageIndex = Math.min(currentPage, totalPages);
  const pageRows = useMemo(() => {
    const start = (pageIndex - 1) * pageSize;
    return sorted.slice(start, start + pageSize);
  }, [sorted, pageIndex, pageSize]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
    setCurrentPage(1);
  };

  const getSortIcon = (field) => {
    if (sortField !== field) return '↕';
    return sortAsc ? '↑' : '↓';
  };

  // CSV Export utility
  const handleExportCSV = () => {
    if (!intervals.length) return;
    const headers = [
      'Start Time (UTC)',
      'Actual Generation (MW)',
      'Forecast Generation (MW)',
      'Forecast Publish Time (UTC)',
      'Forecast Error (MW)',
      'Absolute Error (MW)',
      'Absolute Percentage Error (%)',
    ];

    const rows = intervals.map((row) => [
      row.startTime,
      row.actualGeneration,
      row.forecastGeneration,
      row.forecastPublishTime,
      row.forecastError,
      row.absoluteError,
      row.absolutePercentageError !== null ? row.absolutePercentageError : 'N/A',
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `wind_forecast_analysis_jan_2026.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="table-card">
      <div className="table-header">
        <div>
          <h2 className="table-title">Half-Hourly Interval Records</h2>
          <p className="table-subtitle">
            Inspection table for all {intervals.length.toLocaleString()} delivery periods in January 2026
          </p>
        </div>

        <div className="table-actions">
          <div className="search-box">
            <svg className="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input
              type="text"
              placeholder="Search date (e.g. 2026-01-15)..."
              className="search-input"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
            />
            {searchQuery && (
              <button
                type="button"
                className="btn-clear-search"
                onClick={() => setSearchQuery('')}
              >
                ×
              </button>
            )}
          </div>

          <button
            type="button"
            className="btn btn-secondary btn-export"
            onClick={handleExportCSV}
            title="Download full dataset as CSV"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Export CSV
          </button>
        </div>
      </div>

      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('startTime')} className="sortable">
                Start Time (UTC) <span className="sort-indicator">{getSortIcon('startTime')}</span>
              </th>
              <th onClick={() => handleSort('actualGeneration')} className="sortable text-right">
                Actual (MW) <span className="sort-indicator">{getSortIcon('actualGeneration')}</span>
              </th>
              <th onClick={() => handleSort('forecastGeneration')} className="sortable text-right">
                Forecast (MW) <span className="sort-indicator">{getSortIcon('forecastGeneration')}</span>
              </th>
              <th onClick={() => handleSort('forecastPublishTime')} className="sortable">
                Publish Time (UTC) <span className="sort-indicator">{getSortIcon('forecastPublishTime')}</span>
              </th>
              <th onClick={() => handleSort('forecastError')} className="sortable text-right">
                Forecast Error (MW) <span className="sort-indicator">{getSortIcon('forecastError')}</span>
              </th>
              <th onClick={() => handleSort('absoluteError')} className="sortable text-right">
                Abs Error (MW) <span className="sort-indicator">{getSortIcon('absoluteError')}</span>
              </th>
              <th onClick={() => handleSort('absolutePercentageError')} className="sortable text-right">
                Abs % Error <span className="sort-indicator">{getSortIcon('absolutePercentageError')}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 ? (
              <tr>
                <td colSpan="7" className="table-empty">
                  No matching interval records found.
                </td>
              </tr>
            ) : (
              pageRows.map((row, idx) => {
                const isOver = row.forecastError > 0;
                const isUnder = row.forecastError < 0;

                return (
                  <tr key={row.startTime || idx} className="table-row">
                    <td className="font-mono text-primary font-medium">
                      {formatDateTime(row.startTime)}
                    </td>
                    <td className="font-mono text-right font-medium">
                      {row.actualGeneration !== null ? row.actualGeneration.toLocaleString() : '—'}
                    </td>
                    <td className="font-mono text-right text-teal font-medium">
                      {row.forecastGeneration !== null ? row.forecastGeneration.toLocaleString() : '—'}
                    </td>
                    <td className="font-mono text-secondary text-sm">
                      {formatDateTime(row.forecastPublishTime)}
                    </td>
                    <td className="text-right">
                      <span
                        className={`error-badge ${
                          isOver ? 'badge-over' : isUnder ? 'badge-under' : 'badge-zero'
                        }`}
                      >
                        {isOver ? `+${row.forecastError}` : row.forecastError} MW
                      </span>
                    </td>
                    <td className="font-mono text-right">
                      {row.absoluteError?.toLocaleString()} MW
                    </td>
                    <td className="font-mono text-right">
                      {row.absolutePercentageError !== null ? (
                        `${row.absolutePercentageError}%`
                      ) : (
                        <span className="badge-na" title="Actual wind output is near zero (≤1 kW); excluded to avoid division distortion">
                          N/A (near zero)
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="table-footer">
        <div className="footer-left">
          <span className="text-secondary text-sm">
            Showing {(pageIndex - 1) * pageSize + (sorted.length > 0 ? 1 : 0)}–
            {Math.min(pageIndex * pageSize, sorted.length)} of {sorted.length.toLocaleString()} records
          </span>
          <div className="page-size-selector">
            <label htmlFor="page-size" className="text-sm text-secondary">
              Per page:
            </label>
            <select
              id="page-size"
              className="select-input"
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
            >
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="250">250</option>
            </select>
          </div>
        </div>

        <div className="pagination-controls">
          <button
            type="button"
            className="btn btn-page"
            disabled={pageIndex <= 1}
            onClick={() => setCurrentPage(1)}
            title="First page"
          >
            «
          </button>
          <button
            type="button"
            className="btn btn-page"
            disabled={pageIndex <= 1}
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            title="Previous page"
          >
            ‹ Prev
          </button>
          <span className="page-indicator">
            Page {pageIndex} of {totalPages}
          </span>
          <button
            type="button"
            className="btn btn-page"
            disabled={pageIndex >= totalPages}
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            title="Next page"
          >
            Next ›
          </button>
          <button
            type="button"
            className="btn btn-page"
            disabled={pageIndex >= totalPages}
            onClick={() => setCurrentPage(totalPages)}
            title="Last page"
          >
            »
          </button>
        </div>
      </div>
    </div>
  );
}

