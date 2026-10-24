import type { NextConfig } from "next";

// Dashboard demo diekspor sebagai situs statis: data dibaca sekali saat build dari
// public/demo/report.json, jadi Cache Components dan Partial Prefetching tidak dipakai.
// NEXT_PUBLIC_BASE_PATH dipakai bila situs dihosting di subfolder (mis. GitHub Pages).
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  basePath: basePath || undefined,
  images: { unoptimized: true },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
