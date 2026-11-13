/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
  build: {
    // The recharts chunk alone is ~550 kB minified (library size, not app code);
    // app chunks stay far below this limit.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // IQ-F8: the charting library changes less often than app code; a
        // separate chunk keeps it cached across deploys.
        manualChunks: { recharts: ["recharts"] },
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
