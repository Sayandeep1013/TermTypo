import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        tt: {
          bg:       "#1a1b26",
          surface:  "#24283b",
          overlay:  "#292e42",
          border:   "#2a2b3d",
          text:     "#c0caf5",
          muted:    "#565f89",
          primary:  "#7aa2f7",
          secondary:"#bb9af7",
          accent:   "#7dcfff",
          success:  "#9ece6a",
          warning:  "#e0af68",
          error:    "#f7768e",
        },
      },
      fontFamily: {
        mono: ["var(--font-mono)", "JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "blink": "blink 1.2s step-end infinite",
        "fade-in": "fadeIn 0.4s ease-in",
        "slide-up": "slideUp 0.3s ease-out",
        "typing": "typing 3s steps(30) infinite",
      },
      keyframes: {
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%":       { opacity: "0" },
        },
        fadeIn: {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
