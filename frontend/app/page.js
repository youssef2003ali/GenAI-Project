'use client';

import { useState, useCallback, useRef } from 'react';
import { marked } from 'marked';
import TopicInput from '@/components/TopicInput';
import PipelineVisualizer from '@/components/PipelineVisualizer';
import StagePanel from '@/components/StagePanel';
import ScoreDisplay from '@/components/ScoreDisplay';
import { submitTopic } from '@/lib/api';
import {
  createInitialState, applyChunk, setAgentActive, setAgentDone,
  completeState, failState, STAGES,
} from '@/lib/pipeline-state';

export default function Home() {
  const [state, setState] = useState(createInitialState);
  const [loading, setLoading] = useState(false);
  const wsRef = useRef(null);
  const pingRef = useRef(null);

  // Extract human-readable text from agent JSON outputs
  function extractAgentOutput(agent, output) {
    try {
      const parsed = JSON.parse(output);
      switch (agent) {
        case 'research':
          return parsed.summary || parsed.raw || output;
        case 'planning':
          let ot = `# ${parsed.title || ''}\n\n`;
          (parsed.sections || []).forEach(s => {
            ot += `## ${s.heading}\n`;
            (s.key_points || []).forEach(kp => {
              // Skip raw JSON code blocks, markdown fences
              const clean = kp.replace(/```[\s\S]*?```/g, '').replace(/[{}"]/g, '').trim();
              if (clean) ot += `- ${clean}\n`;
            });
            ot += '\n';
          });
          return ot || output;
        case 'writing':
          return parsed.content || output;
        case 'editing':
          return `**Coherence:** ${parsed.scores?.coherence ?? '-'}/10  
**Relevance:** ${parsed.scores?.relevance ?? '-'}/10  
**Completeness:** ${parsed.scores?.completeness ?? '-'}/10  
**Average:** ${parsed.average?.toFixed(1) ?? '-'}  
**Passed:** ${parsed.passed}${parsed.instructions ? `\n\n**Feedback:** ${parsed.instructions}` : ''}`;
        case 'optimization':
          return parsed.content || output;
        default:
          return output;
      }
    } catch {
      return output; // Not JSON, return as-is
    }
  }

  const cleanup = useCallback(() => {
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
    if (pingRef.current) { clearInterval(pingRef.current); pingRef.current = null; }
  }, []);

  const connectWs = useCallback((jobId) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/${jobId}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case 'chunk':
            setState(prev => applyChunk(prev, data.agent, data.content));
            break;

          case 'agent_start':
            setState(prev => setAgentActive(prev, data.agent));
            break;

          case 'agent_done':
            setState(prev => {
              const clean = extractAgentOutput(data.agent, data.output);
              return setAgentDone(prev, data.agent, clean);
            });
            break;

          case 'pipeline_done':
            cleanup();
            setState(prev => {
              const ctx = data.context || {};
              const finalContent = data.final_output || '';
              // Build clean stage outputs from context (for stages that weren't streamed)
              const outputs = { ...prev.stageOutputs };
              if (ctx.research && !outputs.research) {
                outputs.research = extractAgentOutput('research', JSON.stringify(ctx.research));
              }
              if (ctx.outline && !outputs.planning) {
                outputs.planning = extractAgentOutput('planning', JSON.stringify(ctx.outline));
              }
              if (ctx.draft && !outputs.writing) {
                outputs.writing = extractAgentOutput('writing', JSON.stringify(ctx.draft));
              }
              if (ctx.final && !outputs.optimization) {
                outputs.optimization = extractAgentOutput('optimization', JSON.stringify(ctx.final));
              }
              return completeState({ ...prev, stageOutputs: outputs }, ctx, finalContent);
            });
            setLoading(false);
            break;

          case 'pipeline_error':
            cleanup();
            setState(prev => failState(prev, data.error));
            setLoading(false);
            break;

          case 'pong':
            break; // keepalive
        }
      } catch (e) {
        console.error('WS error:', e);
      }
    };

    ws.onerror = () => {
      setState(prev => failState(prev, 'WebSocket connection failed'));
      setLoading(false);
      cleanup();
    };

    ws.onclose = () => {
      cleanup();
    };

    wsRef.current = ws;

    // Ping every 15s to keep connection alive
    pingRef.current = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 15000);
  }, [cleanup]);

  const handleSubmit = useCallback(async (topic) => {
    cleanup();
    setLoading(true);
    setState({ ...createInitialState(), topic });

    try {
      const { job_id } = await submitTopic(topic);
      setState(prev => ({ ...prev, jobId: job_id }));

      // Connect WebSocket for push-based streaming
      connectWs(job_id);
    } catch (err) {
      setState(prev => failState(prev, err.message));
      setLoading(false);
    }
  }, [cleanup, connectWs]);

  const stageOutput = (id) => {
    return state.stageOutputs[id] || null;
  };

  // Render final output as markdown
  const finalHtml = state.finalOutput
    ? marked.parse(state.finalOutput, { breaks: true, gfm: true })
    : '';

  return (
    <>
      <header className="header">
        <h1>Agentic Content System</h1>
        <span className="status-badge">
          {state.jobId ? `Job: ${state.jobId.slice(0, 8)}...` : 'Ready'}
        </span>
      </header>

      <div className="container">
        <TopicInput onSubmit={handleSubmit} disabled={loading} />

        <PipelineVisualizer stageStatus={state.stageStatus} />

        {state.error && (
          <div className="error-banner visible">{state.error}</div>
        )}

        <div className="output-grid">
          {STAGES.filter(st => st.id !== 'optimization').map(st => (
            <StagePanel
              key={st.id}
              stageId={st.id}
              output={stageOutput(st.id)}
              status={state.stageStatus[st.id]}
            />
          ))}
        </div>

        <StagePanel
          stageId="optimization"
          output={stageOutput('optimization')}
          status={state.stageStatus.optimization}
        />

        {state.status === 'completed' && (
          <div className="card result-section visible">
            <h2 style={{ color: 'var(--accent-green)', marginBottom: '0.5rem' }}>
              {'\u2705'} Final Output
            </h2>
            <div className="result-content markdown-content">
              <div dangerouslySetInnerHTML={{ __html: finalHtml }} />
            </div>
            <ScoreDisplay edit={state.context?.edit} />
          </div>
        )}
      </div>
    </>
  );
}
