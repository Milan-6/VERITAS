"use client";

import React, { useState } from "react";
import { DocumentItem } from "../types";
import {
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  Trash2,
  Download,
  Eye,
  Loader2,
  Calendar,
  Layers,
  Search,
  Hash,
  BookOpen,
  Filter,
  Network,
} from "lucide-react";
import { api } from "../lib/api";
import { useKnowledgeStore } from "../store/useKnowledgeStore";

interface DocumentHubViewProps {
  documents: DocumentItem[];
  isLoading: boolean;
  onSelectDocument: (doc: DocumentItem) => void;
  onRefresh: () => void;
  onOpenUpload: () => void;
  onViewGraph?: (doc: DocumentItem) => void;
}

export const DocumentHubView: React.FC<DocumentHubViewProps> = ({
  documents,
  isLoading,
  onSelectDocument,
  onRefresh,
  onOpenUpload,
  onViewGraph,
}) => {
  const setGraphData = useKnowledgeStore((state) => state.setGraphData);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [loadingGraphId, setLoadingGraphId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Ensure documents are fetched on component mount if initially empty
  React.useEffect(() => {
    if (documents.length === 0) {
      onRefresh();
    }
  }, []);

  const handleOpenGraph = async (doc: DocumentItem, e: React.MouseEvent) => {
    e.stopPropagation();
    setLoadingGraphId(doc.id);
    try {
      const tree = await api.getDocumentTree(doc.id);
      if (tree && tree.nodes) {
        setGraphData({
          documentId: doc.id,
          filename: doc.filename,
          nodes: tree.nodes,
          links: tree.links || [],
          hierarchy: tree.nodes.map((n) => ({
            id: n.id,
            title: n.label,
            level: n.level,
            level_name: `L${n.level} - ${n.level === 0 ? "Root" : n.level === 1 ? "Section" : n.level === 2 ? "Subsection" : "Concept"}`,
            page: 1,
          })),
          evidence: tree.nodes.slice(1).map((n) => ({
            id: `ev_${n.id}`,
            section: n.label,
            page: 1,
            text: n.panel_payload,
            level: n.level,
          })),
        });
      }
      if (onViewGraph) {
        onViewGraph(doc);
      }
    } catch (err: any) {
      console.error("Failed to load document graph:", err);
    } finally {
      setLoadingGraphId(null);
    }
  };

  const handleRetry = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setRetryingId(docId);
    try {
      await api.retryProcessing(docId);
      onRefresh();
    } catch (err: any) {
      alert(`Retry failed: ${err.message}`);
    } finally {
      setRetryingId(null);
    }
  };

  const handleDelete = async (docId: string, filename: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Are you sure you want to permanently delete "${filename}"?`)) {
      return;
    }
    setDeletingId(docId);
    try {
      await api.deleteDocument(docId);
      onRefresh();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const handleDownload = (docId: string, filename: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const downloadUrl = api.getDownloadUrl(docId);
    const token = api.getToken();
    if (token) {
      // Direct authenticated fetch download
      fetch(downloadUrl, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.blob())
        .then((blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);
        })
        .catch((err) => alert(`Download failed: ${err.message}`));
    } else {
      window.open(downloadUrl, "_blank");
    }
  };

  // Filter & Search logic
  const filteredDocs = documents.filter((doc) => {
    const matchesStatus = statusFilter === "ALL" || doc.status === statusFilter;
    const matchesQuery =
      searchQuery === "" ||
      doc.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.metadata?.title && doc.metadata.title.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (doc.metadata?.doi && doc.metadata.doi.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesQuery;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            <span>Indexed</span>
          </span>
        );
      case "PROCESSING":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200 animate-pulse">
            <Loader2 className="w-3 h-3 animate-spin text-amber-600" />
            <span>Processing</span>
          </span>
        );
      case "QUEUED":
      case "UPLOADED":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
            <Clock className="w-3 h-3 text-blue-600" />
            <span>Queued</span>
          </span>
        );
      case "FAILED":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3 h-3 text-rose-600" />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-surface-subtle text-ink-500 border border-border">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Search & Filter Header Bar */}
      <div className="bg-panel border border-border rounded-2xl p-4 shadow-subtle flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="relative flex-1 w-full max-w-md">
          <Search className="w-4 h-4 text-ink-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search papers by filename, title, or DOI..."
            className="w-full bg-surface-subtle border border-border rounded-xl pl-9 pr-4 py-2 text-xs text-ink-900 placeholder-ink-400 focus:outline-none focus:border-veritas-500 transition-colors"
          />
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center space-x-1 bg-surface-subtle p-1 rounded-xl border border-border text-xs w-full md:w-auto overflow-x-auto">
          {["ALL", "COMPLETED", "PROCESSING", "FAILED"].map((tab) => (
            <button
              key={tab}
              onClick={() => setStatusFilter(tab)}
              className={`px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-colors ${
                statusFilter === tab
                  ? "bg-panel text-ink-900 shadow-subtle font-semibold"
                  : "text-ink-500 hover:text-ink-900"
              }`}
            >
              {tab === "ALL" ? "All Papers" : tab === "COMPLETED" ? "Indexed" : tab}
            </button>
          ))}
        </div>
      </div>

      {/* Main Table / Grid */}
      {isLoading && documents.length === 0 ? (
        <div className="bg-panel border border-border rounded-2xl p-12 text-center text-xs text-ink-400 space-y-3 shadow-subtle">
          <Loader2 className="w-6 h-6 animate-spin text-veritas-600 mx-auto" />
          <p>Loading research library from database...</p>
        </div>
      ) : filteredDocs.length === 0 ? (
        <div className="bg-panel border border-border rounded-2xl p-12 text-center space-y-4 shadow-subtle">
          <div className="w-12 h-12 rounded-2xl bg-surface-subtle border border-border flex items-center justify-center text-ink-400 mx-auto">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-ink-900">No documents found</h3>
            <p className="text-xs text-ink-500 mt-1">
              {searchQuery || statusFilter !== "ALL"
                ? "Try adjusting your search query or status filter."
                : "Upload research papers (PDF) to begin grounded extraction and 3D indexing."}
            </p>
          </div>
          <button
            onClick={onOpenUpload}
            className="inline-flex items-center space-x-1.5 bg-ink-900 hover:bg-ink-700 text-white px-4 py-2 rounded-xl text-xs font-medium transition-colors shadow-subtle"
          >
            <span>Upload Research Paper</span>
          </button>
        </div>
      ) : (
        <div className="bg-panel border border-border rounded-2xl shadow-subtle overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-border bg-surface-subtle text-ink-500 font-semibold text-[11px] uppercase tracking-wider">
                  <th className="py-3 px-4">Research Document</th>
                  <th className="py-3 px-4 hidden md:table-cell">Metadata & DOI</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 hidden sm:table-cell">Fingerprint</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredDocs.map((doc) => (
                  <tr
                    key={doc.id}
                    onClick={() => onSelectDocument(doc)}
                    className="hover:bg-surface-subtle cursor-pointer transition-colors group"
                  >
                    {/* Document Title / Filename */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-start space-x-3">
                        <div className="w-8 h-8 rounded-lg bg-veritas-50 border border-veritas-100 flex items-center justify-center text-veritas-600 shrink-0 mt-0.5">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div className="min-w-0 max-w-xs sm:max-w-md">
                          <p className="font-semibold text-ink-900 truncate group-hover:text-veritas-600 transition-colors">
                            {doc.metadata?.title || doc.filename}
                          </p>
                          <div className="flex items-center space-x-2 text-[11px] text-ink-400 mt-0.5">
                            <span className="font-mono">{doc.filename}</span>
                            <span>•</span>
                            <span>{(doc.file_size_bytes / (1024 * 1024)).toFixed(2)} MB</span>
                            {doc.metadata?.total_pages ? (
                              <>
                                <span>•</span>
                                <span>{doc.metadata.total_pages} Pages</span>
                              </>
                            ) : null}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Metadata / Authors */}
                    <td className="py-3.5 px-4 hidden md:table-cell text-ink-500">
                      {doc.metadata?.doi ? (
                        <div className="space-y-0.5">
                          <span className="font-mono text-[10px] bg-surface-muted px-1.5 py-0.5 rounded text-ink-700 border border-border">
                            DOI: {doc.metadata.doi}
                          </span>
                          {doc.metadata.authors && doc.metadata.authors.length > 0 && (
                            <p className="text-[11px] text-ink-400 truncate max-w-[200px]">
                              {doc.metadata.authors.join(", ")}
                            </p>
                          )}
                        </div>
                      ) : (
                        <span className="text-ink-400 text-[11px]">Auto-extracted</span>
                      )}
                    </td>

                    {/* Status Badge */}
                    <td className="py-3.5 px-4">{getStatusBadge(doc.status)}</td>

                    {/* Cryptographic SHA-256 Badge */}
                    <td className="py-3.5 px-4 hidden sm:table-cell">
                      <span className="inline-flex items-center space-x-1 font-mono text-[10px] text-ink-500 bg-surface-subtle px-2 py-1 rounded border border-border" title={doc.file_hash_sha256}>
                        <Hash className="w-3 h-3 text-veritas-gold shrink-0" />
                        <span>{doc.file_hash_sha256.slice(0, 10)}...</span>
                      </span>
                    </td>

                    {/* Action Controls */}
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end space-x-1.5" onClick={(e) => e.stopPropagation()}>
                        {doc.status === "FAILED" && (
                          <button
                            onClick={(e) => handleRetry(doc.id, e)}
                            title="Retry Extraction"
                            disabled={retryingId === doc.id}
                            className="p-1.5 rounded-lg text-ink-500 hover:text-ink-900 hover:bg-surface-muted border border-border transition-colors"
                          >
                            <RotateCcw className={`w-3.5 h-3.5 ${retryingId === doc.id ? "animate-spin" : ""}`} />
                          </button>
                        )}

                        <button
                          onClick={(e) => handleOpenGraph(doc, e)}
                          title="Explore Knowledge Graph"
                          disabled={loadingGraphId === doc.id}
                          className="p-1.5 rounded-lg text-veritas-600 hover:text-veritas-700 hover:bg-veritas-50 border border-veritas-200 transition-colors"
                        >
                          <Network className={`w-3.5 h-3.5 ${loadingGraphId === doc.id ? "animate-spin" : ""}`} />
                        </button>

                        <button
                          onClick={(e) => handleDownload(doc.id, doc.filename, e)}
                          title="Download Original PDF"
                          className="p-1.5 rounded-lg text-ink-500 hover:text-ink-900 hover:bg-surface-muted border border-border transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </button>

                        <button
                          onClick={(e) => handleDelete(doc.id, doc.filename, e)}
                          title="Delete Paper"
                          disabled={deletingId === doc.id}
                          className="p-1.5 rounded-lg text-ink-400 hover:text-rose-600 hover:bg-rose-50 border border-border transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
