"use client";

import React, { useEffect, useRef, useState, useMemo } from "react";
import {
  Network as NetworkIcon,
  Search,
  Filter,
  RefreshCw,
  Sparkles,
  Layers,
  FileText,
  Database,
  Cpu,
  Award,
  BookOpen,
  User,
  ShieldCheck,
  ChevronRight,
  Maximize2,
  Minimize2,
  Info,
} from "lucide-react";
import { api } from "../lib/api";
import { GraphNode, GraphEdge, WorkspaceGraph, DocumentItem } from "../types";

// Dynamic import or check for vis-network
interface KnowledgeGraphViewProps {
  documents: DocumentItem[];
  onOpenDocument?: (docId: string) => void;
}

const TYPE_COLORS: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  Paper: { bg: "#0284C7", border: "#38BDF8", text: "#FFFFFF", badge: "bg-sky-950 text-sky-400 border-sky-800" },
  Author: { bg: "#7C3AED", border: "#A78BFA", text: "#FFFFFF", badge: "bg-purple-950 text-purple-400 border-purple-800" },
  Dataset: { bg: "#059669", border: "#34D399", text: "#FFFFFF", badge: "bg-emerald-950 text-emerald-400 border-emerald-800" },
  Algorithm: { bg: "#D97706", border: "#FBBF24", text: "#FFFFFF", badge: "bg-amber-950 text-amber-400 border-amber-800" },
  Metric: { bg: "#E11D48", border: "#FB7185", text: "#FFFFFF", badge: "bg-rose-950 text-rose-400 border-rose-800" },
  Concept: { bg: "#4F46E5", border: "#818CF8", text: "#FFFFFF", badge: "bg-indigo-950 text-indigo-400 border-indigo-800" },
};

export const KnowledgeGraphView: React.FC<KnowledgeGraphViewProps> = ({
  documents,
  onOpenDocument,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkInstanceRef = useRef<any>(null);

  const [graphData, setGraphData] = useState<WorkspaceGraph | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<Record<string, boolean>>({
    Paper: true,
    Author: true,
    Dataset: true,
    Algorithm: true,
    Metric: true,
    Concept: true,
  });

  // Selected item state (Node or Edge)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<{
    edge: GraphEdge;
    source: GraphNode;
    target: GraphNode;
  } | null>(null);

  const [isFullscreen, setIsFullscreen] = useState(false);

  const fetchGraph = async () => {
    setIsRefreshing(true);
    setError(null);
    try {
      const data = await api.getWorkspaceKnowledgeGraph();
      setGraphData(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load workspace knowledge graph");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, []);

  // Filtered nodes and edges
  const filteredData = useMemo(() => {
    if (!graphData) return { nodes: [], edges: [] };

    const nodes = graphData.nodes.filter((node) => {
      const typeAllowed = selectedTypes[node.type] !== false;
      const searchMatches =
        !searchQuery.trim() ||
        node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.type.toLowerCase().includes(searchQuery.toLowerCase());
      return typeAllowed && searchMatches;
    });

    const nodeIds = new Set(nodes.map((n) => n.id));

    const edges = graphData.edges.filter(
      (edge) => nodeIds.has(edge.source_node_id) && nodeIds.has(edge.target_node_id)
    );

    return { nodes, edges };
  }, [graphData, selectedTypes, searchQuery]);

  // Mount vis-network canvas
  useEffect(() => {
    if (!containerRef.current || typeof window === "undefined") return;

    let network: any = null;

    const initNetwork = async () => {
      try {
        const { Network } = await import("vis-network");
        const { DataSet } = await import("vis-data");

        const visNodes = new DataSet(
          filteredData.nodes.map((node) => {
            const colorMeta = TYPE_COLORS[node.type] || TYPE_COLORS.Concept;
            const isPaper = node.type === "Paper";
            return {
              id: node.id,
              label: node.label,
              title: `${node.type}: ${node.label}`,
              color: {
                background: colorMeta.bg,
                border: colorMeta.border,
                highlight: {
                  background: colorMeta.border,
                  border: "#FFFFFF",
                },
              },
              font: {
                color: "#F8FAFC",
                size: isPaper ? 14 : 12,
                face: "Inter, sans-serif",
                strokeWidth: 2,
                strokeColor: "#0F172A",
              },
              shape: isPaper ? "diamond" : "dot",
              size: isPaper ? 24 : 16,
              borderWidth: 2,
              shadow: {
                enabled: true,
                color: "rgba(0,0,0,0.5)",
                size: 6,
              },
            };
          })
        );

        const visEdges = new DataSet(
          filteredData.edges.map((edge) => ({
            id: edge.id,
            from: edge.source_node_id,
            to: edge.target_node_id,
            label: edge.relationship_type,
            font: {
              color: "#94A3B8",
              size: 9,
              align: "middle",
              strokeWidth: 2,
              strokeColor: "#0B0F19",
            },
            arrows: {
              to: { enabled: true, scaleFactor: 0.6 },
            },
            color: {
              color: "#334155",
              highlight: "#38BDF8",
              hover: "#64748B",
            },
            width: 1.5,
            smooth: {
              enabled: true,
              type: "continuous",
              roundness: 0.2,
            },
          }))
        );

        const options: any = {
          physics: {
            solver: "forceAtlas2Based",
            forceAtlas2Based: {
              gravitationalConstant: -40,
              centralGravity: 0.008,
              springLength: 110,
              springConstant: 0.06,
              damping: 0.85,
            },
            stabilization: {
              enabled: true,
              iterations: 150,
            },
          },
          interaction: {
            hover: true,
            tooltipDelay: 150,
            zoomView: true,
            dragView: true,
          },
        };

        if (containerRef.current) {
          network = new Network(containerRef.current, { nodes: visNodes as any, edges: visEdges as any }, options);
          networkInstanceRef.current = network;

          network.on("selectNode", (params: any) => {
            const nodeId = params.nodes[0];
            const node = filteredData.nodes.find((n) => n.id === nodeId) || null;
            setSelectedNode(node);
            setSelectedEdge(null);
          });

          network.on("selectEdge", (params: any) => {
            if (params.nodes.length === 0 && params.edges.length > 0) {
              const edgeId = params.edges[0];
              const edge = filteredData.edges.find((e) => e.id === edgeId);
              if (edge) {
                const src = filteredData.nodes.find((n) => n.id === edge.source_node_id);
                const tgt = filteredData.nodes.find((n) => n.id === edge.target_node_id);
                if (src && tgt) {
                  setSelectedEdge({ edge, source: src, target: tgt });
                  setSelectedNode(null);
                }
              }
            }
          });

          network.on("deselectNode", () => {
            setSelectedNode(null);
          });

          network.on("deselectEdge", () => {
            setSelectedEdge(null);
          });
        }
      } catch (e) {
        console.error("Error mounting vis-network:", e);
      }
    };

    initNetwork();

    return () => {
      if (network) network.destroy();
    };
  }, [filteredData]);

  const toggleType = (type: string) => {
    setSelectedTypes((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  return (
    <div
      className={`space-y-6 ${
        isFullscreen
          ? "fixed inset-0 z-50 bg-[#0B0F19] p-6 overflow-hidden flex flex-col"
          : "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
      }`}
    >
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold tracking-widest text-cyan-400 uppercase bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
              Phase 8 Feature
            </span>
            <span className="text-xs text-slate-400">PostgreSQL Relational Graph</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight mt-1 flex items-center space-x-2.5">
            <NetworkIcon className="w-6 h-6 text-cyan-400" />
            <span>Scientific Knowledge Graph</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Force-directed relational network of datasets, algorithms, metrics, concepts, and papers with sentence-level provenance.
          </p>
        </div>

        {/* Global Statistics */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-4 px-4 py-2 bg-slate-900 border border-slate-800 rounded-xl">
            <div className="text-center">
              <div className="text-[10px] uppercase font-mono text-slate-400">Entities</div>
              <div className="text-base font-bold text-white font-mono">
                {graphData?.total_nodes || 0}
              </div>
            </div>
            <div className="w-px h-6 bg-slate-800" />
            <div className="text-center">
              <div className="text-[10px] uppercase font-mono text-slate-400">Relationships</div>
              <div className="text-base font-bold text-cyan-400 font-mono">
                {graphData?.total_edges || 0}
              </div>
            </div>
          </div>

          <button
            onClick={fetchGraph}
            disabled={isRefreshing}
            title="Refresh Knowledge Graph"
            className="p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-cyan-400" : ""}`} />
          </button>

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? "Exit Fullscreen" : "Fullscreen Graph"}
            className="p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition-all"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between gap-4 shadow-md">
        {/* Search */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search entities (e.g. ImageNet, Transformer)..."
            className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>

        {/* Entity Type Toggles */}
        <div className="flex flex-wrap items-center gap-2">
          {Object.keys(TYPE_COLORS).map((type) => {
            const active = selectedTypes[type] !== false;
            const meta = TYPE_COLORS[type];
            return (
              <button
                key={type}
                onClick={() => toggleType(type)}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all border ${
                  active
                    ? `${meta.badge} shadow-sm`
                    : "bg-slate-950/60 text-slate-500 border-slate-800/80 line-through opacity-60"
                }`}
              >
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: meta.border }}
                />
                <span>{type}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Canvas and Inspector Split */}
      <div className={`relative flex gap-4 ${isFullscreen ? "flex-1 min-h-0" : "h-[620px]"}`}>
        {/* Graph Canvas Container */}
        <div
          ref={containerRef}
          className="flex-1 bg-gradient-to-b from-[#0A0E1A] to-[#070B14] border border-slate-800/90 rounded-2xl overflow-hidden shadow-2xl relative"
        >
          {isLoading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/80 backdrop-blur-sm z-20 space-y-3">
              <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
              <p className="text-xs text-slate-400 font-mono">
                Constructing force-directed knowledge graph...
              </p>
            </div>
          )}

          {!isLoading && filteredData.nodes.length === 0 && (
            <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center z-10 space-y-3">
              <NetworkIcon className="w-12 h-12 text-slate-600" />
              <h3 className="text-base font-bold text-white">No Graph Entities Found</h3>
              <p className="text-xs text-slate-400 max-w-sm leading-relaxed">
                Upload research documents to automatically extract scientific entities, datasets, algorithms, and metrics.
              </p>
            </div>
          )}

          {/* Quick Graph Navigation Tip */}
          <div className="absolute bottom-3 left-3 z-10 px-3 py-1.5 rounded-lg bg-slate-950/80 border border-slate-800/80 text-[10px] text-slate-400 flex items-center space-x-2 pointer-events-none">
            <Info className="w-3.5 h-3.5 text-cyan-400" />
            <span>Click nodes to inspect entities • Click lines for exact provenance excerpts</span>
          </div>
        </div>

        {/* Side Inspector Drawer */}
        {(selectedNode || selectedEdge) && (
          <div className="w-80 sm:w-96 bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-2xl overflow-y-auto flex flex-col justify-between space-y-4">
            {selectedNode && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <span
                    className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                      TYPE_COLORS[selectedNode.type]?.badge || "bg-slate-800 text-slate-300"
                    }`}
                  >
                    {selectedNode.type}
                  </span>
                  <button
                    onClick={() => setSelectedNode(null)}
                    className="text-slate-400 hover:text-white text-xs px-1.5 py-0.5 rounded hover:bg-slate-800"
                  >
                    ✕
                  </button>
                </div>

                <div>
                  <h3 className="text-lg font-bold text-white leading-tight">
                    {selectedNode.label}
                  </h3>
                  {selectedNode.description && (
                    <p className="text-xs text-slate-300 mt-2 leading-relaxed bg-slate-950/80 p-3 rounded-xl border border-slate-800">
                      {selectedNode.description}
                    </p>
                  )}
                </div>

                {selectedNode.document_id && onOpenDocument && (
                  <button
                    onClick={() => onOpenDocument(selectedNode.document_id!)}
                    className="w-full py-2 px-3 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold rounded-xl text-xs flex items-center justify-center space-x-1.5 transition-colors shadow-sm"
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>View Originating Paper</span>
                  </button>
                )}
              </div>
            )}

            {selectedEdge && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-cyan-950/80 text-cyan-400 border border-cyan-800">
                    Relationship
                  </span>
                  <button
                    onClick={() => setSelectedEdge(null)}
                    className="text-slate-400 hover:text-white text-xs px-1.5 py-0.5 rounded hover:bg-slate-800"
                  >
                    ✕
                  </button>
                </div>

                <div className="space-y-2">
                  <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-xs space-y-2">
                    <div className="flex items-center space-x-1.5 font-semibold text-white">
                      <span>{selectedEdge.source.label}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
                      <span className="text-cyan-300">{selectedEdge.edge.relationship_type}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
                      <span>{selectedEdge.target.label}</span>
                    </div>
                  </div>

                  {/* Provenance quote */}
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono uppercase text-slate-400 flex items-center space-x-1">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Verified Grounding Excerpt</span>
                    </span>
                    <blockquote className="p-3 bg-slate-950/90 border border-slate-800 rounded-xl text-xs text-slate-200 italic leading-relaxed font-serif">
                      &ldquo;{selectedEdge.edge.source_excerpt || "Evidence excerpt preserved in semantic chunk."}&rdquo;
                    </blockquote>
                  </div>

                  {selectedEdge.edge.provenance_chunk_id && (
                    <div className="text-[10px] font-mono text-slate-500">
                      Chunk ID: {selectedEdge.edge.provenance_chunk_id.slice(0, 12)}...
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
