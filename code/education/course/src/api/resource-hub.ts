import axios from 'axios';
import type { ResourceRecord } from './resources';

export interface ResourceRecommendationItem {
  id: string;
  origin: 'generated' | 'external';
  title: string;
  type: string;
  subject: string;
  knowledge_point: string;
  difficulty: string;
  source: string;
  source_domain?: string | null;
  url?: string | null;
  reason: string;
  evidence: string[];
  preview: string;
  favorite: boolean;
  status: string;
  generation: number;
  resource?: ResourceRecord | null;
}

export interface RecommendationPreviewResource {
  id: string;
  title: string;
  type: string;
  file_name: string;
  file_size: number;
  content_type: string;
  knowledge_point?: string | null;
  difficulty?: string | null;
  content?: Record<string, unknown> | null;
}

export interface RecommendationPreviewResponse {
  recommendation: ResourceRecommendationItem;
  resource?: RecommendationPreviewResource | null;
  message: string;
}

export interface ResourceRecommendationResponse {
  generated_at: string;
  profile_signals: string[];
  agent_trace: string[];
  items: ResourceRecommendationItem[];
}

export function fetchResourceRecommendations(limit = 8, refresh = false) {
  return axios.get<ResourceRecommendationResponse>('/api/resource-hub/recommendations', {
    params: { limit, refresh },
    timeout: refresh ? 30000 : 12000,
  });
}

export function dismissResourceRecommendation(recommendationId: string) {
  return axios.delete(`/api/resource-hub/recommendations/${recommendationId}`);
}

export function favoriteResourceRecommendation(recommendationId: string, favorite: boolean) {
  return axios.put<ResourceRecommendationItem>(
    `/api/resource-hub/recommendations/${recommendationId}/favorite`,
    { favorite }
  );
}

export interface RecommendationActionResponse {
  recommendation: ResourceRecommendationItem;
  resource_id?: string | null;
  message: string;
}

export function regenerateResourceRecommendation(recommendationId: string) {
  return axios.post<RecommendationActionResponse>(
    `/api/resource-hub/recommendations/${recommendationId}/regenerate`,
    {},
    { timeout: 180000 }
  );
}

export function addRecommendationToLibrary(recommendationId: string) {
  return axios.post<RecommendationActionResponse>(
    `/api/resource-hub/recommendations/${recommendationId}/add-to-library`,
    {},
    { timeout: 180000 }
  );
}

export function previewRecommendation(recommendationId: string) {
  return axios.post<RecommendationPreviewResponse>(
    `/api/resource-hub/recommendations/${recommendationId}/preview`,
    {},
    { timeout: 180000 }
  );
}

export function reportRecommendationSourceOpened(recommendationId: string) {
  return axios.post<ResourceRecommendationItem>(
    `/api/resource-hub/recommendations/${recommendationId}/feedback`,
    { action: 'source_opened' },
    { timeout: 5000 }
  );
}
