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
  const url = `/api/education/courses/${queryString ? `?${queryString}` : ''}`;

  return axios
    .get(url, { timeout: READ_TIMEOUT_MS })
    .then((res) => res.data as CoursesResponse);
}

export function fetchCourseById(courseId: string) {
  return axios
    .get(`/api/education/courses/${courseId}`, { timeout: READ_TIMEOUT_MS })
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
    .get(`/api/education/tc/?course_id=${courseId}`, { timeout: READ_TIMEOUT_MS })
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
    .get(`/api/education/courses/${courseId}/resources/analysis`, {
      timeout: READ_TIMEOUT_MS,
    })
    .then((res) => res.data as CourseResourceAnalysis)
}

export interface CourseWorkspaceData {
  course: Course;
  teaching_classes: TeachingClass[];
  course_plans: Array<{
    id: string;
    tc_id: string;
    week: number;
    goal: string;
    key_point: string;
    created_at: string;
    updated_at: string;
  }>;
  assignments: Array<{
    id: string;
    course_id: string;
    title: string;
    description: string | null;
    due_date: string;
  }>;
  resources: Array<{
    id: string;
    course_id: string;
    title: string;
    type: string;
    file_name: string;
    file_size: number;
  }>;
  summary: {
    teaching_class_count: number;
    plan_count: number;
    assignment_count: number;
    resource_count: number;
  };
}

export function fetchCourseWorkspace(courseId: string) {
  return axios
    .get(`/api/education/courses/${courseId}/workspace`, {
      timeout: READ_TIMEOUT_MS,
    })
    .then((res) => res.data as CourseWorkspaceData);
}
