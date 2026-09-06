import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
    return backendUrl
      ? [{ source: "/api/backend/:path*", destination: `${backendUrl}/api/:path*` }]
      : [];
  },
};

export default nextConfig;
