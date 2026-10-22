import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
    return backendUrl
      ? [{ source: "/api/backend/:path*", destination: `${backendUrl}/api/:path*` }]
      : [];
  },
};

export default nextConfig;
