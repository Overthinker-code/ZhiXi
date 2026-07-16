import axios from 'axios';

export type ConversationRole = 'user' | 'assistant' | 'system';

export type AgentTaskStatus = 'waiting' | 'running' | 'completed' | 'failed';

export interface AgentTask {
  id: number;
  session_id: string;
  run_id: string;
  task_key: string;
  agent_name: string;
  status: AgentTaskStatus;
  progress: number;
  message: string;
  created_time: string;
  updated_time: string;
}

export interface ConversationMessage {
  id: number;
  session_id: string;
  role: ConversationRole;
  content: string;
  status: string;
  metadata: Record<string, any>;
  timestamp: string;
}

export interface LearningContext {
  session_id: string;
  current_course?: string | null;
  current_knowledge_point?: string | null;
  user_goal?: string | null;
  weak_points: string[];
  generated_resources: any[];
  historical_tasks: any[];
  context_data: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export type LearningContextPatch = Partial<
  Pick<
    LearningContext,
    | 'current_course'
    | 'current_knowledge_point'
    | 'user_goal'
    | 'weak_points'
    | 'generated_resources'
    | 'historical_tasks'
    | 'context_data'
  >
>;

export function fetchSessionMessages(sessionId: string) {
  return axios
    .get(`/api/chat/session/${encodeURIComponent(sessionId)}/messages`)
    .then((response) => response.data as ConversationMessage[]);
}

export function fetchLearningContext(sessionId: string) {
  return axios
    .get(`/api/chat/session/${encodeURIComponent(sessionId)}/context`)
    .then((response) => response.data as LearningContext);
}

export function updateLearningContext(
  sessionId: string,
  patch: LearningContextPatch
) {
  return axios
    .patch(`/api/chat/session/${encodeURIComponent(sessionId)}/context`, patch)
    .then((response) => response.data as LearningContext);
}

export function fetchAgentTasks(sessionId: string) {
  return axios
    .get(`/api/agent/tasks/${encodeURIComponent(sessionId)}`)
    .then((response) => response.data as AgentTask[]);
}
