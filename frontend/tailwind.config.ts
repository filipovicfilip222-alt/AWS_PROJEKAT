import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: { DEFAULT: "1rem", sm: "1.5rem", lg: "2rem" },
      screens: { "2xl": "1280px" },
    },
    extend: {
      fontFamily: {
        sans: [
          "Geist",
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        serif: [
          "Fraunces",
          "Source Serif Pro",
          "Georgia",
          "Times New Roman",
          "serif",
        ],
        display: [
          "Fraunces",
          "Source Serif Pro",
          "Georgia",
          "Times New Roman",
          "serif",
        ],
      },
      fontSize: {
        display: ["2.25rem", { lineHeight: "2.75rem", letterSpacing: "-0.02em" }],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
          muted: "hsl(var(--accent-muted))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        info: {
          DEFAULT: "hsl(var(--info))",
          foreground: "hsl(var(--info-foreground))",
        },
        aiBubble: {
          DEFAULT: "hsl(var(--ai-bubble-bg))",
          foreground: "hsl(var(--ai-bubble-fg))",
          border: "hsl(var(--ai-bubble-border))",
        },
        userBubble: {
          DEFAULT: "hsl(var(--user-bubble-bg))",
          foreground: "hsl(var(--user-bubble-fg))",
          border: "hsl(var(--user-bubble-border))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 4px)",
        sm: "calc(var(--radius) - 8px)",
        xl: "calc(var(--radius) + 4px)",
        "2xl": "calc(var(--radius) + 8px)",
      },
      boxShadow: {
        card: "0 1px 2px 0 hsl(220 13% 12% / 0.04), 0 1px 3px 0 hsl(220 13% 12% / 0.04)",
        "card-hover":
          "0 4px 14px -2px hsl(220 13% 12% / 0.08), 0 2px 6px -1px hsl(220 13% 12% / 0.05)",
        elevated:
          "0 10px 30px -10px hsl(220 13% 12% / 0.18), 0 4px 12px -4px hsl(220 13% 12% / 0.08)",
      },
    },
  },
  plugins: [animate],
};

export default config;
