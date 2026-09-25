import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["women-attachment-ringtones-outer.trycloudflare.com", "localhost:3000"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8001/api/:path*", // Proxy to Backend
      },
    ];
  },
};

export default nextConfig;
