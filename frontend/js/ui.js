/**
 * UI Renderer - Single responsibility: all DOM manipulation and rendering.
 * SOLID: Dependency Inversion - receives state, doesn't create it.
 */
class UIRenderer {
  constructor() {
    this._cache = {};
  }

  /** Lazily cache DOM references. */
  _el(id) {
    if (!this._cache[id]) this._cache[id] = document.getElementById(id);
    return this._cache[id];
  }

  /** Render the pipeline stage visualization. */
  renderPipeline(state) {
    const container = this._el('pipeline-visual');
    if (!container) return;

    container.innerHTML = PipelineState.STAGES.map((stage, i) => {
      const status = state.stageStatus[stage.id] || 'pending';
      const isActive = status === 'active';
      const isCompleted = status === 'completed';
      const isFailed = status === 'failed';

      const className = [
        'pipeline-stage',
        isActive ? 'active' : '',
        isCompleted ? 'completed' : '',
        isFailed ? 'failed' : '',
      ].filter(Boolean).join(' ');

      const statusIcon = isCompleted ? '✅' : isActive ? '⏳' : isFailed ? '❌' : '';

      const arrow = i < PipelineState.STAGES.length - 1
        ? '<span class="pipeline-arrow">→</span>'
        : '';

      return `
        <div class="${className}">
          <div class="stage-icon">${isCompleted || isFailed ? statusIcon : stage.icon}</div>
          <div class="stage-label">${stage.label}</div>
        </div>
        ${arrow}
      `;
    }).join('');
  }

  /** Render the output panels for each stage. */
  renderOutputPanels(state) {
    PipelineState.STAGES.forEach(stage => {
      const panel = this._el(`panel-${stage.id}`);
      const body = this._el(`panel-body-${stage.id}`);
      const badge = this._el(`badge-${stage.id}`);
      if (!body) return;

      const status = state.stageStatus[stage.id];
      const output = state.stageOutputs[stage.id];

      if (status === 'completed' && output) {
        body.className = 'output-panel-body';
        body.innerHTML = `<pre>${this._escapeHtml(output)}</pre>`;
      } else if (status === 'active') {
        body.className = 'output-panel-body empty';
        body.innerHTML = '<span class="spinner"></span> Generating...';
      } else if (status === 'failed') {
        body.className = 'output-panel-body';
        body.innerHTML = `<span style="color: var(--accent-red)">Failed</span>`;
      } else if (status === 'pending' && state.status === 'running') {
        body.className = 'output-panel-body empty';
        body.innerHTML = 'Waiting...';
      } else {
        body.className = 'output-panel-body empty';
        body.innerHTML = 'Awaiting pipeline start...';
      }

      if (badge) {
        badge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
      }
    });
  }

  /** Render the final result section. */
  renderFinalResult(state) {
    const section = this._el('result-section');
    const content = this._el('result-content');
    if (!section || !content) return;

    if (state.status === 'completed' && state.finalOutput) {
      section.className = 'result-section visible';
      content.innerHTML = `<pre>${this._escapeHtml(state.finalOutput)}</pre>`;

      // Render context scores if available
      if (state.context?.edit) {
        const edit = state.context.edit;
        content.innerHTML += `
          <div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--border)">
            <strong>Edit Scores</strong>
            <div class="scores-row">
              <div class="score-item">
                <span class="score-value" style="color:var(--accent-blue)">${edit.scores?.coherence ?? '-'}</span>
                <span class="score-label">Coherence</span>
              </div>
              <div class="score-item">
                <span class="score-value" style="color:var(--accent-purple)">${edit.scores?.relevance ?? '-'}</span>
                <span class="score-label">Relevance</span>
              </div>
              <div class="score-item">
                <span class="score-value" style="color:var(--accent-green)">${edit.scores?.completeness ?? '-'}</span>
                <span class="score-label">Completeness</span>
              </div>
              <div class="score-item">
                <span class="score-value" style="color:var(--accent-amber)">${edit.average?.toFixed(1) ?? '-'}</span>
                <span class="score-label">Average</span>
              </div>
            </div>
          </div>
        `;
      }
    } else if (state.status === 'failed') {
      section.className = 'result-section visible';
      content.innerHTML = `<span style="color: var(--accent-red)">${this._escapeHtml(state.error || 'Pipeline failed')}</span>`;
    }
  }

  /** Show or hide the error banner. */
  showError(message) {
    const banner = this._el('error-banner');
    if (!banner) return;
    if (message) {
      banner.className = 'error-banner visible';
      banner.textContent = message;
    } else {
      banner.className = 'error-banner';
    }
  }

  /** Update the job ID display. */
  updateJobId(jobId) {
    const el = this._el('job-id-display');
    if (el) el.textContent = `Job: ${jobId}`;
  }

  /** Set form state during pipeline execution. */
  setFormEnabled(enabled) {
    const input = this._el('topic-input');
    const btn = this._el('generate-btn');
    if (input) input.disabled = !enabled;
    if (btn) {
      btn.disabled = !enabled;
      btn.textContent = enabled ? 'Generate Content' : 'Running...';
    }
  }

  /** Escape HTML to prevent XSS. */
  _escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}
