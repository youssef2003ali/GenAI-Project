/**
 * API Client — handles all HTTP + WebSocket communication with the FastAPI backend.
 * SOLID: Single responsibility — network layer only.
 *
 * The API URL can be configured via NEXT_PUBLIC_API_URL env var.
 * - In dev: http://localhost:8000 (or set NEXT_PUBLIC_API_URL=http://host:port)
 * - In production: the Next.js rewrite in next.config.js proxies /api/*
 * - WebSocket: derived from the API URL automatically
 */

function getBaseUrl() {
  // In production, /api/* is rewritten by Next.js — use relative path
  if (typeof window !== 'undefined' && !process.env.NEXT_PUBLIC_API_URL) {
    return '/api';
  }
  return process.env.NEXT_PUBLIC_API_URL || '/api';
}

function getWsUrl() {
  if (process.env.NEXT_PUBLIC_API_URL) {
    // Direct connection to backend
    const api = process.env.NEXT_PUBLIC_API_URL.replace(/^http/, 'ws');
    return api;
  }
  // Via Next.js rewrite
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/api`;
}

const BASE = getBaseUrl();
const WS_BASE = typeof window !== 'undefined' ? getWsUrl() : '';

export async function submitTopic(topic) {
  const res = await fetch(`${BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic }),
  });
  if (!res.ok) throw new Error(`Submit failed (${res.status})`);
  return res.json();
}

export async function getStatus(jobId) {
  const res = await fetch(`${BASE}/status/${jobId}`);
  if (!res.ok) throw new Error(`Status failed (${res.status})`);
  return res.json();
}

export async function getResult(jobId) {
  const res = await fetch(`${BASE}/result/${jobId}`);
  if (!res.ok) throw new Error(`Result failed (${res.status})`);
  return res.json();
}

export function connectWs(jobId, handlers) {
  const ws = new WebSocket(`${WS_BASE}/ws/${jobId}`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handlers.onStatus?.(data);
      if (data.status === 'completed') handlers.onComplete?.(data);
      if (data.status === 'failed') handlers.onError?.(new Error(data.error || 'Pipeline failed'));
    } catch (e) {
      console.error('WS error:', e);
    }
  };

  ws.onerror = () => handlers.onError?.(new Error('WebSocket connection failed'));
  return ws;
}
