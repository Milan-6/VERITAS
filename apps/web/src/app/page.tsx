"use client";

import React, { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { Header, NavTab } from "../components/Header";
import { DashboardView } from "../components/DashboardView";
import { DocumentHubView } from "../components/DocumentHubView";
import { ResearchStudioView } from "../components/ResearchStudioView";
import { AdaptiveStudySuite } from "../components/AdaptiveStudySuite";
import { UploadModal } from "../components/UploadModal";
import { DocumentDetailView } from "../components/DocumentDetailView";
import { AuthModal } from "../components/AuthModal";
import { WorkspaceSettingsModal } from "../components/WorkspaceSettingsModal";
import { DocumentItem, User, WorkspaceItem } from "../types";
import { api } from "../lib/api";
import { RefreshCw } from "lucide-react";

// Dynamic client-only import for Three.js WebGL Knowledge Explorer (prevents SSR window errors)
const UniversalKnowledgeExplorer = dynamic(
  () => import("../components/UniversalKnowledgeExplorer").then((mod) => mod.UniversalKnowledgeExplorer),
  {
    ssr: false,
    loading: () => (
      <div className="flex-1 flex items-center justify-center bg-canvas text-ink-500 text-xs">
        Initializing 3D WebGL Canvas...
      </div>
    ),
  }
);

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceItem[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [isWorkspaceSettingsOpen, setIsWorkspaceSettingsOpen] = useState(false);

  const fetchWorkspaces = useCallback(async () => {
    try {
      if (!api.getToken()) {
        setWorkspaces([]);
        setActiveWorkspaceId(null);
        return;
      }
      const list = await api.listWorkspaces();
      setWorkspaces(list);
      if (list.length > 0 && !activeWorkspaceId) {
        setActiveWorkspaceId(list[0].id);
      }
    } catch (err) {
      console.error("Error fetching workspaces:", err);
    }
  }, [activeWorkspaceId]);

  // Check initial user authentication
  useEffect(() => {
    const checkAuth = async () => {
      try {
        if (api.getToken()) {
          const u = await api.getMe();
          setUser(u);
          fetchWorkspaces();
        }
      } catch {
        api.logout();
        setUser(null);
      }
    };
    checkAuth();
  }, [fetchWorkspaces]);

  // Fetch document catalog
  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    try {
      const docs = await api.listDocuments(activeWorkspaceId || undefined);
      setDocuments(docs);
    } catch (err) {
      console.error("Error fetching documents:", err);
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspaceId]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

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

  const activeWorkspace = workspaces.find((w) => w.id === activeWorkspaceId) || null;

  return (
    <div className="min-h-screen bg-canvas text-ink-900 flex flex-col font-sans selection:bg-veritas-100 selection:text-veritas-700">
      <Header
        user={user}
        activeTab={activeTab}
        onTabChange={(t) => {
          setSelectedDocId(null);
          setActiveTab(t);
        }}
        onOpenAuth={() => setIsAuthOpen(true)}
        onOpenUpload={() => {
          if (!user) {
            setIsAuthOpen(true);
          } else {
            setIsUploadOpen(true);
          }
        }}
        onLogout={() => {
          api.logout();
          setUser(null);
          setWorkspaces([]);
          setActiveWorkspaceId(null);
        }}
        activeWorkspace={activeWorkspace}
        workspaces={workspaces}
        onSelectWorkspace={(id) => setActiveWorkspaceId(id)}
        onOpenWorkspaceSettings={() => setIsWorkspaceSettingsOpen(true)}
      />

      <main className="flex-1 flex flex-col">
        {activeTab === "dashboard" ? (
          <DashboardView
            user={user}
            documents={documents}
            onNavigateTab={(t) => setActiveTab(t)}
            onOpenUpload={() => setIsUploadOpen(true)}
          />
        ) : activeTab === "chat" ? (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex-1 flex flex-col">
            <ResearchStudioView
              documents={documents}
              onOpenUpload={() => setIsUploadOpen(true)}
            />
          </div>
        ) : activeTab === "graph" ? (
          <UniversalKnowledgeExplorer />
        ) : activeTab === "study" ? (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex-1 flex flex-col">
            <AdaptiveStudySuite documents={documents} initialDocumentId={selectedDocId} />
          </div>
        ) : (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-border">
              <div>
                <h1 className="text-xl font-semibold text-ink-900">Document Hub</h1>
                <p className="text-xs text-ink-500 mt-0.5">
                  Academic papers, preprints, and research dossiers with verified layout decomposition.
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={fetchDocuments}
                  title="Refresh Catalog"
                  className="p-2 rounded-xl text-ink-500 hover:text-ink-900 hover:bg-surface-subtle border border-border transition-colors"
                >
                  <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
                </button>
                <button
                  onClick={() => setIsUploadOpen(true)}
                  className="bg-ink-900 hover:bg-ink-700 text-white text-xs font-medium px-4 py-2 rounded-xl transition-colors shadow-subtle"
                >
                  Upload Research PDF
                </button>
              </div>
            </div>

            <DocumentHubView
              documents={documents}
              isLoading={isLoading}
              onSelectDocument={(doc) => setSelectedDocId(doc.id)}
              onRefresh={fetchDocuments}
              onOpenUpload={() => setIsUploadOpen(true)}
              onViewGraph={(doc) => {
                setSelectedDocId(doc.id);
                setActiveTab("graph");
              }}
            />
          </div>
        )}
      </main>

      {/* Minimalist Linear Footer */}
      <footer className="border-t border-border bg-panel py-5 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-ink-500">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-ink-900">VERITAS</span>
            <span>•</span>
            <span>Research Intelligence. Grounded in Truth.</span>
          </div>
          <div className="font-mono text-[11px] text-ink-400">
            Universal Light Architecture • Three.js Motion Engine • Multi-Tenant Isolation
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

      <WorkspaceSettingsModal
        isOpen={isWorkspaceSettingsOpen}
        onClose={() => setIsWorkspaceSettingsOpen(false)}
        activeWorkspaceId={activeWorkspaceId}
        onSelectWorkspace={(wsId) => setActiveWorkspaceId(wsId)}
        onWorkspacesChanged={fetchWorkspaces}
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
