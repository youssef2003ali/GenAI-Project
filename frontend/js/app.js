/**
 * App Controller - Single responsibility: orchestrate the application.
 * SOLID: Dependency Inversion - depends on abstractions (ApiClient, PipelineState, UIRenderer).
 */
class AppController {
  constructor() {
    this.api = new ApiClient('');
    this.state = new PipelineState();
    this.ui = new UIRenderer();
    this._pollTimer = null;
    this._pollInterval = 1000; // ms
    this._maxPollTime = 120000; // 2 minutes max polling

    this._bindEvents();
  }

  /** Bind DOM events. */
  _bindEvents() {
    const form = document.getElementById('generate-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this._startPipeline();
      });
    }
  }

  /** Start a new pipeline run. */
  async _startPipeline() {
    const input = document.getElementById('topic-input');
    const topic = input?.value.trim();
    if (!topic) return;

    // Reset UI state
    this.state.reset();
    this.state.topic = topic;
    this.ui.setFormEnabled(false);
    this.ui.showError(null);
    this.ui.renderPipeline(this.state);
    this.ui.renderOutputPanels(this.state);

    // Reset all panel bodies to empty
    PipelineState.STAGES.forEach(stage => {
      const body = document.getElementById(`panel-body-${stage.id}`);
      if (body) {
        body.className = 'output-panel-body empty';
        body.innerHTML = 'Awaiting pipeline start...';
      }
    });

    // Hide result section
    const resultSection = document.getElementById('result-section');
    if (resultSection) resultSection.className = 'result-section';

    try {
      // Submit topic
      const { job_id } = await this.api.submitTopic(topic);
      this.state.jobId = job_id;
      this.ui.updateJobId(job_id);

      // Start polling and WebSocket
      this._startPolling(job_id);
      this.api.connectWs(job_id, {
        onStatus: (data) => this._handleWsUpdate(data),
        onComplete: () => this._handleCompletion(),
        onError: (err) => this._handleError(err),
      });
    } catch (err) {
      this._handleError(err);
    }
  }

  /** Poll job status periodically (backup for WebSocket). */
  _startPolling(jobId) {
    const startTime = Date.now();
    this._pollTimer = setInterval(async () => {
      // Stop polling if exceeded max time
      if (Date.now() - startTime > this._maxPollTime) {
        this._stopPolling();
        if (this.state.status === 'running') {
          this._handleError(new Error('Pipeline timed out'));
        }
        return;
      }

      try {
        const status = await this.api.getStatus(jobId);
        if (status.current_agent) {
          this.state.applyWsUpdate(status);
          this.ui.renderPipeline(this.state);
          this.ui.renderOutputPanels(this.state);
        }

        if (status.status === 'completed') {
          this._stopPolling();
          await this._fetchResult(jobId);
        } else if (status.status === 'failed') {
          this._stopPolling();
          this._handleError(new Error(status.error || 'Pipeline failed'));
        }
      } catch (err) {
        // Silently retry on poll errors
      }
    }, this._pollInterval);
  }

  /** Stop polling. */
  _stopPolling() {
    if (this._pollTimer) {
      clearInterval(this._pollTimer);
      this._pollTimer = null;
    }
    this.api.disconnectWs();
  }

  /** Handle WebSocket status update. */
  _handleWsUpdate(data) {
    this.state.applyWsUpdate(data);

    // If the WS sends output for the current stage, update the panel
    if (data.current_agent && data.progress?.output) {
      this.state.stageOutputs[data.current_agent] = data.progress.output;
    }

    this.ui.renderPipeline(this.state);
    this.ui.renderOutputPanels(this.state);
  }

  /** Handle pipeline completion (from WebSocket or polling). */
  async _handleCompletion() {
    this._stopPolling();
    if (this.state.jobId) {
      await this._fetchResult(this.state.jobId);
    }
  }

  /** Fetch and display final results. */
  async _fetchResult(jobId) {
    try {
      const result = await this.api.getResult(jobId);
      const context = result.context || {};

      // Extract outputs from context
      const outputs = {};
      if (context.research) outputs['research'] = context.research.summary || JSON.stringify(context.research);
      if (context.outline) {
        const outline = context.outline;
        let outlineText = `Title: ${outline.title || ''}\n`;
        if (outline.sections) {
          outline.sections.forEach((s, i) => {
            outlineText += `\n${i + 1}. ${s.heading}\n`;
            (s.key_points || []).forEach(kp => { outlineText += `   - ${kp}\n`; });
          });
        }
        outputs['planning'] = outlineText;
      }
      if (context.draft) outputs['writing'] = context.draft.content || JSON.stringify(context.draft);
      if (context.edit) {
        const e = context.edit;
        let editText = `Coherence: ${e.scores?.coherence ?? '-'}/10\nRelevance: ${e.scores?.relevance ?? '-'}/10\nCompleteness: ${e.scores?.completeness ?? '-'}/10\nAverage: ${e.average?.toFixed(1) ?? '-'}\nPassed: ${e.passed}\n`;
        if (e.instructions) editText += `\nFeedback: ${e.instructions}`;
        outputs['editing'] = editText;
      }
      if (context.final) outputs['optimization'] = context.final.content || JSON.stringify(context.final);

      // Mark all stages completed
      PipelineState.STAGES.forEach(s => {
        if (outputs[s.id]) {
          this.state.setStageCompleted(s.id, outputs[s.id]);
        }
      });

      this.state.complete(context, context.final?.content || result.final_output || '');

      this.ui.renderPipeline(this.state);
      this.ui.renderOutputPanels(this.state);
      this.ui.renderFinalResult(this.state);
      this.ui.setFormEnabled(true);
    } catch (err) {
      this._handleError(err);
    }
  }

  /** Handle errors. */
  _handleError(err) {
    this._stopPolling();
    this.state.fail(err.message || 'Unknown error');
    this.ui.renderPipeline(this.state);
    this.ui.renderOutputPanels(this.state);
    this.ui.renderFinalResult(this.state);
    this.ui.showError(err.message || 'An error occurred');
    this.ui.setFormEnabled(true);
  }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.app = new AppController();
});
