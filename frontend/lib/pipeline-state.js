/**
 * PipelineState — immutable state management for pipeline execution.
 * SOLID: Single responsibility — state transitions only.
 */
export const STAGES = [
  { id: 'research',     label: 'Research',     icon: '\uD83D\uDD0D' },
  { id: 'planning',     label: 'Planning',     icon: '\uD83D\uDCCB' },
  { id: 'writing',      label: 'Writing',      icon: '\u270D\uFE0F' },
  { id: 'editing',      label: 'Editing',      icon: '\uD83D\uDCDD' },
  { id: 'optimization', label: 'Optimization',  icon: '\u2728' },
];

function freshStatus() {
  const s = {};
  STAGES.forEach(st => { s[st.id] = 'pending'; });
  return s;
}

export function createInitialState() {
  return {
    jobId: null,
    topic: '',
    status: 'idle',
    currentAgent: null,
    stageStatus: freshStatus(),
    stageOutputs: {},
    finalOutput: null,
    context: null,
    error: null,
  };
}

export function applyWsUpdate(state, data) {
  const next = { ...state, stageStatus: { ...state.stageStatus }, stageOutputs: { ...state.stageOutputs } };

  if (data.current_agent && data.current_agent !== next.currentAgent) {
    if (next.currentAgent) next.stageStatus[next.currentAgent] = 'completed';
    next.currentAgent = data.current_agent;
    next.stageStatus[data.current_agent] = 'active';
  }
  if (data.status) next.status = data.status;
  if (data.stage_output != null) {
    next.stageOutputs[data.current_agent || ''] = data.stage_output;
  } else if (data.progress?.output) {
    next.stageOutputs[data.current_agent || ''] = data.progress.output;
  }
  return next;
}

export function applyChunk(state, agent, chunk) {
  /** Append a streaming chunk to an agent's stage output. */
  const next = { ...state, stageOutputs: { ...state.stageOutputs } };
  const prev = next.stageOutputs[agent] || '';
  next.stageOutputs[agent] = prev + chunk;
  return next;
}

export function setAgentActive(state, agent) {
  const next = { ...state, stageStatus: { ...state.stageStatus } };
  if (next.currentAgent) next.stageStatus[next.currentAgent] = 'completed';
  next.currentAgent = agent;
  next.stageStatus[agent] = 'active';
  return next;
}

export function setAgentDone(state, agent, output) {
  const next = { ...state, stageStatus: { ...state.stageStatus }, stageOutputs: { ...state.stageOutputs } };
  next.stageStatus[agent] = 'completed';
  if (output) next.stageOutputs[agent] = output;
  return next;
}

export function completeState(state, context, finalOutput) {
  const next = { ...state, stageStatus: { ...state.stageStatus } };
  if (next.currentAgent) next.stageStatus[next.currentAgent] = 'completed';
  next.status = 'completed';
  next.finalOutput = finalOutput;
  next.context = context;
  return next;
}

export function failState(state, error) {
  const next = { ...state, stageStatus: { ...state.stageStatus } };
  if (next.currentAgent) next.stageStatus[next.currentAgent] = 'failed';
  next.status = 'failed';
  next.error = error;
  return next;
}
