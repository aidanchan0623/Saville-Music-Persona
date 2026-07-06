/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"],
      },
      colors: {
        ink: "#07070d",
        panel: "#11111d",
        panelSoft: "#171726",
        line: "rgba(255,255,255,0.11)",
        violet: "#8b5cf6",
        indigo: "#6366f1",
        magenta: "#d946ef",
        mist: "#c7c4dc",
      },
      boxShadow: {
        glow: "0 20px 80px rgba(139,92,246,0.18)",
      },
    },
  },
  plugins: [],
};

