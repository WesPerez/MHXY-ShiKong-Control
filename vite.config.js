import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
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
