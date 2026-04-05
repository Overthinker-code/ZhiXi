export const demoVisitsTrend = [
  { x: '2025-05-23', y: 1234 },
  { x: '2025-05-24', y: 1380 },
  { x: '2025-05-25', y: 1498 },
  { x: '2025-05-26', y: 1572 },
  { x: '2025-05-27', y: 1641 },
  { x: '2025-05-28', y: 1703 },
  { x: '2025-05-29', y: 1766 },
  { x: '2025-05-30', y: 1820 },
];

export const demoResourceDistribution = {
  total: 9285,
  items: [
    { name: 'resources', value: 5179 },
    { name: 'courses', value: 2301 },
    { name: 'homework', value: 1116 },
    { name: 'discussions', value: 689 },
  ],
};

export const demoCourseResourcePie = [
  { name: '文档', value: 1884, percent: 20.29 },
  { name: '作业', value: 920, percent: 9.91 },
  { name: '视频', value: 5548, percent: 59.79 },
  { name: '图片', value: 933, percent: 10.01 },
];

/** 与后端 `app/core/db.py` 中 `seed_education_demo` 使用的课程 id 一致 */
export const DEMO_COURSE_IDS = [
  'c1111111-1111-4111-9111-111111111101',
  'c1111111-1111-4111-9111-111111111102',
  'c1111111-1111-4111-9111-111111111103',
  'c1111111-1111-4111-9111-111111111104',
  'c1111111-1111-4111-9111-111111111105',
  'c1111111-1111-4111-9111-111111111106',
] as const;

const _demoCourseTime = '2025-01-15T08:00:00.000Z';

/** 与后端种子院系、教师 id 一致 */
export const DEMO_UD_ID = 'b0000001-0000-4000-8000-000000000001';
export const DEMO_TEACHER_ID = 'b0000002-0000-4000-8000-000000000001';

/** 接口不可用时的课程列表/详情兜底（与后端种子数据字段一致） */
export const demoCourses = [
  {
    id: DEMO_COURSE_IDS[0],
    name: '数据库系统',
    description: '关系模型、SQL、事务与存储，配套实验与案例。',
    course_type: '专业核心',
    identifier: 'CS-DB-001',
    ud_id: DEMO_UD_ID,
    created_at: _demoCourseTime,
    updated_at: _demoCourseTime,
  },
  {
    id: DEMO_COURSE_IDS[1],
    name: '数据结构',
    description: '线性表、树、图与常用算法，注重动手实现。',
    course_type: '专业核心',
    identifier: 'CS-DS-001',
    ud_id: DEMO_UD_ID,
    created_at: _demoCourseTime,
    updated_at: _demoCourseTime,
  },
  {
    id: DEMO_COURSE_IDS[2],
    name: '人工智能导论',
    description: '搜索、机器学习与深度学习入门。',
    course_type: '专业选修',
    identifier: 'CS-AI-001',
    ud_id: DEMO_UD_ID,
    created_at: _demoCourseTime,
    updated_at: _demoCourseTime,
  },
  {
    id: DEMO_COURSE_IDS[3],
    name: '宏观经济学',
    description: '国民收入、货币与财政政策分析。',
    course_type: '专业核心',
    identifier: 'EC-MAC-001',
    ud_id: DEMO_UD_ID,
    created_at: _demoCourseTime,
    updated_at: _demoCourseTime,
  },
  {
    id: DEMO_COURSE_IDS[4],
    name: '审计学',
    description: '审计准则、风险评估与内部控制。',
    course_type: '专业核心',
    identifier: 'AC-AUD-001',
    ud_id: DEMO_UD_ID,
    created_at: _demoCourseTime,
    updated_at: _demoCourseTime,
  },
  {
    id: DEMO_COURSE_IDS[5],
    name: '金融学',
    description: '金融市场、资产定价与公司金融基础。',
    course_type: '专业核心',
    identifier: 'FI-FIN-001',
    ud_id: DEMO_UD_ID,
    created_at: _demoCourseTime,
    updated_at: _demoCourseTime,
  },
] as const;

export function getDemoCourseById(id: string) {
  return demoCourses.find((c) => c.id === id) ?? null;
}

/** 演示教学班（仅兜底展示；授课人列显示教师 id，与后端一致） */
export function getDemoTeachingClasses(courseId: string) {
  if (!demoCourses.some((c) => c.id === courseId)) {
    return [];
  }
  return [
    {
      id: 'd0000001-0000-4000-8000-000000000001',
      name: '春季教学班',
      course_id: courseId,
      lecturer_id: DEMO_TEACHER_ID,
      created_at: _demoCourseTime,
      updated_at: _demoCourseTime,
    },
  ];
}

export const demoAttendanceStudents = [
  { id: 'S001', name: '张三', status: '已签到' },
  { id: 'S002', name: '李四', status: '已签到' },
  { id: 'S003', name: '王五', status: '缺席' },
  { id: 'S004', name: '赵六', status: '迟到' },
  { id: 'S005', name: '钱七', status: '已签到' },
  { id: 'S006', name: '孙八', status: '请假' },
  { id: 'S007', name: '周九', status: '已签到' },
  { id: 'S008', name: '吴十', status: '已签到' },
  { id: 'S009', name: '郑十一', status: '迟到' },
  { id: 'S010', name: '王十二', status: '已签到' },
  { id: 'S011', name: '冯十三', status: '已签到' },
  { id: 'S012', name: '陈十四', status: '请假' },
];
