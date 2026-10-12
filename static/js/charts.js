/**
 * Crime Data Analysis Prediction System
 * charts.js — Chart.js wrappers for all visualizations
 */

'use strict';

// ============================================================
// Color Palette (matches project theme)
// ============================================================
const CRIME_COLORS = {
  blue:   '#1769FF',
  cyan:   '#20D5F5',
  green:  '#16A36A',
  amber:  '#F59E0B',
  red:    '#EF4444',
  purple: '#8B5CF6',
  pink:   '#EC4899',
  teal:   '#14B8A6',
  navy:   '#071B3A',
};

const CHART_PALETTE = [
  '#1769FF', '#20D5F5', '#16A36A', '#F59E0B',
  '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6',
  '#F97316', '#06B6D4', '#84CC16', '#A855F7'
];

// ============================================================
// Global Chart.js Defaults
// ============================================================
if (typeof Chart !== 'undefined') {
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = '#6B7A99';
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.pointStyleWidth = 10;
  Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(7,27,58,0.92)';
  Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
  Chart.defaults.plugins.tooltip.bodyColor = 'rgba(255,255,255,0.85)';
  Chart.defaults.plugins.tooltip.borderColor = 'rgba(23,105,255,0.4)';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
}

// ============================================================
// Shared Responsive Options
// ============================================================
const responsiveOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
};

// Chart registry to prevent re-initialization
const chartRegistry = {};

function destroyChart(canvasId) {
  if (chartRegistry[canvasId]) {
    chartRegistry[canvasId].destroy();
    delete chartRegistry[canvasId];
  }
}

// ============================================================
// Line Chart — Crime Trends
// ============================================================
function createLineChart(canvasId, labels, datasets, options = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  const chartDatasets = datasets.map((ds, i) => ({
    label: ds.label || `Dataset ${i + 1}`,
    data: ds.data || [],
    borderColor: ds.color || CHART_PALETTE[i % CHART_PALETTE.length],
    backgroundColor: hexToRgba(ds.color || CHART_PALETTE[i % CHART_PALETTE.length], 0.08),
    borderWidth: 2.5,
    pointRadius: 4,
    pointHoverRadius: 6,
    pointBackgroundColor: ds.color || CHART_PALETTE[i % CHART_PALETTE.length],
    tension: 0.4,
    fill: ds.fill !== undefined ? ds.fill : true,
  }));

  const chart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: chartDatasets },
    options: {
      ...responsiveOptions,
      plugins: {
        legend: { position: 'top' },
        tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString()}` } }
      },
      scales: {
        x: {
          grid: { color: 'rgba(0,0,0,0.05)', drawBorder: false },
          ticks: { maxTicksLimit: 10 }
        },
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(0,0,0,0.05)', drawBorder: false },
          ticks: { callback: v => v.toLocaleString() }
        }
      },
      ...options
    }
  });
  chartRegistry[canvasId] = chart;
  return chart;
}

// ============================================================
// Bar Chart — Category / Location Comparison
// ============================================================
function createBarChart(canvasId, labels, data, label = 'Count', color = CRIME_COLORS.blue, options = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  const colors = Array.isArray(color) ? color : CHART_PALETTE.slice(0, labels.length);

  const chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label,
        data,
        backgroundColor: colors.map(c => hexToRgba(c, 0.8)),
        borderColor: colors,
        borderWidth: 1.5,
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      ...responsiveOptions,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString()}` } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 30 } },
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: { callback: v => v.toLocaleString() }
        }
      },
      ...options
    }
  });
  chartRegistry[canvasId] = chart;
  return chart;
}

// ============================================================
// Doughnut Chart — Category Distribution
// ============================================================
function createDoughnutChart(canvasId, labels, data, colors = CHART_PALETTE, options = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  const chart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors.map(c => hexToRgba(c, 0.85)),
        borderColor: '#fff',
        borderWidth: 3,
        hoverOffset: 10,
      }]
    },
    options: {
      ...responsiveOptions,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 16, font: { size: 11 } }
        },
        tooltip: {
          callbacks: {
            label: ctx => {
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct = ((ctx.parsed / total) * 100).toFixed(1);
              return ` ${ctx.label}: ${ctx.parsed.toLocaleString()} (${pct}%)`;
            }
          }
        }
      },
      ...options
    }
  });
  chartRegistry[canvasId] = chart;
  return chart;
}

// ============================================================
// Stacked Bar Chart — Multi-category comparison
// ============================================================
function createStackedBarChart(canvasId, labels, datasets, options = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  const chartDatasets = datasets.map((ds, i) => ({
    label: ds.label || `Group ${i + 1}`,
    data: ds.data || [],
    backgroundColor: hexToRgba(ds.color || CHART_PALETTE[i % CHART_PALETTE.length], 0.8),
    borderColor: ds.color || CHART_PALETTE[i % CHART_PALETTE.length],
    borderWidth: 1,
    borderRadius: i === datasets.length - 1 ? { topLeft: 4, topRight: 4 } : 0,
    borderSkipped: false,
  }));

  const chart = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets: chartDatasets },
    options: {
      ...responsiveOptions,
      plugins: { legend: { position: 'top' } },
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { callback: v => v.toLocaleString() } }
      },
      ...options
    }
  });
  chartRegistry[canvasId] = chart;
  return chart;
}

// ============================================================
// Area Chart — Actual vs Predicted
// ============================================================
function createAreaChart(canvasId, labels, actualData, predictedData, options = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  const datasets = [
    {
      label: 'Actual',
      data: actualData,
      borderColor: CRIME_COLORS.blue,
      backgroundColor: hexToRgba(CRIME_COLORS.blue, 0.12),
      borderWidth: 2.5,
      pointRadius: 4,
      tension: 0.35,
      fill: true,
    }
  ];

  if (predictedData && predictedData.length) {
    datasets.push({
      label: 'Predicted',
      data: predictedData,
      borderColor: CRIME_COLORS.amber,
      backgroundColor: hexToRgba(CRIME_COLORS.amber, 0.08),
      borderWidth: 2.5,
      borderDash: [6, 3],
      pointRadius: 4,
      tension: 0.35,
      fill: true,
    });
  }

  const chart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      ...responsiveOptions,
      plugins: { legend: { position: 'top' } },
      scales: {
        x: { grid: { color: 'rgba(0,0,0,0.05)' } },
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: { callback: v => v.toLocaleString() }
        }
      },
      ...options
    }
  });
  chartRegistry[canvasId] = chart;
  return chart;
}

// ============================================================
// Horizontal Bar Chart — Location rankings
// ============================================================
function createHorizontalBarChart(canvasId, labels, data, label = 'Incidents', options = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  const chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label,
        data,
        backgroundColor: CHART_PALETTE.slice(0, labels.length).map(c => hexToRgba(c, 0.8)),
        borderColor: CHART_PALETTE.slice(0, labels.length),
        borderWidth: 1.5,
        borderRadius: 4,
      }]
    },
    options: {
      ...responsiveOptions,
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: {
        x: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { callback: v => v.toLocaleString() } },
        y: { grid: { display: false } }
      },
      ...options
    }
  });
  chartRegistry[canvasId] = chart;
  return chart;
}

// ============================================================
// Radar Chart — Category pattern comparison
// ============================================================
function createRadarChart(canvasId, labels, datasets, options = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  const chartDatasets = datasets.map((ds, i) => ({
    label: ds.label || `Series ${i + 1}`,
    data: ds.data || [],
    borderColor: ds.color || CHART_PALETTE[i % CHART_PALETTE.length],
    backgroundColor: hexToRgba(ds.color || CHART_PALETTE[i % CHART_PALETTE.length], 0.15),
    borderWidth: 2,
    pointRadius: 4,
  }));

  const chart = new Chart(ctx, {
    type: 'radar',
    data: { labels, datasets: chartDatasets },
    options: {
      ...responsiveOptions,
      plugins: { legend: { position: 'top' } },
      scales: {
        r: {
          beginAtZero: true,
          grid: { color: 'rgba(0,0,0,0.08)' },
          ticks: { backdropColor: 'transparent', font: { size: 10 } }
        }
      },
      ...options
    }
  });
  chartRegistry[canvasId] = chart;
  return chart;
}

// ============================================================
// Update existing chart data
// ============================================================
function updateChart(canvasId, newLabels, newData, datasetIndex = 0) {
  const chart = chartRegistry[canvasId];
  if (!chart) return;
  chart.data.labels = newLabels;
  chart.data.datasets[datasetIndex].data = newData;
  chart.update('active');
}

// ============================================================
// Helper: hex to rgba
// ============================================================
function hexToRgba(hex, alpha = 1) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// ============================================================
// Expose API
// ============================================================
window.CrimeCharts = {
  createLineChart,
  createBarChart,
  createDoughnutChart,
  createStackedBarChart,
  createAreaChart,
  createHorizontalBarChart,
  createRadarChart,
  updateChart,
  destroyChart,
  hexToRgba,
  CHART_PALETTE,
  CRIME_COLORS,
};
