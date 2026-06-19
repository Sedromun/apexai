import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Lean production runtime: .next/standalone + server.js (no node_modules in the image).
  output: "standalone",
};

export default nextConfig;
