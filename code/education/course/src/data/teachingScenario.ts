import type { Course, CourseResourceAnalysis, TeachingClass } from '@/api/course';
import type {
  PopularItem,
  TeacherContentDistribution,
  TeacherStats,
} from '@/api/dashboard';

const scenarioBaseTime = '2026-05-01T08:00:00.000Z';

export const SCENARIO_COURSE_IDS = [
  'c1111111-1111-4111-9111-111111111101',
  'c1111111-1111-4111-9111-111111111102',
  'c1111111-1111-4111-9111-111111111103',
  'c1111111-1111-4111-9111-111111111104',
  'c1111111-1111-4111-9111-111111111105',
  'c1111111-1111-4111-9111-111111111106',
] as const;

export const SCENARIO_UD_ID = 'b0000001-0000-4000-8000-000000000001';
export const SCENARIO_TEACHER_ID = 'b0000002-0000-4000-8000-000000000001';

export const scenarioCourses: Course[] = [
  {
    id: SCENARIO_COURSE_IDS[0],
    name: '数据库系统',
    description: '关系模型、SQL、事务与存储，配套实验与案例。',
    course_type: '专业核心',
    identifier: 'CS-DB-001',
    ud_id: SCENARIO_UD_ID,
    created_at: scenarioBaseTime,
    updated_at: scenarioBaseTime,
  },
  {
    id: SCENARIO_COURSE_IDS[1],
    name: '数据结构',
    description: '线性表、树、图与常用算法，注重动手实现。',
    course_type: '专业核心',
    identifier: 'CS-DS-001',
    ud_id: SCENARIO_UD_ID,
    created_at: scenarioBaseTime,
    updated_at: scenarioBaseTime,
  },
  {
    id: SCENARIO_COURSE_IDS[2],
    name: '人工智能导论',
    description: '搜索、机器学习与深度学习入门。',
    course_type: '专业选修',
    identifier: 'CS-AI-001',
    ud_id: SCENARIO_UD_ID,
    created_at: scenarioBaseTime,
    updated_at: scenarioBaseTime,
  },
  {
    id: SCENARIO_COURSE_IDS[3],
    name: '宏观经济学',
    description: '国民收入、货币与财政政策分析。',
    course_type: '专业核心',
    identifier: 'EC-MAC-001',
    ud_id: SCENARIO_UD_ID,
    created_at: scenarioBaseTime,
    updated_at: scenarioBaseTime,
  },
  {
    id: SCENARIO_COURSE_IDS[4],
    name: '审计学',
    description: '审计准则、风险评估与内部控制。',
    course_type: '专业核心',
    identifier: 'AC-AUD-001',
    ud_id: SCENARIO_UD_ID,
    created_at: scenarioBaseTime,
    updated_at: scenarioBaseTime,
  },
  {
    id: SCENARIO_COURSE_IDS[5],
    name: '金融学',
    description: '金融市场、资产定价与公司金融基础。',
    course_type: '专业核心',
    identifier: 'FI-FIN-001',
    ud_id: SCENARIO_UD_ID,
    created_at: scenarioBaseTime,
    updated_at: scenarioBaseTime,
  },
];

export const scenarioCourseDepartments: Record<string, '计算机学院' | '经管学院'> = {
  [SCENARIO_COURSE_IDS[0]]: '计算机学院',
  [SCENARIO_COURSE_IDS[1]]: '计算机学院',
  [SCENARIO_COURSE_IDS[2]]: '计算机学院',
  [SCENARIO_COURSE_IDS[3]]: '经管学院',
  [SCENARIO_COURSE_IDS[4]]: '经管学院',
  [SCENARIO_COURSE_IDS[5]]: '经管学院',
};

export const scenarioCourseMetrics: Record<
  string,
  { progress: number; rating: string; teacher: string; learners: number }
> = {
  [SCENARIO_COURSE_IDS[0]]: { progress: 68, rating: '4.8', teacher: '林老师', learners: 128 },
  [SCENARIO_COURSE_IDS[1]]: { progress: 56, rating: '4.7', teacher: '陈老师', learners: 116 },
  [SCENARIO_COURSE_IDS[2]]: { progress: 62, rating: '4.9', teacher: '周老师', learners: 142 },
  [SCENARIO_COURSE_IDS[3]]: { progress: 48, rating: '4.6', teacher: '王老师', learners: 96 },
  [SCENARIO_COURSE_IDS[4]]: { progress: 52, rating: '4.7', teacher: '赵老师', learners: 88 },
  [SCENARIO_COURSE_IDS[5]]: { progress: 44, rating: '4.6', teacher: '许老师', learners: 103 },
};

export function getScenarioCourseById(id: string) {
  return scenarioCourses.find((course) => course.id === id) ?? null;
}

export function getScenarioTeachingClasses(courseId: string): TeachingClass[] {
  if (!getScenarioCourseById(courseId)) return [];
  return [
    {
      id: 'd0000001-0000-4000-8000-000000000001',
      name: '2026 春季教学班',
      course_id: courseId,
      lecturer_id: SCENARIO_TEACHER_ID,
      created_at: scenarioBaseTime,
      updated_at: scenarioBaseTime,
    },
  ];
}

export const scenarioCourseResourceAnalysis: Record<string, CourseResourceAnalysis> = {
  [SCENARIO_COURSE_IDS[0]]: {
    document_size: 86.4,
    document_count: 42,
    video_size: 512.8,
    video_count: 18,
    image_size: 37.6,
    image_count: 64,
    homework_count: 128,
  },
  [SCENARIO_COURSE_IDS[1]]: {
    document_size: 72.1,
    document_count: 36,
    video_size: 438.5,
    video_count: 16,
    image_size: 29.4,
    image_count: 52,
    homework_count: 112,
  },
  [SCENARIO_COURSE_IDS[2]]: {
    document_size: 91.8,
    document_count: 48,
    video_size: 624.2,
    video_count: 21,
    image_size: 44.3,
    image_count: 78,
    homework_count: 96,
  },
};

export const defaultScenarioResourceAnalysis: CourseResourceAnalysis = {
  document_size: 58.6,
  document_count: 28,
  video_size: 316.4,
  video_count: 12,
  image_size: 18.9,
  image_count: 35,
  homework_count: 72,
};

export function getScenarioResourceAnalysis(courseId: string): CourseResourceAnalysis {
  return scenarioCourseResourceAnalysis[courseId] || defaultScenarioResourceAnalysis;
}

export const scenarioDashboardStats: TeacherStats = {
  today_login_count: 186,
  total_courses: 18,
  total_resources: 1284,
  total_teaching_classes: 32,
  active_students: 486,
};

export const scenarioVisitsTrend = [
  { date: '2026-05-13', alert_count: 612 },
  { date: '2026-05-14', alert_count: 688 },
  { date: '2026-05-15', alert_count: 742 },
  { date: '2026-05-16', alert_count: 703 },
  { date: '2026-05-17', alert_count: 815 },
  { date: '2026-05-18', alert_count: 774 },
  { date: '2026-05-19', alert_count: 836 },
];

export const scenarioPopular: Record<'course' | 'resource', PopularItem[]> = {
  course: [
    { key: 1, title: '数据库系统：SQL 查询与索引优化', click_number: 523, increases: 18 },
    { key: 2, title: '数据结构：链表与树结构训练', click_number: 486, increases: 14 },
    { key: 3, title: '人工智能导论：模型应用案例', click_number: 458, increases: 21 },
    { key: 4, title: '计算机网络：分层模型复习', click_number: 392, increases: 12 },
    { key: 5, title: '操作系统：进程调度专题', click_number: 351, increases: 9 },
  ],
  resource: [
    { key: 1, title: 'SQL 实验指导手册', click_number: 612, increases: 16 },
    { key: 2, title: 'ER 图建模训练包', click_number: 574, increases: 19 },
    { key: 3, title: '链表与树结构课件', click_number: 536, increases: 13 },
    { key: 4, title: 'AI 伴学答疑样例库', click_number: 489, increases: 11 },
    { key: 5, title: '课堂行为识别说明', click_number: 432, increases: 8 },
  ],
};

export const scenarioContentDistribution: TeacherContentDistribution = {
  total: 1284,
  items: [
    { name: 'resources', value: 642 },
    { name: 'courses', value: 18 },
    { name: 'homework', value: 386 },
    { name: 'discussions', value: 238 },
  ],
};

export const scenarioCourseResourcePie = [
  { name: '文档', value: 328, percent: 25.55 },
  { name: '作业', value: 386, percent: 30.06 },
  { name: '视频', value: 274, percent: 21.34 },
  { name: '图片', value: 296, percent: 23.05 },
];

export const scenarioAttendanceStudents = [
  { id: 'S001', name: '陈思远', status: '已签到' },
  { id: 'S002', name: '李沐阳', status: '已签到' },
  { id: 'S003', name: '周嘉宁', status: '缺席' },
  { id: 'S004', name: '赵一然', status: '迟到' },
  { id: 'S005', name: '钱予安', status: '已签到' },
  { id: 'S006', name: '孙若溪', status: '请假' },
  { id: 'S007', name: '吴书航', status: '已签到' },
  { id: 'S008', name: '郑清越', status: '已签到' },
  { id: 'S009', name: '王子墨', status: '迟到' },
  { id: 'S010', name: '冯嘉禾', status: '已签到' },
  { id: 'S011', name: '林知夏', status: '已签到' },
  { id: 'S012', name: '许安然', status: '请假' },
];

export const scenarioLearningArchive = {
  enrolled: ['数据库系统', '数据结构', '人工智能导论', '操作系统', '计算机网络'],
  calendarDate: new Date(2026, 4, 19),
  events: [
    { date: '5月19日', desc: 'SQL 事务实验复盘 · 数据库系统' },
    { date: '5月20日', desc: '链表专项练习截止 · 数据结构' },
    { date: '5月22日', desc: '课堂行为分析报告更新 · 人工智能导论' },
  ],
  stats: [
    { label: '学习时长', value: 18 },
    { label: '讨论次数', value: 7 },
    { label: '互动次数', value: 26 },
    { label: '缺勤次数', value: 1 },
    { label: '考勤次数', value: 21 },
    { label: '平均掌握度', value: 82 },
  ],
  warnings: [
    { date: '2026.5.18', text: '数据库系统 - 事务隔离级别练习正确率偏低' },
    { date: '2026.5.16', text: '数据结构 - 树结构递归题耗时偏长' },
    { date: '2026.5.12', text: '人工智能导论 - 模型评估指标需要复习' },
  ],
  timeShare: [
    { name: '数据库系统', pct: 31.2, color: '#6366f1' },
    { name: '数据结构', pct: 25.8, color: '#1677FF' },
    { name: '人工智能导论', pct: 23.4, color: '#2563eb' },
    { name: '操作系统', pct: 19.6, color: '#0ea5e9' },
  ],
};
