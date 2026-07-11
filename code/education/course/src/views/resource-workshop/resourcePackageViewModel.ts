import type {
  GeneratedResourceArtifact,
  ResourceGenerationResponse,
  ResourceKind,
} from '@/api/resource-generation';

export type ResourceDifficulty =
  | 'auto'
  | 'foundation'
  | 'standard'
  | 'challenge';

export type ResourceItemType =
  | 'lecture_doc'
  | 'mind_map'
  | 'practice_set'
  | 'reading'
  | 'case_project'
  | 'video_script'
  | 'reflection';

export interface ResourceItem {
  title: string;
  type: ResourceItemType;
  estimated_minutes: number;
  difficulty: Exclude<ResourceDifficulty, 'auto'>;
  description: string;
  mastery_target: string;
  content_preview: string;
}

export interface ResourcePackageViewModel {
  package_id: string;
  subject: string;
  topic: string;
  goal: string;
  personalization_basis: string[];
  resources: ResourceItem[];
  agent_steps: Array<{
    agent: string;
    label: string;
    message: string;
    status: 'done';
  }>;
}

interface ResourcePackageViewModelOptions {
  goal: string;
  difficulty: Exclude<ResourceDifficulty, 'auto'>;
  targetMinutes: number;
  personalizationBasis: string[];
}

interface ResourceDefinition {
  type: ResourceItemType;
  kinds: ResourceKind[];
  description: string;
}

const RESOURCE_DEFINITIONS: ResourceDefinition[] = [
  {
    type: 'lecture_doc',
    kinds: ['lecture_markdown', 'lecture_pdf'],
    description: '围绕学习目标梳理概念、证据、例题与迁移方法。',
  },
  {
    type: 'mind_map',
    kinds: ['mind_map'],
    description: '呈现知识点、先修关系与后续学习路径。',
  },
  {
    type: 'practice_set',
    kinds: ['practice_markdown', 'practice_pdf'],
    description: '包含分层练习、答案框架、评分点与错因追练。',
  },
  {
    type: 'reading',
    kinds: ['reading_list'],
    description: '整理可核验的课程资料与拓展阅读顺序。',
  },
  {
    type: 'case_project',
    kinds: ['case_project'],
    description: '提供任务背景、操作步骤、提交物和验收标准。',
  },
  {
    type: 'video_script',
    kinds: ['video_script'],
    description: '生成可用于讲解视频或数字人的分段教学脚本。',
  },
];

const TRACE_GROUPS = [
  {
    agent: 'context',
    label: '画像与课程分析',
    pattern: /ProfileAgent|DomainAgent|EvidenceAgent/,
  },
  {
    agent: 'content',
    label: '核心内容生成',
    pattern: /ResourcePlannerAgent|ContentAgent|LectureAgent|ExerciseAgent/,
  },
  {
    agent: 'multimodal',
    label: '多模态资源组装',
    pattern: /MindMapAgent|ReadingAgent|CaseAgent|ScriptAgent/,
  },
  {
    agent: 'quality',
    label: '质量与安全审查',
    pattern: /QualityAgent|SafetyReviewAgent/,
  },
  {
    agent: 'finalize',
    label: '资源包归档',
    pattern: /FinalizerAgent/,
  },
] as const;

function findPreferredArtifact(
  artifacts: GeneratedResourceArtifact[],
  kinds: ResourceKind[]
) {
  for (const kind of kinds) {
    const artifact = artifacts.find((item) => item.kind === kind);
    if (artifact) return artifact;
  }
  return null;
}

function traceMessage(trace: string) {
  const separator = trace.indexOf(':');
  return separator >= 0 ? trace.slice(separator + 1).trim() : trace.trim();
}

function buildAgentSteps(trace: string[]) {
  return TRACE_GROUPS.flatMap((group) => {
    const messages = trace.filter((item) => group.pattern.test(item)).map(traceMessage);
    if (!messages.length) return [];
    return [
      {
        agent: group.agent,
        label: group.label,
        message: messages.join('；'),
        status: 'done' as const,
      },
    ];
  });
}

export function buildResourcePackageViewModel(
  pkg: ResourceGenerationResponse,
  options: ResourcePackageViewModelOptions
): ResourcePackageViewModel {
  const selected = RESOURCE_DEFINITIONS.map((definition) => ({
    definition,
    artifact: findPreferredArtifact(pkg.artifacts, definition.kinds),
  })).filter(
    (
      item
    ): item is {
      definition: ResourceDefinition;
      artifact: GeneratedResourceArtifact;
    } => Boolean(item.artifact)
  );
  const estimatedMinutes = Math.max(
    5,
    Math.round(options.targetMinutes / Math.max(selected.length, 1))
  );
  const personalizationBasis = Array.from(
    new Set(options.personalizationBasis.map((item) => item.trim()).filter(Boolean))
  );

  return {
    package_id: pkg.package_id,
    subject: pkg.subject,
    topic: pkg.topic,
    goal: options.goal,
    personalization_basis: personalizationBasis,
    resources: selected.map(({ definition, artifact }) => ({
      title: artifact.title,
      type: definition.type,
      estimated_minutes: estimatedMinutes,
      difficulty: options.difficulty,
      description: definition.description,
      mastery_target: options.goal,
      content_preview: artifact.preview || '该文件已生成，可在上方文件区预览或下载。',
    })),
    agent_steps: buildAgentSteps(pkg.agent_trace),
  };
}
