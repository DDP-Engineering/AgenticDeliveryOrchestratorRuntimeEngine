import { defineConfig } from "vite";

export default defineConfig({
  base: "/",
  build: {
    outDir: "../adore/web/static",
    emptyOutDir: true,
    // Include full license texts for the React/GFM dependency graph in every build.
    license: { fileName: "BUNDLED_LICENSES.json" },
  },
  server: {
    proxy: { "/api": "http://127.0.0.1:8765" },
  },
});
