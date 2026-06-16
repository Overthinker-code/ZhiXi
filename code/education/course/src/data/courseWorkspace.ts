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

export const courseAgentTasks = [
  {
    key: 'explain',
    title: '本节知识答疑',
    description: '结合课程章节与资料，分步讲清概念、条件和常见误区。',
    estimate: '约 5 分钟',
    icon: 'icon-question-circle',
    forceAgent: 'tutor_agent',
    prompt: '请结合当前课程，讲解我正在学习的知识点，并先确认我卡住的位置。',
  },
  {
    key: 'review',
    title: '生成复习单',
    description: '提炼重点、易错点、检查题，并形成可执行的 20 分钟复习计划。',
    estimate: '约 3 分钟',
    icon: 'icon-file',
    forceAgent: 'profile_agent',
    prompt: '请根据当前课程进度生成一份 20 分钟复习单，包含重点、易错点和自测题。',
  },
  {
    key: 'grade',
    title: '批改当前作业',
    description: '按得分点、错因、订正步骤和掌握度反馈完成结构化批改。',
    estimate: '约 4 分钟',
    icon: 'icon-check-circle',
    forceAgent: 'grading_agent',
    prompt: '我要批改当前课程作业。请先提示我上传题目和答案，再按评分标准逐项反馈。',
  },
  {
    key: 'quiz',
    title: '薄弱点强化练习',
    description: '根据课程进度生成梯度练习，完成后继续给出针对性追练。',
    estimate: '约 8 分钟',
    icon: 'icon-bulb',
    forceAgent: 'quiz_master',
    prompt: '请围绕当前课程薄弱点生成一组由浅入深的练习，先不要给答案。',
  },
  {
    key: 'resource',
    title: '围绕资料提问',
    description: '挂载课件或讲义后，只依据当前课程资料进行可追溯回答。',
    estimate: '约 5 分钟',
    icon: 'icon-storage',
    forceAgent: 'retrieval_agent',
    prompt: '我将上传当前课程资料，请只根据资料回答，并在结论后标注依据。',
  },
  {
    key: 'project',
    title: '课程项目教练',
    description: '拆解项目目标、里程碑与验收标准，持续跟踪下一步行动。',
    estimate: '约 10 分钟',
    icon: 'icon-branch',
    forceAgent: 'planner',
    prompt: '请作为当前课程项目教练，帮我拆解目标、里程碑、风险和今天的第一步。',
  },
] as const;
