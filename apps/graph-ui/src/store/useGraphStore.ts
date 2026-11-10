import { create } from "zustand";
import { DocumentTreeNode, DocumentTreeLink } from "../data/types";
import mockTree from "../data/mock_document_tree.json";

interface GraphState {
  // Graph Data
  nodes: DocumentTreeNode[];
  links: DocumentTreeLink[];
  dataSource: "live" | "fallback";
  
  // Selection & Inspector State
  selectedNode: DocumentTreeNode | null;
  hoveredNode: DocumentTreeNode | null;
  
  // Visual Mode & Engine State
  dimension: "2d" | "3d";
  isEngineIdle: boolean;
  
  // Cluster Filter
  activeCluster: string | null;

  // Search & Knowledge Path Tracer State
  searchQuery: string;
  isSearching: boolean;
  searchPath: string[]; // Node IDs in sequence: [Root, H1, H2, Flashcard]
  searchLinks: any[];   // Link objects along the path
  targetNode: DocumentTreeNode | null;

  // Actions
  setGraphData: (data: { nodes: DocumentTreeNode[]; links: DocumentTreeLink[] }, source?: "live" | "fallback") => void;
  setSelectedNode: (node: DocumentTreeNode | null) => void;
  setHoveredNode: (node: DocumentTreeNode | null) => void;
  setDimension: (dimension: "2d" | "3d") => void;
  setIsEngineIdle: (isIdle: boolean) => void;
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
  links: mockTree.links as DocumentTreeLink[],
  dataSource: "fallback",
  
  selectedNode: null,
  hoveredNode: null,
  dimension: "3d",
  isEngineIdle: false,
  activeCluster: null,

  // Initial Search State
  searchQuery: "",
  isSearching: false,
  searchPath: [],
  searchLinks: [],
  targetNode: null,

  setGraphData: ({ nodes, links }, source = "fallback") =>
    set((state) => {
      // Re-verify selectedNode within new dataset
      const updatedSelected = state.selectedNode
        ? nodes.find((n) => n.id === state.selectedNode?.id) || nodes[0] || null
        : nodes[0] || null;

      return {
        nodes,
        links,
        dataSource: source,
        selectedNode: updatedSelected,
        searchPath: [],
        searchLinks: [],
        isSearching: false,
        targetNode: null,
      };
    }),

  setSelectedNode: (node) => set({ selectedNode: node }),
  setHoveredNode: (node) => set({ hoveredNode: node }),
  setDimension: (dimension) => set({ dimension }),
  setIsEngineIdle: (isEngineIdle) => set({ isEngineIdle }),
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
