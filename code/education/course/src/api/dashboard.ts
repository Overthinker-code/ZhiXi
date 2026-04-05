import axios from 'axios';
import type { TableData } from '@arco-design/web-vue/es/table/interface';

const READ_TIMEOUT_MS = 8000;

export interface ContentDataRecord {
  x: string;
  y: number;
}

export interface DashboardOverview {
  total_classes: number;
  total_teachers: number;
  total_resources: number;
}

export function queryDashboardOverview() {
  return axios.get<DashboardOverview>('/dashboard/overview', {
    timeout: READ_TIMEOUT_MS,
  });
}

export function queryContentData() {
  return axios.get<ContentDataRecord[]>('/dashboard/visits-trend', {
    timeout: READ_TIMEOUT_MS,
  });
}

export interface PopularRecord {
  key: number;
  clickNumber: string;
  title: string;
  increases: number;
}

export function queryPopularList(params: { type: string }) {
  return axios.get<TableData[]>('/dashboard/popular', {
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
  return axios.get<ContentDistribution>('/dashboard/content-distribution', {
    timeout: READ_TIMEOUT_MS,
  });
}
