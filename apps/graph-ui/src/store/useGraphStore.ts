import { create } from "zustand";
import { DocumentTreeNode } from "../data/types";
import mockTree from "../data/mock_document_tree.json";

interface GraphState {
  // Graph Data
  nodes: DocumentTreeNode[];
  links: Array<{ source: string; target: string }>;
  
  // Selection & Inspector State
  selectedNode: DocumentTreeNode | null;
  hoveredNode: DocumentTreeNode | null;
  
  // Visual Mode
  dimension: "2d" | "3d";
  
  // Cluster Filter
  activeCluster: string | null;

  // Search & Knowledge Path Tracer State
  searchQuery: string;
  isSearching: boolean;
  searchPath: string[]; // Node IDs in sequence: [Root, H1, H2, Flashcard]
  searchLinks: any[];   // Link objects corresponding to the path
  targetNode: DocumentTreeNode | null;

  // Actions
  setSelectedNode: (node: DocumentTreeNode | null) => void;
  setHoveredNode: (node: DocumentTreeNode | null) => void;
  setDimension: (dimension: "2d" | "3d") => void;
  setActiveCluster: (cluster: string | null) => void;
  setSearchQuery: (query: string) => void;
  setSearchState: (params: {
    query: string;
    isSearching: boolean;
    searchPath: string[];
    targetNode?: DocumentTreeNode | null;
    searchLinks?: any[];
  }) => void;
  clearSearch: () => void;
  resetSelection: () => void;
}

export const useGraphStore = create<GraphState>((set) => ({
  nodes: mockTree.nodes as DocumentTreeNode[],
  links: mockTree.links,
  
  selectedNode: null,
  hoveredNode: null,
  dimension: "3d",
  activeCluster: null,

  // Initial Search State
  searchQuery: "",
  isSearching: false,
  searchPath: [],
  searchLinks: [],
  targetNode: null,

  setSelectedNode: (node) => set({ selectedNode: node }),
  setHoveredNode: (node) => set({ hoveredNode: node }),
  setDimension: (dimension) => set({ dimension }),
  setActiveCluster: (activeCluster) => set({ activeCluster }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),

  setSearchState: ({ query, isSearching, searchPath, targetNode = null, searchLinks = [] }) =>
    set({
      searchQuery: query,
      isSearching,
      searchPath,
      targetNode,
      searchLinks,
      selectedNode: targetNode || null,
    }),

  clearSearch: () =>
    set({
      searchQuery: "",
      isSearching: false,
      searchPath: [],
      searchLinks: [],
      targetNode: null,
      selectedNode: null,
    }),

  resetSelection: () => set({ selectedNode: null, hoveredNode: null }),
}));
