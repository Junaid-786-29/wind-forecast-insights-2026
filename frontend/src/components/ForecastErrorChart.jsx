import React, { useState, useMemo } from 'react';

function formatDateTime(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    const day = d.getUTCDate().toString().padStart(2, '0');
    const month = d.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' });
    const hours = d.getUTCHours().toString().padStart(2, '0');
    const minutes = d.getUTCMinutes().toString().padStart(2, '0');
    return `${day} ${month} ${hours}:${minutes} UTC`;
  } catch {
    return isoString;
  }
}

function formatDateShort(isoString) {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    const day = d.getUTCDate().toString().padStart(2, '0');
    const month = d.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' });
    return `${day} ${month}`;
  } catch {
    return '';
  }
}

/**
 * ForecastErrorChart Component
 *
 * Dedicated visualization of forecast error (forecast - actual) over time.
 * Clearly separates:
 * - Over-forecasting (error > 0, amber/orange): grid expected more wind than was generated.
 * - Under-forecasting (error < 0, indigo/blue): wind was higher than expected.
 * Features:
 * - Zero baseline reference line
 * - Dual-color bar / area visualization
 * - Interactive hover inspector
 */
export default function ForecastErrorChart({ intervals = [] }) {
  const [hoverIndex, setHoverIndex] = useState(null);

  const width = 1000;
  const height = 300;
  const margin = { top: 25, right: 30, bottom: 40, left: 65 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  // Compute symmetrical domain around zero so baseline is cleanly centered
  const { maxAbsError, yTicks, xTicks } = useMemo(() => {
    if (!intervals.length) {
      return { maxAbsError: 1000, yTicks: [-1000, 0, 1000], xTicks: [] };
    }

    let peak = 0;
    intervals.forEach((item) => {
      const absErr = Math.abs(item.forecastError || 0);
      if (absErr > peak) peak = absErr;
    });

    const ceiling = Math.ceil((peak * 1.15) / 500) * 500 || 500;
    const ticks = [-ceiling, -Math.round(ceiling / 2), 0, Math.round(ceiling / 2), ceiling];

    const xTicksArr = [];
    const step = Math.max(1, Math.floor(intervals.length / 7));
    for (let i = 0; i < intervals.length; i += step) {
      xTicksArr.push({
        index: i,
        label: formatDateShort(intervals[i].startTime),
      });
    }

    return {
      maxAbsError: ceiling,
      yTicks: ticks,
      xTicks: xTicksArr,
    };
  }, [intervals]);

  const getX = (idx) => {
    if (intervals.length <= 1) return margin.left + innerWidth / 2;
    return margin.left + (idx / (intervals.length - 1)) * innerWidth;
  };

  const getY = (val) => {
    if (val === null || val === undefined || isNaN(val)) return margin.top + innerHeight / 2;
    // Map [-maxAbsError, +maxAbsError] to [margin.top + innerHeight, margin.top]
    const clamped = Math.max(-maxAbsError, Math.min(maxAbsError, val));
    const ratio = (clamped - -maxAbsError) / (2 * maxAbsError);
    return margin.top + innerHeight - ratio * innerHeight;
  };

  const zeroY = getY(0);

  // Build error line segments
  const linePoints = useMemo(() => {
    return intervals
      .map((item, i) => `${getX(i).toFixed(1)},${getY(item.forecastError).toFixed(1)}`)
      .join(' ');
  }, [intervals, maxAbsError]);

  // Handle pointer tracking
  const handleMouseMove = (e) => {
    if (!intervals.length) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const svgX = (clientX / rect.width) * width;

    if (svgX < margin.left || svgX > width - margin.right) {
      setHoverIndex(null);
      return;
    }

    const relX = svgX - margin.left;
    const ratio = relX / innerWidth;
    const idx = Math.min(intervals.length - 1, Math.max(0, Math.round(ratio * (intervals.length - 1))));
    setHoverIndex(idx);
  };

  const handleMouseLeave = () => {
    setHoverIndex(null);
  };

  const activeRecord = hoverIndex !== null ? intervals[hoverIndex] : null;

  return (
    <div className="chart-card">
      <div className="chart-header">
        <div>
          <h2 className="chart-title">Forecast Error Time Series (Forecast − Actual)</h2>
          <p className="chart-subtitle">
            Sign convention: <strong>Positive (+MW) = Overforecasting</strong> (surplus purchased),{' '}
            <strong>Negative (−MW) = Underforecasting</strong> (unexpected deficit)
          </p>
        </div>

        <div className="error-legend">
          <span className="legend-chip chip-over">
            <span className="chip-color color-over"></span> Overforecast (+MW)
          </span>
          <span className="legend-chip chip-under">
            <span className="chip-color color-under"></span> Underforecast (−MW)
          </span>
        </div>
      </div>

      <div className="chart-container" onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="chart-svg"
          preserveAspectRatio="none"
          role="img"
          aria-label="Forecast error line chart"
        >
          {/* Background zones */}
          <rect
            x={margin.left}
            y={margin.top}
            width={innerWidth}
            height={zeroY - margin.top}
            className="zone-overforecast"
            opacity="0.04"
          />
          <rect
            x={margin.left}
            y={zeroY}
            width={innerWidth}
            height={height - margin.bottom - zeroY}
            className="zone-underforecast"
            opacity="0.04"
          />

          {/* Grid lines & Y ticks */}
          {yTicks.map((tick) => {
            const y = getY(tick);
            const isZero = tick === 0;
            return (
              <g key={`yerr-${tick}`}>
                <line
                  x1={margin.left}
                  y1={y}
                  x2={width - margin.right}
                  y2={y}
                  className={isZero ? 'grid-baseline-zero' : 'grid-line'}
                  strokeDasharray={isZero ? 'none' : '2 2'}
                />
                <text
                  x={margin.left - 10}
                  y={y + 4}
                  className={`axis-label axis-y ${isZero ? 'font-bold' : ''}`}
                  textAnchor="end"
                >
                  {tick > 0 ? `+${tick}` : tick} MW
                </text>
              </g>
            );
          })}

          {/* X ticks */}
          {xTicks.map((tick) => {
            const x = getX(tick.index);
            return (
              <g key={`xerr-${tick.index}`}>
                <line
                  x1={x}
                  y1={height - margin.bottom}
                  x2={x}
                  y2={height - margin.bottom + 6}
                  className="axis-tick-line"
                />
                <text
                  x={x}
                  y={height - margin.bottom + 22}
                  className="axis-label axis-x"
                  textAnchor="middle"
                >
                  {tick.label}
                </text>
              </g>
            );
          })}

          {/* Zero reference line label */}
          <text
            x={width - margin.right - 8}
            y={zeroY - 6}
            className="zero-ref-label"
            textAnchor="end"
          >
            Zero Error Baseline
          </text>

          {/* Error line */}
          {linePoints && (
            <polyline
              points={linePoints}
              className="line-error"
              fill="none"
              strokeWidth="2"
            />
          )}

          {/* Hover Crosshair & Dot */}
          {hoverIndex !== null && activeRecord && (
            <g className="hover-group">
              <line
                x1={getX(hoverIndex)}
                y1={margin.top}
                x2={getX(hoverIndex)}
                y2={height - margin.bottom}
                className="hover-crosshair"
              />
              <circle
                cx={getX(hoverIndex)}
                cy={getY(activeRecord.forecastError)}
                r="5"
                className={`hover-dot ${activeRecord.forecastError >= 0 ? 'dot-over' : 'dot-under'}`}
              />
            </g>
          )}
        </svg>

        {/* Floating Tooltip */}
        {activeRecord && hoverIndex !== null && (
          <div
            className="chart-tooltip"
            style={{
              left: `${(getX(hoverIndex) / width) * 100}%`,
              transform: getX(hoverIndex) > width * 0.7 ? 'translate(-105%, 0)' : 'translate(10px, 0)',
            }}
          >
            <div className="tooltip-title">{formatDateTime(activeRecord.startTime)}</div>
            <div className="tooltip-row">
              <span className="tooltip-label">Forecast Error:</span>
              <span
                className={`tooltip-value font-mono font-bold ${
                  activeRecord.forecastError > 0
                    ? 'text-amber'
                    : activeRecord.forecastError < 0
                    ? 'text-indigo'
                    : ''
                }`}
              >
                {activeRecord.forecastError > 0 ? `+${activeRecord.forecastError}` : activeRecord.forecastError} MW
              </span>
            </div>
            <div className="tooltip-row tooltip-subrow">
              <span className="tooltip-label">Classification:</span>
              <span className="tooltip-value">
                {activeRecord.forecastError > 0
                  ? 'Overforecasting (+)'
                  : activeRecord.forecastError < 0
                  ? 'Underforecasting (−)'
                  : 'Perfect Match (0)'}
              </span>
            </div>
            <div className="tooltip-row tooltip-subrow">
              <span className="tooltip-label">Abs Error:</span>
              <span className="tooltip-value font-mono">{activeRecord.absoluteError} MW</span>
            </div>
            {activeRecord.absolutePercentageError !== null && (
              <div className="tooltip-row tooltip-subrow">
                <span className="tooltip-label">Abs % Error:</span>
                <span className="tooltip-value font-mono">{activeRecord.absolutePercentageError}%</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

