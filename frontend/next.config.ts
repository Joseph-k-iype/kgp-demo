import type { NextConfig } from "next";
const config: NextConfig = {
  devIndicators: false,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://127.0.0.1:58123/:path*" },
    ];
  },
};
export default config;
