import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        brand: {
          primary: "#0F7B3F",
          dark: "#0A5C2F",
          positive: "#16A34A",
          danger: "#DC2626",
          surface: "#FFFFFF",
          muted: "#64748B",
          border: "#E2E8F0",
          bg: "#F8FAFC",
        },
      },
      letterSpacing: {
        tightest: "-0.035em",
      },
      boxShadow: {
        card: "0 1px 2px 0 rgba(15, 23, 42, 0.04), 0 1px 3px 0 rgba(15, 23, 42, 0.06)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
