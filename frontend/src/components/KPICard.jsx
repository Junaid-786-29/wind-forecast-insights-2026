import React from 'react';

/**
 * Individual KPI Card
 */
export default function KPICard({
  title,
  value,
  unit,
  description,
  badge,
  badgeType = 'default',
  trend,
  tooltip,
}) {
  const displayValue = value === null || value === undefined ? '—' : value;

  return (
    <div className="kpi-card" title={tooltip || description}>
      <div className="kpi-header">
        <span className="kpi-title">{title}</span>
        {badge && (
          <span className={`kpi-badge kpi-badge-${badgeType}`}>
            {badge}
          </span>
        )}
      </div>
      <div className="kpi-body">
        <span className="kpi-value">{displayValue}</span>
        {unit && <span className="kpi-unit">{unit}</span>}
      </div>
      {description && <div className="kpi-description">{description}</div>}
    </div>
  );
}

