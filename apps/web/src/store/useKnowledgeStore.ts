import { create } from "zustand";

export interface GraphNode {
  id: string;
  label: string;
  level: number; // 0: Root, 1: H1, 2: H2, 3: Flashcard / Concept
  topic_cluster: string;
  panel_payload: string;
  x?: number;
  y?: number;
  z?: number;
}

export interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  relationship?: string;
}

export interface HierarchyItem {
  id: string;
  title: string;
  level: number;
  level_name: string;
  page: number;
  parent_id?: string | null;
}

export interface EvidenceItem {
  id: string;
  section: string;
  page: number;
  text: string;
  level: number;
}

export interface KnowledgeStoreState {
  // Document context
  documentId: string | null;
  filename: string | null;

  // Graph and hierarchy state
  nodes: GraphNode[];
  links: GraphLink[];
  hierarchy: HierarchyItem[];
  evidence: EvidenceItem[];

  // Selection & UI state
  selectedNode: GraphNode | null;
  activeCluster: string | null;
  searchQuery: string;
  searchPath: string[];
  dimension: "2d" | "3d";
  isLoading: boolean;
  dataSource: "live" | "fallback";

  // Actions
  setGraphData: (data: {
    documentId?: string | null;
    filename?: string | null;
    graph?: { nodes: GraphNode[]; links: GraphLink[] };
    nodes?: GraphNode[];
    links?: GraphLink[];
    hierarchy?: HierarchyItem[];
    evidence?: EvidenceItem[];
  }) => void;

  setSelectedNode: (node: GraphNode | null) => void;
  setActiveCluster: (cluster: string | null) => void;
  setSearchQuery: (query: string) => void;
  setDimension: (dimension: "2d" | "3d") => void;
  setIsLoading: (isLoading: boolean) => void;
  resetToFallback: () => void;
}

// Canonical default fallback state (only when no documents have been uploaded or selected)
const CANONICAL_MOCK_NODES: GraphNode[] = [
  {
    id: "node_root",
    label: "VERITAS: Cryptographic Traceability & Grounded Entailment",
    level: 0,
    topic_cluster: "cluster_foundation",
    panel_payload:
      "Comprehensive research paper introducing VERITAS, an architecture engineered to solve LLM hallucination and unverified attribution in scientific literature review.",
  },
  {
    id: "node_h1_ingestion",
    label: "1. Multi-Column PDF Decomposition & Coordinate Mapping",
    level: 1,
    topic_cluster: "cluster_ingestion",
    panel_payload:
      "Details the layout-aware document processing pipeline. Preserves multi-column reading order and maps every extracted text segment to physical coordinates.",
  },
  {
    id: "node_h2_pymupdf",
    label: "1.1 Bounding Box Normalization & Layout Analysis",
    level: 2,
    topic_cluster: "cluster_ingestion",
    panel_payload:
      "Employs PyMuPDF page geometry analysis to extract reading blocks with normalized coordinates [x0, y0, x1, y1].",
  },
  {
    id: "node_fc_sha256",
    label: "Flashcard: Cryptographic SHA-256 Deduplication",
    level: 3,
    topic_cluster: "cluster_ingestion",
    panel_payload:
      "Incoming documents generate a deterministic SHA-256 binary hash upon upload. Existing hashes trigger immediate pointer reuse.",
  },
  {
    id: "node_h1_retrieval",
    label: "2. Hybrid Semantic Retrieval & Reciprocal Rank Fusion",
    level: 1,
    topic_cluster: "cluster_retrieval",
    panel_payload:
      "Combines dense vector embeddings with sparse BM25 lexical search using Qdrant vector database.",
  },
  {
    id: "node_h2_rrf",
    label: "2.1 Reciprocal Rank Fusion (RRF) Ranking",
    level: 2,
    topic_cluster: "cluster_retrieval",
    panel_payload:
      "Calculates unified chunk relevance using the RRF algorithm: Score(d) = sum(1 / (k + rank_i(d))).",
  },
];

const CANONICAL_MOCK_LINKS: GraphLink[] = [
  { source: "node_root", target: "node_h1_ingestion", relationship: "contains" },
  { source: "node_h1_ingestion", target: "node_h2_pymupdf", relationship: "subdivision" },
  { source: "node_h2_pymupdf", target: "node_fc_sha256", relationship: "concept" },
  { source: "node_root", target: "node_h1_retrieval", relationship: "contains" },
  { source: "node_h1_retrieval", target: "node_h2_rrf", relationship: "subdivision" },
];

const CANONICAL_MOCK_HIERARCHY: HierarchyItem[] = [
  { id: "node_root", title: "VERITAS Overview", level: 0, level_name: "L0 - Document Root", page: 1 },
  { id: "node_h1_ingestion", title: "1. Multi-Column PDF Decomposition", level: 1, level_name: "L1 - Section", page: 2, parent_id: "node_root" },
  { id: "node_h2_pymupdf", title: "1.1 Bounding Box Normalization", level: 2, level_name: "L2 - Subsection", page: 3, parent_id: "node_h1_ingestion" },
  { id: "node_fc_sha256", title: "SHA-256 Deduplication", level: 3, level_name: "L3 - Concept", page: 3, parent_id: "node_h2_pymupdf" },
  { id: "node_h1_retrieval", title: "2. Hybrid Semantic Retrieval", level: 1, level_name: "L1 - Section", page: 4, parent_id: "node_root" },
  { id: "node_h2_rrf", title: "2.1 Reciprocal Rank Fusion", level: 2, level_name: "L2 - Subsection", page: 5, parent_id: "node_h1_retrieval" },
];

const CANONICAL_MOCK_EVIDENCE: EvidenceItem[] = [
  { id: "ev_1", section: "PDF Decomposition", page: 2, text: "Preserves multi-column reading order and maps text coordinates.", level: 1 },
  { id: "ev_2", section: "Bounding Box Normalization", page: 3, text: "PyMuPDF layout analysis with normalized bounding boxes.", level: 2 },
  { id: "ev_3", section: "Hybrid Retrieval", page: 4, text: "Dense embeddings + BM25 reciprocal rank fusion on Qdrant.", level: 1 },
];

export const useKnowledgeStore = create<KnowledgeStoreState>((set) => ({
  documentId: null,
  filename: null,
  nodes: CANONICAL_MOCK_NODES,
  links: CANONICAL_MOCK_LINKS,
  hierarchy: CANONICAL_MOCK_HIERARCHY,
  evidence: CANONICAL_MOCK_EVIDENCE,
  selectedNode: CANONICAL_MOCK_NODES[0],
  activeCluster: null,
  searchQuery: "",
  searchPath: [],
  dimension: "3d",
  isLoading: false,
  dataSource: "fallback",

  setGraphData: (payload) =>
    set(() => {
      const incomingNodes = payload.nodes || payload.graph?.nodes || [];
      const incomingLinks = payload.links || payload.graph?.links || [];
      const incomingHierarchy = payload.hierarchy || [];
      const incomingEvidence = payload.evidence || [];

      // If valid nodes arrived, completely replace store data with the new document
      if (incomingNodes.length > 0) {
        return {
          documentId: payload.documentId || null,
          filename: payload.filename || null,
          nodes: incomingNodes,
          links: incomingLinks,
          hierarchy: incomingHierarchy,
          evidence: incomingEvidence,
          selectedNode: incomingNodes[0] || null,
          searchQuery: "",
          searchPath: [],
          isLoading: false,
          dataSource: "live",
        };
      }

      return {};
    }),

  setSelectedNode: (node) => set({ selectedNode: node }),
  setActiveCluster: (cluster) => set({ activeCluster: cluster }),
  setSearchQuery: (query) =>
    set((state) => {
      if (!query.trim()) {
        return { searchQuery: "", searchPath: [] };
      }
      const match = state.nodes.find(
        (n) =>
          n.label.toLowerCase().includes(query.toLowerCase()) ||
          n.panel_payload.toLowerCase().includes(query.toLowerCase())
      );
      if (match) {
        const root = state.nodes.find((n) => n.level === 0);
        const path = root && root.id !== match.id ? [root.id, match.id] : [match.id];
        return { searchQuery: query, selectedNode: match, searchPath: path };
      }
      return { searchQuery: query, searchPath: [] };
    }),
  setDimension: (dimension) => set({ dimension }),
  setIsLoading: (isLoading) => set({ isLoading }),
  resetToFallback: () =>
    set({
      documentId: null,
      filename: null,
      nodes: CANONICAL_MOCK_NODES,
      links: CANONICAL_MOCK_LINKS,
      hierarchy: CANONICAL_MOCK_HIERARCHY,
      evidence: CANONICAL_MOCK_EVIDENCE,
      selectedNode: CANONICAL_MOCK_NODES[0],
      dataSource: "fallback",
      searchQuery: "",
      searchPath: [],
    }),
}));
