import type { NextConfig } from "next";

const API_PROXY = process.env.API_PROXY ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_PROXY}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;