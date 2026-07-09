import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
  plugins: [
    {
      name: "tauri-local-assets",
      apply: "build",
      enforce: "post",
      transformIndexHtml(html) {
        return html.replace(/\s+crossorigin(?=[\s/>])/g, "");
      },
    },
  ],
});
