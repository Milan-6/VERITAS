import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VERITAS — Research Intelligence. Grounded in Truth.",
  description: "Enterprise Research Intelligence and Literature Synthesis platform with deterministic evidence provenance.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#080C14] text-[#F8FAFC] antialiased min-h-screen selection:bg-cyan-500/20 selection:text-cyan-300">
        {children}
      </body>
    </html>
  );
}
