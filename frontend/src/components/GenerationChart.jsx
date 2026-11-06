import React, { useState, useMemo } from 'react';

/**
 * Format a UTC ISO timestamp for display.
 */
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
 * GenerationChart Component
 *
 * Interactive time-series comparing Actual vs Day-Ahead Forecasted wind generation.
 * Features:
 * - Responsive SVG rendering
 * - Dual series: Actual Generation (Solid Navy) & Day-Ahead Forecast (Teal / Cyan)
 * - Hover crosshair with detailed metrics tooltip
 * - Series visibility toggles in legend
 * - Dynamic Y-axis scaling with grid lines
 */
export default function GenerationChart({ intervals = [] }) {
  const [hoverIndex, setHoverIndex] = useState(null);
  const [showActual, setShowActual] = useState(true);
  const [showForecast, setShowForecast] = useState(true);

  // SVG dimensions & margins
  const width = 1000;
  const height = 380;
  const margin = { top: 20, right: 30, bottom: 40, left: 65 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  // Compute domains
  const { maxVal, minVal, yTicks, xTicks } = useMemo(() => {
    if (!intervals.length) {
      return { maxVal: 1000, minVal: 0, yTicks: [0, 500, 1000], xTicks: [] };
    }

    let highest = 0;
    intervals.forEach((item) => {
      if (item.actualGeneration !== null && item.actualGeneration > highest) {
        highest = item.actualGeneration;
      }
      if (item.forecastGeneration !== null && item.forecastGeneration > highest) {
        highest = item.forecastGeneration;
      }
    });

    // Round up to sensible ceiling
    const ceiling = Math.ceil((highest * 1.1) / 1000) * 1000 || 1000;
    const ticksCount = 5;
    const yStep = ceiling / ticksCount;
    const yTicksArr = [];
    for (let i = 0; i <= ticksCount; i++) {
      yTicksArr.push(Math.round(i * yStep));
    }

    // X-axis ticks: sample 6-8 evenly spaced intervals
    const xTicksArr = [];
    const step = Math.max(1, Math.floor(intervals.length / 7));
    for (let i = 0; i < intervals.length; i += step) {
      xTicksArr.push({
        index: i,
        label: formatDateShort(intervals[i].startTime),
      });
    }

    return {
      maxVal: ceiling,
      minVal: 0,
      yTicks: yTicksArr,
      xTicks: xTicksArr,
    };
  }, [intervals]);

  // Coordinate mappers
  const getX = (idx) => {
    if (intervals.length <= 1) return margin.left + innerWidth / 2;
    return margin.left + (idx / (intervals.length - 1)) * innerWidth;
  };

  const getY = (val) => {
    if (val === null || val === undefined || isNaN(val)) return null;
    const clamped = Math.max(minVal, Math.min(maxVal, val));
    return margin.top + innerHeight - ((clamped - minVal) / (maxVal - minVal)) * innerHeight;
  };

  // Build SVG polyline paths
  const actualPoints = useMemo(() => {
    if (!showActual) return '';
    return intervals
      .map((item, i) => {
        const y = getY(item.actualGeneration);
        return y !== null ? `${getX(i).toFixed(1)},${y.toFixed(1)}` : null;
      })
      .filter(Boolean)
      .join(' ');
  }, [intervals, showActual, maxVal]);

  const forecastPoints = useMemo(() => {
    if (!showForecast) return '';
    return intervals
      .map((item, i) => {
        const y = getY(item.forecastGeneration);
        return y !== null ? `${getX(i).toFixed(1)},${y.toFixed(1)}` : null;
      })
      .filter(Boolean)
      .join(' ');
  }, [intervals, showForecast, maxVal]);

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
          <h2 className="chart-title">Actual vs Day-Ahead Forecast Generation</h2>
          <p className="chart-subtitle">
            Half-hourly UK national wind outturn (FUELHH) compared against selected day-ahead forecast (WINDFOR)
          </p>
        </div>

        <div className="chart-legend">
          <button
            type="button"
            className={`legend-item ${showActual ? 'active' : 'inactive'}`}
            onClick={() => setShowActual(!showActual)}
            title="Toggle Actual Generation series"
          >
            <span className="legend-indicator legend-actual"></span>
            <span className="legend-text">Actual Wind (MW)</span>
          </button>
          <button
            type="button"
            className={`legend-item ${showForecast ? 'active' : 'inactive'}`}
            onClick={() => setShowForecast(!showForecast)}
            title="Toggle Day-Ahead Forecast series"
          >
            <span className="legend-indicator legend-forecast"></span>
            <span className="legend-text">Day-Ahead Forecast (MW)</span>
          </button>
        </div>
      </div>

      <div className="chart-container" onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="chart-svg"
          preserveAspectRatio="none"
          role="img"
          aria-label="Actual vs Forecast line chart"
        >
          {/* Horizontal Grid lines & Y-axis labels */}
          {yTicks.map((tick) => {
            const y = getY(tick);
            return (
              <g key={`ytick-${tick}`}>
                <line
                  x1={margin.left}
                  y1={y}
                  x2={width - margin.right}
                  y2={y}
                  className="grid-line"
                />
                <text
                  x={margin.left - 10}
                  y={y + 4}
                  className="axis-label axis-y"
                  textAnchor="end"
                >
                  {tick.toLocaleString()} MW
                </text>
              </g>
            );
          })}

          {/* X-axis ticks */}
          {xTicks.map((tick) => {
            const x = getX(tick.index);
            return (
              <g key={`xtick-${tick.index}`}>
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

          {/* Axis border */}
          <line
            x1={margin.left}
            y1={height - margin.bottom}
            x2={width - margin.right}
            y2={height - margin.bottom}
            className="axis-baseline"
          />

          {/* Actual generation line */}
          {showActual && actualPoints && (
            <polyline
              points={actualPoints}
              className="line-actual"
              fill="none"
              strokeWidth="2.5"
            />
          )}

          {/* Forecast generation line */}
          {showForecast && forecastPoints && (
            <polyline
              points={forecastPoints}
              className="line-forecast"
              fill="none"
              strokeWidth="2.5"
              strokeDasharray="4 2"
            />
          )}

          {/* Hover Crosshair & Dots */}
          {hoverIndex !== null && activeRecord && (
            <g className="hover-group">
              <line
                x1={getX(hoverIndex)}
                y1={margin.top}
                x2={getX(hoverIndex)}
                y2={height - margin.bottom}
                className="hover-crosshair"
              />

              {showActual && activeRecord.actualGeneration !== null && (
                <circle
                  cx={getX(hoverIndex)}
                  cy={getY(activeRecord.actualGeneration)}
                  r="5"
                  className="hover-dot dot-actual"
                />
              )}

              {showForecast && activeRecord.forecastGeneration !== null && (
                <circle
                  cx={getX(hoverIndex)}
                  cy={getY(activeRecord.forecastGeneration)}
                  r="5"
                  className="hover-dot dot-forecast"
                />
              )}
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
              <span className="tooltip-label">
                <span className="tooltip-bullet bullet-actual"></span> Actual:
              </span>
              <span className="tooltip-value font-mono">
                {activeRecord.actualGeneration?.toLocaleString()} MW
              </span>
            </div>
            <div className="tooltip-row">
              <span className="tooltip-label">
                <span className="tooltip-bullet bullet-forecast"></span> Forecast:
              </span>
              <span className="tooltip-value font-mono">
                {activeRecord.forecastGeneration?.toLocaleString()} MW
              </span>
            </div>
            <div className="tooltip-row tooltip-subrow">
              <span className="tooltip-label">Error (Fc - Act):</span>
              <span
                className={`tooltip-value font-mono ${
                  activeRecord.forecastError > 0 ? 'text-amber' : activeRecord.forecastError < 0 ? 'text-indigo' : ''
                }`}
              >
                {activeRecord.forecastError > 0 ? `+${activeRecord.forecastError}` : activeRecord.forecastError} MW
              </span>
            </div>
            {activeRecord.absolutePercentageError !== null && (
              <div className="tooltip-row tooltip-subrow">
                <span className="tooltip-label">Abs % Error:</span>
                <span className="tooltip-value font-mono">{activeRecord.absolutePercentageError}%</span>
              </div>
            )}
            <div className="tooltip-footer">
              Published: {formatDateTime(activeRecord.forecastPublishTime)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

