"use client";

import React, { useState, useRef, useEffect } from "react";
import { User, WorkspaceItem } from "../types";
import {
  Compass,
  FileText,
  MessageSquare,
  Network,
  GraduationCap,
  Sparkles,
  Upload,
  User as UserIcon,
  LogOut,
  ChevronDown,
  Building,
  Plus,
} from "lucide-react";

export type NavTab = "dashboard" | "catalog" | "chat" | "graph" | "study";

interface HeaderProps {
  user: User | null;
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  onOpenAuth: () => void;
  onOpenUpload: () => void;
  onLogout: () => void;
  activeWorkspace?: WorkspaceItem | null;
  workspaces?: WorkspaceItem[];
  onSelectWorkspace?: (wsId: string) => void;
  onOpenWorkspaceSettings?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  user,
  activeTab,
  onTabChange,
  onOpenAuth,
  onOpenUpload,
  onLogout,
  activeWorkspace,
  workspaces = [],
  onSelectWorkspace,
  onOpenWorkspaceSettings,
}) => {
  const [isWorkspaceMenuOpen, setIsWorkspaceMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsWorkspaceMenuOpen(false);
        setIsUserMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: Compass },
    { id: "catalog", label: "Document Hub", icon: FileText },
    { id: "chat", label: "Research Studio", icon: MessageSquare },
    { id: "graph", label: "Knowledge Explorer", icon: Network },
    { id: "study", label: "Study Suite", icon: GraduationCap },
  ];

  return (
    <header className="sticky top-0 z-40 bg-panel border-b border-border shadow-subtle">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        
        {/* Left: Brand Identity & Workspace Selector */}
        <div className="flex items-center space-x-4 shrink-0">
          <div className="flex items-center space-x-2.5 cursor-pointer" onClick={() => onTabChange("dashboard")}>
            <div className="w-8 h-8 rounded-lg bg-veritas-50 border border-veritas-100 flex items-center justify-center text-veritas-600 shadow-subtle">
              <Sparkles className="w-4 h-4 text-veritas-600" />
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="font-semibold text-sm tracking-tight text-ink-900 font-sans">
                  VERITAS
                </span>
                <span className="text-[10px] font-mono tracking-wider bg-surface-subtle text-ink-500 border border-border px-1.5 py-0.2 rounded font-medium">
                  Research AI
                </span>
              </div>
            </div>
          </div>

          {/* Workspace Pill / Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setIsWorkspaceMenuOpen(!isWorkspaceMenuOpen)}
              className="hidden md:flex items-center space-x-2 px-2.5 py-1.5 rounded-lg border border-border hover:bg-surface-subtle text-xs text-ink-700 transition-colors"
            >
              <Building className="w-3.5 h-3.5 text-ink-500" />
              <span className="font-medium max-w-[130px] truncate">
                {activeWorkspace ? activeWorkspace.name : "Personal Workspace"}
              </span>
              <ChevronDown className="w-3 h-3 text-ink-400" />
            </button>

            {isWorkspaceMenuOpen && (
              <div className="absolute left-0 mt-1.5 w-60 rounded-xl bg-panel border border-border shadow-floating py-1.5 z-50 text-xs">
                <div className="px-3 py-1.5 text-[10px] font-semibold text-ink-400 uppercase tracking-wider">
                  Active Workspaces
                </div>
                {workspaces.map((ws) => (
                  <button
                    key={ws.id}
                    onClick={() => {
                      onSelectWorkspace?.(ws.id);
                      setIsWorkspaceMenuOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-surface-subtle transition-colors ${
                      activeWorkspace?.id === ws.id ? "font-semibold text-veritas-600 bg-veritas-50" : "text-ink-700"
                    }`}
                  >
                    <span className="truncate">{ws.name}</span>
                    <span className="text-[10px] text-ink-400">{ws.role}</span>
                  </button>
                ))}
                <div className="border-t border-border mt-1 pt-1">
                  <button
                    onClick={() => {
                      onOpenWorkspaceSettings?.();
                      setIsWorkspaceMenuOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 text-ink-700 hover:bg-surface-subtle flex items-center space-x-2"
                  >
                    <Plus className="w-3.5 h-3.5 text-ink-500" />
                    <span>Workspace Settings & Members</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Center: Linear-style Segmented Navigation */}
        <nav className="hidden lg:flex items-center space-x-1 bg-surface-subtle p-1 rounded-xl border border-border">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id as NavTab)}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? "bg-panel text-ink-900 shadow-subtle border border-border"
                    : "text-ink-500 hover:text-ink-900 hover:bg-surface-hover border border-transparent"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? "text-veritas-600" : "text-ink-400"}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Right: Actions & User Avatar */}
        <div className="flex items-center space-x-2.5 shrink-0">
          {/* Upload Button */}
          <button
            onClick={onOpenUpload}
            className="flex items-center space-x-1.5 bg-ink-900 hover:bg-ink-700 text-white px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shadow-subtle"
          >
            <Upload className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Add Document</span>
          </button>

          {/* User Profile / Auth State */}
          {user ? (
            <div className="relative">
              <button
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                className="flex items-center space-x-2 p-1 rounded-lg hover:bg-surface-subtle border border-transparent hover:border-border transition-colors"
              >
                <div className="w-7 h-7 rounded-full bg-veritas-100 text-veritas-700 font-semibold text-xs flex items-center justify-center">
                  {user.full_name ? user.full_name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
                </div>
                <ChevronDown className="w-3 h-3 text-ink-400 hidden sm:block" />
              </button>

              {isUserMenuOpen && (
                <div className="absolute right-0 mt-1.5 w-52 rounded-xl bg-panel border border-border shadow-floating py-1.5 z-50 text-xs">
                  <div className="px-3 py-2 border-b border-border">
                    <p className="font-semibold text-ink-900 truncate">{user.full_name || "Researcher"}</p>
                    <p className="text-[11px] text-ink-500 truncate">{user.email}</p>
                  </div>
                  <button
                    onClick={() => {
                      onLogout();
                      setIsUserMenuOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 text-red-600 hover:bg-red-50 flex items-center space-x-2 transition-colors"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={onOpenAuth}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-ink-700 hover:text-ink-900 border border-border hover:bg-surface-subtle transition-colors"
            >
              <UserIcon className="w-3.5 h-3.5 text-ink-500" />
              <span>Sign In</span>
            </button>
          )}
        </div>
      </div>

      {/* Mobile Navigation Bar */}
      <div className="lg:hidden border-t border-border px-4 py-2 flex items-center justify-around bg-surface-subtle overflow-x-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id as NavTab)}
              className={`flex flex-col items-center py-1 px-2 text-[10px] font-medium transition-colors ${
                isActive ? "text-veritas-600 font-semibold" : "text-ink-500"
              }`}
            >
              <Icon className="w-4 h-4 mb-0.5" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </header>
  );
};
