import axios from 'axios';

/** 列表/详情等读接口：后端不可达时尽快失败并走前端兜底，避免卡满默认 30s */
const READ_TIMEOUT_MS = 8000;

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

  return axios
    .get(url, { timeout: READ_TIMEOUT_MS })
    .then((res) => res.data as CoursesResponse);
}

export function fetchCourseById(courseId: string) {
  return axios
    .get(`/education/courses/${courseId}`, { timeout: READ_TIMEOUT_MS })
    .then((res) => res.data as Course);
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
    .get(`/education/tc?course_id=${courseId}`, { timeout: READ_TIMEOUT_MS })
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
    .get(`/education/courses/${courseId}/resources/analysis`, {
      timeout: READ_TIMEOUT_MS,
    })
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
