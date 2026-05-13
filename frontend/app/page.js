'use client';

import { useState, useCallback, useRef } from 'react';
import TopicInput from '@/components/TopicInput';
import PipelineVisualizer from '@/components/PipelineVisualizer';
import StagePanel from '@/components/StagePanel';
import ScoreDisplay from '@/components/ScoreDisplay';
import { submitTopic, getStatus, getResult, connectWs } from '@/lib/api';
import {
  createInitialState, applyWsUpdate, completeState, failState, STAGES,
} from '@/lib/pipeline-state';

export default function Home() {
  const [state, setState] = useState(createInitialState);
  const [loading, setLoading] = useState(false);
  const wsRef = useRef(null);
  const pollRef = useRef(null);

  const cleanup = useCallback(() => {
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  const fetchResult = useCallback(async (jobId) => {
    try {
      const result = await getResult(jobId);
      const ctx = result.context || {};

      // Build stage outputs from context
      const outputs = {};
      if (ctx.research) outputs.research = ctx.research.summary || JSON.stringify(ctx.research);
      if (ctx.outline) {
        let ot = `Title: ${ctx.outline.title || ''}\n`;
        (ctx.outline.sections || []).forEach((s, i) => {
          ot += `\n${i + 1}. ${s.heading}\n`;
          (s.key_points || []).forEach(kp => { ot += `   - ${kp}\n`; });
        });
        outputs.planning = ot;
      }
      if (ctx.draft) outputs.writing = ctx.draft.content || JSON.stringify(ctx.draft);
      if (ctx.edit) {
        const e = ctx.edit;
        let et = `Coherence: ${e.scores?.coherence ?? '-'}/10\nRelevance: ${e.scores?.relevance ?? '-'}/10\nCompleteness: ${e.scores?.completeness ?? '-'}/10\nAverage: ${e.average?.toFixed(1) ?? '-'}\nPassed: ${e.passed}`;
        if (e.instructions) et += `\n\nFeedback: ${e.instructions}`;
        outputs.editing = et;
      }
      if (ctx.final) outputs.optimization = ctx.final.content || JSON.stringify(ctx.final);

      // Set stage outputs before completing
      const withOutputs = { ...state, stageOutputs: { ...state.stageOutputs, ...outputs } };
      setState(completeState(withOutputs, ctx, ctx.final?.content || result.final_output || ''));
    } catch (err) {
      setState(prev => failState(prev, err.message));
    }
  }, [state]);

  const handleSubmit = useCallback(async (topic) => {
    cleanup();
    setLoading(true);
    setState({ ...createInitialState(), topic });

    try {
      const { job_id } = await submitTopic(topic);

      // WebSocket
      wsRef.current = connectWs(job_id, {
        onStatus: (data) => setState(prev => applyWsUpdate(prev, data)),
        onComplete: async () => {
          cleanup();
          await fetchResult(job_id);
          setLoading(false);
        },
        onError: (err) => {
          setState(prev => failState(prev, err.message));
          setLoading(false);
        },
      });

      // Poll as backup
      pollRef.current = setInterval(async () => {
        try {
          const st = await getStatus(job_id);
          setState(prev => applyWsUpdate(prev, st));
          if (st.status === 'completed') {
            clearInterval(pollRef.current);
            await fetchResult(job_id);
            setLoading(false);
          }
          if (st.status === 'failed') {
            clearInterval(pollRef.current);
            setState(prev => failState(prev, st.error || 'Pipeline failed'));
            setLoading(false);
          }
        } catch { /* retry */ }
      }, 2000);
    } catch (err) {
      setState(prev => failState(prev, err.message));
      setLoading(false);
    }
  }, [cleanup, fetchResult]);

  const stageOutput = (id) => {
    // If completed, show stored output; if active, show whatever we have
    return state.stageOutputs[id] || null;
  };

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
            <div className="result-content">
              <pre>{state.finalOutput}</pre>
            </div>
            <ScoreDisplay edit={state.context?.edit} />
          </div>
        )}
      </div>
    </>
  );
}
