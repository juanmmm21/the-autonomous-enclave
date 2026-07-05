/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        enclave: {
          // Surfaces (from deepest to most elevated)
          bg: "#0a0e14",
          inset: "#0a0f18",
          panel: "#0f1521",
          // Hairlines / borders
          edge: {
            DEFAULT: "#1e2938",
            bright: "#2e3d55",
          },
          // Text ("ink") scale
          ink: {
            DEFAULT: "#dce5f0",
            mid: "#8fa0b6",
            dim: "#5c6b82",
          },
          // Status accents: alive / warning / danger
          accent: "#2dd4bf",
          warn: "#fbbf24",
          danger: "#f87171",
        },
      },
      fontFamily: {
        sans: [
          '"JetBrains Mono"',
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
        mono: [
          '"JetBrains Mono"',
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        // Subtle top inner highlight + soft drop: gives panels real depth on a dark bg.
        panel:
          "inset 0 1px 0 0 rgb(255 255 255 / 0.04), 0 12px 32px -16px rgb(0 0 0 / 0.7)",
        glow: "0 0 8px 0 rgb(45 212 191 / 0.6)",
        "glow-warn": "0 0 8px 0 rgb(251 191 36 / 0.5)",
        "glow-danger": "0 0 8px 0 rgb(248 113 113 / 0.5)",
      },
    },
  },
  plugins: [],
};
