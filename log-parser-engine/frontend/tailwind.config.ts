import type { Config } from "tailwindcss";
import forms from "@tailwindcss/forms";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        panel: "var(--panel)",
        ink: "var(--ink)",
        inkSoft: "var(--ink-soft)",
        accent: "var(--accent)",
        accent2: "var(--accent-2)",
        ok: "var(--ok)",
        warn: "var(--warn)",
        err: "var(--err)"
      },
      boxShadow: {
        panel: "0 12px 40px rgba(0,0,0,0.18)"
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" }
        }
      },
      animation: {
        rise: "rise 320ms ease-out both"
      }
    }
  },
  plugins: [forms]
} satisfies Config;
