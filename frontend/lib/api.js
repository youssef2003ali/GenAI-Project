/**
 * API Client — handles all HTTP + WebSocket communication with the FastAPI backend.
 * SOLID: Single responsibility — network layer only.
 */
const BASE = '/api';

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
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${window.location.host}/api/ws/${jobId}`);

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
