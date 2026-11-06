import React, { useState, useEffect, useCallback, useMemo } from 'react';
import './App.css';
import { fetchWindAnalysis } from './services/api.js';

import DashboardHeader from './components/DashboardHeader.jsx';
import KPISection from './components/KPISection.jsx';
import DateFilter from './components/DateFilter.jsx';
import GenerationChart from './components/GenerationChart.jsx';
import ForecastErrorChart from './components/ForecastErrorChart.jsx';
import DataTable from './components/DataTable.jsx';
import LoadingState from './components/LoadingState.jsx';
import ErrorState from './components/ErrorState.jsx';

/**
 * Main WindForecast Analytics Dashboard
 */
export default function App() {
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Date filtering state
  const [selectedRange, setSelectedRange] = useState({
    id: 'all',
    label: 'All January (1–31)',
    from: '2026-01-01',
    to: '2026-01-31',
  });
  const [selectedDay, setSelectedDay] = useState('');

  // Fetch analysis data from FastAPI backend
  const loadData = useCallback(async (signal) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchWindAnalysis({
        dateFrom: '2026-01-01',
        dateTo: '2026-01-31',
        cutoffHourUtc: 10,
        signal,
      });
      setAnalysisData(result);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Failed to fetch wind forecast analysis');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadData(controller.signal);
    return () => controller.abort();
  }, [loadData]);

  // Client-side date slice filtering
  const filteredIntervals = useMemo(() => {
    if (!analysisData || !analysisData.intervals) return [];
    if (!selectedRange || selectedRange.id === 'all') return analysisData.intervals;

    const { from, to } = selectedRange;
    return analysisData.intervals.filter((item) => {
      const datePart = (item.startTime || '').slice(0, 10);
      return datePart >= from && datePart <= to;
    });
  }, [analysisData, selectedRange]);

  return (
    <div className="dashboard-container">
      {/* A. Header */}
      <DashboardHeader
        dateFrom={analysisData?.date_from || '2026-01-01'}
        dateTo={analysisData?.date_to || '2026-01-31'}
        cutoffHourUtc={analysisData?.day_ahead_cutoff_hour_utc ?? 10}
        cutoffAssumption={analysisData?.cutoff_assumption}
        onRefresh={() => loadData()}
        loading={loading}
      />

      {/* Main Content Area */}
      {loading && !analysisData && (
        <LoadingState message="Connecting to FastAPI backend & retrieving Elexon datasets..." />
      )}

      {error && !loading && (
        <ErrorState error={error} onRetry={() => loadData()} />
      )}

      {analysisData && (
        <>
          {/* B. KPI Overview */}
          <KPISection data={analysisData} />

          {/* F. Date Navigation / Range Filtering */}
          <DateFilter
            selectedRange={selectedRange}
            onSelectRange={setSelectedRange}
            selectedDay={selectedDay}
            onSelectDay={setSelectedDay}
            totalIntervals={analysisData.intervals?.length || 0}
            filteredCount={filteredIntervals.length}
          />

          {/* C. Actual vs Forecast Chart */}
          <GenerationChart intervals={filteredIntervals} />

          {/* D. Forecast Error Analysis Chart */}
          <ForecastErrorChart intervals={filteredIntervals} />

          {/* E. Detailed Interval Data Table */}
          <DataTable intervals={filteredIntervals} />
        </>
      )}
    </div>
  );
}
