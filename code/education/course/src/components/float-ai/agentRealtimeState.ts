export type AgentProcessStatus = 'running' | 'done' | 'cancelled' | 'error';

export interface AgentProcessStep {
  key: string;
  title: string;
  detail: string;
  status: AgentProcessStatus;
}

export interface AgentWindowMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  loading: boolean;
  interrupted: boolean;
  currentStage: string;
  processOpen: boolean;
  process: AgentProcessStep[];
  suggestions: string[];
}

export const AGENT_CONTINUE_PROMPT =
  '请从刚才停止的位置继续完成，并避免重复已经生成的内容。';

export interface AgentStreamToken {
  sessionToken: string;
  requestId: number;
}

export function isAgentStreamTokenCurrent(
  activeSessionToken: string,
  activeRequestId: number,
  token: AgentStreamToken
) {
  return (
    Boolean(activeSessionToken) &&
    activeSessionToken === token.sessionToken &&
    activeRequestId === token.requestId
  );
}

export function agentProcessStatusFromPhase(status: unknown): AgentProcessStatus {
  const normalized = String(status || 'done').toLowerCase();
  if (normalized === 'cancelled') return 'cancelled';
  if (normalized === 'error' || normalized === 'failed') return 'error';
  if (normalized === 'running' || normalized === 'started') return 'running';
  return 'done';
}

export function markAgentMessageInterrupted(message: AgentWindowMessage) {
  message.loading = false;
  message.interrupted = true;
  message.currentStage = '已中断显示';
  // Do not turn unfinished backend phases into fake successes.
  message.process.forEach((step) => {
    if (step.status === 'running') step.status = 'cancelled';
  });
  return message;
}
