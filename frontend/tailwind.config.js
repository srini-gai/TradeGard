/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          bg: "#0a0e1a",
          surface: "#111827",
          card: "#1a2235",
          border: "#1e2d45",
          accent: "#00d4aa",
          accent2: "#3b82f6",
          bull: "#22c55e",
          bear: "#ef4444",
          warn: "#f59e0b",
          muted: "#64748b",
          text: "#e2e8f0",
          subtext: "#94a3b8",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
        sans: ["DM Sans", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
}
