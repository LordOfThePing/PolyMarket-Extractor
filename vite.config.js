import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { getPlugin } from "./src/services/plugin";

export default defineConfig({
  plugins: [react(), getPlugin()],
  build: {
    outDir: "dist",
  },
});
