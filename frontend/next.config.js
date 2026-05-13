/** @type {import('next').NextConfig} */

// Backend API URL — configurable via NEXT_PUBLIC_API_URL env var or defaults to port 8000
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${API_URL}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
