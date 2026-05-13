/**
 * API Client - Single responsibility: all HTTP + WebSocket communication.
 * SOLID: Interface Segregation - focused methods for each operation.
 */
class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.ws = null;
    this._handlers = {};
  }

  /**
   * Submit a topic for content generation.
   * @param {string} topic
   * @returns {Promise<{job_id: string, status: string}>}
   */
  async submitTopic(topic) {
    const res = await fetch(`${this.baseUrl}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic }),
    });
    if (!res.ok) throw new Error(`Submit failed: ${res.status}`);
    return res.json();
  }

  /**
   * Poll job status.
   * @param {string} jobId
   * @returns {Promise<{status: string, current_agent: string|null, progress: object}>}
   */
  async getStatus(jobId) {
    const res = await fetch(`${this.baseUrl}/status/${jobId}`);
    if (!res.ok) throw new Error(`Status failed: ${res.status}`);
    return res.json();
  }

  /**
   * Get final job result.
   * @param {string} jobId
   * @returns {Promise<{status: string, final_output: string|null, context: object|null}>}
   */
  async getResult(jobId) {
    const res = await fetch(`${this.baseUrl}/result/${jobId}`);
    if (!res.ok) throw new Error(`Result failed: ${res.status}`);
    return res.json();
  }

  /**
   * Connect to WebSocket for real-time job updates.
   * @param {string} jobId
   * @param {object} handlers - { onStatus, onComplete, onError }
   */
  connectWs(jobId, handlers = {}) {
    this._handlers = handlers;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}${this.baseUrl}/ws/${jobId}`;

    this.ws = new WebSocket(wsUrl);
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (handlers.onStatus) handlers.onStatus(data);

        if (data.status === 'completed' && handlers.onComplete) {
          handlers.onComplete(data);
        }
        if (data.status === 'failed' && handlers.onError) {
          handlers.onError(new Error(data.error || 'Pipeline failed'));
        }
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };
    this.ws.onerror = () => {
      if (handlers.onError) handlers.onError(new Error('WebSocket connection failed'));
    };
  }

  /** Close WebSocket connection. */
  disconnectWs() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
