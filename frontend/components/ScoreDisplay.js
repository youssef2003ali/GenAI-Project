'use client';

const COLORS = {
  Coherence: 'var(--accent-blue)',
  Relevance: 'var(--accent-purple)',
  Completeness: 'var(--accent-green)',
};

export default function ScoreDisplay({ edit }) {
  if (!edit) return null;

  const items = [
    { label: 'Coherence', value: edit.scores?.coherence, color: COLORS.Coherence },
    { label: 'Relevance', value: edit.scores?.relevance, color: COLORS.Relevance },
    { label: 'Completeness', value: edit.scores?.completeness, color: COLORS.Completeness },
    { label: 'Average', value: edit.average?.toFixed(1), color: 'var(--accent-amber)' },
  ];

  return (
    <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
      <strong>Edit Scores</strong>
      <div className="scores-row">
        {items.map(item => (
          <div className="score-item" key={item.label}>
            <span className="score-value" style={{ color: item.color }}>
              {item.value ?? '-'}
            </span>
            <span className="score-label">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
