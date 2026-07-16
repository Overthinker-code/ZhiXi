import axios from 'axios';

export interface LearningPathNode {
  title: string;
  status: 'pending' | 'in_progress' | 'done';
  order: number;
  topic?: string;
  action?: string;
}

export interface LearningPath {
  user_id: string;
  subject: string;
  summary: string;
  nodes: LearningPathNode[];
  updated_at: string;
}

export function fetchLearningPath() {
  return axios
    .get('/api/learning-path/me')
    .then((res: any) => res.data as LearningPath | null);
}
