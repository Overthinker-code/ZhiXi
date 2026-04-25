import axios from 'axios';

export interface TeacherStats {
  today_login_count: number;
  total_courses: number;
  total_resources: number;
  total_teaching_classes: number;
  active_students: number;
}

export function getTeacherStats(): Promise<TeacherStats> {
  return axios
    .get<TeacherStats>('/api/dashboard/teacher/stats')
    .then((res) => res.data);
}

export interface AlertsTrendItem {
  date: string;
  alert_count: number;
}

export function getTeacherAlertsTrend(days = 7): Promise<AlertsTrendItem[]> {
  return axios
    .get<AlertsTrendItem[]>('/api/dashboard/teacher/alerts-trend', {
      params: { days },
    })
    .then((res) => res.data);
}

export interface PopularItem {
  key: number;
  title: string;
  click_number: number;
  increases: number;
}

export function getTeacherPopular(
  type: 'course' | 'resource'
): Promise<PopularItem[]> {
  return axios
    .get<PopularItem[]>('/api/dashboard/teacher/popular', {
      params: { type },
    })
    .then((res) => res.data);
}

export interface TeacherContentDistribution {
  total: number;
  items: { name: string; value: number }[];
}

export function getTeacherContentDistribution(): Promise<TeacherContentDistribution> {
  return axios
    .get<TeacherContentDistribution>(
      '/api/dashboard/teacher/content-distribution'
    )
    .then((res) => res.data);
}
