import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Download, Expand, Maximize2, Minimize2, Minus, Plus, Search, X,
} from 'lucide-react';
import { fetchEntityGraph } from '@/lib/intelligencePlatformApi';
import './knowledgeGraph.css';

const LEGEND = [
  { type: 'pe_firm', label: 'Firms', color: '#0B3B60' },
  { type: 'company', label: 'Companies', color: '#1D6B4F' },
  { type: 'fund', label: 'Funds', color: '#B8860B' },
  { type: 'person', label: 'People', color: '#6D28D9' },
  { type: 'industry', label: 'Industries', color: '#C2410C' },
  { type: 'article', label: 'Articles', color: '#64748B' },
  { type: 'transaction', label: 'Transactions', color: '#B91C1C' },
];

const TYPE_OPTIONS = [
  { value: '', label: 'All types' },
  { value: 'pe_firm,fund', label: 'Firms & Funds' },
  { value: 'portfolio_company,company', label: 'Companies' },
  { value: 'person', label: 'People' },
  { value: 'transaction', label: 'Transactions' },
  { value: 'industry', label: 'Industries' },
  { value: 'news,article', label: 'News & Articles' },
];

function nodeRadius(node, isRoot) {
  if (isRoot) return 22;
  if (node.entity_type === 'pe_firm') return 18;
  if (node.entity_type === 'fund') return 16;
  return 14;
}

export default function KnowledgeGraph({ entitySlug, entityId, onNodeSelect }) {
  const navigate = useNavigate();
  const svgRef = useRef(null);
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [depth, setDepth] = useState(2);
  const [typeFilter, setTypeFilter] = useState('');
  const [search, setSearch] = useState('');
  const [fullscreen, setFullscreen] = useState(false);
  const [collapsed, setCollapsed] = useState(new Set());
  const [hover, setHover] = useState(null);
  const [hoverPos, setHoverPos] = useState({ x: 0, y: 0 });
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const dragRef = useRef(null);

  const loadGraph = useCallback(() => {
    if (!entitySlug && !entityId) return;
    setLoading(true);
    const slug = entitySlug || entityId;
    fetchEntityGraph(slug, {
      depth,
      entity_types: typeFilter || undefined,
      include_ai_summary: true,
      include_timeline: true,
    })
      .then(setGraph)
      .catch(() => setGraph(null))
      .finally(() => setLoading(false));
  }, [entitySlug, entityId, depth, typeFilter]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const visibleNodes = useMemo(() => {
    if (!graph?.nodes) return [];
    let nodes = graph.nodes.filter((n) => !collapsed.has(n.id));
    if (search.trim()) {
      const q = search.toLowerCase();
      nodes = nodes.filter((n) => n.name.toLowerCase().includes(q));
    }
    return nodes;
  }, [graph, collapsed, search]);

  const visibleIds = useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes]);

  const visibleEdges = useMemo(() => {
    if (!graph?.edges) return [];
    return graph.edges.filter((e) => visibleIds.has(e.from) && visibleIds.has(e.to));
  }, [graph, visibleIds]);

  const highlightIds = useMemo(() => {
    if (!hover?.id) return new Set();
    const ids = new Set([hover.id]);
    visibleEdges.forEach((e) => {
      if (e.from === hover.id) ids.add(e.to);
      if (e.to === hover.id) ids.add(e.from);
    });
    return ids;
  }, [hover, visibleEdges]);

  const onWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setTransform((t) => ({ ...t, scale: Math.min(3, Math.max(0.3, t.scale * delta)) }));
  };

  const onPointerDown = (e) => {
    if (e.target.closest('.kg-node') || e.target.closest('.kg-hover-card')) return;
    dragRef.current = { x: e.clientX, y: e.clientY, tx: transform.x, ty: transform.y };
  };

  const onPointerMove = (e) => {
    if (!dragRef.current) return;
    setTransform((t) => ({
      ...t,
      x: dragRef.current.tx + (e.clientX - dragRef.current.x),
      y: dragRef.current.ty + (e.clientY - dragRef.current.y),
    }));
  };

  const onPointerUp = () => {
    dragRef.current = null;
  };

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(graph, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${graph?.root_slug || 'graph'}-intelligence.json`;
    a.click();
  };

  const exportImage = () => {
    const svg = svgRef.current;
    if (!svg) return;
    const serializer = new XMLSerializer();
    const source = serializer.serializeToString(svg);
    const img = new Image();
    const svgBlob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = 1200;
      canvas.height = 800;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#fafaf8';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      const a = document.createElement('a');
      a.href = canvas.toDataURL('image/png');
      a.download = `${graph?.root_slug || 'graph'}-knowledge-graph.png`;
      a.click();
      URL.revokeObjectURL(url);
    };
    img.src = url;
  };

  const toggleCollapse = (id) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const cx = 400;
  const cy = 260;

  return (
    <div className={`kg-wrap ${fullscreen ? 'fullscreen' : ''}`}>
      <div className="kg-toolbar">
        <Search size={14} className="text-slate-400" />
        <input
          type="search"
          placeholder="Search graph…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="min-w-[140px]"
        />
        <select value={depth} onChange={(e) => setDepth(Number(e.target.value))}>
          <option value={1}>Depth 1</option>
          <option value={2}>Depth 2</option>
          <option value={3}>Depth 3</option>
        </select>
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
          {TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <button type="button" onClick={() => setTransform((t) => ({ ...t, scale: t.scale * 1.2 }))}>
          <Plus size={12} /> Zoom
        </button>
        <button type="button" onClick={() => setTransform((t) => ({ ...t, scale: t.scale * 0.8 }))}>
          <Minus size={12} />
        </button>
        <button type="button" onClick={exportJson}><Download size={12} /> JSON</button>
        <button type="button" onClick={exportImage}><Download size={12} /> PNG</button>
        <button type="button" onClick={() => setFullscreen((f) => !f)}>
          {fullscreen ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
          {fullscreen ? 'Exit' : 'Full'}
        </button>
      </div>

      <div
        className="kg-canvas"
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
      >
        {loading && <div className="kg-loading">Loading intelligence graph…</div>}
        <svg ref={svgRef} className="kg-svg" viewBox="0 0 800 520">
          <g transform={`translate(${cx + transform.x}, ${cy + transform.y}) scale(${transform.scale})`}>
            {visibleEdges.map((edge) => {
              const from = visibleNodes.find((n) => n.id === edge.from);
              const to = visibleNodes.find((n) => n.id === edge.to);
              if (!from || !to) return null;
              const highlighted = highlightIds.has(edge.from) && highlightIds.has(edge.to);
              const mx = (from.x + to.x) / 2;
              const my = (from.y + to.y) / 2;
              return (
                <g key={edge.id}>
                  <line
                    className={`kg-edge ${highlighted ? 'highlight' : ''}`}
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                  />
                  {highlighted && (
                    <text className="kg-edge-label" x={mx} y={my - 4} textAnchor="middle">
                      {edge.label}
                    </text>
                  )}
                </g>
              );
            })}
            {visibleNodes.map((node) => {
              const isRoot = node.id === graph?.root_id;
              const r = nodeRadius(node, isRoot);
              const highlighted = highlightIds.has(node.id);
              return (
                <g
                  key={node.id}
                  className={`kg-node ${highlighted ? 'highlight' : ''} ${collapsed.has(node.id) ? 'collapsed' : ''}`}
                  transform={`translate(${node.x}, ${node.y})`}
                  onMouseEnter={(e) => {
                    setHover(node);
                    const rect = e.currentTarget.closest('.kg-canvas')?.getBoundingClientRect();
                    if (rect) setHoverPos({ x: e.clientX - rect.left + 12, y: e.clientY - rect.top + 12 });
                  }}
                  onMouseLeave={() => setHover(null)}
                  onClick={() => onNodeSelect?.(node)}
                  style={{ cursor: 'pointer' }}
                >
                  <circle r={r} fill={node.color || '#64748B'} />
                  <text y={r + 14} textAnchor="middle">{node.name.length > 22 ? `${node.name.slice(0, 20)}…` : node.name}</text>
                  <text className="kg-node-type" y={r + 26} textAnchor="middle">{node.entity_type_label}</text>
                </g>
              );
            })}
          </g>
        </svg>

        {hover && (
          <div className="kg-hover-card" style={{ left: hoverPos.x, top: hoverPos.y }}>
            <p className="type">{hover.entity_type_label}</p>
            <h4>{hover.name}</h4>
            {hover.ai_summary && <p>{hover.ai_summary.slice(0, 160)}…</p>}
            <div className="text-[10px] text-slate-400 mt-2">
              {hover.relationship_count} relationships · {hover.timeline_count} timeline events
            </div>
            <div className="kg-hover-actions">
              <button type="button" onClick={() => navigate(hover.path)}>View Entity</button>
              <button type="button" onClick={() => toggleCollapse(hover.id)}>
                <Expand size={10} /> {collapsed.has(hover.id) ? 'Expand' : 'Collapse'}
              </button>
              <a href={hover.path} target="_blank" rel="noopener noreferrer">New Tab</a>
            </div>
          </div>
        )}

        <svg className="kg-minimap" viewBox="-400 -300 800 600">
          {visibleNodes.map((n) => (
            <circle key={n.id} cx={n.x} cy={n.y} r={3} fill={n.color || '#64748B'} opacity={0.6} />
          ))}
        </svg>
      </div>

      <div className="kg-legend">
        {LEGEND.map((item) => (
          <span key={item.type} className="kg-legend-item">
            <span className="kg-legend-dot" style={{ background: item.color }} />
            {item.label}
          </span>
        ))}
        {graph && (
          <span className="kg-legend-item ml-auto">
            {graph.node_count} nodes · {graph.edge_count} edges
          </span>
        )}
      </div>
    </div>
  );
}
