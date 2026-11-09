"use client";

import React, { useState, useEffect } from "react";
import { DocumentDetail, DocumentItem } from "../types";
import {
  X,
  FileText,
  Layers,
  BookOpen,
  Hash,
  Download,
  RotateCcw,
  Code,
  Tag,
  Calendar,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { api } from "../lib/api";

interface DocumentDetailViewProps {
  documentId: string;
  onClose: () => void;
  onRefreshList: () => void;
}

export const DocumentDetailView: React.FC<DocumentDetailViewProps> = ({
  documentId,
  onClose,
  onRefreshList,
}) => {
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"metadata" | "sections" | "chunks" | "pages" | "raw">("metadata");
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  const fetchDetail = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getDocumentDetail(documentId);
      setDetail(data);
    } catch (err: any) {
      setError(err.message || "Failed to load document details");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [documentId]);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await api.retryProcessing(documentId);
      await fetchDetail();
      onRefreshList();
    } catch (err: any) {
      alert(`Retry failed: ${err.message}`);
    } finally {
      setRetrying(false);
    }
  };

  if (!detail && isLoading) {
    return (
      <div className="fixed inset-y-0 right-0 w-full sm:max-w-2xl bg-[#0B0F17] border-l border-[#1E293B] z-50 p-6 flex flex-col justify-center items-center space-y-3">
        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
        <p className="text-sm font-medium text-slate-400">Loading research provenance...</p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="fixed inset-y-0 right-0 w-full sm:max-w-2xl bg-[#0B0F17] border-l border-[#1E293B] z-50 p-6 flex flex-col">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-sm font-bold text-red-400">Error Loading Document</h2>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="text-sm text-slate-300 font-mono">{error || "Document not found."}</p>
      </div>
    );
  }

  const meta = detail.metadata;

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:max-w-2xl bg-[#0A0E1A] border-l border-[#1E293B] z-50 flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
      {/* Top Header */}
      <div className="p-5 border-b border-[#1E293B] bg-[#0E1424] flex items-start justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-mono uppercase bg-cyan-950 text-cyan-400 border border-cyan-800/60 px-2 py-0.5 rounded">
              {detail.status}
            </span>
            <span className="text-xs text-slate-400 font-mono truncate">{detail.filename}</span>
          </div>
          <h2 className="text-base font-bold text-white truncate">
            {meta?.title || detail.filename}
          </h2>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <button
            onClick={() => window.open(api.getDownloadUrl(detail.id), "_blank")}
            title="Download PDF"
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <Download className="w-4 h-4" />
          </button>

          {detail.status === "FAILED" && (
            <button
              onClick={handleRetry}
              disabled={retrying}
              title="Retry Extraction"
              className="p-2 rounded-lg text-slate-400 hover:text-cyan-400 hover:bg-slate-800 transition-colors"
            >
              <RotateCcw className={`w-4 h-4 ${retrying ? "animate-spin" : ""}`} />
            </button>
          )}

          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center space-x-1 px-4 border-b border-[#1E293B] bg-[#080C14] overflow-x-auto">
        {[
          { id: "metadata", label: "Overview & Metadata", icon: BookOpen },
          { id: "sections", label: `Sections (${detail.extracted_sections?.length || 0})`, icon: Layers },
          { id: "chunks", label: `Provenance (${detail.extracted_contents?.length || 0})`, icon: Hash },
          { id: "pages", label: `Pages (${detail.extracted_pages?.length || 0})`, icon: FileText },
          { id: "raw", label: "JSON Raw", icon: Code },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 py-3 px-3 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? "border-cyan-400 text-cyan-400 bg-cyan-950/20"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Content Body */}
      <div className="p-6 overflow-y-auto flex-1 space-y-6">
        {/* Tab 1: Overview & Metadata */}
        {activeTab === "metadata" && (
          <div className="space-y-6 text-sm">
            {/* Title & Authors */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Title</h3>
              <p className="text-base font-semibold text-slate-100">
                {meta?.title || "No title extracted"}
              </p>
            </div>

            {meta?.authors && meta.authors.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Authors</h3>
                <div className="flex flex-wrap gap-1.5">
                  {meta.authors.map((author, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-xs text-slate-200 font-medium"
                    >
                      {author}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Abstract */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Abstract</h3>
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs leading-relaxed text-slate-300 whitespace-pre-line font-serif">
                {meta?.abstract || "No abstract recognized in document."}
              </div>
            </div>

            {/* Scientific Properties Grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800">
                <span className="text-[11px] text-slate-400">Digital Object Identifier (DOI)</span>
                <p className="text-xs font-mono text-cyan-300 mt-1 font-semibold truncate">
                  {meta?.doi || "None detected"}
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800">
                <span className="text-[11px] text-slate-400">Total Pages</span>
                <p className="text-xs font-mono text-slate-100 mt-1 font-semibold">
                  {meta?.total_pages || detail.extracted_pages.length} pages
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800">
                <span className="text-[11px] text-slate-400">Publication Date</span>
                <p className="text-xs font-mono text-slate-100 mt-1 truncate">
                  {meta?.publication_date || "Unknown"}
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800">
                <span className="text-[11px] text-slate-400">Cryptographic SHA-256</span>
                <p className="text-[10px] font-mono text-slate-400 mt-1 truncate" title={detail.file_hash_sha256}>
                  {detail.file_hash_sha256}
                </p>
              </div>
            </div>

            {/* Keywords */}
            {meta?.keywords && meta.keywords.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                  <Tag className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Keywords</span>
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {meta.keywords.map((kw, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-950/40 text-cyan-300 border border-cyan-800/50"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Extracted Sections */}
        {activeTab === "sections" && (
          <div className="space-y-2.5">
            <p className="text-xs text-slate-400">
              Hierarchical section structure recognized by the layout decomposition engine:
            </p>

            {detail.extracted_sections.length === 0 ? (
              <p className="text-xs text-slate-500 font-mono">No structured sections detected.</p>
            ) : (
              detail.extracted_sections.map((sec) => (
                <div
                  key={sec.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs"
                >
                  <div className="flex items-center space-x-2">
                    <span className="w-5 h-5 rounded flex items-center justify-center text-[10px] font-mono font-bold bg-cyan-950 text-cyan-400 border border-cyan-800">
                      {sec.section_level}
                    </span>
                    <span className="font-semibold text-slate-100">{sec.section_title}</span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    Pages {sec.start_page} – {sec.end_page}
                  </span>
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 3: Provenance Chunks */}
        {activeTab === "chunks" && (
          <div className="space-y-4">
            <p className="text-xs text-slate-400">
              Deterministic chunks preserved with page-level bounding boxes and section ancestry:
            </p>

            <div className="space-y-3 max-h-[550px] overflow-y-auto pr-1">
              {detail.extracted_contents.map((chunk) => (
                <div
                  key={chunk.id}
                  className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-[10px] text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800/50">
                        {chunk.chunk_id}
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300">
                        {chunk.content_type}
                      </span>
                    </div>
                    <span className="font-mono text-[11px] text-slate-400">
                      Page {chunk.page_number} • {chunk.section}
                    </span>
                  </div>

                  <p className="text-slate-200 leading-relaxed font-sans text-xs">
                    {chunk.source_text}
                  </p>

                  {chunk.bounding_box && (
                    <div className="text-[10px] font-mono text-slate-500 pt-1">
                      bbox: [x0: {chunk.bounding_box.x0}, y0: {chunk.bounding_box.y0}, x1: {chunk.bounding_box.x1}, y1: {chunk.bounding_box.y1}] • method: {chunk.extraction_method}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 4: Pages */}
        {activeTab === "pages" && (
          <div className="grid grid-cols-2 gap-3">
            {detail.extracted_pages.map((p) => (
              <div
                key={p.id}
                className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1.5 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-200 font-mono">Page {p.page_number}</span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {Math.round(p.width)} × {Math.round(p.height)} pt
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 font-mono space-y-0.5">
                  <p>Text length: {p.text_length} chars</p>
                  <p>Images detected: {p.has_images ? "Yes" : "No"}</p>
                  <p>Tables detected: {p.has_tables ? "Yes" : "No"}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Tab 5: Raw JSON */}
        {activeTab === "raw" && (
          <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-cyan-300 overflow-x-auto max-h-[500px]">
            {JSON.stringify(detail, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
};
