'use client';

import { STAGES } from '@/lib/pipeline-state';

export default function PipelineVisualizer({ stageStatus }) {
  return (
    <div className="pipeline-row">
      {STAGES.map((st, i) => {
        const status = stageStatus[st.id] || 'pending';
        const cls = ['stage-box'];
        if (status === 'active') cls.push('active');
        if (status === 'completed') cls.push('completed');
        if (status === 'failed') cls.push('failed');

        const icon = status === 'completed' ? '\u2705' : status === 'active' ? '\u23F3' : status === 'failed' ? '\u274C' : st.icon;

        return (
          <span key={st.id} style={{ display: 'contents' }}>
            <span className={cls.join(' ')}>
              <span className="stage-icon">{icon}</span>
              <span className="stage-label">{st.label}</span>
            </span>
            {i < STAGES.length - 1 && <span className="arrow">\u2192</span>}
          </span>
        );
      })}
    </div>
  );
}
