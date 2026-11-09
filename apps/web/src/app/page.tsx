"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Header } from "../components/Header";
import { DocumentList } from "../components/DocumentList";
import { UploadModal } from "../components/UploadModal";
import { DocumentDetailView } from "../components/DocumentDetailView";
import { AuthModal } from "../components/AuthModal";
import { DocumentItem, User } from "../types";
import { api } from "../lib/api";
import {
  FileText,
  Layers,
  Sparkles,
  ShieldCheck,
  Activity,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);

  // Check initial user authentication
  useEffect(() => {
    const checkAuth = async () => {
      try {
        if (api.getToken()) {
          const u = await api.getMe();
          setUser(u);
        }
      } catch {
        api.logout();
        setUser(null);
      }
    };
    checkAuth();
  }, []);

  // Fetch document catalog
  const fetchDocuments = useCallback(async () => {
    try {
      if (!api.getToken()) {
        setDocuments([]);
        setIsLoading(false);
        return;
      }
      const data = await api.listDocuments();
      setDocuments(data);
    } catch (err) {
      console.error("Error fetching documents:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments, user]);

  // Real-time polling for in-flight processing jobs
  useEffect(() => {
    const hasActiveJobs = documents.some((d) =>
      ["UPLOADED", "QUEUED", "PROCESSING"].includes(d.status)
    );

    if (!hasActiveJobs) return;

    const interval = setInterval(() => {
      fetchDocuments();
    }, 2500);

    return () => clearInterval(interval);
  }, [documents, fetchDocuments]);

  const handleLogout = () => {
    api.logout();
    setUser(null);
    setDocuments([]);
  };

  // Compute metrics
  const totalDocs = documents.length;
  const completedDocs = documents.filter((d) => d.status === "COMPLETED").length;
  const totalPages = documents.reduce(
    (acc, d) => acc + (d.metadata?.total_pages || 0),
    0
  );
  const processingCount = documents.filter((d) =>
    ["UPLOADED", "QUEUED", "PROCESSING"].includes(d.status)
  ).length;

  return (
    <div className="min-h-screen flex flex-col bg-[#080C14]">
      {/* Header */}
      <Header
        user={user}
        onOpenAuth={() => setIsAuthOpen(true)}
        onOpenUpload={() => {
          if (!user) {
            setIsAuthOpen(true);
          } else {
            setIsUploadOpen(true);
          }
        }}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero & Workspace Banner */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#0E1424] via-[#141C2E] to-[#0A0E1A] border border-[#1E293B] p-6 sm:p-8">
          <div className="absolute right-0 top-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10 max-w-2xl space-y-3">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-cyan-300 text-xs font-mono">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Phase 1 — Deterministic Ingestion & Extraction Engine</span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              VERITAS Research Intelligence
            </h1>

            <p className="text-sm text-slate-400 leading-relaxed font-normal">
              High-fidelity PDF document ingestion with multi-stage layout decomposition,
              cryptographic integrity verification, and page-level provenance preservation.
            </p>
          </div>

          {/* Metrics bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-6 border-t border-slate-800/80">
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-[11px] text-slate-400 font-medium">Total Ingested</span>
              <p className="text-xl font-bold text-slate-100 font-mono mt-0.5">{totalDocs}</p>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-[11px] text-slate-400 font-medium">Ready for RAG</span>
              <p className="text-xl font-bold text-emerald-400 font-mono mt-0.5">{completedDocs}</p>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-[11px] text-slate-400 font-medium">Decomposed Pages</span>
              <p className="text-xl font-bold text-cyan-400 font-mono mt-0.5">{totalPages}</p>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-[11px] text-slate-400 font-medium">Active Workers</span>
              <p className="text-xl font-bold text-sky-400 font-mono mt-0.5 flex items-center space-x-1.5">
                <span>{processingCount}</span>
                {processingCount > 0 && <Activity className="w-4 h-4 animate-pulse text-cyan-400" />}
              </p>
            </div>
          </div>
        </div>

        {/* Auth prompt if not logged in */}
        {!user && !isLoading && (
          <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-800/40 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <ShieldCheck className="w-5 h-5 text-cyan-400 shrink-0" />
              <p className="text-xs text-cyan-200">
                Please sign in to your institutional account to upload and explore your private research documents.
              </p>
            </div>
            <button
              onClick={() => setIsAuthOpen(true)}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 transition-colors"
            >
              Sign In Now
            </button>
          </div>
        )}

        {/* Document Library Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">
                Literature Catalog
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic provenance • Structured chunks • Section hierarchy
              </p>
            </div>

            <button
              onClick={fetchDocuments}
              title="Refresh Catalog"
              className="p-2 rounded-lg text-slate-400 hover:text-cyan-400 hover:bg-slate-900 border border-slate-800/80 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            </button>
          </div>

          <DocumentList
            documents={documents}
            isLoading={isLoading}
            onSelectDocument={(doc) => setSelectedDocId(doc.id)}
            onRefresh={fetchDocuments}
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#1E293B] bg-[#0A0E1A] py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-slate-300">VERITAS</span>
            <span>•</span>
            <span>Research Intelligence. Grounded in Truth.</span>
          </div>
          <div className="font-mono text-[11px]">
            Phase 1 Engine v1.0.0 • PyMuPDF Layout Parser • Strict Multi-Tenant Isolation
          </div>
        </div>
      </footer>

      {/* Modals */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={() => {
          setIsUploadOpen(false);
          fetchDocuments();
        }}
      />

      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onAuthSuccess={(u) => {
          setUser(u);
          fetchDocuments();
        }}
      />

      {selectedDocId && (
        <DocumentDetailView
          documentId={selectedDocId}
          onClose={() => setSelectedDocId(null)}
          onRefreshList={fetchDocuments}
        />
      )}
    </div>
  );
}
