'use client';

import { useMemo, useRef, useEffect } from 'react';
import { marked } from 'marked';
import { STAGES } from '@/lib/pipeline-state';

const BADGE_COLORS = {
  research: 'var(--accent-blue)',
  planning: 'var(--accent-purple)',
  writing: 'var(--accent-green)',
  editing: 'var(--accent-amber)',
  optimization: 'var(--accent-red)',
};

export default function StagePanel({ stageId, output, status }) {
  const stage = STAGES.find(s => s.id === stageId);
  const bodyRef = useRef(null);
  if (!stage) return null;

  const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Pending';
  const isActive = status === 'active';
  const isEmpty = !output;

  const html = useMemo(() => {
    if (!output) return '';
    try {
      return marked.parse(output, { breaks: true, gfm: true });
    } catch {
      return output;
    }
  }, [output]);

  // Auto-scroll to bottom on new chunks
  useEffect(() => {
    if (isActive && bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [html, isActive]);

  return (
    <div className="panel" style={stageId === 'optimization' ? { gridColumn: '1 / -1' } : {}}>
      <div className="panel-header">
        <span>
          <span style={{ color: BADGE_COLORS[stageId], marginRight: 8 }}>{stage.icon}</span>
          {stage.label}
        </span>
        <span className="status-badge" style={{ borderColor: BADGE_COLORS[stageId] }}>{label}</span>
      </div>
      <div ref={bodyRef} className={`panel-body ${isEmpty ? 'panel-empty' : ''}`}>
        {isEmpty ? (
          <>
            <span className="spinner" />
            {status !== 'active' && status !== 'completed' && (
              <span style={{ marginLeft: 8 }}>Awaiting pipeline...</span>
            )}
          </>
        ) : (
          <div
            className={`markdown-content ${isActive ? 'streaming-cursor' : ''}`}
            dangerouslySetInnerHTML={{ __html: html }}
          />
        )}
      </div>
    </div>
  );
}
