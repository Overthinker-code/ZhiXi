import type { ClassroomProfile } from './classroomCourses';

export type CourseTaskStatus = 'active' | 'upcoming' | 'done';

export interface CourseTask {
  id: string;
  title: string;
  type: '作业' | '测验' | '复习' | 'AI 任务';
  chapter: string;
  dueLabel: string;
  duration: number;
  status: CourseTaskStatus;
  progress: number;
}

export interface CourseResourceItem {
  id: string;
  title: string;
  type: '课件' | '讲义' | '案例' | '练习' | '导图' | '数据集';
  chapter: string;
  size: string;
  updatedAt: string;
  downloads: number;
}

export type CourseKnowledgeMapType =
  | 'knowledge'
  | 'problem'
  | 'ability'
  | 'target'
  | 'tutor';

export interface CourseKnowledgeNode {
  id: string;
  label: string;
  type: 'chapter' | 'concept' | 'resource' | 'task' | 'ability';
  x: number;
  y: number;
  weight: number;
}

export interface CourseKnowledgeLink {
  source: string;
  target: string;
  relation: '父子关系' | '前后置关系' | '关联关系' | '资料支撑' | '任务驱动';
}

export interface CourseKnowledgeMap {
  type: CourseKnowledgeMapType;
  title: string;
  description: string;
  nodes: CourseKnowledgeNode[];
  links: CourseKnowledgeLink[];
  focusTags: string[];
}

export interface CourseStructureBranch {
  id: string;
  title: string;
  resourceBadges: Array<'讲义' | '自测' | '案例' | '导图' | '讨论'>;
  taskCount: number;
  weakPoint: string;
  progress: number;
}

export type CourseAgentCategory = '教学增强' | '学习工具' | '资料科研';

const resourceTypes: CourseResourceItem['type'][] = [
  '课件',
  '讲义',
  '案例',
  '练习',
  '导图',
  '数据集',
];

export function buildCourseTasks(course: ClassroomProfile): CourseTask[] {
  const lessons = course.chapters.flatMap((chapter) =>
    chapter.lessons.map((lesson) => ({ chapter, lesson }))
  );
  const completed = lessons.filter((item) => item.lesson.status === 'done').length;
  const activeIndex = Math.min(completed, Math.max(lessons.length - 1, 0));

  return lessons.slice(0, 8).map(({ chapter, lesson }, index) => {
    const status: CourseTaskStatus =
      index < Math.max(activeIndex - 1, 0)
        ? 'done'
        : index <= activeIndex + 1
          ? 'active'
          : 'upcoming';
    const type: CourseTask['type'] =
      index % 4 === 0
        ? '作业'
        : index % 4 === 1
          ? '测验'
          : index % 4 === 2
            ? 'AI 任务'
            : '复习';

    return {
      id: `${course.id}-task-${index + 1}`,
      title:
        type === '作业'
          ? `${lesson.title}课后作业`
          : type === '测验'
            ? `${lesson.title}随堂测验`
            : type === 'AI 任务'
              ? `让小智总结：${lesson.title}`
              : `${lesson.title}重点复习`,
      type,
      chapter: chapter.title,
      dueLabel:
        status === 'done'
          ? '已完成'
          : status === 'active'
            ? index % 2
              ? '今天 22:00 前'
              : '本周五前'
            : `第 ${Math.min(index + 2, 12)} 周`,
      duration: 15 + (index % 4) * 10,
      status,
      progress: status === 'done' ? 100 : status === 'active' ? 35 + index * 4 : 0,
    };
  });
}

export function buildCourseResources(
  course: ClassroomProfile
): CourseResourceItem[] {
  const lessons = course.chapters.flatMap((chapter) =>
    chapter.lessons.map((lesson) => ({ chapter, lesson }))
  );
  return lessons.slice(0, 10).map(({ chapter, lesson }, index) => ({
    id: `${course.id}-resource-${index + 1}`,
    title: `${lesson.title}${index % 3 === 0 ? '核心讲义' : index % 3 === 1 ? '学习课件' : '案例与练习'}`,
    type: resourceTypes[index % resourceTypes.length],
    chapter: chapter.title,
    size: `${(1.8 + index * 0.7).toFixed(1)} MB`,
    updatedAt: `2026-05-${String(Math.max(5, 26 - index)).padStart(2, '0')}`,
    downloads: 86 + index * 17,
  }));
}

export function buildCourseStructureBranches(
  course: ClassroomProfile
): CourseStructureBranch[] {
  const resources = buildCourseResources(course);
  const tasks = buildCourseTasks(course);
  const weakPoints = course.concepts.flatMap((item) => item.points);

  return course.chapters.map((chapter, index) => {
    const completed = chapter.lessons.filter((lesson) => lesson.status === 'done').length;
    const resourceStart = index * 2;
    return {
      id: chapter.id,
      title: chapter.title.replace(/^第\d+章\s*/, ''),
      resourceBadges: [
        '讲义',
        resources[resourceStart]?.type === '案例' ? '案例' : '导图',
        tasks[index]?.type === '测验' ? '自测' : '讨论',
        resources[resourceStart + 1]?.type === '讲义' ? '讲义' : '案例',
      ],
      taskCount: tasks.filter((task) => task.chapter === chapter.title).length || 1,
      weakPoint: weakPoints[index % Math.max(weakPoints.length, 1)] || chapter.title,
      progress: Math.round((completed / Math.max(chapter.lessons.length, 1)) * 100),
    };
  });
}

export function buildCourseKnowledgeMaps(
  course: ClassroomProfile
): CourseKnowledgeMap[] {
  const chapters = course.chapters.slice(0, 5);
  const conceptNodes = course.concepts
    .flatMap((group) => group.points.map((point) => ({ group: group.title, point })))
    .slice(0, 14);
  const resources = buildCourseResources(course).slice(0, 6);
  const tasks = buildCourseTasks(course).slice(0, 5);
  const baseX = 470;
  const baseY = 230;
  const ring = 185;

  const chapterNodes: CourseKnowledgeNode[] = chapters.map((chapter, index) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(chapters.length, 1);
    return {
      id: `chapter-${index}`,
      label: chapter.title.replace(/^第\d+章\s*/, ''),
      type: 'chapter',
      x: baseX + Math.cos(angle) * ring,
      y: baseY + Math.sin(angle) * ring * 0.72,
      weight: 3,
    };
  });

  const conceptGraphNodes: CourseKnowledgeNode[] = conceptNodes.map((item, index) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(conceptNodes.length, 1);
    return {
      id: `concept-${index}`,
      label: item.point,
      type: 'concept',
      x: baseX + Math.cos(angle) * (ring + (index % 2 ? 72 : 34)),
      y: baseY + Math.sin(angle) * (ring * 0.75 + (index % 3) * 18),
      weight: index < 5 ? 2 : 1,
    };
  });

  const centerNode: CourseKnowledgeNode = {
    id: 'course-root',
    label: course.shortTitle,
    type: 'chapter',
    x: baseX,
    y: baseY,
    weight: 4,
  };

  const resourceNodes: CourseKnowledgeNode[] = resources.map((item, index) => ({
    id: `resource-${index}`,
    label: item.title.replace(course.shortTitle, ''),
    type: 'resource',
    x: 170 + (index % 2) * 128,
    y: 92 + Math.floor(index / 2) * 96,
    weight: 1,
  }));

  const taskNodes: CourseKnowledgeNode[] = tasks.map((item, index) => ({
    id: `task-${index}`,
    label: item.title.replace(course.shortTitle, ''),
    type: 'task',
    x: 710 + (index % 2) * 118,
    y: 106 + Math.floor(index / 2) * 106,
    weight: item.status === 'active' ? 2 : 1,
  }));

  const abilityNodes: CourseKnowledgeNode[] = course.concepts.slice(0, 5).map((item, index) => ({
    id: `ability-${index}`,
    label: `${item.title}能力`,
    type: 'ability',
    x: 250 + index * 110,
    y: index % 2 ? 310 : 150,
    weight: 2,
  }));

  const chapterLinks: CourseKnowledgeLink[] = chapterNodes.map((node, index) => ({
    source: index === 0 ? centerNode.id : chapterNodes[index - 1].id,
    target: node.id,
    relation: index === 0 ? '父子关系' : '前后置关系',
  }));

  const conceptLinks: CourseKnowledgeLink[] = conceptGraphNodes.map((node, index) => ({
    source: index % 3 === 0 ? centerNode.id : `concept-${Math.max(index - 1, 0)}`,
    target: node.id,
    relation: index % 4 === 0 ? '前后置关系' : '关联关系',
  }));

  return [
    {
      type: 'knowledge',
      title: '知识图谱',
      description: '围绕章节、概念和先修关系建立课程知识网络。',
      nodes: [centerNode, ...chapterNodes, ...conceptGraphNodes],
      links: [...chapterLinks, ...conceptLinks],
      focusTags: ['重点', '难点', '先修', '跨章关联'],
    },
    {
      type: 'problem',
      title: '问题图谱',
      description: '把资料、任务和易错点放到同一张问题地图里。',
      nodes: [centerNode, ...resourceNodes, ...taskNodes],
      links: [
        ...resourceNodes.map((node) => ({
          source: centerNode.id,
          target: node.id,
          relation: '资料支撑' as const,
        })),
        ...taskNodes.map((node, index) => ({
          source: resourceNodes[index % Math.max(resourceNodes.length, 1)]?.id || centerNode.id,
          target: node.id,
          relation: '任务驱动' as const,
        })),
      ],
      focusTags: ['资料支撑', '作业任务', '错题追踪', '讨论主题'],
    },
    {
      type: 'ability',
      title: '能力图谱',
      description: '把知识点提升为可评价的课程能力。',
      nodes: [centerNode, ...abilityNodes, ...conceptGraphNodes.slice(0, 8)],
      links: [
        ...abilityNodes.map((node) => ({
          source: centerNode.id,
          target: node.id,
          relation: '父子关系' as const,
        })),
        ...conceptGraphNodes.slice(0, 8).map((node, index) => ({
          source: abilityNodes[index % Math.max(abilityNodes.length, 1)]?.id || centerNode.id,
          target: node.id,
          relation: '关联关系' as const,
        })),
      ],
      focusTags: ['理解', '分析', '应用', '迁移'],
    },
    {
      type: 'target',
      title: '目标图谱',
      description: '把章节目标、评价任务和课程出口能力连起来。',
      nodes: [centerNode, ...chapterNodes, ...taskNodes],
      links: [
        ...chapterLinks,
        ...taskNodes.map((node, index) => ({
          source: chapterNodes[index % Math.max(chapterNodes.length, 1)]?.id || centerNode.id,
          target: node.id,
          relation: '任务驱动' as const,
        })),
      ],
      focusTags: ['学习目标', '评价证据', '课程项目', '验收标准'],
    },
    {
      type: 'tutor',
      title: '学习辅导图谱',
      description: '面向学生下一步行动，标出薄弱点、资料和 AI 辅导入口。',
      nodes: [centerNode, ...conceptGraphNodes.slice(0, 6), ...resourceNodes.slice(0, 4), ...taskNodes.slice(0, 4)],
      links: [
        ...conceptGraphNodes.slice(0, 6).map((node) => ({
          source: centerNode.id,
          target: node.id,
          relation: '关联关系' as const,
        })),
        ...resourceNodes.slice(0, 4).map((node, index) => ({
          source: conceptGraphNodes[index]?.id || centerNode.id,
          target: node.id,
          relation: '资料支撑' as const,
        })),
        ...taskNodes.slice(0, 4).map((node, index) => ({
          source: conceptGraphNodes[index + 2]?.id || centerNode.id,
          target: node.id,
          relation: '任务驱动' as const,
        })),
      ],
      focusTags: ['薄弱点', '复习路径', '资料问答', 'AI 陪练'],
    },
  ];
}

export const courseAgentTasks = [
  {
    key: 'explain',
    title: '本节知识答疑',
    description: '结合课程章节与资料，分步讲清概念、条件和常见误区。',
    estimate: '约 5 分钟',
    icon: 'icon-question-circle',
    forceAgent: 'tutor_agent',
    prompt: '请结合当前课程，讲解我正在学习的知识点，并先确认我卡住的位置。',
    category: '学习工具' as CourseAgentCategory,
  },
  {
    key: 'review',
    title: '生成复习单',
    description: '提炼重点、易错点、检查题，并形成可执行的 20 分钟复习计划。',
    estimate: '约 3 分钟',
    icon: 'icon-file',
    forceAgent: 'profile_agent',
    prompt: '请根据当前课程进度生成一份 20 分钟复习单，包含重点、易错点和自测题。',
    category: '学习工具' as CourseAgentCategory,
  },
  {
    key: 'grade',
    title: '批改当前作业',
    description: '按得分点、错因、订正步骤和掌握度反馈完成结构化批改。',
    estimate: '约 4 分钟',
    icon: 'icon-check-circle',
    forceAgent: 'grading_agent',
    prompt: '我要批改当前课程作业。请先提示我上传题目和答案，再按评分标准逐项反馈。',
    category: '教学增强' as CourseAgentCategory,
  },
  {
    key: 'quiz',
    title: '薄弱点强化练习',
    description: '根据课程进度生成梯度练习，完成后继续给出针对性追练。',
    estimate: '约 8 分钟',
    icon: 'icon-bulb',
    forceAgent: 'quiz_master',
    prompt: '请围绕当前课程薄弱点生成一组由浅入深的练习，先不要给答案。',
    category: '学习工具' as CourseAgentCategory,
  },
  {
    key: 'resource',
    title: '围绕资料提问',
    description: '挂载课件或讲义后，只依据当前课程资料进行可追溯回答。',
    estimate: '约 5 分钟',
    icon: 'icon-storage',
    forceAgent: 'retrieval_agent',
    prompt: '我将上传当前课程资料，请只根据资料回答，并在结论后标注依据。',
    category: '资料科研' as CourseAgentCategory,
  },
  {
    key: 'project',
    title: '课程项目教练',
    description: '拆解项目目标、里程碑与验收标准，持续跟踪下一步行动。',
    estimate: '约 10 分钟',
    icon: 'icon-branch',
    forceAgent: 'planner',
    prompt: '请作为当前课程项目教练，帮我拆解目标、里程碑、风险和今天的第一步。',
    category: '教学增强' as CourseAgentCategory,
  },
  {
    key: 'research',
    title: 'AI 科研助手',
    description: '围绕课程主题生成检索式、阅读框架和可引用的研究问题。',
    estimate: '约 8 分钟',
    icon: 'icon-experiment',
    forceAgent: 'research_agent',
    prompt: '请围绕当前课程主题设计一个小型研究问题，给出检索关键词、阅读路径和可验证的资料依据。',
    category: '资料科研' as CourseAgentCategory,
  },
  {
    key: 'map',
    title: '生成课程图谱',
    description: '把章节、资料、作业和薄弱点整理成可执行的学习路径图。',
    estimate: '约 6 分钟',
    icon: 'icon-relation',
    forceAgent: 'graph_agent',
    prompt: '请根据当前课程生成一张文字版课程图谱，包含知识、问题、能力和下一步学习路径。',
    category: '资料科研' as CourseAgentCategory,
  },
  {
    key: 'video',
    title: '视频理解助手',
    description: '上传课堂截图或视频片段后，提炼讲解结构与关键节点。',
    estimate: '约 7 分钟',
    icon: 'icon-video-camera',
    forceAgent: 'vision_agent',
    prompt: '我将上传课堂视频截图或片段，请提炼讲解结构、关键知识点和建议复习动作。',
    category: '资料科研' as CourseAgentCategory,
  },
  {
    key: 'formula',
    title: '公式识别与讲解',
    description: '把公式转成标准 LaTeX，并解释符号含义、推导步骤和适用条件。',
    estimate: '约 5 分钟',
    icon: 'icon-code-square',
    forceAgent: 'formula_agent',
    prompt: '请把我提供的公式整理为标准 LaTeX，并解释每个符号、推导步骤和适用条件。',
    category: '学习工具' as CourseAgentCategory,
  },
] as const;
