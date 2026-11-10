import React, { ReactNode } from "react";

interface LayoutProps {
  children?: ReactNode;
  overlayPanel?: ReactNode;
  headerBar?: ReactNode;
}

/**
 * Base Viewport-Locked Layout Component
 * Enforces strict 100vw x 100vh constraints with overflow:hidden
 * providing the host container for the WebGL force-directed canvas
 * and glassmorphism UI overlays.
 */
export const Layout: React.FC<LayoutProps> = ({
  children,
  overlayPanel,
  headerBar,
}) => {
  return (
    <div className="relative w-screen h-screen overflow-hidden bg-[var(--color-canvas-bg)] select-none">
      {/* Background Starfield / Ambience Glow Gradients */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute -top-[25%] -left-[10%] w-[60vw] h-[60vw] rounded-full bg-cyan-500/5 blur-[140px]" />
        <div className="absolute -bottom-[20%] -right-[10%] w-[50vw] h-[50vw] rounded-full bg-purple-600/5 blur-[160px]" />
        <div className="absolute top-[40%] right-[20%] w-[35vw] h-[35vw] rounded-full bg-pink-500/5 blur-[120px]" />
      </div>

      {/* Full-Bleed WebGL Canvas Container */}
      <main className="absolute inset-0 w-full h-full z-0">
        {children}
      </main>

      {/* Floating Glassmorphic Header Controls (Optional Slot) */}
      {headerBar && (
        <header className="absolute top-4 left-4 right-4 z-20 pointer-events-auto">
          {headerBar}
        </header>
      )}

      {/* Floating Glassmorphic Inspector Panel (Optional Slot) */}
      {overlayPanel && (
        <aside className="absolute top-20 right-4 bottom-4 w-96 max-w-[calc(100vw-2rem)] z-20 pointer-events-auto">
          {overlayPanel}
        </aside>
      )}
    </div>
  );
};
