import axios from 'axios';

export interface QuizOption {
  key: string;
  text: string;
}

export interface QuizQuestion {
  id: string;
  knowledge_point: string;
  question_type: string;
  content: string;
  options: QuizOption[];
  difficulty: string;
  order: number;
}

export interface QuizResource {
  resource_id: string;
  title: string;
  knowledge_point: string;
  difficulty: string;
  questions: QuizQuestion[];
}

export interface QuizQuestionResult {
  question_id: string;
  selected_answer: string;
  correct_answer: string;
  is_correct: boolean;
  analysis: string;
  knowledge_point: string;
  saved_to_wrong_book: boolean;
}

export interface QuizSubmitResult {
  attempt_id: string;
  total_questions: number;
  correct_count: number;
  score: number;
  wrong_knowledge_points: string[];
  results: QuizQuestionResult[];
  profile_updated: boolean;
  learning_path_updated: boolean;
  recommendation_refresh: boolean;
}

export interface QuizAttemptSummary {
  attempt_id: string;
  resource_id: string;
  total_questions: number;
  correct_count: number;
  score: number;
  wrong_knowledge_points: string[];
  created_time: string;
}

export interface QuizAttemptDetail extends QuizSubmitResult {
  resource_id: string;
  created_time: string;
}

export interface WrongQuestionItem {
  id: string;
  question: QuizQuestion;
  resource_id: string;
  resource_title: string;
  subject: string;
  wrong_count: number;
  mastered: boolean;
  created_time: string;
  updated_time: string;
}

export interface WrongQuestionBook {
  items: WrongQuestionItem[];
  count: number;
}

export interface WrongBookSubmitResult {
  total_questions: number;
  correct_count: number;
  score: number;
  wrong_knowledge_points: string[];
  results: QuizQuestionResult[];
  attempt_ids: string[];
  profile_updated: boolean;
}

export interface WrongBookPracticeRequest {
  subject?: string;
  question_ids?: string[];
  count?: number;
  difficulty?: 'foundation' | 'standard' | 'challenge';
}

export function getQuiz(resourceId: string) {
  return axios.get<QuizResource>(`/api/resource-hub/quizzes/${resourceId}`);
}

export function submitQuiz(resourceId: string, answers: Record<string, string>) {
  return axios.post<QuizSubmitResult>(`/api/resource-hub/quizzes/${resourceId}/submit`, {
    answers,
  });
}

export function getQuizAttempts(resourceId: string) {
  return axios.get<QuizAttemptSummary[]>(`/api/resource-hub/quizzes/${resourceId}/attempts`);
}

export function getQuizAttempt(attemptId: string) {
  return axios.get<QuizAttemptDetail>(`/api/resource-hub/quiz-attempts/${attemptId}`);
}

export function setWrongQuestionFavorite(questionId: string, favorite: boolean) {
  return axios.put<{ question_id: string; favorite: boolean; wrong_count: number }>(
    `/api/resource-hub/wrong-book/${questionId}`,
    { favorite }
  );
}

export function getWrongQuestionBook() {
  return axios.get<WrongQuestionBook>('/api/resource-hub/wrong-book');
}

export function submitWrongQuestionBook(answers: Record<string, string>) {
  return axios.post<WrongBookSubmitResult>('/api/resource-hub/wrong-book/submit', { answers });
}

export function generateWrongQuestionPractice(payload: WrongBookPracticeRequest) {
  return axios.post<QuizResource>('/api/resource-hub/wrong-book/practice', payload);
}
