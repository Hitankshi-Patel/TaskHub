import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        // Apply to all pages
        source: "/(.*)",
        headers: [
          {
            // Required for Firebase signInWithPopup to communicate back to the opener window.
            // Vercel sets this to 'same-origin' by default which blocks the Google auth popup.
            key: "Cross-Origin-Opener-Policy",
            value: "same-origin-allow-popups",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
