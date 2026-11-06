import React from 'react';

/**
 * DateFilter Component
 *
 * Provides date-slice navigation across January 2026 data:
 * - Quick range presets (Full Month, W1, W2, W3, W4, Late Jan)
 * - Specific single-day selection
 * - Filter summary badge showing filtered interval count
 */
export default function DateFilter({
  selectedRange,
  onSelectRange,
  selectedDay,
  onSelectDay,
  totalIntervals,
  filteredCount,
}) {
  const PRESETS = [
    { id: 'all', label: 'All January (1–31)', from: '2026-01-01', to: '2026-01-31' },
    { id: 'w1', label: 'Week 1 (Jan 1–7)', from: '2026-01-01', to: '2026-01-07' },
    { id: 'w2', label: 'Week 2 (Jan 8–14)', from: '2026-01-08', to: '2026-01-14' },
    { id: 'w3', label: 'Week 3 (Jan 15–21)', from: '2026-01-15', to: '2026-01-21' },
    { id: 'w4', label: 'Week 4 (Jan 22–28)', from: '2026-01-22', to: '2026-01-28' },
    { id: 'w5', label: 'Jan 29–31', from: '2026-01-29', to: '2026-01-31' },
  ];

  const handlePresetClick = (preset) => {
    onSelectRange(preset);
    onSelectDay(''); // reset single day if preset clicked
  };

  const handleDayChange = (e) => {
    const val = e.target.value;
    onSelectDay(val);
    if (val) {
      onSelectRange({ id: 'day', label: `Day: ${val}`, from: val, to: val });
    }
  };

  return (
    <div className="filter-bar">
      <div className="filter-presets">
        <span className="filter-label">Quick Views:</span>
        <div className="preset-buttons">
          {PRESETS.map((preset) => {
            const isActive = selectedRange && selectedRange.id === preset.id && !selectedDay;
            return (
              <button
                key={preset.id}
                type="button"
                className={`btn btn-filter ${isActive ? 'active' : ''}`}
                onClick={() => handlePresetClick(preset)}
              >
                {preset.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="filter-specific-day">
        <label htmlFor="day-picker" className="filter-label">
          Single Day:
        </label>
        <input
          id="day-picker"
          type="date"
          className="date-input"
          min="2026-01-01"
          max="2026-01-31"
          value={selectedDay || ''}
          onChange={handleDayChange}
          title="Select a specific day in January 2026"
        />
        {selectedDay && (
          <button
            type="button"
            className="btn btn-clear"
            onClick={() => handlePresetClick(PRESETS[0])}
            title="Reset to Full Month"
          >
            Clear
          </button>
        )}
      </div>

      <div className="filter-summary">
        <span className="summary-pill">
          Showing <strong>{filteredCount.toLocaleString()}</strong> of {totalIntervals.toLocaleString()} intervals
        </span>
      </div>
    </div>
  );
}

