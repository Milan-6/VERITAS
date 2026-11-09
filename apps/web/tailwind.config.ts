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
        background: "#080C14",
        foreground: "#F8FAFC",
        surface: {
          50: "#1A2234",
          100: "#141C2E",
          200: "#0E1424",
          300: "#0A0E1A",
        },
        navy: {
          900: "#060A12",
          800: "#0B1120",
          700: "#0F172A",
          600: "#1E293B",
          500: "#334155",
        },
        veritas: {
          cyan: "#00E5FF",
          cyanDim: "#00B4D8",
          cyanDark: "#0077B6",
          accent: "#38BDF8",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Courier New", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
