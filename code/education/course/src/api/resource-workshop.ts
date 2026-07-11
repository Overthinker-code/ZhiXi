import axios from 'axios';

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
