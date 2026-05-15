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

/**
 * Connect to the push-based WebSocket for pipeline progress.
 *
 * The backend sends JSON messages with a ``type`` field:
 *
 * - ``chunk``        → ``{ type, agent, content }``
 * - ``agent_start``  → ``{ type, agent }``
 * - ``agent_done``   → ``{ type, agent, output }``
 * - ``pipeline_done``→ ``{ type, final_output, context }``
 * - ``pipeline_error``→ ``{ type, error }``
 * - ``pong``         → keepalive reply
 */
export function connectWs(jobId, handlers) {
  const ws = new WebSocket(`${WS_BASE}/ws/${jobId}`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case 'chunk':
          handlers.onChunk?.(data.agent, data.content);
          break;
        case 'agent_start':
          handlers.onAgentStart?.(data.agent);
          break;
        case 'agent_done':
          handlers.onAgentDone?.(data.agent, data.output);
          break;
        case 'pipeline_done':
          handlers.onComplete?.(data.final_output, data.context);
          break;
        case 'pipeline_error':
          handlers.onError?.(new Error(data.error || 'Pipeline failed'));
          break;
        // pong: ignore (keepalive)
      }
    } catch (e) {
      console.error('WS parse error:', e);
    }
  };

  ws.onerror = () => handlers.onError?.(new Error('WebSocket connection failed'));
  return ws;
}
