import DatabaseDemo from '@/assets/images/course-demo/database.jpg';
import DataStructuresDemo from '@/assets/images/course-demo/data-structures.jpg';
import AiDemo from '@/assets/images/course-demo/artificial-intelligence.jpg';
import MacroeconomicsDemo from '@/assets/images/course-demo/macroeconomics.jpg';
import AuditingDemo from '@/assets/images/course-demo/auditing.jpg';
import FinanceDemo from '@/assets/images/course-demo/finance.jpg';
import { SCENARIO_COURSE_IDS } from '@/data/teachingScenario';

export type ClassroomLesson = {
  id: string;
  label: string;
  title: string;
  status: 'done' | 'pending';
};

export type ClassroomChapter = {
  id: string;
  title: string;
  lessons: ClassroomLesson[];
};

export type ClassroomConcept = {
  title: string;
  points: string[];
  detail?: string;
  outcomes?: string[];
  misconceptions?: string[];
  activities?: string[];
  resources?: string[];
  checks?: string[];
};

export type ClassroomProfile = {
  id: string;
  title: string;
  shortTitle: string;
  description: string;
  teacher: string;
  team: string;
  department: string;
  cover: string;
  hours: number;
  difficulty: string;
  type: string;
  updatedAt: string;
  progress: number;
  learned: number;
  total: number;
  chapters: ClassroomChapter[];
  notes: ClassroomConcept[];
  concepts: ClassroomConcept[];
  accent: string;
};

function makeChapters(
  sections: Array<{ title: string; lessons: string[] }>,
  completedCount: number
): ClassroomChapter[] {
  let lessonIndex = 0;
  return sections.map((section, chapterIndex) => ({
    id: `ch${chapterIndex + 1}`,
    title: `第${chapterIndex + 1}章 ${section.title}`,
    lessons: section.lessons.map((title, lessonOffset) => {
      lessonIndex += 1;
      const id = `${chapterIndex + 1}.${lessonOffset + 1}`;
      return {
        id,
        label: `${id} ${title}`,
        title,
        status: lessonIndex <= completedCount ? 'done' : 'pending',
      };
    }),
  }));
}

function enrichConcept(
  concept: ClassroomConcept,
  course: Pick<ClassroomProfile, 'shortTitle' | 'difficulty'>
): ClassroomConcept {
  const points = concept.points.filter(Boolean);
  const primary = points[0] || concept.title;
  const secondary = points[1] || concept.title;
  const third = points[2] || concept.title;
  return {
    ...concept,
    detail:
      concept.detail ||
      `${concept.title} 是 ${course.shortTitle} 的关键学习单元，需要同时掌握“概念定义、适用条件、与相邻知识的边界、在题目或案例中的判断步骤”。`,
    outcomes: concept.outcomes || [
      `能用自己的话解释 ${concept.title}，并说明它解决哪类问题。`,
      `能在题目或案例中定位 ${primary}、${secondary} 与 ${third} 的作用。`,
      `能把该主题连接到前后章节，形成一条可复述的学习路径。`,
    ],
    misconceptions: concept.misconceptions || [
      `只背 ${concept.title} 的结论，但说不清适用条件。`,
      `把 ${primary} 与 ${secondary} 混用，导致推理步骤跳跃。`,
      `忽略最后的校验或反例，答案看似完整但无法落到课程任务。`,
    ],
    activities: concept.activities || [
      `先用 3 句话复述 ${concept.title}，再用课程案例标出条件、方法和结论。`,
      `把 ${points.join('、')} 做成三列对比表，写出每一列的判断标准。`,
      `完成 1 道基础题和 1 道变式题，并让 AI 批改错因。`,
    ],
    resources: concept.resources || [
      `${concept.title} 课堂讲义`,
      `${primary} 例题卡片`,
      `${secondary} 与 ${third} 对比练习`,
    ],
    checks: concept.checks || [
      `我能否说清 ${concept.title} 的定义和边界？`,
      `我能否指出 ${primary} 在案例中的证据？`,
      `我能否把错误答案改写成符合课程术语的答案？`,
    ],
  };
}

function enrichCourse(course: ClassroomProfile): ClassroomProfile {
  const lessons = course.chapters.flatMap((chapter) => chapter.lessons);
  const learned = lessons.filter((lesson) => lesson.status === 'done').length;
  const total = lessons.length;
  return {
    ...course,
    learned,
    total,
    progress: Math.round((learned / Math.max(total, 1)) * 100),
    notes: course.notes.map((note) => enrichConcept(note, course)),
    concepts: course.concepts.map((concept) => enrichConcept(concept, course)),
  };
}

const classroomCourseSeed: ClassroomProfile[] = [
  {
    id: SCENARIO_COURSE_IDS[0],
    title: '数据库系统原理',
    shortTitle: '数据库系统',
    description: '从关系模型、SQL 到事务并发与恢复，建立完整的数据管理知识体系。',
    teacher: '林老师',
    team: '数据库课程组',
    department: '计算机学院',
    cover: DatabaseDemo,
    hours: 48,
    difficulty: '中等',
    type: '专业必修',
    updatedAt: '2026-05-20',
    progress: 62,
    learned: 18,
    total: 29,
    accent: '#5367f8',
    chapters: makeChapters(
      [
        { title: '关系数据模型', lessons: ['数据模型与关系模型', '关系代数', 'SQL 基础'] },
        { title: '完整性与约束', lessons: ['实体完整性', '参照完整性', '用户定义完整性'] },
        { title: '事务与并发控制', lessons: ['事务与原子性', '可串行化', '死锁处理'] },
        { title: '规范化与恢复', lessons: ['函数依赖', '范式与 BCNF', '日志与检查点'] },
      ],
      7
    ),
    notes: [
      { title: '关系模型', points: ['二维表组织数据', '元组与属性', '主键唯一标识实体'] },
      { title: 'SQL 查询', points: ['SELECT 投影与筛选', 'JOIN 多表关联', '聚合与子查询'] },
      { title: '完整性约束', points: ['实体完整性', '参照完整性', '用户定义约束'] },
      { title: '事务机制', points: ['ACID 特性', '锁与并发调度', '日志恢复策略'] },
    ],
    concepts: [
      { title: '数据模型', points: ['关系模型', 'ER 模型', '数据字典'] },
      { title: 'SQL 语言', points: ['查询', '更新', '视图'] },
      { title: '并发控制', points: ['锁机制', '可串行化', '死锁处理'] },
      { title: '数据库设计', points: ['函数依赖', '规范化', '索引优化'] },
    ],
  },
  {
    id: SCENARIO_COURSE_IDS[1],
    title: '数据结构',
    shortTitle: '数据结构',
    description: '理解线性结构、树、图和经典算法，并能完成复杂度分析与工程实现。',
    teacher: '陈老师',
    team: '算法课程组',
    department: '计算机学院',
    cover: DataStructuresDemo,
    hours: 56,
    difficulty: '中高',
    type: '专业必修',
    updatedAt: '2026-05-18',
    progress: 56,
    learned: 14,
    total: 25,
    accent: '#1f9d78',
    chapters: makeChapters(
      [
        { title: '线性结构', lessons: ['顺序表', '链表', '栈与队列'] },
        { title: '树结构', lessons: ['二叉树遍历', '堆与优先队列', '平衡搜索树'] },
        { title: '图结构', lessons: ['图的存储', '深度与广度搜索', '最短路径'] },
        { title: '排序与查找', lessons: ['快速排序', '归并排序', '哈希查找'] },
      ],
      6
    ),
    notes: [
      { title: '复杂度分析', points: ['时间复杂度', '空间复杂度', '均摊分析'] },
      { title: '线性结构', points: ['数组连续存储', '链表动态连接', '栈与队列限制访问'] },
      { title: '树与图', points: ['层次关系', '遍历策略', '连通与路径问题'] },
      { title: '算法设计', points: ['分治思想', '贪心选择', '动态规划'] },
    ],
    concepts: [
      { title: '线性表', points: ['数组', '链表', '跳表'] },
      { title: '树', points: ['二叉树', '堆', '平衡树'] },
      { title: '图', points: ['遍历', '最短路径', '生成树'] },
      { title: '算法', points: ['排序', '查找', '复杂度'] },
    ],
  },
  {
    id: SCENARIO_COURSE_IDS[2],
    title: '人工智能导论',
    shortTitle: '人工智能导论',
    description: '覆盖智能搜索、知识表示、机器学习与神经网络，理解 AI 系统的基本范式。',
    teacher: '周老师',
    team: '智能科学课程组',
    department: '计算机学院',
    cover: AiDemo,
    hours: 48,
    difficulty: '中高',
    type: '专业选修',
    updatedAt: '2026-05-24',
    progress: 62,
    learned: 16,
    total: 26,
    accent: '#805ad5',
    chapters: makeChapters(
      [
        { title: '智能与搜索', lessons: ['人工智能概览', '状态空间搜索', '启发式搜索'] },
        { title: '知识与推理', lessons: ['知识表示', '逻辑推理', '概率推理'] },
        { title: '机器学习', lessons: ['监督学习', '无监督学习', '模型评估'] },
        { title: '神经网络', lessons: ['感知机', '反向传播', '深度学习应用'] },
      ],
      7
    ),
    notes: [
      { title: '问题求解', points: ['状态空间', '搜索树', '启发函数'] },
      { title: '知识推理', points: ['命题逻辑', '贝叶斯网络', '不确定性推断'] },
      { title: '机器学习', points: ['特征与标签', '训练与验证', '偏差与方差'] },
      { title: '神经网络', points: ['激活函数', '损失函数', '梯度下降'] },
    ],
    concepts: [
      { title: '智能搜索', points: ['BFS', 'A*', '博弈搜索'] },
      { title: '知识表示', points: ['逻辑', '语义网络', '概率图'] },
      { title: '机器学习', points: ['分类', '回归', '聚类'] },
      { title: '深度学习', points: ['神经元', '反向传播', 'Transformer'] },
    ],
  },
  {
    id: SCENARIO_COURSE_IDS[3],
    title: '宏观经济学',
    shortTitle: '宏观经济学',
    description: '用总量模型理解经济增长、通货膨胀、失业以及财政与货币政策。',
    teacher: '王老师',
    team: '经济理论课程组',
    department: '经管学院',
    cover: MacroeconomicsDemo,
    hours: 48,
    difficulty: '中等',
    type: '专业必修',
    updatedAt: '2026-05-16',
    progress: 48,
    learned: 12,
    total: 25,
    accent: '#d97706',
    chapters: makeChapters(
      [
        { title: '国民收入核算', lessons: ['GDP 核算', '价格指数', '收入与支出循环'] },
        { title: '短期经济波动', lessons: ['总需求', '总供给', '乘数效应'] },
        { title: '宏观政策', lessons: ['财政政策', '货币政策', '政策组合'] },
        { title: '长期增长', lessons: ['资本积累', '技术进步', '开放经济'] },
      ],
      5
    ),
    notes: [
      { title: '总量指标', points: ['名义与实际 GDP', 'CPI 与通胀率', '失业率'] },
      { title: '需求管理', points: ['消费函数', '投资需求', '政府支出乘数'] },
      { title: '货币体系', points: ['货币供给', '利率传导', '中央银行工具'] },
      { title: '经济增长', points: ['储蓄与资本', '人口因素', '技术进步'] },
    ],
    concepts: [
      { title: '国民收入', points: ['GDP', 'GNI', '价格指数'] },
      { title: '经济波动', points: ['总需求', '总供给', '经济周期'] },
      { title: '宏观政策', points: ['财政政策', '货币政策', '政策时滞'] },
      { title: '长期增长', points: ['资本', '劳动', '技术'] },
    ],
  },
  {
    id: SCENARIO_COURSE_IDS[4],
    title: '审计学',
    shortTitle: '审计学',
    description: '掌握审计准则、风险评估、内部控制测试与审计证据形成过程。',
    teacher: '赵老师',
    team: '审计与风控课程组',
    department: '经管学院',
    cover: AuditingDemo,
    hours: 44,
    difficulty: '中等',
    type: '专业必修',
    updatedAt: '2026-05-14',
    progress: 52,
    learned: 13,
    total: 25,
    accent: '#c24178',
    chapters: makeChapters(
      [
        { title: '审计基础', lessons: ['审计目标', '职业道德', '审计准则'] },
        { title: '风险评估', lessons: ['重大错报风险', '了解被审计单位', '风险应对'] },
        { title: '内部控制', lessons: ['控制环境', '控制测试', '实质性程序'] },
        { title: '审计报告', lessons: ['审计证据', '审计意见', '关键审计事项'] },
      ],
      6
    ),
    notes: [
      { title: '审计目标', points: ['合理保证', '财务报表认定', '职业怀疑'] },
      { title: '风险模型', points: ['固有风险', '控制风险', '检查风险'] },
      { title: '审计证据', points: ['充分性', '适当性', '函证与观察'] },
      { title: '审计报告', points: ['无保留意见', '非无保留意见', '关键审计事项'] },
    ],
    concepts: [
      { title: '审计准则', points: ['独立性', '职业判断', '质量控制'] },
      { title: '风险评估', points: ['重大错报', '舞弊风险', '分析程序'] },
      { title: '内部控制', points: ['控制环境', '控制活动', '信息沟通'] },
      { title: '形成意见', points: ['审计证据', '错报评价', '审计报告'] },
    ],
  },
  {
    id: SCENARIO_COURSE_IDS[5],
    title: '金融学',
    shortTitle: '金融学',
    description: '理解金融市场、利率形成、资产定价、风险管理与公司融资决策。',
    teacher: '许老师',
    team: '金融市场课程组',
    department: '经管学院',
    cover: FinanceDemo,
    hours: 48,
    difficulty: '中高',
    type: '专业必修',
    updatedAt: '2026-05-22',
    progress: 44,
    learned: 11,
    total: 25,
    accent: '#2563a6',
    chapters: makeChapters(
      [
        { title: '金融体系', lessons: ['金融市场', '金融机构', '货币时间价值'] },
        { title: '资产定价', lessons: ['债券定价', '股票估值', '资本资产定价'] },
        { title: '风险管理', lessons: ['收益与风险', '投资组合', '衍生工具'] },
        { title: '公司金融', lessons: ['资本预算', '融资结构', '股利政策'] },
      ],
      5
    ),
    notes: [
      { title: '时间价值', points: ['现值与终值', '年金', '贴现率'] },
      { title: '资产定价', points: ['现金流折现', '债券久期', '股票估值'] },
      { title: '投资组合', points: ['期望收益', '波动率', '分散化'] },
      { title: '公司金融', points: ['净现值', '资本成本', '资本结构'] },
    ],
    concepts: [
      { title: '金融市场', points: ['货币市场', '资本市场', '外汇市场'] },
      { title: '资产定价', points: ['债券', '股票', 'CAPM'] },
      { title: '风险管理', points: ['组合', '对冲', '衍生品'] },
      { title: '公司金融', points: ['投资', '融资', '分配'] },
    ],
  },
  {
    id: SCENARIO_COURSE_IDS[6],
    title: '软件工程导论',
    shortTitle: '软件工程',
    description: '从软件危机出发，系统学习需求、设计、实现、测试、维护与项目管理。',
    teacher: '软件工程课程组',
    team: '软件工程课程组',
    department: '计算机学院',
    cover: AiDemo,
    hours: 56,
    difficulty: '中等',
    type: '专业核心',
    updatedAt: '2026-07-19',
    progress: 38,
    learned: 10,
    total: 26,
    accent: '#4f46e5',
    chapters: makeChapters(
      [
        { title: '软件工程学概述', lessons: ['软件危机与软件工程', '软件工程基本原理'] },
        { title: '可行性研究', lessons: ['系统流程图', '成本效益分析'] },
        { title: '需求分析', lessons: ['需求获取', '数据流图与数据字典'] },
        { title: '形式化说明技术', lessons: ['有限状态机', 'Petri 网'] },
        { title: '总体设计', lessons: ['模块化设计', '耦合与内聚'] },
        { title: '详细设计', lessons: ['过程设计工具', '人机界面设计'] },
        { title: '实现', lessons: ['编码规范', '单元测试'] },
        { title: '维护', lessons: ['维护类型', '软件再工程'] },
        { title: '面向对象方法学', lessons: ['对象模型', '动态模型'] },
        { title: '面向对象分析', lessons: ['识别类', '建立对象模型'] },
        { title: '面向对象设计', lessons: ['系统设计', '对象设计'] },
        { title: '面向对象实现', lessons: ['程序设计语言', '面向对象测试'] },
        { title: '软件项目管理', lessons: ['估算与进度', '质量保证与 CMM'] },
      ],
      10
    ),
    notes: [
      { title: '过程与生命周期', points: ['软件危机', '生命周期', '过程模型'] },
      { title: '分析与建模', points: ['需求获取', '数据流图', 'UML'] },
      { title: '设计与实现', points: ['模块化', '耦合与内聚', '编码规范'] },
      { title: '验证与演化', points: ['软件测试', '维护', '再工程'] },
    ],
    concepts: [
      { title: '软件过程', points: ['瀑布模型', '增量模型', '敏捷开发'] },
      { title: '需求工程', points: ['需求获取', '需求建模', '需求验证'] },
      { title: '软件设计', points: ['模块化', '体系结构', '详细设计'] },
      { title: '软件质量', points: ['黑盒测试', '白盒测试', '质量保证'] },
      { title: '面向对象建模', points: ['用例图', '类图', '顺序图'] },
      { title: '项目管理', points: ['工作量估算', '进度计划', '风险管理'] },
    ],
  },
];

export const classroomCourses: ClassroomProfile[] = classroomCourseSeed.map(enrichCourse);

export function getClassroomCourse(id?: string | null) {
  return classroomCourses.find((course) => course.id === id) || null;
}
