"use client";

import React from "react";
import { User } from "../types";
import { ShieldCheck, LogIn, LogOut, User as UserIcon, Plus } from "lucide-react";

interface HeaderProps {
  user: User | null;
  activeTab: "catalog" | "chat" | "matrix";
  onTabChange: (tab: "catalog" | "chat" | "matrix") => void;
  onOpenAuth: () => void;
  onOpenUpload: () => void;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  user,
  activeTab,
  onTabChange,
  onOpenAuth,
  onOpenUpload,
  onLogout,
}) => {
  return (
    <header className="border-b border-[#1E293B] bg-[#0A0E1A]/80 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand identity */}
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-400/20 to-blue-600/30 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-sm shadow-cyan-500/10">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg tracking-wider text-white">
                  VERITAS
                </span>
                <span className="text-[10px] font-mono tracking-widest bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 px-1.5 py-0.5 rounded uppercase">
                  Phase 5
                </span>
              </div>
              <p className="text-[11px] text-slate-400 tracking-tight font-medium hidden sm:block">
                Research Intelligence. Grounded in Truth.
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center space-x-1 pl-4 border-l border-slate-800">
            <button
              onClick={() => onTabChange("catalog")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                activeTab === "catalog"
                  ? "bg-slate-800 text-cyan-300 font-semibold"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              Document Catalog
            </button>
            <button
              onClick={() => onTabChange("chat")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center space-x-1.5 ${
                activeTab === "chat"
                  ? "bg-cyan-950/80 border border-cyan-800/60 text-cyan-300 font-semibold"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>Grounded AI Assistant</span>
            </button>
            <button
              onClick={() => onTabChange("matrix")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center space-x-1.5 ${
                activeTab === "matrix"
                  ? "bg-cyan-950/80 border border-cyan-800/60 text-cyan-300 font-semibold"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <span>Literature Matrix</span>
            </button>
          </nav>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-3">
          <button
            onClick={onOpenUpload}
            className="flex items-center space-x-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-semibold text-xs sm:text-sm px-3.5 py-2 rounded-lg shadow-sm shadow-cyan-500/20 transition-all active:scale-[0.98]"
          >
            <Plus className="w-4 h-4" />
            <span>Ingest Document</span>
          </button>

          {user ? (
            <div className="flex items-center space-x-2 pl-2 border-l border-slate-800">
              <div className="flex items-center space-x-2 px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300">
                <UserIcon className="w-3.5 h-3.5 text-cyan-400" />
                <span className="max-w-[120px] truncate">{user.full_name || user.email}</span>
              </div>
              <button
                onClick={onLogout}
                title="Log Out"
                className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-900 transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenAuth}
              className="flex items-center space-x-1.5 text-xs text-slate-300 hover:text-white px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 transition-colors"
            >
              <LogIn className="w-3.5 h-3.5 text-cyan-400" />
              <span>Sign In</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
