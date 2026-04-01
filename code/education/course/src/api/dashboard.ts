import axios from 'axios';
import type { TableData } from '@arco-design/web-vue/es/table/interface';

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
  return axios.get<DashboardOverview>('/dashboard/overview');
}

export function queryContentData() {
  return axios.get<ContentDataRecord[]>('/dashboard/visits-trend');
}

export interface PopularRecord {
  key: number;
  clickNumber: string;
  title: string;
  increases: number;
}

export function queryPopularList(params: { type: string }) {
  return axios.get<TableData[]>('/dashboard/popular', { params });
}

export interface ContentDistribution {
  total: number;
  items: Array<{
    name: 'resources' | 'courses' | 'homework' | 'discussions';
    value: number;
  }>;
}

export function queryContentDistribution() {
  return axios.get<ContentDistribution>('/dashboard/content-distribution');
}

export interface DashboardOverview {
  onlineContent: number;
  putIn: number;
  newDay: number;
  growthRate: number;
}

export function queryDashboardOverview() {
  return axios.get<DashboardOverview>('/api/dashboard/overview');
}

export interface CategoryItem {
  name: string;
  value: number;
}

export interface DashboardCategories {
  total: number;
  categories: CategoryItem[];
}

export function queryDashboardCategories() {
  return axios.get<DashboardCategories>('/api/dashboard/categories');
}
