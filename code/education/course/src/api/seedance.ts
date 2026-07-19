import axios from 'axios';

export type SeedanceGenerationType = 'text-to-video' | 'image-to-video' | 'reference-to-video';
export type SeedanceAspectRatio = '16:9' | '4:3' | '1:1' | '3:4' | '9:16' | '21:9' | 'adaptive';
export type SeedanceResolution = '480p' | '720p' | '1080p' | '4k';

export interface SeedanceVideoRequest {
  prompt: string;
  generation_type?: SeedanceGenerationType;
  image_urls?: string[];
  video_urls?: string[];
  audio_urls?: string[];
  duration?: number;
  aspect_ratio?: SeedanceAspectRatio;
  resolution?: SeedanceResolution;
  generate_audio?: boolean;
  watermark?: boolean;
  web_search?: boolean;
  return_last_frame?: boolean;
  seed?: number;
  callback_url?: string;
  model?: string;
}

export interface SeedanceCreateResponse {
  taskId: string;
  credits?: number;
}

export interface SeedanceTaskResponse {
  id: string;
  status: 'queued' | 'generating' | 'completed' | 'failed' | string;
  created_at?: number;
  model?: string;
  billing_status?: string;
  credits?: number;
  failed_reason?: string | null;
  data?: {
    results?: string[];
    video_expires_at?: string;
    last_frame_url?: string | null;
    processing_time?: number;
    failed_reason?: string;
  };
}

export function fetchSeedanceConfig() {
  return axios.get('/seedance/config').then((res) => res.data as {
    configured: boolean;
    api_base: string;
    model: string;
  });
}

export function createSeedanceVideo(payload: SeedanceVideoRequest) {
  return axios
    .post('/seedance/videos/generations', payload)
    .then((res) => res.data as SeedanceCreateResponse);
}

export function fetchSeedanceTask(taskId: string) {
  return axios
    .get(`/seedance/tasks/${encodeURIComponent(taskId)}`)
    .then((res) => res.data as SeedanceTaskResponse);
}
