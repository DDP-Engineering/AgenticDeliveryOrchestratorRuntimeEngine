/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
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
