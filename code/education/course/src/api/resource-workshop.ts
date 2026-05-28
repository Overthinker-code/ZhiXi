import axios from 'axios';

export type ResourceDifficulty = 'auto' | 'foundation' | 'standard' | 'challenge';

export interface ResourcePackageRequest {
  subject: string;
  topic?: string;
  goal?: string;
  difficulty?: ResourceDifficulty;
  minutes?: number;
  resource_count?: number;
}

export interface ResourceItem {
  title: string;
  type:
    | 'lecture_doc'
    | 'mind_map'
    | 'practice_set'
    | 'reading'
    | 'case_project'
    | 'video_script'
    | 'reflection';
  estimated_minutes: number;
  difficulty: Exclude<ResourceDifficulty, 'auto'>;
  description: string;
  mastery_target: string;
  content_preview: string;
}

export interface ResourcePackageResponse {
  package_id: string;
  subject: string;
  topic: string;
  goal: string;
  personalization_basis: string[];
  resources: ResourceItem[];
  next_check: {
    method: string;
    endpoint: string;
    target_mastery_delta: number;
  };
}

export interface ExerciseGradeRequest {
  subject: string;
  topic: string;
  question: string;
  student_answer: string;
  reference_answer?: string;
  max_score?: number;
}

export interface ExerciseGradeResponse {
  topic: string;
  score: number;
  is_correct: boolean;
  mastery_before: number;
  mastery_after: number;
  mastery_delta: number;
  feedback: string;
  strengths: string[];
  gaps: string[];
  follow_up: string[];
  mastery_update: Record<string, unknown>;
}

export interface ImageAnalyzeRequest {
  subject?: string;
  question_text?: string;
  image_url?: string;
  image_base64?: string;
}

export interface ImageAnalyzeResponse {
  source: 'qwen3-vl' | 'fallback';
  status: 'success' | 'fallback';
  subject: string;
  problem_type: string;
  extracted_text: string;
  answer_markdown: string;
  solution_outline: string[];
  answer_hint: string;
  diagram: {
    type?: string;
    content?: string;
  };
  confidence: number;
  limitations: string[];
}

export function generateResourcePackage(payload: ResourcePackageRequest) {
  return axios
    .post('/api/resource-workshop/packages', payload, { timeout: 0 })
    .then((res: any) => res.data as ResourcePackageResponse);
}

export function gradeResourceExercise(payload: ExerciseGradeRequest) {
  return axios
    .post('/api/resource-workshop/exercises/grade', payload, { timeout: 0 })
    .then((res: any) => res.data as ExerciseGradeResponse);
}

export function analyzeImageProblem(payload: ImageAnalyzeRequest) {
  return axios
    .post('/api/resource-workshop/images/analyze', payload, { timeout: 0 })
    .then((res: any) => res.data as ImageAnalyzeResponse);
}
