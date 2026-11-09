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
} from "lucide-react";
import { api } from "../lib/api";

interface DocumentListProps {
  documents: DocumentItem[];
  isLoading: boolean;
  onSelectDocument: (doc: DocumentItem) => void;
  onRefresh: () => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  isLoading,
  onSelectDocument,
  onRefresh,
}) => {
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("ALL");

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

  const handleDownload = (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const url = api.getDownloadUrl(docId);
    window.open(url, "_blank");
  };

  const filteredDocs = documents.filter((doc) => {
    if (filter === "ALL") return true;
    if (filter === "PROCESSING") return ["QUEUED", "PROCESSING", "UPLOADED"].includes(doc.status);
    return doc.status === filter;
  });

  const getStatusBadge = (doc: DocumentItem) => {
    switch (doc.status) {
      case "COMPLETED":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-950/70 text-emerald-400 border border-emerald-800/60">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Ready</span>
          </span>
        );
      case "PROCESSING":
      case "QUEUED":
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 animate-pulse">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>
              {doc.latest_job?.stage ? doc.latest_job.stage.replace(/_/g, " ") : "Processing..."} (
              {Math.round(doc.latest_job?.progress_pct || 0)}%)
            </span>
          </span>
        );
      case "FAILED":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-rose-950/70 text-rose-400 border border-rose-800/60">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-slate-900 text-slate-400 border border-slate-800">
            <Clock className="w-3.5 h-3.5" />
            <span>Uploaded</span>
          </span>
        );
    }
  };

  return (
    <div className="space-y-4">
      {/* Filtering Toolbar */}
      <div className="flex items-center justify-between border-b border-[#1E293B] pb-3">
        <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-xl border border-slate-900">
          {(["ALL", "PROCESSING", "COMPLETED", "FAILED"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                filter === tab
                  ? "bg-slate-800 text-cyan-400 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {tab.charAt(0) + tab.slice(1).toLowerCase()}
            </button>
          ))}
        </div>

        <div className="text-xs text-slate-500 font-mono">
          Showing {filteredDocs.length} of {documents.length} papers
        </div>
      </div>

      {/* Loading Skeleton */}
      {isLoading && documents.length === 0 && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 bg-slate-900/50 rounded-xl border border-slate-800/60 animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && filteredDocs.length === 0 && (
        <div className="text-center py-16 px-4 border border-dashed border-slate-800 rounded-2xl bg-slate-950/20">
          <div className="w-12 h-12 rounded-xl bg-slate-900 flex items-center justify-center mx-auto mb-3 text-slate-600">
            <FileText className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-semibold text-slate-300">No Research Documents Found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
            {filter === "ALL"
              ? "Upload academic papers in PDF format to begin deterministic evidence extraction."
              : `No documents currently in '${filter}' status.`}
          </p>
        </div>
      )}

      {/* Documents Grid / List */}
      <div className="space-y-2.5">
        {filteredDocs.map((doc) => {
          const isProcessing = ["QUEUED", "PROCESSING", "UPLOADED"].includes(doc.status);
          const title = doc.metadata?.title || doc.filename;

          return (
            <div
              key={doc.id}
              onClick={() => onSelectDocument(doc)}
              className="group p-4 rounded-xl bg-[#0E1424] hover:bg-[#141C2E] border border-slate-800/80 hover:border-cyan-500/40 transition-all cursor-pointer shadow-sm relative overflow-hidden"
            >
              {/* Subtle top indicator bar for processing */}
              {isProcessing && (
                <div
                  className="absolute top-0 left-0 h-0.5 bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
                  style={{ width: `${doc.latest_job?.progress_pct || 15}%` }}
                />
              )}

              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start space-x-3.5 min-w-0">
                  <div className="w-10 h-10 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-cyan-400 shrink-0 group-hover:border-cyan-500/40 transition-colors">
                    <FileText className="w-5 h-5" />
                  </div>

                  <div className="min-w-0 space-y-1">
                    <div className="flex items-center space-x-2">
                      <h4 className="font-semibold text-sm text-slate-100 group-hover:text-cyan-300 transition-colors truncate">
                        {title}
                      </h4>
                      {doc.metadata?.doi && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-cyan-400 border border-slate-800 shrink-0">
                          DOI:{doc.metadata.doi}
                        </span>
                      )}
                    </div>

                    {/* Metadata tags */}
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400 font-mono">
                      <span>{doc.filename}</span>
                      <span>•</span>
                      <span>{(doc.file_size_bytes / (1024 * 1024)).toFixed(2)} MB</span>
                      {doc.metadata?.total_pages ? (
                        <>
                          <span>•</span>
                          <span className="flex items-center space-x-1">
                            <Layers className="w-3 h-3 text-cyan-400" />
                            <span>{doc.metadata.total_pages} pages</span>
                          </span>
                        </>
                      ) : null}
                      <span>•</span>
                      <span className="flex items-center space-x-1">
                        <Calendar className="w-3 h-3 text-slate-500" />
                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                      </span>
                    </div>

                    {doc.error_message && (
                      <p className="text-xs text-rose-400 font-mono mt-1">
                        Error: {doc.error_message}
                      </p>
                    )}
                  </div>
                </div>

                {/* Right Status & Actions */}
                <div className="flex items-center space-x-3 shrink-0">
                  {getStatusBadge(doc)}

                  <div className="flex items-center space-x-1 opacity-80 group-hover:opacity-100 transition-opacity">
                    {doc.status === "FAILED" && (
                      <button
                        onClick={(e) => handleRetry(doc.id, e)}
                        disabled={retryingId === doc.id}
                        title="Retry Extraction"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-cyan-400 hover:bg-slate-900 transition-colors"
                      >
                        <RotateCcw
                          className={`w-4 h-4 ${retryingId === doc.id ? "animate-spin" : ""}`}
                        />
                      </button>
                    )}

                    <button
                      onClick={(e) => handleDownload(doc.id, e)}
                      title="Download PDF"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-900 transition-colors"
                    >
                      <Download className="w-4 h-4" />
                    </button>

                    <button
                      onClick={(e) => handleDelete(doc.id, doc.filename, e)}
                      disabled={deletingId === doc.id}
                      title="Delete Document"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-900 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>

                    <button
                      onClick={() => onSelectDocument(doc)}
                      title="Inspect Provenance"
                      className="p-1.5 rounded-lg text-cyan-400 hover:bg-slate-900 transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
