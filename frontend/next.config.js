/** @type {import('next').NextConfig} */
const nextConfig = {
  // Backend API runs on port 8000, frontend on 3000
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
