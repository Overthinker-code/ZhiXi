import axios from 'axios';

export interface CurrentLearningTask {
  id: number;
  title: string;
  goal: string;
  deadline?: string | null;
  current_stage: string;
  progress: number;
  status: string;
  session_id?: string | null;
  created_at: string;
  updated_at: string;
}

export function fetchCurrentLearningTask() {
  return axios
    .get('/api/learning/current-task')
    .then((response) => response.data as CurrentLearningTask | null);
}

export function updateCurrentLearningTask(payload: {
  title?: string;
  goal?: string;
  deadline?: string | null;
}) {
  return axios
    .patch('/api/learning/current-task', payload)
    .then((response) => response.data as CurrentLearningTask);
}
