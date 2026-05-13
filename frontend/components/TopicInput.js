'use client';

export default function TopicInput({ onSubmit, disabled }) {
  const handleSubmit = (e) => {
    e.preventDefault();
    const topic = e.target.topic.value.trim();
    if (topic) onSubmit(topic);
  };

  return (
    <div className="card">
      <h2 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--text-secondary)' }}>
        Generate Content
      </h2>
      <form onSubmit={handleSubmit} className="input-row">
        <input
          name="topic"
          type="text"
          placeholder="Enter a topic (e.g., Quantum Computing, Climate Change)..."
          disabled={disabled}
          required
        />
        <button type="submit" className="btn btn-primary" disabled={disabled}>
          {disabled ? 'Running...' : 'Generate Content'}
        </button>
      </form>
    </div>
  );
}
