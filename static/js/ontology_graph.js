/**
 * Crime Data Analysis Prediction System
 * ontology_graph.js — Interactive D3.js v7 knowledge graph
 */

'use strict';

// ============================================================
// Node type color scheme
// ============================================================
const NODE_COLORS = {
  'Crime':           '#EF4444',
  'CrimeRecord':     '#1769FF',
  'CrimeCategory':   '#F59E0B',
  'Location':        '#16A36A',
  'DateTime':        '#8B5CF6',
  'PoliceStation':   '#20D5F5',
  'AnalysisResult':  '#EC4899',
  'Prediction':      '#F97316',
  'User':            '#14B8A6',
  'default':         '#6B7A99',
};

function getNodeColor(type) {
  return NODE_COLORS[type] || NODE_COLORS.default;
}

// ============================================================
// Main: initOntologyGraph
// ============================================================
function initOntologyGraph(containerId, graphData) {
  const container = document.getElementById(containerId);
  if (!container || typeof d3 === 'undefined') {
    console.warn('D3 or container not available');
    return null;
  }

  const { nodes = [], edges = [] } = graphData;
  const width  = container.clientWidth  || 800;
  const height = container.clientHeight || 520;

  // Clear previous
  d3.select(`#${containerId}`).selectAll('*').remove();

  // Create SVG
  const svg = d3.select(`#${containerId}`)
    .append('svg')
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .style('background', 'transparent');

  // Zoom/pan
  const zoomG = svg.append('g').attr('class', 'zoom-group');
  const zoom = d3.zoom()
    .scaleExtent([0.3, 4])
    .on('zoom', (event) => {
      zoomG.attr('transform', event.transform);
    });
  svg.call(zoom);

  // Arrow markers for directed edges
  const defs = svg.append('defs');
  Object.entries(NODE_COLORS).forEach(([type, color]) => {
    defs.append('marker')
      .attr('id', `arrow-${type.replace(/[^a-zA-Z0-9]/g, '_')}`)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 24)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', color)
        .attr('opacity', 0.7);
  });

  // Force simulation
  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges)
      .id(d => d.id)
      .distance(d => d.distance || 130)
      .strength(0.7)
    )
    .force('charge', d3.forceManyBody().strength(-400))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(45));

  // Draw edges
  const link = zoomG.append('g').attr('class', 'links')
    .selectAll('line')
    .data(edges)
    .join('line')
    .attr('stroke', d => {
      const sourceNode = nodes.find(n => n.id === (d.source.id || d.source));
      return sourceNode ? getNodeColor(sourceNode.type) : '#6B7A99';
    })
    .attr('stroke-opacity', 0.5)
    .attr('stroke-width', 1.5)
    .attr('marker-end', d => {
      const sourceNode = nodes.find(n => n.id === (d.source.id || d.source));
      const type = sourceNode ? (sourceNode.type || 'default') : 'default';
      return `url(#arrow-${type.replace(/[^a-zA-Z0-9]/g, '_')})`;
    });

  // Edge labels
  const linkLabel = zoomG.append('g').attr('class', 'link-labels')
    .selectAll('text')
    .data(edges)
    .join('text')
    .attr('font-size', '9px')
    .attr('fill', 'rgba(255,255,255,0.55)')
    .attr('text-anchor', 'middle')
    .attr('font-family', "'Inter', sans-serif")
    .text(d => d.label || '');

  // Draw nodes
  const node = zoomG.append('g').attr('class', 'nodes')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .attr('class', 'node-group')
    .style('cursor', 'pointer')
    .call(d3.drag()
      .on('start', dragStarted)
      .on('drag', dragged)
      .on('end', dragEnded)
    );

  // Node circles
  node.append('circle')
    .attr('r', d => d.size || 20)
    .attr('fill', d => getNodeColor(d.type))
    .attr('stroke', '#fff')
    .attr('stroke-width', 2)
    .attr('opacity', 0.9)
    .on('mouseover', function(event, d) {
      d3.select(this).attr('r', (d.size || 20) + 4).attr('opacity', 1);
      highlightConnected(d.id, true);
    })
    .on('mouseout', function(event, d) {
      d3.select(this).attr('r', d.size || 20).attr('opacity', 0.9);
      highlightConnected(d.id, false);
    })
    .on('click', (event, d) => {
      event.stopPropagation();
      showNodeInfo(d);
    });

  // Node icons (text)
  node.append('text')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-size', '12px')
    .attr('fill', '#fff')
    .attr('font-weight', '700')
    .attr('pointer-events', 'none')
    .text(d => (d.label || d.id || '').charAt(0).toUpperCase());

  // Node labels below
  node.append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', d => (d.size || 20) + 14)
    .attr('font-size', '10px')
    .attr('fill', 'rgba(255,255,255,0.85)')
    .attr('font-family', "'Inter', sans-serif")
    .attr('font-weight', '600')
    .attr('pointer-events', 'none')
    .text(d => d.label || d.id || '');

  // Highlight connected nodes/edges
  function highlightConnected(nodeId, on) {
    const connectedIds = new Set([nodeId]);
    edges.forEach(e => {
      const sId = e.source.id || e.source;
      const tId = e.target.id || e.target;
      if (sId === nodeId) connectedIds.add(tId);
      if (tId === nodeId) connectedIds.add(sId);
    });
    node.selectAll('circle').attr('opacity', d =>
      on ? (connectedIds.has(d.id) ? 1 : 0.2) : 0.9
    );
    link.attr('stroke-opacity', d => {
      const sId = d.source.id || d.source;
      const tId = d.target.id || d.target;
      return on ? (sId === nodeId || tId === nodeId ? 0.9 : 0.1) : 0.5;
    });
  }

  // Node info panel
  function showNodeInfo(nodeData) {
    const panel = document.getElementById('nodeInfoPanel');
    if (!panel) return;
    panel.classList.add('visible');
    document.getElementById('nodeInfoName').textContent = nodeData.label || nodeData.id;
    document.getElementById('nodeInfoType').textContent = nodeData.type || 'Class';
    document.getElementById('nodeInfoDesc').textContent = nodeData.description || 'No description available.';

    // Find relationships
    const rels = edges.filter(e => {
      const sId = e.source.id || e.source;
      const tId = e.target.id || e.target;
      return sId === nodeData.id || tId === nodeData.id;
    });
    const relList = document.getElementById('nodeInfoRelations');
    if (relList) {
      relList.innerHTML = rels.map(e => {
        const sId = e.source.id || e.source;
        const tId = e.target.id || e.target;
        const other = sId === nodeData.id ? tId : sId;
        const dir = sId === nodeData.id ? '→' : '←';
        return `<div style="font-size:0.75rem;color:rgba(255,255,255,0.7);margin-bottom:4px;"><span style="color:#20D5F5;">${dir} ${e.label || 'relatedTo'}</span> ${other}</div>`;
      }).join('') || '<div style="font-size:0.75rem;color:rgba(255,255,255,0.4);">No relationships found</div>';
    }
  }

  // Click background to close panel
  svg.on('click', () => {
    const panel = document.getElementById('nodeInfoPanel');
    if (panel) panel.classList.remove('visible');
  });

  // Simulation tick
  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);

    linkLabel
      .attr('x', d => ((d.source.x || 0) + (d.target.x || 0)) / 2)
      .attr('y', d => ((d.source.y || 0) + (d.target.y || 0)) / 2 - 5);

    node.attr('transform', d => `translate(${d.x || 0},${d.y || 0})`);
  });

  // Drag handlers
  function dragStarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x; d.fy = d.y;
  }
  function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
  function dragEnded(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null; d.fy = null;
  }

  // Resize handler
  function handleResize() {
    const w = container.clientWidth;
    const h = container.clientHeight;
    svg.attr('viewBox', `0 0 ${w} ${h}`);
    simulation.force('center', d3.forceCenter(w / 2, h / 2));
    simulation.alpha(0.2).restart();
  }
  window.addEventListener('resize', debounceGraph(handleResize, 250));

  // Center/zoom controls
  const centerBtn = document.getElementById('graphCenterBtn');
  if (centerBtn) {
    centerBtn.addEventListener('click', () => {
      svg.transition().duration(600).call(
        zoom.transform,
        d3.zoomIdentity.translate(width / 2, height / 2).scale(1)
      );
    });
  }

  const zoomInBtn = document.getElementById('graphZoomIn');
  if (zoomInBtn) zoomInBtn.addEventListener('click', () => svg.transition().call(zoom.scaleBy, 1.4));
  const zoomOutBtn = document.getElementById('graphZoomOut');
  if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => svg.transition().call(zoom.scaleBy, 0.7));

  // Search highlight
  const searchInput = document.getElementById('ontologySearch');
  if (searchInput) {
    searchInput.addEventListener('input', debounceGraph((e) => {
      const query = e.target.value.toLowerCase().trim();
      node.selectAll('circle').attr('opacity', d => {
        if (!query) return 0.9;
        const match = (d.label || '').toLowerCase().includes(query) || (d.type || '').toLowerCase().includes(query);
        return match ? 1 : 0.2;
      });
    }, 300));
  }

  return { simulation, svg, nodes, edges };
}

// ============================================================
// Debounce helper (local)
// ============================================================
function debounceGraph(fn, delay) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

// ============================================================
// Build default ontology graph data from Django context
// ============================================================
function buildGraphFromContext(classes, properties) {
  const nodes = (classes || []).map(cls => ({
    id: cls.name,
    label: cls.label || cls.name,
    type: cls.name,
    description: cls.description || '',
    color: cls.color_code || getNodeColor(cls.name),
    size: 22,
  }));

  const edges = (properties || []).map(prop => ({
    source: prop.domain_class,
    target: prop.range_class || prop.domain_class,
    label: prop.label || prop.name,
  })).filter(e => e.source && e.target && e.source !== e.target);

  return { nodes, edges };
}

// ============================================================
// Expose API
// ============================================================
window.OntologyGraph = {
  initOntologyGraph,
  buildGraphFromContext,
  getNodeColor,
  NODE_COLORS,
};
