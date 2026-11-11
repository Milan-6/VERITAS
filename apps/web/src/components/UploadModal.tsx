"use client";

import React, { useState, useRef } from "react";
import { Upload, X, FileText, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { useKnowledgeStore } from "../store/useKnowledgeStore";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (uploadResponse?: any) => void;
}

interface PendingFile {
  file: File;
  progress: number;
  status: "idle" | "uploading" | "done" | "error";
  error?: string;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [files, setFiles] = useState<PendingFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const setGraphData = useKnowledgeStore((state) => state.setGraphData);

  if (!isOpen) return null;

  const handleFilesSelected = (selectedFiles: FileList | null) => {
    if (!selectedFiles) return;

    const newEntries: PendingFile[] = [];
    for (let i = 0; i < selectedFiles.length; i++) {
      const f = selectedFiles[i];

      // Pre-flight validation
      if (!f.name.toLowerCase().endsWith(".pdf")) {
        newEntries.push({
          file: f,
          progress: 0,
          status: "error",
          error: "Only .pdf files are accepted.",
        });
        continue;
      }

      if (f.size === 0) {
        newEntries.push({
          file: f,
          progress: 0,
          status: "error",
          error: "Empty 0-byte file rejected.",
        });
        continue;
      }

      if (f.size > 50 * 1024 * 1024) {
        newEntries.push({
          file: f,
          progress: 0,
          status: "error",
          error: "Exceeds 50MB size limit.",
        });
        continue;
      }

      newEntries.push({
        file: f,
        progress: 0,
        status: "idle",
      });
    }

    setFiles((prev) => [...prev, ...newEntries]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFilesSelected(e.dataTransfer.files);
  };

  const handleUploadAll = async () => {
    setIsSubmitting(true);
    let anySuccess = false;

    for (let i = 0; i < files.length; i++) {
      const entry = files[i];
      if (entry.status === "done" || entry.status === "error") continue;

      setFiles((prev) =>
        prev.map((item, idx) => (idx === i ? { ...item, status: "uploading", progress: 10 } : item))
      );

      try {
        const res = await api.uploadDocument(entry.file, (pct) => {
          setFiles((prev) =>
            prev.map((item, idx) => (idx === i ? { ...item, progress: pct } : item))
          );
        });

        // Immediately sync new document data into Zustand Knowledge Store
        if (res) {
          const docId = res.document_id || res.document?.id;
          const fileName = res.filename || res.document?.filename || entry.file.name;
          if (res.graph?.nodes && res.graph.nodes.length > 0) {
            setGraphData({
              documentId: docId,
              filename: fileName,
              graph: res.graph,
              hierarchy: res.hierarchy,
              evidence: res.evidence,
            });
          }
        }

        setFiles((prev) =>
          prev.map((item, idx) =>
            idx === i ? { ...item, status: "done", progress: 100 } : item
          )
        );
        anySuccess = true;
      } catch (err: any) {
        setFiles((prev) =>
          prev.map((item, idx) =>
            idx === i
              ? { ...item, status: "error", error: err.message || "Upload failed." }
              : item
          )
        );
      }
    }

    setIsSubmitting(false);
    if (anySuccess) {
      onUploadSuccess();
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, idx) => idx !== index));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-[#0E1424] border border-[#1E293B] rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-[#1E293B] flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <span>Ingest Scientific Documents</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Secure PDF Ingestion & Extraction Engine • 50MB Limit
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
          {/* Drag & Drop Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
              isDragging
                ? "border-cyan-400 bg-cyan-950/20"
                : "border-slate-800 hover:border-cyan-500/50 hover:bg-slate-900/40 bg-slate-950/30"
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => handleFilesSelected(e.target.files)}
              multiple
              accept="application/pdf"
              className="hidden"
            />
            <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mx-auto mb-3 text-cyan-400">
              <Upload className="w-6 h-6" />
            </div>
            <p className="text-sm font-medium text-slate-200">
              Drop academic PDF files here, or <span className="text-cyan-400 underline">browse</span>
            </p>
            <p className="text-xs text-slate-500 mt-1 font-mono">
              Supports single and batch uploads. Layout-aware parsed into deterministic chunks.
            </p>
          </div>

          {/* Pending Files List */}
          {files.length > 0 && (
            <div className="space-y-2 mt-4">
              <div className="flex items-center justify-between text-xs text-slate-400 px-1">
                <span>Selected Documents ({files.length})</span>
                <button
                  onClick={() => setFiles([])}
                  className="text-slate-500 hover:text-slate-300 transition-colors"
                >
                  Clear all
                </button>
              </div>

              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {files.map((item, index) => (
                  <div
                    key={index}
                    className="flex flex-col p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2.5 truncate pr-2">
                        <FileText className="w-4 h-4 text-cyan-400 shrink-0" />
                        <span className="font-medium text-slate-200 truncate">
                          {item.file.name}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono shrink-0">
                          ({(item.file.size / (1024 * 1024)).toFixed(2)} MB)
                        </span>
                      </div>

                      <div className="flex items-center space-x-2 shrink-0">
                        {item.status === "uploading" && (
                          <div className="flex items-center space-x-1 text-cyan-400">
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            <span>{item.progress}%</span>
                          </div>
                        )}
                        {item.status === "done" && (
                          <span className="flex items-center text-emerald-400 space-x-1">
                            <CheckCircle2 className="w-4 h-4" />
                            <span>Ready</span>
                          </span>
                        )}
                        {item.status === "error" && (
                          <span className="flex items-center text-red-400 space-x-1">
                            <AlertCircle className="w-4 h-4" />
                            <span>Error</span>
                          </span>
                        )}
                        {item.status === "idle" && (
                          <button
                            onClick={() => removeFile(index)}
                            className="text-slate-500 hover:text-red-400"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>

                    {item.status === "uploading" && (
                      <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-cyan-400 h-1.5 rounded-full transition-all duration-200"
                          style={{ width: `${item.progress}%` }}
                        />
                      </div>
                    )}

                    {item.error && (
                      <p className="text-[11px] text-red-400 font-mono">{item.error}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-[#1E293B] bg-[#0A0E1A] flex items-center justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleUploadAll}
            disabled={isSubmitting || files.every((f) => f.status === "done" || f.status === "error")}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm shadow-cyan-500/20"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Uploading & Queueing...</span>
              </>
            ) : (
              <span>Start Ingestion</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
