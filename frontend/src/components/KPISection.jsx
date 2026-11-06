import React from 'react';
import KPICard from './KPICard.jsx';

/**
 * KPISection Component
 *
 * Displays executive summary metrics from the backend analysis:
 * - Actual & Forecast coverage / matched intervals
 * - MAE (Mean Absolute Error)
 * - RMSE (Root Mean Squared Error)
 * - Bias (Overforecasting / Underforecasting)
 * - MAPE (Mean Absolute Percentage Error)
 */
export default function KPISection({ data }) {
  if (!data) return null;

  const {
    total_actual_intervals = 0,
    total_forecast_intervals = 0,
    matched_interval_count = 0,
    unmatched_interval_count = 0,
    mape_excluded_count = 0,
    mae,
    rmse,
    bias,
    mape,
  } = data;

  const coveragePercent = total_actual_intervals > 0
    ? ((matched_interval_count / total_actual_intervals) * 100).toFixed(1)
    : '0';

  // Bias direction label
  let biasBadge = 'Neutral';
  let biasBadgeType = 'neutral';
  if (bias !== null && bias !== undefined) {
    if (bias > 0) {
      biasBadge = `+${bias} MW Over`;
      biasBadgeType = 'warning';
    } else if (bias < 0) {
      biasBadge = `${bias} MW Under`;
      biasBadgeType = 'info';
    }
  }

  return (
    <section className="kpi-section" aria-label="Key Performance Indicators">
      <div className="kpi-grid">
        <KPICard
          title="Matched Delivery Intervals"
          value={matched_interval_count.toLocaleString()}
          unit="intervals"
          badge={`${coveragePercent}% coverage`}
          badgeType="success"
          description={`From ${total_actual_intervals.toLocaleString()} actual & ${total_forecast_intervals.toLocaleString()} forecast intervals`}
          tooltip="Intervals where both actual generation and an eligible day-ahead forecast exist."
        />

        <KPICard
          title="MAE (Mean Absolute Error)"
          value={mae !== null && mae !== undefined ? mae.toLocaleString() : '—'}
          unit="MW"
          badge="Average Magnitude"
          badgeType="default"
          description="Average magnitude of interval forecast deviations"
          tooltip="MAE = mean(|forecast - actual|). Unweighted average error."
        />

        <KPICard
          title="RMSE (Root Mean Sq Error)"
          value={rmse !== null && rmse !== undefined ? rmse.toLocaleString() : '—'}
          unit="MW"
          badge="Peak Penalty"
          badgeType="default"
          description="Square-root of mean squared errors (penalizes extreme spikes)"
          tooltip="RMSE = sqrt(mean((forecast - actual)^2)). Reflects sensitivity to large forecast misses."
        />

        <KPICard
          title="Forecast Bias"
          value={bias !== null && bias !== undefined ? (bias > 0 ? `+${bias}` : bias) : '—'}
          unit="MW"
          badge={biasBadge}
          badgeType={biasBadgeType}
          description={
            bias > 0
              ? 'Tendency to over-forecast (procured excess)'
              : bias < 0
              ? 'Tendency to under-forecast (unexpected deficit)'
              : 'Zero net systematic deviation'
          }
          tooltip="Bias = mean(forecast - actual). Positive = net overforecast; Negative = net underforecast."
        />

        <KPICard
          title="MAPE (Percentage Error)"
          value={mape !== null && mape !== undefined ? `${mape}%` : '—'}
          unit=""
          badge={mape_excluded_count > 0 ? `${mape_excluded_count} zero-wind excluded` : 'Full Coverage'}
          badgeType="default"
          description={
            mape_excluded_count > 0
              ? `Excludes ${mape_excluded_count} intervals with near-zero wind (≤1 kW)`
              : 'Mean percentage error across all matched intervals'
          }
          tooltip="MAPE = mean(|forecast - actual| / actual) * 100. Intervals with actual generation near zero are excluded to prevent division-by-zero skew."
        />

        <KPICard
          title="Unmatched Intervals"
          value={unmatched_interval_count.toLocaleString()}
          unit="intervals"
          badge={unmatched_interval_count === 0 ? '0 Missing' : 'Incomplete'}
          badgeType={unmatched_interval_count === 0 ? 'success' : 'warning'}
          description={
            unmatched_interval_count === 0
              ? 'Complete continuous half-hourly alignment'
              : 'Intervals missing either actual outturn or eligible forecast'
          }
          tooltip="Unmatched intervals are excluded from accuracy metrics to prevent distorted statistics."
        />
      </div>
    </section>
  );
}

