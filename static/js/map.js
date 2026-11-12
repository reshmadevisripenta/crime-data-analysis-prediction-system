/**
 * Crime Data Analysis Prediction System
 * map.js — Leaflet.js map utilities for crime hotspot visualization
 */

'use strict';

// ============================================================
// Category color mapping
// ============================================================
const CATEGORY_COLORS = {
  'Theft':     '#1769FF',
  'Assault':   '#EF4444',
  'Burglary':  '#F59E0B',
  'Vandalism': '#8B5CF6',
  'Fraud':     '#20D5F5',
  'Robbery':   '#EC4899',
  'Murder':    '#7F1D1D',
  'Drug':      '#16A36A',
  'Default':   '#6B7A99',
};

function getCategoryColor(category) {
  for (const [key, color] of Object.entries(CATEGORY_COLORS)) {
    if (category && category.toLowerCase().includes(key.toLowerCase())) return color;
  }
  return CATEGORY_COLORS.Default;
}

// ============================================================
// Create a colored SVG marker icon
// ============================================================
function createCategoryIcon(category, count = null) {
  const color = getCategoryColor(category);
  const size = count ? Math.min(12 + Math.log(count + 1) * 4, 28) : 16;
  const svgIcon = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size * 2}" height="${size * 2.4}" viewBox="0 0 32 40">
      <path d="M16 0C7.163 0 0 7.163 0 16c0 8.837 16 24 16 24s16-15.163 16-24C32 7.163 24.837 0 16 0z"
            fill="${color}" stroke="white" stroke-width="2"/>
      <circle cx="16" cy="16" r="7" fill="white" opacity="0.9"/>
    </svg>`;
  return L.divIcon({
    html: svgIcon,
    className: 'crime-marker',
    iconSize: [size * 2, size * 2.4],
    iconAnchor: [size, size * 2.4],
    popupAnchor: [0, -size * 2.4],
  });
}

// ============================================================
// Initialize the Leaflet map
// ============================================================
function initializeMap(containerId, center = [20.5937, 78.9629], zoom = 5) {
  const map = L.map(containerId, {
    center,
    zoom,
    zoomControl: true,
    attributionControl: true,
  });

  // Compliant CartoDB Voyager tile layer with attribution
  const tileLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    subdomains: 'abcd',
    maxZoom: 20,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>'
  });
  tileLayer.addTo(map);

  return map;
}

// ============================================================
// Add crime record markers to the map
// ============================================================
function addCrimeMarkers(map, crimeData) {
  const markerGroup = L.layerGroup();
  const markers = [];

  crimeData.forEach(record => {
    if (!record.lat || !record.lng) return;

    const icon = createCategoryIcon(record.category, record.count);
    const marker = L.marker([record.lat, record.lng], { icon });

    const popupContent = `
      <div style="min-width:180px;font-family:'Inter',sans-serif;">
        <div style="font-weight:700;font-size:0.9rem;margin-bottom:6px;color:#1C2940;">${record.title || 'Crime Incident'}</div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
          <span style="background:${getCategoryColor(record.category)};color:white;padding:2px 8px;border-radius:10px;font-size:0.72rem;font-weight:700;">${record.category || 'Unknown'}</span>
        </div>
        ${record.count ? `<div style="font-size:0.8rem;color:#6B7A99;margin-top:4px;"><strong style="color:#1769FF;">${record.count}</strong> recorded incidents</div>` : ''}
        ${record.date ? `<div style="font-size:0.78rem;color:#6B7A99;margin-top:2px;">📅 ${record.date}</div>` : ''}
        ${record.city ? `<div style="font-size:0.78rem;color:#6B7A99;margin-top:2px;">📍 ${record.city}</div>` : ''}
      </div>`;

    marker.bindPopup(popupContent, { maxWidth: 250 });
    marker.crimeData = record;
    markerGroup.addLayer(marker);
    markers.push(marker);
  });

  markerGroup.addTo(map);
  return { group: markerGroup, markers };
}

// ============================================================
// Add Heatmap layer (requires Leaflet.heat plugin)
// ============================================================
function createHeatmapLayer(map, crimeData) {
  if (typeof L.heatLayer === 'undefined') {
    console.warn('Leaflet.heat plugin not loaded. Skipping heatmap.');
    return null;
  }
  const heatData = crimeData
    .filter(r => r.lat && r.lng)
    .map(r => [r.lat, r.lng, Math.min((r.count || 1) / 10, 1.0)]);

  const heatLayer = L.heatLayer(heatData, {
    radius: 35,
    blur: 20,
    maxZoom: 17,
    gradient: {
      0.2: '#1769FF',
      0.4: '#20D5F5',
      0.6: '#F59E0B',
      0.8: '#EF4444',
      1.0: '#7F1D1D'
    }
  });
  return heatLayer;
}

// ============================================================
// Add a legend control to the map
// ============================================================
function addMapLegend(map, categories) {
  const legend = L.control({ position: 'bottomright' });
  legend.onAdd = function () {
    const div = L.DomUtil.create('div', 'map-legend');
    div.style.cssText = `
      background: rgba(255,255,255,0.95);
      backdrop-filter: blur(8px);
      border-radius: 8px;
      padding: 10px 14px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.15);
      font-family: 'Inter', sans-serif;
      font-size: 12px;
      min-width: 130px;
    `;
    div.innerHTML = `<div style="font-weight:700;margin-bottom:8px;color:#1C2940;">Crime Categories</div>`;
    (categories || Object.keys(CATEGORY_COLORS).filter(k => k !== 'Default')).forEach(cat => {
      const color = getCategoryColor(cat);
      div.innerHTML += `
        <div style="display:flex;align-items:center;gap:7px;margin-bottom:5px;">
          <span style="width:10px;height:10px;border-radius:50%;background:${color};display:inline-block;flex-shrink:0;"></span>
          <span style="color:#1C2940;">${cat}</span>
        </div>`;
    });
    return div;
  };
  legend.addTo(map);
  return legend;
}

// ============================================================
// Filter markers by category
// ============================================================
function filterMarkersByCategory(markerGroup, markers, category) {
  markerGroup.clearLayers();
  markers.forEach(marker => {
    if (!category || category === 'all' || marker.crimeData.category === category) {
      markerGroup.addLayer(marker);
    }
  });
}

// ============================================================
// Fit map to markers bounds
// ============================================================
function fitMapToMarkers(map, markers) {
  if (!markers || markers.length === 0) return;
  const group = L.featureGroup(markers);
  map.fitBounds(group.getBounds().pad(0.1));
}

// ============================================================
// Toggle between markers and heatmap
// ============================================================
function toggleMapView(map, markerGroup, heatLayer, mode) {
  if (mode === 'heat') {
    if (markerGroup) markerGroup.remove();
    if (heatLayer) heatLayer.addTo(map);
  } else {
    if (heatLayer) heatLayer.remove();
    if (markerGroup) markerGroup.addTo(map);
  }
}

// ============================================================
// Expose API
// ============================================================
window.CrimeMap = {
  initializeMap,
  addCrimeMarkers,
  createHeatmapLayer,
  addMapLegend,
  filterMarkersByCategory,
  fitMapToMarkers,
  toggleMapView,
  createCategoryIcon,
  getCategoryColor,
  CATEGORY_COLORS,
};
