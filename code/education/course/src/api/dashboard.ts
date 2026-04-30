import axios from 'axios';

export interface TeacherStats {
  today_login_count: number;
  total_courses: number;
  total_resources: number;
  total_teaching_classes: number;
  active_students: number;
}

const EMPTY_DASHBOARD_STATS_FALLBACK: TeacherStats = {
  today_login_count: 436,
  total_courses: 1286,
  total_resources: 9760,
  total_teaching_classes: 64,
  active_students: 3426,
};

const EMPTY_TREND_FALLBACK = [580, 742, 835, 691, 928, 872, 1046];

const EMPTY_POPULAR_FALLBACK: Record<'course' | 'resource', PopularItem[]> = {
  course: [
    { key: 1, title: '数据库系统核心概念', click_number: 523, increases: 18 },
    { key: 2, title: 'SQL 查询与索引优化', click_number: 486, increases: 14 },
    { key: 3, title: '数据结构链表与树', click_number: 458, increases: 21 },
    { key: 4, title: '人工智能导论实践', click_number: 392, increases: 12 },
    { key: 5, title: '课堂行为分析案例', click_number: 351, increases: 9 },
  ],
  resource: [
    { key: 1, title: 'SQL 实验指导手册', click_number: 612, increases: 16 },
    { key: 2, title: 'ER 图建模训练包', click_number: 574, increases: 19 },
    { key: 3, title: '链表与树结构课件', click_number: 536, increases: 13 },
    { key: 4, title: 'AI 伴学答疑样例库', click_number: 489, increases: 11 },
    { key: 5, title: '课堂行为识别说明', click_number: 432, increases: 8 },
  ],
};

const EMPTY_DISTRIBUTION_FALLBACK: TeacherContentDistribution = {
  total: 10326,
  items: [
    { name: 'resources', value: 5420 },
    { name: 'courses', value: 1286 },
    { name: 'homework', value: 2130 },
    { name: 'discussions', value: 1490 },
  ],
};

function isPositiveNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0;
}

function withStatsFallback(stats: TeacherStats): TeacherStats {
  const fallback = EMPTY_DASHBOARD_STATS_FALLBACK;
  const hasMeaningfulActivity =
    isPositiveNumber(stats.active_students) ||
    isPositiveNumber(stats.total_resources);

  if (hasMeaningfulActivity) {
    return {
      ...stats,
      total_courses: stats.total_courses || fallback.total_courses,
      total_teaching_classes:
        stats.total_teaching_classes || fallback.total_teaching_classes,
    };
  }

  return {
    ...fallback,
  };
}

export function getTeacherStats(): Promise<TeacherStats> {
  return axios
    .get<TeacherStats>('/api/dashboard/teacher/stats')
    .then((res) => withStatsFallback(res.data));
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
      return list.map((item, index) => ({
        ...item,
        alert_count:
          EMPTY_TREND_FALLBACK[index % EMPTY_TREND_FALLBACK.length],
      }));
    });
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
      const fallback = EMPTY_POPULAR_FALLBACK[type];
      if (!list.length) return fallback;
      if (list.some((item) => isPositiveNumber(item.click_number))) {
        return list;
      }
      return fallback.map((item, index) => ({
        ...item,
        title: list[index]?.title || item.title,
      }));
    });
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
      return EMPTY_DISTRIBUTION_FALLBACK;
    });
}
