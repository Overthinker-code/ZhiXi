import axios from 'axios';

export interface MyProjectRecord {
  id: number;
  name: string;
  description: string;
  peopleNumber: number;
  contributors: {
    name: string;
    email: string;
    avatar: string;
  }[];
}
export function queryMyProjectList() {
  return axios.post('/api/user/my-project/list');
}

export interface MyTeamRecord {
  id: number;
  avatar: string;
  name: string;
  peopleNumber: number;
}
export function queryMyTeamList() {
  return axios.post('/api/user/my-team/list');
}

export interface LatestActivity {
  id: number;
  title: string;
  description: string;
  avatar: string;
}
export function queryLatestActivity() {
  return axios.post<LatestActivity[]>('/api/user/latest-activity');
}

export interface BasicInfoModel {
  email: string;
  nickname: string;
  countryRegion: string;
  area: string | string[];
  address: string;
  profile: string;
}

export function saveUserInfo(data: BasicInfoModel) {
  return axios.post('/api/user/save-info', data);
}

export interface EnterpriseCertificationModel {
  accountType: string;
  status: number;
  time: string;
  legalPerson: string;
  certificateType: string;
  authenticationNumber: string;
  enterpriseName: string;
  enterpriseCertificateType: string;
  organizationCode: string;
}

export type CertificationRecord = Array<{
  certificationType: number;
  certificationContent: string;
  status: number;
  time: string;
}>;

export interface UnitCertification {
  enterpriseInfo: EnterpriseCertificationModel;
  record: CertificationRecord;
}

export function queryCertification() {
  return axios.post<UnitCertification>('/api/user/certification');
}

export function userUploadApi(
  data: FormData,
  config: {
    controller: AbortController;
    onUploadProgress?: (progressEvent: any) => void;
  }
) {
  // const controller = new AbortController();
  return axios.post('/api/user/upload', data, config);
}

// ========== 学情分析 API ==========

export interface StudyOverview {
  cloudTime: number;
  discussions: number;
  interactions: number;
  avgScore: number;
  attendance: number;
  alerts: number;
}

export interface StudyAlert {
  id: string;
  course: string;
  reason: string;
  date: string;
  level: 'warning' | 'error';
}

export interface TimeDistributionItem {
  name: string;
  value: number;
}

export interface StudyCalendarEvent {
  id: string;
  title: string;
  dueDate: string;
  type: 'assignment' | 'exam' | 'experiment';
  dueDayjs?: string; // ISO string
}

export function queryStudyOverview() {
  return axios.get<StudyOverview>('/api/v1/user-center/study/summary');
}

export function queryStudyAlerts() {
  return axios.get<StudyAlert[]>('/api/v1/user-center/study/alerts');
}

export function queryTimeDistribution() {
  return axios.get<TimeDistributionItem[]>(
    '/api/v1/user-center/study/time-distribution'
  );
}

export function queryStudyCalendar() {
  return axios.get<StudyCalendarEvent[]>(
    '/api/v1/user-center/study/calendar'
  );
}

