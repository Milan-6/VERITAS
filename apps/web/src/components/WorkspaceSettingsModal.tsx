"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Users,
  UserPlus,
  Shield,
  Trash2,
  FolderPlus,
  CheckCircle2,
  AlertCircle,
  Building,
  KeyRound,
  FileText,
  Webhook,
  BookOpen,
  RefreshCw,
  Copy,
  Check,
  ExternalLink,
  Lock,
} from "lucide-react";
import { api } from "../lib/api";
import {
  WorkspaceItem,
  WorkspaceDetail,
  IntegrationStatus,
  WebhookSubscriptionItem,
} from "../types";

interface WorkspaceSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeWorkspaceId: string | null;
  onSelectWorkspace: (workspaceId: string) => void;
  onWorkspacesChanged?: () => void;
}

export const WorkspaceSettingsModal: React.FC<WorkspaceSettingsModalProps> = ({
  isOpen,
  onClose,
  activeWorkspaceId,
  onSelectWorkspace,
  onWorkspacesChanged,
}) => {
  const [activeTab, setActiveTab] = useState<"members" | "integrations">("members");
  const [workspaces, setWorkspaces] = useState<WorkspaceItem[]>([]);
  const [activeDetail, setActiveDetail] = useState<WorkspaceDetail | null>(null);
  const [loading, setLoading] = useState(false);

  // Members state
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"EDITOR" | "VIEWER">("VIEWER");
  const [newWsName, setNewWsName] = useState("");

  // Integrations state (Phase 12)
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [zoteroApiKey, setZoteroApiKey] = useState("");
  const [zoteroUserId, setZoteroUserId] = useState("");
  const [connectingZotero, setConnectingZotero] = useState(false);
  const [syncingZotero, setSyncingZotero] = useState(false);

  // Webhooks state (Phase 12)
  const [webhooks, setWebhooks] = useState<WebhookSubscriptionItem[]>([]);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookDesc, setWebhookDesc] = useState("");
  const [subEvents, setSubEvents] = useState<string[]>([
    "document.ingested",
    "agent.task.completed",
    "dossier.generated",
  ]);
  const [creatingWebhook, setCreatingWebhook] = useState(false);
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);

  // Status feedback
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchIntegrationsAndWebhooks = async (wsId: string) => {
    try {
      const [intStatus, whList] = await Promise.all([
        api.getIntegrationStatus(wsId),
        api.listWebhooks(wsId),
      ]);
      setIntegrations(intStatus);
      setWebhooks(whList);

      const zot = intStatus.find((i) => i.provider === "zotero");
      if (zot && zot.external_user_id) {
        setZoteroUserId(zot.external_user_id);
      }
    } catch (err: any) {
      console.warn("Could not load integrations/webhooks:", err);
    }
  };

  const fetchWorkspaces = async () => {
    try {
      setLoading(true);
      setError(null);
      const list = await api.listWorkspaces();
      setWorkspaces(list);

      const targetId = activeWorkspaceId || (list.length > 0 ? list[0].id : null);
      if (targetId) {
        const detail = await api.getWorkspace(targetId);
        setActiveDetail(detail);
        await fetchIntegrationsAndWebhooks(targetId);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load workspaces");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchWorkspaces();
      setError(null);
      setSuccess(null);
    }
  }, [isOpen, activeWorkspaceId]);

  const handleSelectWorkspaceTab = async (wsId: string) => {
    try {
      setLoading(true);
      setError(null);
      const detail = await api.getWorkspace(wsId);
      setActiveDetail(detail);
      onSelectWorkspace(wsId);
      await fetchIntegrationsAndWebhooks(wsId);
    } catch (err: any) {
      setError(err?.message || "Failed to switch workspace");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWsName.trim()) return;

    try {
      setSubmitting(true);
      setError(null);
      setSuccess(null);
      const newWs = await api.createWorkspace(newWsName.trim());
      setNewWsName("");
      setSuccess(`Workspace "${newWs.name}" created successfully.`);
      await fetchWorkspaces();
      onSelectWorkspace(newWs.id);
      if (onWorkspacesChanged) onWorkspacesChanged();
    } catch (err: any) {
      setError(err?.message || "Failed to create workspace");
    } finally {
      setSubmitting(false);
    }
  };

  const handleInviteMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeDetail || !inviteEmail.trim()) return;

    try {
      setSubmitting(true);
      setError(null);
      setSuccess(null);
      await api.inviteWorkspaceMember(activeDetail.id, inviteEmail.trim(), inviteRole);
      setSuccess(`Collaborator ${inviteEmail} invited as ${inviteRole}.`);
      setInviteEmail("");
      const updated = await api.getWorkspace(activeDetail.id);
      setActiveDetail(updated);
      if (onWorkspacesChanged) onWorkspacesChanged();
    } catch (err: any) {
      setError(err?.message || "Failed to invite collaborator");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemoveMember = async (userId: string, memberEmail: string) => {
    if (!activeDetail) return;
    if (!confirm(`Are you sure you want to remove ${memberEmail} from this workspace?`)) return;

    try {
      setSubmitting(true);
      setError(null);
      setSuccess(null);
      await api.removeWorkspaceMember(activeDetail.id, userId);
      setSuccess(`Member removed from workspace.`);
      const updated = await api.getWorkspace(activeDetail.id);
      setActiveDetail(updated);
      if (onWorkspacesChanged) onWorkspacesChanged();
    } catch (err: any) {
      setError(err?.message || "Failed to remove member");
    } finally {
      setSubmitting(false);
    }
  };

  // Zotero Connect & Sync Handlers
  const handleConnectZotero = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeDetail || !zoteroApiKey.trim() || !zoteroUserId.trim()) return;

    try {
      setConnectingZotero(true);
      setError(null);
      setSuccess(null);
      await api.connectZotero(zoteroApiKey.trim(), zoteroUserId.trim(), activeDetail.id);
      setSuccess("Zotero API key verified and encrypted securely at rest.");
      setZoteroApiKey("");
      await fetchIntegrationsAndWebhooks(activeDetail.id);
    } catch (err: any) {
      setError(err?.message || "Failed to connect Zotero");
    } finally {
      setConnectingZotero(false);
    }
  };

  const handleSyncZotero = async () => {
    if (!activeDetail) return;
    try {
      setSyncingZotero(true);
      setError(null);
      setSuccess(null);
      const res = await api.syncZotero(activeDetail.id, 50);
      setSuccess(
        `Zotero sync complete! Imported ${res.documents_created} new research papers (${res.synced_references} references processed).`
      );
      if (onWorkspacesChanged) onWorkspacesChanged();
    } catch (err: any) {
      setError(err?.message || "Zotero sync failed");
    } finally {
      setSyncingZotero(false);
    }
  };

  // Webhooks Handlers
  const handleCreateWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeDetail || !webhookUrl.trim()) return;

    try {
      setCreatingWebhook(true);
      setError(null);
      setSuccess(null);
      const newWh = await api.createWebhook(
        activeDetail.id,
        webhookUrl.trim(),
        subEvents,
        webhookDesc.trim() || undefined
      );
      setSuccess(`Webhook registered successfully. HMAC secret: ${newWh.secret_key}`);
      setWebhookUrl("");
      setWebhookDesc("");
      await fetchIntegrationsAndWebhooks(activeDetail.id);
    } catch (err: any) {
      setError(err?.message || "Failed to register webhook");
    } finally {
      setCreatingWebhook(false);
    }
  };

  const handleDeleteWebhook = async (webhookId: string) => {
    if (!confirm("Are you sure you want to delete this webhook subscription?")) return;
    try {
      setError(null);
      await api.deleteWebhook(webhookId);
      setSuccess("Webhook subscription deleted.");
      if (activeDetail) await fetchIntegrationsAndWebhooks(activeDetail.id);
    } catch (err: any) {
      setError(err?.message || "Failed to delete webhook");
    }
  };

  const handleCopySecret = (key: string, id: string) => {
    navigator.clipboard.writeText(key);
    setCopiedKeyId(id);
    setTimeout(() => setCopiedKeyId(null), 2000);
  };

  if (!isOpen) return null;

  const isOwner = activeDetail?.role === "OWNER";
  const canManage = activeDetail?.role === "OWNER" || activeDetail?.role === "EDITOR";
  const zoteroConnected = integrations.some((i) => i.provider === "zotero" && i.is_active);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-[#0F172A] border border-slate-800 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-cyan-950/80 border border-cyan-800/60 text-cyan-400">
              <Building className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Workspaces & Advanced Integrations</h2>
              <p className="text-xs text-slate-400">
                Manage team members, Zotero reference sync, and secure HMAC webhooks
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status Alerts */}
        {error && (
          <div className="mx-6 mt-4 p-3 rounded-lg bg-red-950/60 border border-red-800/60 text-red-300 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div className="mx-6 mt-4 p-3 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 text-xs flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{success}</span>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Workspace Selector Tabs */}
          <div>
            <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
              Select Active Workspace
            </label>
            <div className="flex flex-wrap gap-2">
              {workspaces.map((ws) => (
                <button
                  key={ws.id}
                  onClick={() => handleSelectWorkspaceTab(ws.id)}
                  className={`px-3 py-2 rounded-lg text-xs font-medium flex items-center space-x-2 border transition-all ${
                    activeDetail?.id === ws.id
                      ? "bg-cyan-950/80 border-cyan-500/80 text-cyan-300 shadow-sm shadow-cyan-500/10"
                      : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700"
                  }`}
                >
                  <Building className="w-3.5 h-3.5" />
                  <span>{ws.name}</span>
                  <span
                    className={`text-[9px] px-1.5 py-0.2 rounded font-mono uppercase ${
                      ws.role === "OWNER"
                        ? "bg-amber-950/80 text-amber-300 border border-amber-800/60"
                        : ws.role === "EDITOR"
                        ? "bg-blue-950/80 text-blue-300 border border-blue-800/60"
                        : "bg-slate-800 text-slate-300"
                    }`}
                  >
                    {ws.role || "MEMBER"}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Subtabs: Members vs Integrations */}
          <div className="flex border-b border-slate-800 space-x-4">
            <button
              onClick={() => setActiveTab("members")}
              className={`pb-2.5 text-xs font-semibold flex items-center space-x-1.5 border-b-2 transition-colors ${
                activeTab === "members"
                  ? "border-cyan-400 text-cyan-300"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              <span>Team & Members</span>
            </button>
            <button
              onClick={() => setActiveTab("integrations")}
              className={`pb-2.5 text-xs font-semibold flex items-center space-x-1.5 border-b-2 transition-colors ${
                activeTab === "integrations"
                  ? "border-cyan-400 text-cyan-300"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Webhook className="w-3.5 h-3.5" />
              <span>Integrations & Webhooks (Phase 12)</span>
            </button>
          </div>

          {/* TAB 1: MEMBERS */}
          {activeTab === "members" && activeDetail && (
            <div className="space-y-5">
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                  <div>
                    <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
                      <span>{activeDetail.name}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-cyan-950 text-cyan-400 border border-cyan-800">
                        Your Role: {activeDetail.role}
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">slug: {activeDetail.slug}</p>
                  </div>
                  <div className="flex items-center space-x-3 text-xs text-slate-400">
                    <div className="flex items-center space-x-1.5 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
                      <FileText className="w-3.5 h-3.5 text-cyan-400" />
                      <span>{activeDetail.document_count} Documents</span>
                    </div>
                    <div className="flex items-center space-x-1.5 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
                      <Users className="w-3.5 h-3.5 text-blue-400" />
                      <span>{activeDetail.members.length} Members</span>
                    </div>
                  </div>
                </div>

                {/* Member Roster Table */}
                <div className="mt-4">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5 flex items-center space-x-1.5">
                    <Users className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Team Collaborators</span>
                  </h4>
                  <div className="space-y-2">
                    {activeDetail.members.map((member) => (
                      <div
                        key={member.id}
                        className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80 text-xs"
                      >
                        <div className="flex items-center space-x-2.5 min-w-0">
                          <div className="w-7 h-7 rounded-full bg-slate-800 flex items-center justify-center text-slate-300 font-semibold text-xs shrink-0">
                            {member.email.charAt(0).toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <p className="text-slate-200 font-medium truncate">
                              {member.full_name || member.email}
                            </p>
                            <p className="text-[11px] text-slate-400 truncate">{member.email}</p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-3">
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded font-mono font-semibold uppercase ${
                              member.role === "OWNER"
                                ? "bg-amber-950/80 text-amber-300 border border-amber-800/60"
                                : member.role === "EDITOR"
                                ? "bg-blue-950/80 text-blue-300 border border-blue-800/60"
                                : "bg-slate-800 text-slate-400 border border-slate-700"
                            }`}
                          >
                            {member.role}
                          </span>
                          {isOwner && member.role !== "OWNER" && (
                            <button
                              onClick={() => handleRemoveMember(member.user_id, member.email)}
                              title="Remove collaborator"
                              className="p-1 rounded text-slate-500 hover:text-red-400 hover:bg-slate-800 transition-colors"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Invite Member Form */}
                <div className="mt-5 pt-4 border-t border-slate-800">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                    <UserPlus className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Invite Collaborator</span>
                  </h4>
                  {canManage ? (
                    <form onSubmit={handleInviteMember} className="flex flex-col sm:flex-row gap-2">
                      <input
                        type="email"
                        value={inviteEmail}
                        onChange={(e) => setInviteEmail(e.target.value)}
                        placeholder="colleague@institution.edu"
                        required
                        className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                      />
                      <select
                        value={inviteRole}
                        onChange={(e) => setInviteRole(e.target.value as "EDITOR" | "VIEWER")}
                        className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                      >
                        <option value="VIEWER">VIEWER (Read & Search)</option>
                        <option value="EDITOR">EDITOR (Edit & Upload)</option>
                      </select>
                      <button
                        type="submit"
                        disabled={submitting || !inviteEmail.trim()}
                        className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-950 font-semibold text-xs transition-colors shrink-0 flex items-center justify-center space-x-1"
                      >
                        <UserPlus className="w-3.5 h-3.5" />
                        <span>{submitting ? "Inviting..." : "Invite"}</span>
                      </button>
                    </form>
                  ) : (
                    <p className="text-xs text-slate-500 italic">
                      You have VIEWER access in this workspace and cannot invite collaborators.
                    </p>
                  )}
                </div>
              </div>

              {/* Create New Workspace */}
              <div className="bg-slate-900/30 border border-slate-800 rounded-xl p-4">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                  <FolderPlus className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Create New Workspace</span>
                </h4>
                <form onSubmit={handleCreateWorkspace} className="flex gap-2">
                  <input
                    type="text"
                    value={newWsName}
                    onChange={(e) => setNewWsName(e.target.value)}
                    placeholder="e.g. LLM Reasoning Research Group"
                    required
                    className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                  <button
                    type="submit"
                    disabled={submitting || !newWsName.trim()}
                    className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-semibold text-xs transition-colors shrink-0 flex items-center space-x-1"
                  >
                    <FolderPlus className="w-3.5 h-3.5" />
                    <span>{submitting ? "Creating..." : "Create Workspace"}</span>
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* TAB 2: INTEGRATIONS & WEBHOOKS (PHASE 12) */}
          {activeTab === "integrations" && activeDetail && (
            <div className="space-y-6">
              {/* Zotero Reference Manager Card */}
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center space-x-2.5">
                    <div className="w-8 h-8 rounded-lg bg-red-950/80 border border-red-800/60 flex items-center justify-center text-red-400 font-bold text-sm">
                      Z
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-white">Zotero Reference Manager</h4>
                      <p className="text-xs text-slate-400">
                        Sync research collections and academic metadata directly into VERITAS
                      </p>
                    </div>
                  </div>
                  {zoteroConnected ? (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center space-x-1">
                      <Check className="w-3 h-3" />
                      <span>Connected</span>
                    </span>
                  ) : (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                      Not Configured
                    </span>
                  )}
                </div>

                {/* Zotero Credentials Form */}
                <form onSubmit={handleConnectZotero} className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-medium text-slate-400 mb-1">
                        Zotero User ID / Library ID
                      </label>
                      <input
                        type="text"
                        value={zoteroUserId}
                        onChange={(e) => setZoteroUserId(e.target.value)}
                        placeholder="e.g. 1234567"
                        required
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-medium text-slate-400 mb-1 flex items-center justify-between">
                        <span>Zotero API Key</span>
                        <span className="text-[10px] text-slate-500 flex items-center space-x-1">
                          <Lock className="w-2.5 h-2.5" />
                          <span>Fernet Encrypted</span>
                        </span>
                      </label>
                      <input
                        type="password"
                        value={zoteroApiKey}
                        onChange={(e) => setZoteroApiKey(e.target.value)}
                        placeholder="Zotero Private Key (read access)"
                        required
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <button
                      type="submit"
                      disabled={connectingZotero || !zoteroApiKey.trim() || !zoteroUserId.trim()}
                      className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-950 font-semibold text-xs transition-colors flex items-center space-x-1.5"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>{connectingZotero ? "Verifying..." : "Save & Encrypt Credentials"}</span>
                    </button>
                    {zoteroConnected && (
                      <button
                        type="button"
                        onClick={handleSyncZotero}
                        disabled={syncingZotero}
                        className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-500 hover:to-amber-500 disabled:opacity-50 text-white font-semibold text-xs shadow-sm transition-all flex items-center space-x-1.5"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${syncingZotero ? "animate-spin" : ""}`} />
                        <span>{syncingZotero ? "Syncing..." : "Sync Zotero Library Now"}</span>
                      </button>
                    )}
                  </div>
                </form>
              </div>

              {/* Mendeley Connector Stub Card */}
              <div className="bg-slate-900/30 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 rounded-lg bg-red-950/40 border border-red-800/40 flex items-center justify-center text-red-400 font-bold text-sm">
                    M
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-white">Mendeley Reference Manager</h4>
                    <p className="text-xs text-slate-400">OAuth 2.0 academic library connector interface</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => alert("Mendeley OAuth connector interface initialized and ready for production app credentials.")}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs font-medium transition-colors flex items-center space-x-1.5"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Connect Mendeley</span>
                </button>
              </div>

              {/* Webhooks & Automation Card */}
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center space-x-2.5">
                    <div className="p-1.5 rounded-lg bg-cyan-950/80 border border-cyan-800/60 text-cyan-400">
                      <Webhook className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-white">Event Webhooks & Automation</h4>
                      <p className="text-xs text-slate-400">
                        Dispatch real-time JSON payloads with HMAC-SHA256 signatures (SSRF protected)
                      </p>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800">
                    {webhooks.length} Active
                  </span>
                </div>

                {/* Webhooks List */}
                {webhooks.length > 0 && (
                  <div className="space-y-2.5">
                    {webhooks.map((wh) => (
                      <div
                        key={wh.id}
                        className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 text-xs space-y-2"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="font-mono text-cyan-300 text-[11px] truncate max-w-[400px]">
                              {wh.url}
                            </p>
                            {wh.description && (
                              <p className="text-slate-400 text-[11px] mt-0.5">{wh.description}</p>
                            )}
                          </div>
                          <button
                            onClick={() => handleDeleteWebhook(wh.id)}
                            className="p-1 text-slate-500 hover:text-red-400 hover:bg-slate-800 rounded transition-colors"
                            title="Delete webhook"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                          {wh.events_subscribed.map((ev) => (
                            <span
                              key={ev}
                              className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700"
                            >
                              {ev}
                            </span>
                          ))}
                        </div>

                        <div className="flex items-center space-x-2 pt-1 border-t border-slate-900 text-[11px]">
                          <span className="text-slate-500">HMAC Secret:</span>
                          <span className="font-mono text-slate-400 truncate max-w-[200px]">
                            {wh.secret_key}
                          </span>
                          <button
                            onClick={() => handleCopySecret(wh.secret_key, wh.id)}
                            className="text-cyan-400 hover:text-cyan-300 transition-colors flex items-center space-x-1"
                          >
                            {copiedKeyId === wh.id ? (
                              <>
                                <Check className="w-3 h-3 text-emerald-400" />
                                <span className="text-[10px] text-emerald-400">Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" />
                                <span className="text-[10px]">Copy</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Add Webhook Form */}
                <form onSubmit={handleCreateWebhook} className="space-y-3 pt-2">
                  <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Register New Webhook URL
                  </h5>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <input
                      type="url"
                      value={webhookUrl}
                      onChange={(e) => setWebhookUrl(e.target.value)}
                      placeholder="https://your-domain.com/webhook-endpoint"
                      required
                      className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                    />
                    <input
                      type="text"
                      value={webhookDesc}
                      onChange={(e) => setWebhookDesc(e.target.value)}
                      placeholder="Description (e.g. Lab Slack Notifications)"
                      className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  {/* Event Checkboxes */}
                  <div>
                    <label className="block text-[11px] font-medium text-slate-400 mb-1.5">
                      Subscribed Events:
                    </label>
                    <div className="flex flex-wrap gap-3 text-xs text-slate-300">
                      {[
                        { id: "document.ingested", label: "document.ingested" },
                        { id: "agent.task.completed", label: "agent.task.completed" },
                        { id: "dossier.generated", label: "dossier.generated" },
                      ].map((item) => (
                        <label key={item.id} className="flex items-center space-x-1.5 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={subEvents.includes(item.id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSubEvents([...subEvents, item.id]);
                              } else {
                                setSubEvents(subEvents.filter((ev) => ev !== item.id));
                              }
                            }}
                            className="rounded border-slate-700 text-cyan-500 focus:ring-0 bg-slate-950"
                          />
                          <span className="font-mono text-[11px]">{item.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <p className="text-[10px] text-slate-500 italic">
                      Destination URLs are verified against SSRF (private and internal networks are blocked).
                    </p>
                    <button
                      type="submit"
                      disabled={creatingWebhook || !webhookUrl.trim() || subEvents.length === 0}
                      className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-950 font-semibold text-xs transition-colors shrink-0 flex items-center space-x-1"
                    >
                      <Webhook className="w-3.5 h-3.5" />
                      <span>{creatingWebhook ? "Registering..." : "Register Webhook"}</span>
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/40 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
