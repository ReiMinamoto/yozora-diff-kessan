import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./pages/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        add: {
          bg: "#DCFCE7",
          text: "#166534"
        },
        del: {
          bg: "#FEE2E2",
          text: "#991B1B"
        },
        fact: {
          border: "#1D4ED8",
          bg: "#DBEAFE",
          text: "#1E3A8A"
        },
        insight: {
          border: "#F97316",
          bg: "#FFEDD5",
          text: "#C2410C"
        }
      },
      boxShadow: {
        soft: "0 8px 24px rgba(15, 23, 42, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
