"use client";

import React, { useState } from "react";
import {
  Search,
  Globe,
  Download,
  ExternalLink,
  BookOpen,
  Award,
  ChevronDown,
  ChevronUp,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Network,
  Filter,
  Sparkles,
  Layers,
} from "lucide-react";
import { api } from "../lib/api";
import {
  ExternalPaperMetadata,
  DiscoverySearchResponse,
  CitationNetworkResponse,
  DocumentItem,
} from "../types";

interface GlobalDiscoveryViewProps {
  documents: DocumentItem[];
  onDocumentImported?: () => void;
  onOpenDocument?: (docId: string) => void;
}

export const GlobalDiscoveryView: React.FC<GlobalDiscoveryViewProps> = ({
  documents,
  onDocumentImported,
  onOpenDocument,
}) => {
  // Search parameters
  const [query, setQuery] = useState("");
  const [authorFilter, setAuthorFilter] = useState("");
  const [yearFilter, setYearFilter] = useState<string>("");
  const [showFilters, setShowFilters] = useState(false);

  // Direct DOI/URL import bar
  const [directInput, setDirectInput] = useState("");
  const [isDirectImporting, setIsDirectImporting] = useState(false);
  const [directError, setDirectError] = useState<string | null>(null);
  const [directSuccess, setDirectSuccess] = useState<string | null>(null);

  // Search state
  const [isSearching, setIsSearching] = useState(false);
  const [searchResponse, setSearchResponse] = useState<DiscoverySearchResponse | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [expandedAbstracts, setExpandedAbstracts] = useState<Record<string, boolean>>({});

  // Ingestion states per paper ID
  const [importingPaperId, setImportingPaperId] = useState<string | null>(null);
  const [importedPapers, setImportedPapers] = useState<Record<string, string>>({}); // id -> docId
  const [importErrors, setImportErrors] = useState<Record<string, string>>({});

  // Citation network drawer
  const [citationPaper, setCitationPaper] = useState<{ id: string; title: string; doi?: string | null } | null>(null);
  const [isLoadingCitations, setIsLoadingCitations] = useState(false);
  const [citationNetwork, setCitationNetwork] = useState<CitationNetworkResponse | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setSearchError(null);

    try {
      const yearNum = yearFilter ? parseInt(yearFilter, 10) : undefined;
      const res = await api.searchGlobalLiterature(
        query.trim(),
        1,
        15,
        authorFilter.trim() || undefined,
        yearNum
      );
      setSearchResponse(res);
    } catch (err: any) {
      setSearchError(err?.message || "Failed to search global literature. Please verify your connection.");
    } finally {
      setIsSearching(false);
    }
  };

  const handleDirectImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!directInput.trim()) return;

    setIsDirectImporting(true);
    setDirectError(null);
    setDirectSuccess(null);

    try {
      const res = await api.ingestPaperFromExternal(directInput.trim());
      setDirectSuccess(`Successfully imported "${res.title}". Background parsing & embedding queued.`);
      setDirectInput("");
      if (onDocumentImported) onDocumentImported();
    } catch (err: any) {
      setDirectError(err?.message || "Failed to import paper. Verify the DOI/URL is a valid Open Access PDF.");
    } finally {
      setIsDirectImporting(false);
    }
  };

  const handleImportResult = async (paper: ExternalPaperMetadata) => {
    const target = paper.pdf_url || paper.doi || paper.landing_page_url;
    if (!target) return;

    setImportingPaperId(paper.id);
    setImportErrors((prev) => ({ ...prev, [paper.id]: "" }));

    try {
      const res = await api.ingestPaperFromExternal(target, undefined, paper.title);
      setImportedPapers((prev) => ({ ...prev, [paper.id]: res.document_id }));
      if (onDocumentImported) onDocumentImported();
    } catch (err: any) {
      setImportErrors((prev) => ({
        ...prev,
        [paper.id]: err?.message || "Import failed: Document may be paywalled or target is restricted.",
      }));
    } finally {
      setImportingPaperId(null);
    }
  };

  const toggleAbstract = (id: string) => {
    setExpandedAbstracts((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const openCitationNetwork = async (id: string, title: string, doi?: string | null) => {
    setCitationPaper({ id, title, doi });
    setIsLoadingCitations(true);
    setCitationNetwork(null);

    try {
      // Find if this paper is in local documents by title or id
      const localDoc = documents.find(
        (d) => d.id === id || (d.metadata && d.metadata.title?.toLowerCase() === title.toLowerCase())
      );

      if (localDoc) {
        const net = await api.getCitationNetwork(localDoc.id);
        setCitationNetwork(net);
      } else {
        // Mock query structure using openalex directly or return graceful preview
        const res = await api.searchGlobalLiterature(title, 1, 5);
        setCitationNetwork({
          document_id: id,
          document_title: title,
          doi: doi || null,
          citation_count: 0,
          references: [],
          cited_by: [],
          top_related: res.results.filter((r) => r.id !== id),
        });
      }
    } catch (err: any) {
      console.error("Citation network fetch error:", err);
    } finally {
      setIsLoadingCitations(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Hero & Intro */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold tracking-widest text-cyan-400 uppercase bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
              Phase 6 Feature
            </span>
            <span className="text-xs text-slate-400">OpenAlex & Global Indexes</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight mt-1 flex items-center space-x-2">
            <Globe className="w-6 h-6 text-cyan-400" />
            <span>Academic Research Discovery</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Search 250M+ scientific publications, discover citation networks, and ingest Open Access papers directly into your workspace.
          </p>
        </div>

        {/* Quick Direct Ingestion Card */}
        <form
          onSubmit={handleDirectImport}
          className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col sm:flex-row items-center gap-2 max-w-xl w-full"
        >
          <div className="flex-1 w-full relative">
            <input
              type="text"
              value={directInput}
              onChange={(e) => setDirectInput(e.target.value)}
              placeholder="Paste DOI (e.g. 10.1038/...) or PDF URL"
              className="w-full bg-slate-950/80 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <button
            type="submit"
            disabled={isDirectImporting || !directInput.trim()}
            className="w-full sm:w-auto px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-950 font-semibold text-xs flex items-center justify-center space-x-1.5 transition-all shadow-sm"
          >
            {isDirectImporting ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Download className="w-3.5 h-3.5" />
            )}
            <span>Direct Ingest</span>
          </button>
        </form>
      </div>

      {/* Direct Ingest Alerts */}
      {directSuccess && (
        <div className="p-3 bg-emerald-950/60 border border-emerald-800/60 rounded-xl flex items-center justify-between text-xs text-emerald-300">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{directSuccess}</span>
          </div>
          <button
            onClick={() => setDirectSuccess(null)}
            className="text-slate-400 hover:text-white text-xs px-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {directError && (
        <div className="p-3 bg-red-950/60 border border-red-800/60 rounded-xl flex items-center justify-between text-xs text-red-300">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{directError}</span>
          </div>
          <button
            onClick={() => setDirectError(null)}
            className="text-slate-400 hover:text-white text-xs px-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Global Search Bar & Filters */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
        <form onSubmit={handleSearch} className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search global research (e.g., Sparse Transformers, Graph Neural Networks, LLM Hallucinations)..."
                className="w-full pl-10 pr-4 py-2.5 bg-slate-950/90 border border-slate-700/80 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 shadow-inner"
              />
            </div>
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className={`px-3 py-2.5 rounded-xl border text-xs font-medium flex items-center space-x-1.5 transition-colors ${
                showFilters
                  ? "bg-slate-800 border-cyan-500/50 text-cyan-300"
                  : "bg-slate-950 border-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              <span>Filters</span>
            </button>
            <button
              type="submit"
              disabled={isSearching || !query.trim()}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-slate-950 font-bold text-sm flex items-center space-x-2 transition-all shadow-md shadow-cyan-500/10 active:scale-95"
            >
              {isSearching ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Searching...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Search Literature</span>
                </>
              )}
            </button>
          </div>

          {/* Collapsible Filters */}
          {showFilters && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-800/80">
              <div>
                <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                  Author Filter
                </label>
                <input
                  type="text"
                  value={authorFilter}
                  onChange={(e) => setAuthorFilter(e.target.value)}
                  placeholder="e.g. Yann LeCun, Geoffrey Hinton"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                  Publication Year
                </label>
                <input
                  type="number"
                  value={yearFilter}
                  onChange={(e) => setYearFilter(e.target.value)}
                  placeholder="e.g. 2024"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          )}
        </form>
      </div>

      {/* Search Results Area */}
      {searchError && (
        <div className="p-4 bg-red-950/40 border border-red-800/50 rounded-xl text-sm text-red-300 flex items-center space-x-2">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <span>{searchError}</span>
        </div>
      )}

      {searchResponse && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400 px-1">
            <span>
              Found <strong className="text-white">{searchResponse.total_results.toLocaleString()}</strong> results for &ldquo;{searchResponse.query}&rdquo;
            </span>
            <span className="font-mono">Page {searchResponse.page}</span>
          </div>

          <div className="space-y-3">
            {searchResponse.results.length === 0 ? (
              <div className="p-8 text-center bg-slate-900/40 border border-slate-800 rounded-2xl text-slate-400 text-sm">
                No matching publications found. Try broadening your keywords.
              </div>
            ) : (
              searchResponse.results.map((paper) => {
                const isImported = Boolean(importedPapers[paper.id]);
                const isCurrentlyImporting = importingPaperId === paper.id;
                const importErr = importErrors[paper.id];
                const isAbstractExpanded = Boolean(expandedAbstracts[paper.id]);

                return (
                  <div
                    key={paper.id}
                    className="p-5 bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 rounded-2xl transition-all shadow-sm space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div className="space-y-1 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          {paper.is_open_access ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                              Open Access
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-950/80 text-amber-400 border border-amber-800/60">
                              Paywalled / Restricted
                            </span>
                          )}

                          {paper.publication_year && (
                            <span className="text-xs font-mono text-slate-400">
                              {paper.publication_year}
                            </span>
                          )}

                          {paper.venue && (
                            <span className="text-xs text-slate-400 truncate max-w-xs">
                              • {paper.venue}
                            </span>
                          )}

                          <span className="text-xs font-mono text-cyan-400/90 flex items-center space-x-1">
                            <Award className="w-3 h-3 inline" />
                            <span>{paper.citation_count.toLocaleString()} citations</span>
                          </span>
                        </div>

                        <h3 className="text-base font-bold text-white hover:text-cyan-300 transition-colors leading-snug">
                          {paper.title}
                        </h3>

                        {paper.authors.length > 0 && (
                          <p className="text-xs text-slate-400 line-clamp-1">
                            By {paper.authors.join(", ")}
                          </p>
                        )}
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center space-x-2 flex-shrink-0">
                        {isImported ? (
                          <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 text-xs font-medium">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                            <span>In Workspace</span>
                          </div>
                        ) : (
                          <button
                            onClick={() => handleImportResult(paper)}
                            disabled={isCurrentlyImporting || !paper.is_open_access}
                            title={
                              paper.is_open_access
                                ? "Import PDF into workspace and start indexing"
                                : "No open access PDF link available"
                            }
                            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all shadow-sm ${
                              paper.is_open_access
                                ? "bg-cyan-500 hover:bg-cyan-400 active:scale-95 text-slate-950"
                                : "bg-slate-800 text-slate-500 cursor-not-allowed"
                            }`}
                          >
                            {isCurrentlyImporting ? (
                              <>
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                <span>Importing...</span>
                              </>
                            ) : (
                              <>
                                <Download className="w-3.5 h-3.5" />
                                <span>Import to Workspace</span>
                              </>
                            )}
                          </button>
                        )}

                        <button
                          onClick={() => openCitationNetwork(paper.id, paper.title, paper.doi)}
                          title="View Citation Network & Related Literature"
                          className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-cyan-300 text-xs flex items-center space-x-1 transition-colors border border-slate-700/60"
                        >
                          <Network className="w-3.5 h-3.5" />
                          <span className="hidden sm:inline">Citations</span>
                        </button>

                        {paper.landing_page_url && (
                          <a
                            href={paper.landing_page_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                            title="Open external publisher page"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>
                    </div>

                    {/* Import error warning */}
                    {importErr && (
                      <div className="p-2.5 bg-red-950/40 border border-red-800/40 rounded-lg text-xs text-red-300 flex items-center space-x-2">
                        <AlertCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
                        <span>{importErr}</span>
                      </div>
                    )}

                    {/* Abstract toggle & content */}
                    {paper.abstract && (
                      <div className="text-xs text-slate-300 space-y-1 bg-slate-950/60 rounded-xl p-3 border border-slate-800/60">
                        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                          <span>Abstract</span>
                          <button
                            onClick={() => toggleAbstract(paper.id)}
                            className="text-cyan-400 hover:underline flex items-center space-x-0.5"
                          >
                            <span>{isAbstractExpanded ? "Collapse" : "Read full"}</span>
                            {isAbstractExpanded ? (
                              <ChevronUp className="w-3 h-3" />
                            ) : (
                              <ChevronDown className="w-3 h-3" />
                            )}
                          </button>
                        </div>
                        <p className={isAbstractExpanded ? "leading-relaxed" : "line-clamp-2 leading-relaxed"}>
                          {paper.abstract}
                        </p>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Citation Network Modal / Drawer */}
      {citationPaper && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center space-x-2">
                <Network className="w-5 h-5 text-cyan-400" />
                <div>
                  <h3 className="text-base font-bold text-white line-clamp-1">
                    Citation Graph: {citationPaper.title}
                  </h3>
                  <p className="text-xs text-slate-400">
                    Outbound References, Inbound Citations & Top Related Literature
                  </p>
                </div>
              </div>
              <button
                onClick={() => setCitationPaper(null)}
                className="text-slate-400 hover:text-white px-2 py-1 text-sm rounded-lg hover:bg-slate-800"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6">
              {isLoadingCitations ? (
                <div className="p-12 text-center space-y-3">
                  <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
                  <p className="text-sm text-slate-400">Traversing OpenAlex citation graph...</p>
                </div>
              ) : citationNetwork ? (
                <div className="space-y-6">
                  {/* Summary Metric */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl text-center">
                      <div className="text-xs text-slate-400">Recorded Citations</div>
                      <div className="text-lg font-bold text-cyan-300 font-mono">
                        {citationNetwork.citation_count.toLocaleString()}
                      </div>
                    </div>
                    <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl text-center">
                      <div className="text-xs text-slate-400">Outbound References</div>
                      <div className="text-lg font-bold text-white font-mono">
                        {citationNetwork.references.length}
                      </div>
                    </div>
                    <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl text-center">
                      <div className="text-xs text-slate-400">Inbound Citing Papers</div>
                      <div className="text-lg font-bold text-white font-mono">
                        {citationNetwork.cited_by.length}
                      </div>
                    </div>
                  </div>

                  {/* Section: Cited By (Inbound) */}
                  {citationNetwork.cited_by.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400 flex items-center space-x-1.5">
                        <Layers className="w-3.5 h-3.5" />
                        <span>Most Influential Citing Papers (Inbound)</span>
                      </h4>
                      <div className="space-y-2">
                        {citationNetwork.cited_by.map((c) => (
                          <div
                            key={c.id}
                            className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl flex items-center justify-between gap-3 text-xs"
                          >
                            <div>
                              <div className="font-semibold text-white">{c.title}</div>
                              <div className="text-slate-400 text-[11px]">
                                {c.authors.slice(0, 3).join(", ")} {c.publication_year ? `(${c.publication_year})` : ""} • {c.citation_count} citations
                              </div>
                            </div>
                            {c.is_open_access && (
                              <button
                                onClick={() => handleImportResult(c)}
                                className="px-2.5 py-1 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold rounded text-[11px] flex items-center space-x-1 flex-shrink-0"
                              >
                                <Download className="w-3 h-3" />
                                <span>Import</span>
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Section: Related Papers */}
                  {citationNetwork.top_related.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400 flex items-center space-x-1.5">
                        <BookOpen className="w-3.5 h-3.5" />
                        <span>Top Related Research</span>
                      </h4>
                      <div className="space-y-2">
                        {citationNetwork.top_related.map((r) => (
                          <div
                            key={r.id}
                            className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl flex items-center justify-between gap-3 text-xs"
                          >
                            <div>
                              <div className="font-semibold text-white">{r.title}</div>
                              <div className="text-slate-400 text-[11px]">
                                {r.authors.slice(0, 3).join(", ")} {r.publication_year ? `(${r.publication_year})` : ""} • {r.citation_count} citations
                              </div>
                            </div>
                            {r.is_open_access && (
                              <button
                                onClick={() => handleImportResult(r)}
                                className="px-2.5 py-1 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold rounded text-[11px] flex items-center space-x-1 flex-shrink-0"
                              >
                                <Download className="w-3 h-3" />
                                <span>Import</span>
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-sm text-slate-400">
                  No citation mapping available for this paper.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
