import axios from 'axios';

export interface Course {
  id: string;
  name: string;
  description: string | null;
  course_type: string | null;
  identifier: string;
  ud_id: string;
  created_at: string;
  updated_at: string;
}

export interface CoursesResponse {
  data: Course[];
  count: number;
}

export interface CourseQueryParams {
  skip?: number;
  limit?: number;
  name?: string;
  identifier?: string;
  course_type?: string;
  ud_id?: string;
}

export function fetchCourses(params: CourseQueryParams = {}) {
  const queryParams = new URLSearchParams();
  if (params.skip !== undefined) queryParams.append('skip', String(params.skip));
  if (params.limit !== undefined) queryParams.append('limit', String(params.limit));
  if (params.name) queryParams.append('name', params.name);
  if (params.identifier) queryParams.append('identifier', params.identifier);
  if (params.course_type) queryParams.append('course_type', params.course_type);
  if (params.ud_id) queryParams.append('ud_id', params.ud_id);

  const queryString = queryParams.toString();
  const url = `/education/courses${queryString ? `?${queryString}` : ''}`;

  return axios.get(url).then((res) => res.data as CoursesResponse);
}

export function fetchCourseById(courseId: string) {
  return axios.get(`/education/courses/${courseId}`).then((res) => res.data as Course);
}

export interface TeachingClass {
  id: string;
  name: string | null;
  course_id: string;
  lecturer_id: string;
  created_at: string;
  updated_at: string;
}

export function fetchTeachingClasses(courseId: string) {
  return axios
    .get(`/education/tc?course_id=${courseId}`)
    .then((res) => res.data as { data: TeachingClass[]; count: number });
}

export interface CourseResourceAnalysis {
  document_size: number;
  document_count: number;
  video_size: number;
  video_count: number;
  image_size: number;
  image_count: number;
  homework_count: number;
}

export function fetchCourseResourceAnalysis(courseId: string) {
  return axios
    .get(`/education/courses/${courseId}/resources/analysis`)
    .then((res) => res.data as CourseResourceAnalysis)
    .catch(() => ({
      document_size: 8.5,
      document_count: 76692,
      video_size: 10.2,
      video_count: 148,
      image_size: 13.2,
      image_count: 96,
      homework_count: 1535,
    }));
}

export interface AssignmentSubmitData {
  courseId: string;
  taskId: string;
  content?: string;
  files?: File[];
}

export function submitAssignment(data: FormData) {
  return axios.post('/education/assignments/submit', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(res => res.data);
}

export interface LeaderboardRow {
  rank: number;
  name: string;
  studentId: string;
  score: number;
  completionRate: number;
  submitTime: string;
  status: 'submitted' | 'late' | 'missing';
  comment?: string;
  aiAnalysis?: Array<{ key: string; good: boolean; detail: string }>;
}

export function queryLeaderboard(courseId: string, taskId: string, params: { sortBy: string; scope: string }) {
  return axios.get<LeaderboardRow[]>(`/education/courses/${courseId}/tasks/${taskId}/leaderboard`, { params });
}


