/**
 * Pipeline State - Single responsibility: manage pipeline execution state.
 * SOLID: Open/Closed - new stages can be added without modifying state logic.
 */
class PipelineState {
  constructor() {
    this.reset();
  }

  /** Define all pipeline stages in order with their display properties. */
  static STAGES = [
    { id: 'research',     label: 'Research',     icon: '🔍', color: 'badge-research' },
    { id: 'planning',     label: 'Planning',     icon: '📋', color: 'badge-planning' },
    { id: 'writing',      label: 'Writing',      icon: '✍️', color: 'badge-writing' },
    { id: 'editing',      label: 'Editing',      icon: '📝', color: 'badge-editing' },
    { id: 'optimization', label: 'Optimization',  icon: '✨', color: 'badge-optimization' },
  ];

  /** Reset state for a new pipeline run. */
  reset() {
    this.jobId = null;
    this.topic = '';
    this.status = 'idle'; // idle | running | completed | failed
    this.currentAgent = null;
    this.stageOutputs = {};
    this.finalOutput = null;
    this.error = null;
    this.stageStatus = {};
    PipelineState.STAGES.forEach(s => { this.stageStatus[s.id] = 'pending'; });
  }

  /** Mark a stage as in progress. */
  setStageActive(stageId) {
    this.currentAgent = stageId;
    this.stageStatus[stageId] = 'active';
  }

  /** Mark a stage as completed with its output. */
  setStageCompleted(stageId, output = '') {
    this.stageStatus[stageId] = 'completed';
    this.stageOutputs[stageId] = output;
  }

  /** Mark a stage as failed. */
  setStageFailed(stageId) {
    this.stageStatus[stageId] = 'failed';
  }

  /** Update from WebSocket status message. */
  applyWsUpdate(data) {
    if (data.current_agent && data.current_agent !== this.currentAgent) {
      // Mark previous stage as completed if transitioning
      if (this.currentAgent) {
        this.setStageCompleted(this.currentAgent);
      }
      this.setStageActive(data.current_agent);
    }
    if (data.status) this.status = data.status;
    if (data.progress?.output) {
      this.stageOutputs[data.current_agent || ''] = data.progress.output;
    }
  }

  /** Complete the pipeline with final data. */
  complete(context, finalOutput) {
    if (this.currentAgent) {
      this.setStageCompleted(this.currentAgent);
    }
    this.status = 'completed';
    this.finalOutput = finalOutput;
    this.context = context;
  }

  /** Fail the pipeline with an error. */
  fail(error) {
    if (this.currentAgent) {
      this.setStageFailed(this.currentAgent);
    }
    this.status = 'failed';
    this.error = error;
  }

  /** Get current stage display info. */
  getCurrentStageInfo() {
    return PipelineState.STAGES.find(s => s.id === this.currentAgent) || null;
  }

  /** Check if a specific stage is completed. */
  isStageComplete(stageId) {
    return this.stageStatus[stageId] === 'completed';
  }
}
