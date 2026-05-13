/** @type {import('next').NextConfig} */

// ── Load .env from project root ────────────────────────────────────
const fs = require('fs');
const path = require('path');

const rootEnv = path.resolve(__dirname, '..', '.env');
if (fs.existsSync(rootEnv)) {
  const content = fs.readFileSync(rootEnv, 'utf-8');
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    const val = trimmed.slice(eqIdx + 1).trim();
    // Only set if not already set (env vars take precedence)
    if (!process.env[key]) process.env[key] = val;
  }
}

// ── Derive API URL from .env ───────────────────────────────────────
const BACKEND_HOST = process.env.HOST || '0.0.0.0';
const BACKEND_PORT = process.env.PORT || '8000';
const FRONTEND_PORT = process.env.FRONTEND_PORT || '3000';

// NEXT_PUBLIC_* vars are inlined at build time by Next.js.
// For dev, we set them here so next.config.js can use them for rewrites.
const API_URL = process.env.NEXT_PUBLIC_API_URL || `http://localhost:${BACKEND_PORT}`;

// Also set it for client-side code
if (!process.env.NEXT_PUBLIC_API_URL) {
  process.env.NEXT_PUBLIC_API_URL = API_URL;
}

// ── Dev server port ────────────────────────────────────────────────
if (!process.env.PORT) {
  process.env.PORT = FRONTEND_PORT;
}

console.log(`\n  ACS Frontend`);
console.log(`  Backend API: ${API_URL}`);
console.log(`  Frontend:    http://localhost:${FRONTEND_PORT}\n`);

// ── Next.js config ─────────────────────────────────────────────────
const nextConfig = {
  // Rewrite /api/* to the backend
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
