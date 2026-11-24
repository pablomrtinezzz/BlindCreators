import type { NextConfig } from "next";

const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  async redirects() {
    return [
      { source: "/retention", destination: "/shorts", permanent: true },
      { source: "/transcripts", destination: "/videos", permanent: true },
      { source: "/comments", destination: "/audience", permanent: true },
      { source: "/rag", destination: "/ask", permanent: true },
      { source: "/ai-tools", destination: "/ideas", permanent: true },
    ];
  },
};

export default nextConfig;
