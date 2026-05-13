'use client';

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
  if (!stage) return null;

  const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Pending';

  return (
    <div className="panel" style={stageId === 'optimization' ? { gridColumn: '1 / -1' } : {}}>
      <div className="panel-header">
        <span>
          <span style={{ color: BADGE_COLORS[stageId], marginRight: 8 }}>{stage.icon}</span>
          {stage.label}
        </span>
        <span className="status-badge" style={{ borderColor: BADGE_COLORS[stageId] }}>{label}</span>
      </div>
      <div className={`panel-body ${!output ? 'panel-empty' : ''}`}>
        {output ? <pre>{output}</pre> : <span className="spinner" />}
        {!output && status !== 'active' && status !== 'completed' && (
          <span style={{ marginLeft: 8 }}>Awaiting pipeline...</span>
        )}
      </div>
    </div>
  );
}
