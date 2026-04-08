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
  onlineContent?: number;
  putIn?: number;
  newDay?: number;
  growthRate?: number;
}

export function queryDashboardOverview() {
  return axios.get<DashboardOverview>('/api/v1/dashboard/overview');
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

// ========== Classroom Monitor API ==========

export interface ClassroomStudent {
  id: string;
  name: string;
  studentId: string;
  status: 'present' | 'late' | 'absent' | 'leave';
  checkInTime?: string;
}

export function queryClassroomAttendance(classroomId = 'default') {
  return axios.get<ClassroomStudent[]>(`/api/v1/classroom/attendance/${classroomId}`);
}

export interface StreamInfo {
  url: string;
  bitrate: string;
  fps: number;
  cdn: string;
}

export function queryStreamInfo(classroomId = 'default') {
  return axios.get<StreamInfo>(`/api/v1/classroom/stream-info/${classroomId}`);
}

export interface YoloDetection {
  id: number;
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
  confidence: number;
}

export function queryYoloDetections(classroomId = 'default') {
  return axios.get<YoloDetection[]>(`/api/v1/classroom/yolo-detections/${classroomId}`);
}

export function toggleClassroomDetection(classroomId = 'default', enabled: boolean) {
  return axios.post(`/api/v1/classroom/toggle-detection/${classroomId}`, { enabled });
}

