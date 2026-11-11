import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Universal Light Theme Foundations
        canvas: "#F4F5F7",
        panel: "#FFFFFF",
        surface: {
          DEFAULT: "#FFFFFF",
          subtle: "#F8F9FA",
          muted: "#F1F3F5",
          border: "#E2E5EA",
          hover: "#EFF1F4",
        },
        border: {
          DEFAULT: "#E2E5EA",
          subtle: "#ECEEF2",
          strong: "#CBD5E1",
        },
        ink: {
          900: "#171A21",
          700: "#334155",
          500: "#687080",
          400: "#94A3B8",
          300: "#CBD5E1",
        },
        // Restrained Academic / Gold Brand Accents
        veritas: {
          50: "#F0F6FF",
          100: "#E0EDFE",
          500: "#2563EB",
          600: "#1D4ED8",
          700: "#1E40AF",
          gold: "#D97706",
          goldLight: "#FEF3C7",
          emerald: "#059669",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Courier New", "monospace"],
      },
      boxShadow: {
        subtle: "0 1px 2px 0 rgba(0, 0, 0, 0.04)",
        card: "0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)",
        floating: "0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04)",
        goldGlow: "0 0 20px -3px rgba(217, 119, 6, 0.25)",
      },
    },
  },
  plugins: [],
};
export default config;
