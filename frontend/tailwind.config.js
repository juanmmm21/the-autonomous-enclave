/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        enclave: {
          bg: "#0b0f1a",
          panel: "#131a2b",
          accent: "#5eead4",
          warn: "#f59e0b",
          danger: "#f87171",
        },
      },
      fontFamily: {
        pixel: ["'Press Start 2P'", "monospace"],
      },
    },
  },
  plugins: [],
};
