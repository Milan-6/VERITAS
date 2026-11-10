/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "var(--color-canvas-bg)",
        glow: {
          cyan: "var(--glow-cyan)",
          magenta: "var(--glow-magenta)",
          green: "var(--glow-green)",
          amber: "var(--glow-amber)",
          purple: "var(--glow-purple)",
        },
      },
      backgroundColor: {
        glass: "var(--glass-bg)",
      },
      borderColor: {
        glass: "var(--glass-border)",
      },
      backdropBlur: {
        glass: "var(--glass-blur)",
      },
      boxShadow: {
        glass: "var(--glass-shadow)",
      },
    },
  },
  plugins: [],
}
