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
