import axios from 'axios';

export type ResourceKind =
  | 'lecture_markdown'
  | 'lecture_pdf'
  | 'practice_markdown'
  | 'practice_pdf'
  | 'mind_map'
  | 'reading_list'
  | 'case_project'
  | 'video_script';

export interface ResourceGenerationRequest {
  course_id?: string;
  subject: string;
  topic: string;
  learning_goal?: string;
  difficulty: 'foundation' | 'standard' | 'challenge';
  target_minutes: number;
  resource_types: ResourceKind[];
  use_web_search?: boolean;
}

export interface GeneratedResourceArtifact {
  kind: ResourceKind;
  title: string;
  file_name: string;
  file_path: string;
  download_url: string;
  content_type: string;
  file_size: number;
  preview: string;
}

export interface ResourceGenerationResponse {
  package_id: string;
  subject: string;
  topic: string;
  generated_at: string;
  local_model_profile: Record<string, any>;
  agent_trace: string[];
  quality_notes: string[];
  artifacts: GeneratedResourceArtifact[];
}

export function generateResourcePackage(payload: ResourceGenerationRequest) {
  return axios
    .post<ResourceGenerationResponse>('/api/resource-generation/packages', payload, {
      timeout: 0,
    })
    .then((res: any) => res.data);
}
