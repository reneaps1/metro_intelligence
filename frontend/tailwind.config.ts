import type { Config } from "tailwindcss";

export default {
  darkMode: ["selector", '[data-theme="dark"]'],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: "var(--brand-primary)",
          "primary-hover": "var(--brand-primary-hover)",
          accent: "var(--brand-accent)",
        },
        surface: {
          app: "var(--bg-app)",
          DEFAULT: "var(--bg-surface)",
          raised: "var(--bg-surface-raised)",
          sidebar: "var(--bg-sidebar)",
        },
        border: {
          DEFAULT: "var(--border-default)",
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          disabled: "var(--text-disabled)",
          "on-brand": "var(--text-on-brand)",
          "on-sidebar": "var(--text-on-sidebar)",
          "on-sidebar-muted": "var(--text-on-sidebar-muted)",
        },
        status: {
          ok: "var(--status-ok)",
          "ok-bg": "var(--status-ok-bg)",
          nok: "var(--status-nok)",
          "nok-bg": "var(--status-nok-bg)",
          warning: "var(--status-warning)",
          "warning-bg": "var(--status-warning-bg)",
          info: "var(--status-info)",
          "info-bg": "var(--status-info-bg)",
          neutral: "var(--status-neutral)",
          "neutral-bg": "var(--status-neutral-bg)",
        },
        chart: {
          1: "var(--chart-1)",
          2: "var(--chart-2)",
          3: "var(--chart-3)",
          4: "var(--chart-4)",
          5: "var(--chart-5)",
          6: "var(--chart-6)",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        xs: "12px",
        sm: "14px",
        base: "16px",
        lg: "18px",
        xl: "24px",
        "2xl": "32px",
      },
      borderRadius: {
        DEFAULT: "6px",
      },
      boxShadow: {
        md: "var(--shadow-md)",
      },
      zIndex: {
        sticky: "10",
        dropdown: "20",
        overlay: "40",
        modal: "50",
        toast: "100",
      },
      spacing: {
        18: "72px",
        66: "264px",
      },
    },
  },
  plugins: [],
} satisfies Config;
