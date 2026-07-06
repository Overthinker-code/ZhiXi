import type {
  AIChatStreamPayload,
  ReasoningLevel,
  TutorMode,
} from '@/api/ai-chat';

export type TutorPanel = 'course_picker' | 'upload' | 'resource_config' | 'research_plan';

export interface TutorAction {
  id: string;
  label: string;
  description: string;
  mode: TutorMode;
  requiredContext?: Array<'course' | 'chapter' | 'attachment' | 'knowledge_point'>;
  requestPatch: Partial<AIChatStreamPayload>;
  openPanel?: TutorPanel;
}

export const DEFAULT_RESOURCE_TYPES = [
  'lecture_note',
  'mind_map',
  'quiz',
  'reading',
  'code_case',
  'video_script',
];

export const TUTOR_ACTIONS: TutorAction[] = [
  {
    id: 'course_qa',
    label: '课程问答',
    description: '基于课程资料与引用证据回答问题',
    mode: 'tutor',
    requestPatch: {
      courseContext: { knowledgePointIds: [], useCourseRag: true },
      tools: {
        webSearch: false,
        deepResearch: false,
        homeworkReview: false,
        resourceGeneration: false,
        citationRequired: true,
      },
      reasoning: { level: 'balanced' as ReasoningLevel, showSummary: true },
    },
    openPanel: 'course_picker',
  },
  {
    id: 'homework_review',
    label: '作业批改',
    description: '上传图片或文档，生成评分、错因和改进建议',
    mode: 'homework_review',
    requiredContext: ['attachment'],
    requestPatch: {
      tools: {
        webSearch: false,
        deepResearch: false,
        homeworkReview: true,
        resourceGeneration: false,
        citationRequired: true,
      },
      reasoning: { level: 'balanced' as ReasoningLevel, showSummary: true },
    },
    openPanel: 'upload',
  },
  {
    id: 'resource_generation',
    label: '资料生成',
    description: '生成讲义、练习题、思维导图和代码案例',
    mode: 'resource_generation',
    requestPatch: {
      tools: {
        webSearch: false,
        deepResearch: false,
        homeworkReview: false,
        resourceGeneration: true,
        citationRequired: true,
      },
      resourceRequest: {
        types: DEFAULT_RESOURCE_TYPES,
        difficulty: 'normal',
        target: '',
      },
      reasoning: { level: 'balanced' as ReasoningLevel, showSummary: true },
    },
    openPanel: 'resource_config',
  },
  {
    id: 'deep_research',
    label: '深度研究',
    description: '多轮检索、分析和报告生成',
    mode: 'deep_research',
    requestPatch: {
      tools: {
        webSearch: true,
        deepResearch: true,
        homeworkReview: false,
        resourceGeneration: false,
        citationRequired: true,
      },
      reasoning: { level: 'deep' as ReasoningLevel, showSummary: true },
    },
    openPanel: 'research_plan',
  },
  {
    id: 'summarize_chapter',
    label: '总结本章',
    description: '按章节证据提炼概念、关系和易错点',
    mode: 'tutor',
    requiredContext: ['course', 'chapter'],
    requestPatch: {
      courseContext: { knowledgePointIds: [], useCourseRag: true },
      tools: {
        webSearch: false,
        deepResearch: false,
        homeworkReview: false,
        resourceGeneration: false,
        citationRequired: true,
      },
      reasoning: { level: 'balanced' as ReasoningLevel, showSummary: true },
    },
    openPanel: 'course_picker',
  },
  {
    id: 'explain_problem',
    label: '讲解这道题',
    description: '识别题目、拆解思路并给相似练习',
    mode: 'homework_review',
    requiredContext: ['attachment'],
    requestPatch: {
      tools: {
        webSearch: false,
        deepResearch: false,
        homeworkReview: true,
        resourceGeneration: false,
        citationRequired: true,
      },
      reasoning: { level: 'balanced' as ReasoningLevel, showSummary: true },
    },
    openPanel: 'upload',
  },
  {
    id: 'generate_outline',
    label: '生成提纲',
    description: '生成可入库的课程讲义提纲',
    mode: 'resource_generation',
    requestPatch: {
      tools: {
        webSearch: false,
        deepResearch: false,
        homeworkReview: false,
        resourceGeneration: true,
        citationRequired: true,
      },
      resourceRequest: {
        types: ['lecture_note'],
        difficulty: 'normal',
        target: '课程讲义提纲',
      },
      reasoning: { level: 'balanced' as ReasoningLevel, showSummary: true },
    },
    openPanel: 'resource_config',
  },
  {
    id: 'review_weak_points',
    label: '复习薄弱点',
    description: '结合画像和课程 RAG 生成复习路径',
    mode: 'tutor',
    requiredContext: ['course'],
    requestPatch: {
      courseContext: { knowledgePointIds: [], useCourseRag: true },
      tools: {
        webSearch: false,
        deepResearch: false,
        homeworkReview: false,
        resourceGeneration: false,
        citationRequired: true,
      },
      reasoning: { level: 'balanced' as ReasoningLevel, showSummary: true },
    },
  },
];

export function getTutorAction(actionId: string) {
  return TUTOR_ACTIONS.find((item) => item.id === actionId) || TUTOR_ACTIONS[0];
}
