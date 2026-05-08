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
          primary: "#0A3D2A",
          dark: "#062818",
          positive: "#1F8A5B",
          danger: "#D73838",
          surface: "#FFFFFF",
          "surface-soft": "#FAFAFA",
          muted: "#707070",
          border: "#ECECEC",
          "border-strong": "#DCDCDC",
          bg: "#FAFAF9",
          paper: "#FBFAF6",
          ink: "#14140F",
          soft: "#4A4A44",
          red: "#B32424",
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
