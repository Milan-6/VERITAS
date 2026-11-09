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
} from "lucide-react";
import { api } from "../lib/api";
import { WorkspaceItem, WorkspaceDetail } from "../types";

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
  const [workspaces, setWorkspaces] = useState<WorkspaceItem[]>([]);
  const [activeDetail, setActiveDetail] = useState<WorkspaceDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"EDITOR" | "VIEWER">("VIEWER");
  const [newWsName, setNewWsName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
      // Refresh active detail
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

  if (!isOpen) return null;

  const isOwner = activeDetail?.role === "OWNER";
  const canInvite = activeDetail?.role === "OWNER" || activeDetail?.role === "EDITOR";

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
              <h2 className="text-base font-semibold text-white">Workspaces & Collaboration</h2>
              <p className="text-xs text-slate-400">Manage multi-user research workspaces, team members, and RBAC permissions</p>
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
          {/* Workspace Tabs */}
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

          {/* Active Workspace Info Card */}
          {activeDetail && (
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
                {canInvite ? (
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
          )}

          {/* Create New Workspace Section */}
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
