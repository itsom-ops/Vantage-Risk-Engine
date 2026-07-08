/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Core palette — warm cream + UBS red accent + charcoal
        navy: {
          950: "#F0EEE6", // main app background (warm cream)
          900: "#F7F5F0", // card background (slightly lighter cream)
          800: "#EBE7DD", // subtle contrast / hover cream
          700: "#DDD9CE", // warm light gray border/divider
          600: "#C8C3B5",
        },
        electric: {
          50:  "#fdf2f2",
          100: "#fde8e8",
          200: "#fbd5d5",
          300: "#f8b4b4",
          400: "#f98080",
          500: "#E60000", // UBS red primary action
          600: "#CC0000",
          700: "#B30000",
        },
        cyan: {
          glow: "#E60000",
          mid:  "#C8C3B5",
          dark: "#1C1C1C",
        },
        // Risk tier colors (distinct semantic palette)
        risk: {
          low:      "#15803d", // deep forest green
          medium:   "#b45309", // muted amber/ochre
          high:     "#E60000", // UBS red
          critical: "#991b1b", // deep crimson red
        },
        // Editorial Card border & bg
        glass: {
          border: "#DDD9CE",
          bg:     "#F7F5F0",
        },
      },
      fontFamily: {
        serif: ["Source Serif 4", "Lora", "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      backgroundImage: {
        "grid-pattern": "none",
        "hero-gradient": "none",
        "card-gradient": "none",
        "glow-blue": "none",
      },
      backgroundSize: {
        "grid-sm": "30px 30px",
      },
      boxShadow: {
        "glow-sm":   "0 1px 3px rgba(28, 28, 28, 0.05)",
        "glow-md":   "0 4px 12px rgba(28, 28, 28, 0.06)",
        "glow-lg":   "0 8px 24px rgba(28, 28, 28, 0.08)",
        "card":      "0 2px 12px rgba(28, 28, 28, 0.05), 0 1px 2px rgba(28, 28, 28, 0.03)",
        "card-hover":"0 8px 24px rgba(28, 28, 28, 0.09), 0 2px 6px rgba(28, 28, 28, 0.04)",
      },
      animation: {
        "pulse-slow":  "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "glow-pulse":  "glowPulse 2s ease-in-out infinite",
        "typewriter":  "typewriter 0.05s steps(1) infinite",
        "float":       "float 6s ease-in-out infinite",
      },
      keyframes: {
        glowPulse: {
          "0%, 100%": { opacity: "0.6" },
          "50%":      { opacity: "1" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%":      { transform: "translateY(-8px)" },
        },
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};
