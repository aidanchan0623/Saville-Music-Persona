/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"],
        display: ["Archivo Black", "Impact", "Arial Black", "ui-sans-serif", "system-ui"],
      },
      colors: {
        ink: "#050303",
        panel: "#120909",
        panelSoft: "#1b0d0d",
        surface: "#0b0707",
        line: "rgba(255,255,255,0.11)",
        mist: "#bdb3b3",
      },
      boxShadow: {
        glow: "0 24px 90px rgba(239,68,68,0.17)",
      },
    },
  },
  plugins: [],
};
