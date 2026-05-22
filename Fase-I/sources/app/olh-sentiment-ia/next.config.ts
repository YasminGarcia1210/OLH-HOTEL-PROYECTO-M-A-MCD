import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Genera un build mínimo (.next/standalone) listo para `node server.js`.
  // Imprescindible para el Dockerfile de Azure Container Apps.
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
