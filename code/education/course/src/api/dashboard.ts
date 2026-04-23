import axios from 'axios';
import type { TableData } from '@arco-design/web-vue/es/table/interface';

const READ_TIMEOUT_MS = 8000;

export interface ContentDataRecord {
  x: string;
  y: number;
}

export interface DashboardOverview {
  today_login_count: number;
  total_courses: number;
  total_resources: number;
  total_teaching_classes: number;
  active_students: number;
}

export function queryDashboardOverview() {
  return axios.get<DashboardOverview>('/api/v1/dashboard/teacher/stats', {
    timeout: READ_TIMEOUT_MS,
  });
}

export function queryContentData() {
  return axios.get<ContentDataRecord[]>('/api/v1/dashboard/teacher/alerts-trend', {
    timeout: READ_TIMEOUT_MS,
  });
}

export interface PopularRecord {
  key: number;
  title: string;
  click_number: number;
  increases: number;
}

export function queryPopularList(params: { type: string }) {
  return axios.get<PopularRecord[]>('/api/v1/dashboard/teacher/popular', {
    params,
    timeout: READ_TIMEOUT_MS,
  });
}

export interface ContentDistribution {
  total: number;
  items: Array<{
    name: 'resources' | 'courses' | 'homework' | 'discussions';
    value: number;
  }>;
}

export function queryContentDistribution() {
  return axios.get<ContentDistribution>('/api/v1/dashboard/teacher/content-distribution', {
    timeout: READ_TIMEOUT_MS,
  });
}
