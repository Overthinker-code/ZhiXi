import axios from 'axios';

const READ_TIMEOUT_MS = 10000;

export interface DigitalHumanJobResponse {
  task_id: string;
  status: 'pending';
  message: string;
}

export interface DigitalHumanJobStatus {
  status: 'pending' | 'processing' | 'success' | 'failed';
  progress: number;
  message: string;
  stage: string;
  video_url?: string;
  script_url?: string;
  render_engine?: string;
  gesture_timeline?: Array<{
    time: number;
    gesture_id: string;
    label?: string;
    segment_index?: number;
  }>;
}

export interface TextToVideoPayload {
  text: string;
  title?: string;
  voice_id?: string;
  digital_human_id?: string;
}

export interface DigitalHumanAsset {
  id: string;
  label: string;
  default_voice: string;
  source_image_exists?: boolean;
  cutout_image_exists?: boolean;
  idle_video_exists?: boolean;
}

export interface DigitalHumanWork {
  id: string;
  title: string;
  description: string;
  type: 'text' | 'ppt';
  duration?: string;
  file_size: number;
  created_at: string;
  video_url: string;
  script_url?: string | null;
  digital_human_id: string;
  digital_human_name: string;
}

export function createTextToVideoJob(payload: TextToVideoPayload) {
  return axios
    .post('/api/digital-human/jobs/text-to-video', payload, {
      timeout: READ_TIMEOUT_MS,
    })
    .then((res: any) => res.data as DigitalHumanJobResponse);
}

export function createPptToVideoJob(payload: {
  file: File;
  title?: string;
  voice_id?: string;
  digital_human_id?: string;
}) {
  const formData = new FormData();
  formData.append('file', payload.file);
  if (payload.title) {
    formData.append('title', payload.title);
  }
  if (payload.voice_id) {
    formData.append('voice_id', payload.voice_id);
  }
  if (payload.digital_human_id) {
    formData.append('digital_human_id', payload.digital_human_id);
  }
  return axios
    .post('/api/digital-human/jobs/ppt-to-video', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 0,
    })
    .then((res: any) => res.data as DigitalHumanJobResponse);
}

export function queryDigitalHumanJobStatus(taskId: string) {
  return axios
    .get(`/api/digital-human/jobs/${taskId}`, { timeout: READ_TIMEOUT_MS })
    .then((res: any) => res.data as DigitalHumanJobStatus);
}

export function fetchDigitalHumanAssets() {
  return axios
    .get('/api/digital-human/assets', { timeout: READ_TIMEOUT_MS })
    .then((res: any) => res.data as { assets: DigitalHumanAsset[]; gestures: any[] });
}

export function fetchDigitalHumanWorks() {
  return axios
    .get('/api/digital-human/works', { timeout: READ_TIMEOUT_MS })
    .then((res: any) => res.data as { works: DigitalHumanWork[] });
}
