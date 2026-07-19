import axios from 'axios';

export interface ProfileBasicRes {
  status: number;
  video: {
    mode: string;
    acquisition: {
      resolution: string;
      frameRate: number;
    };
    encoding: {
      resolution: string;
      rate: {
        min: number;
        max: number;
        default: number;
      };
      frameRate: number;
      profile: string;
    };
  };
  audio: {
    mode: string;
    acquisition: {
      channels: number;
    };
    encoding: {
      channels: number;
      rate: number;
      profile: string;
    };
  };
}

export function queryProfileBasic() {
  return axios.get<ProfileBasicRes>('/api/profile/basic');
}

export type operationLogRes = Array<{
  key: string;
  contentNumber: string;
  updateContent: string;
  status: number;
  updateTime: string;
}>;

export function queryOperationLog() {
  return axios.get<operationLogRes>('/api/operation/log');
}

export interface DynamicStudentProfile {
  school?: string;
  major?: string;
  grade?: string;
  learning_goal?: string;
  current_goal?: string;
  knowledge_state?: Record<string, number>;
  mastery_map?: Record<string, number>;
  learning_preference?: Record<string, number>;
  learning_style?: string;
  cognitive_style?: string;
  learning_behavior?: Record<string, number | string>;
  weak_points?: string[];
  profile_version?: number;
  last_analysis?: Record<string, any>;
}

export interface ProfileUpdateResult {
  status: string;
  analysis: Record<string, any>;
  profile: DynamicStudentProfile;
  update_event_id?: number | null;
}

export interface DigitalTwinDimension {
  key: string;
  label: string;
  score: number;
}

export interface DigitalTwinKnowledgeGraph {
  nodes: Array<{ id: string; name: string; mastery: number }>;
  edges: Array<{ source: string; target: string }>;
}

export interface LearnerDigitalTwin {
  id: string;
  user_id: string;
  learning_stage: string;
  learning_goal: string;
  learning_style: string;
  strengths: string[];
  weaknesses: string[];
  knowledge_state: Record<string, number>;
  learning_behavior: Record<string, any>;
  learning_preference: Record<string, number>;
  cognitive_style: string;
  knowledge_graph: DigitalTwinKnowledgeGraph;
  dimensions: DigitalTwinDimension[];
  overall_score: number;
  ai_summary: string;
  last_updates: string[];
  profile_version: number;
  updated_time: string;
  agent_links: Record<string, string>;
}

export function fetchLearnerDigitalTwin() {
  return axios
    .get('/api/profile/digital-twin')
    .then((response) => response.data as LearnerDigitalTwin);
}

export function fetchDynamicStudentProfile() {
  return axios
    .get('/api/profile/me')
    .then((response) => response.data as DynamicStudentProfile);
}

export function analyzeChatProfile(payload: {
  session_id: string;
  user_message: string;
  assistant_message?: string;
}) {
  return axios
    .post('/api/profile/analyze', payload)
    .then((response) => response.data as ProfileUpdateResult);
}

export function updateProfileSignals(payload: Record<string, any>) {
  return axios
    .post('/api/profile/update', payload)
    .then((response) => response.data as ProfileUpdateResult);
}
