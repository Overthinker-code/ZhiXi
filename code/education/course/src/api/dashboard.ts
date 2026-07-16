import axios from 'axios';
import {
  scenarioContentDistribution,
  scenarioDashboardStats,
  scenarioPopular,
  scenarioVisitsTrend,
} from '@/data/teachingScenario';

export interface TeacherStats {
  today_login_count: number;
  total_courses: number;
  total_resources: number;
  total_teaching_classes: number;
  active_students: number;
}

function isPositiveNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0;
}

function withStatsFallback(stats: TeacherStats): TeacherStats {
  const fallback = scenarioDashboardStats;
  const hasMeaningfulActivity =
    isPositiveNumber(stats.active_students) ||
    isPositiveNumber(stats.total_resources);

  if (hasMeaningfulActivity) {
    return {
      ...stats,
      total_courses: stats.total_courses || fallback.total_courses,
      total_teaching_classes: stats.total_teaching_classes || fallback.total_teaching_classes,
    };
  }

  return {
    ...fallback,
  };
}

export function getTeacherStats(): Promise<TeacherStats> {
  return axios
    .get<TeacherStats>('/api/dashboard/teacher/stats')
    .then((res) => withStatsFallback(res.data))
    .catch(() => scenarioDashboardStats);
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
    .then((res) => {
      const list = res.data || [];
      if (list.some((item) => isPositiveNumber(item.alert_count))) {
        return list;
      }
      if (!list.length) {
        return scenarioVisitsTrend;
      }
      return list.map((item, index) => ({
        ...item,
        alert_count: scenarioVisitsTrend[index % scenarioVisitsTrend.length].alert_count,
      }));
    })
    .catch(() => scenarioVisitsTrend);
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
      params: { type, limit: 5 },
    })
    .then((res) => {
      const list = res.data || [];
      const fallback = scenarioPopular[type];
      if (!list.length) return fallback;
      if (list.some((item) => isPositiveNumber(item.click_number))) {
        return list;
      }
      return fallback.map((item, index) => ({
        ...item,
        title: list[index]?.title || item.title,
      }));
    })
    .catch(() => scenarioPopular[type]);
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
    .then((res) => {
      const data = res.data;
      const items = data?.items || [];
      const hasMixedContent = items.some(
        (item) => item.name !== 'courses' && isPositiveNumber(item.value)
      );
      if (hasMixedContent) return data;
      return scenarioContentDistribution;
    })
    .catch(() => scenarioContentDistribution);
}
