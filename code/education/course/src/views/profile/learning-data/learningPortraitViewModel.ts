import type { Course } from '@/api/course';
import type { LearningPath } from '@/api/learning-path';
import type { PortraitAnalytics } from '@/api/learning-portrait';
import type { LearningReport } from '@/api/rag';
import type { PracticeSummary } from '@/api/student-hub';

export interface PortraitDimension {
  key: string;
  label: string;
  value: number;
  previous: number | null;
  evidenceCount: number;
}

export interface PortraitDimensionStatus {
  key: string;
  label: string;
  stateLabel: string;
  tone: 'neutral' | 'success' | 'warning';
}

export interface PortraitTrendSeries {
  key: string;
  label: string;
  color: string;
  values: Array<number | null>;
}

export interface ResourcePreference {
  key: string;
  label: string;
  value: number | null;
  color: string;
  reason: string;
}

export interface CoursePortraitRow {
  id: string;
  name: string;
  score: number | null;
  trend: number | null;
  focus: string;
  isSample: boolean;
}

export interface PortraitRecommendation {
  tone: 'primary' | 'success' | 'warning';
  title: string;
  description: string;
  topic: string;
  evidence: string;
}

export interface LearningPortraitViewModel {
  previewMode: boolean;
  overallScore: number | null;
  growthRate: number | null;
  engagement: number | null;
  attentionCount: number;
  confidence: number;
  evidenceCount: number;
  updatedAt: string;
  trendLabels: string[];
  trendSeries: PortraitTrendSeries[];
  trendEstimated: boolean;
  dimensions: PortraitDimension[];
  dimensionStatuses: PortraitDimensionStatus[];
  rhythm: number[][];
  focusCurve: number[];
  resourcePreferences: ResourcePreference[];
  resourceInferenceLabel: string;
  courses: CoursePortraitRow[];
  recommendations: PortraitRecommendation[];
}

interface BuildPortraitOptions {
  diagnosis: LearningReport | null;
  practice: PracticeSummary | null;
  courses: Course[];
  learningPath: LearningPath | null;
  analytics?: PortraitAnalytics | null;
  sampleCourses?: Array<{ id: string; title: string; progress: number }>;
}

const clamp = (value: number, min = 0, max = 100) =>
  Math.round(Math.max(min, Math.min(max, Number(value) || 0)));

const asPercent = (value: unknown) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return clamp(number <= 1 ? number * 100 : number);
};

const average = (values: number[]) => {
  if (!values.length) return null;
  return clamp(values.reduce((sum, value) => sum + value, 0) / values.length);
};

const roundTo = (value: unknown, precision = 1): number | null => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  const factor = 10 ** precision;
  return Math.round(number * factor) / factor;
};

function buildDimensions(diagnosis: LearningReport | null): PortraitDimension[] {
  return (diagnosis?.portrait_dimensions || [])
    .map((item) => ({
      key: item.key,
      label: item.label,
      value: asPercent(item.value),
      previous: null,
      evidenceCount: Math.max(0, Number(item.sample_size) || 0),
    }))
    .filter(
      (item): item is typeof item & { value: number } =>
        item.value !== null && item.evidenceCount > 0
    );
}

function buildDimensionStatuses(
  diagnosis: LearningReport | null
): PortraitDimensionStatus[] {
  return (diagnosis?.portrait_dimensions || []).map((item) => {
    if (item.state === 'strong' || item.state === 'steady') {
      return {
        key: item.key,
        label: item.label,
        stateLabel: item.state === 'strong' ? '表现稳定' : '稳定推进',
        tone: 'success' as const,
      };
    }
    if (item.state === 'needs_attention') {
      return {
        key: item.key,
        label: item.label,
        stateLabel: '建议补强',
        tone: 'warning' as const,
      };
    }
    return {
      key: item.key,
      label: item.label,
      stateLabel: '待积累',
      tone: 'neutral' as const,
    };
  });
}

function buildResourcePreferences(diagnosis: LearningReport | null): ResourcePreference[] {
  const styleText = [
    diagnosis?.learning_style || '',
    ...(diagnosis?.recommended_resources || []),
  ]
    .join(' ')
    .toLowerCase();
  if (!styleText.trim()) return [];
  const catalog = [
    { key: 'document', label: '图文讲义', pattern: /图|文档|讲义|阅读|visual|text/, color: '#6366f1', reason: '推荐方向' },
    { key: 'video', label: '视频动画', pattern: /视频|动画|演示|video/, color: '#3b82f6', reason: '推荐方向' },
    { key: 'quiz', label: '测验练习', pattern: /题|练习|quiz|测试/, color: '#06b6d4', reason: '推荐方向' },
    { key: 'case', label: '实操案例', pattern: /案例|实操|项目|实践|case|project/, color: '#f59e0b', reason: '推荐方向' },
  ];
  return catalog
    .filter((item) => item.pattern.test(styleText))
    .map(({ pattern: _pattern, ...item }) => ({ ...item, value: null }));
}

function buildMasterySnapshot(diagnosis: LearningReport | null) {
  const entries = Object.entries(diagnosis?.mastery_map || {})
    .map(([label, value]) => ({ label: label.trim(), value: asPercent(value) }))
    .filter(
      (item): item is { label: string; value: number } =>
        Boolean(item.label) && item.value !== null
    )
    .slice(0, 8);
  if (entries.length < 2) {
    return { labels: [] as string[], series: [] as PortraitTrendSeries[] };
  }
  return {
    labels: entries.map((item) => item.label),
    series: [
      {
        key: 'mastery_snapshot',
        label: '当前掌握度',
        color: '#6366f1',
        values: entries.map((item) => item.value),
      },
    ] as PortraitTrendSeries[],
  };
}

function buildCourses(
  courses: Course[],
  practice: PracticeSummary | null,
  sampleCourses: BuildPortraitOptions['sampleCourses']
): CoursePortraitRow[] {
  const realRows = courses.slice(0, 4).map((course) => {
    const matched = practice?.topics?.filter((topic) =>
      [topic.subject, topic.topic].some((text) =>
        `${text || ''}`.includes(course.name) || course.name.includes(`${text || ''}`)
      )
    );
    const scores = (matched || [])
      .map((topic) => asPercent(topic.avg_score))
      .filter((value): value is number => value !== null);
    const score = average(scores);
    return {
      id: course.id,
      name: course.name,
      score,
      trend: null,
      focus: matched?.[0]?.topic || '完成一次学习任务后生成',
      isSample: false,
    };
  });
  if (realRows.length) return realRows;
  return (sampleCourses || []).slice(0, 4).map((course) => ({
    id: course.id,
    name: course.title,
    score: course.progress,
    trend: null,
    focus: '前端预览课程',
    isSample: true,
  }));
}

function buildRecommendations(
  diagnosis: LearningReport | null,
  dimensions: PortraitDimension[],
  learningPath: LearningPath | null
): PortraitRecommendation[] {
  const items: PortraitRecommendation[] = [];
  const weakTopic =
    diagnosis?.weak_points?.[0] ||
    learningPath?.nodes?.find((node) => node.status !== 'done')?.topic;
  const action = diagnosis?.recommended_actions?.[0];
  if (weakTopic || action) {
    items.push({
      tone: 'warning',
      title: `优先学习：${weakTopic || '当前学习目标'}`,
      description: action || '按当前学习路径完成下一项任务。',
      topic: weakTopic || diagnosis?.current_goal || '当前学习目标',
      evidence: diagnosis ? '来自当前学习诊断' : '来自当前学习路径',
    });
  }
  const strength = diagnosis?.strengths?.[0];
  if (strength) {
    items.push({
      tone: 'success',
      title: '保持当前优势',
      description: strength,
      topic: diagnosis?.current_goal || strength,
      evidence: '来自当前学习诊断',
    });
  }
  const pathNode = learningPath?.nodes?.find((node) => node.status !== 'done');
  const pathTopic = pathNode?.topic?.trim();
  if (pathTopic) {
    items.push({
      tone: 'primary',
      title: `接着学习：${pathTopic}`,
      description: '继续完成学习计划中的下一项任务。',
      topic: pathTopic,
      evidence: '来自已生成的学习路径',
    });
  }
  return items;
}

export function buildLearningPortraitViewModel({
  diagnosis,
  practice,
  courses,
  learningPath,
  analytics,
  sampleCourses,
}: BuildPortraitOptions): LearningPortraitViewModel {
  const practiceHasEvidence = Boolean(
    (practice?.total_questions || 0) > 0 || (practice?.total_sessions || 0) > 0
  );
  const previewMode = !diagnosis && !practiceHasEvidence;
  const dimensions = buildDimensions(diagnosis);
  const dimensionStatuses = buildDimensionStatuses(diagnosis);
  const populatedValues = dimensions.filter((item) => item.evidenceCount > 0).map((item) => item.value);
  const overallScore = previewMode ? null : average(populatedValues);
  const engagementDimension = dimensions.find((item) => item.key === 'learning_engagement');
  const engagement = engagementDimension?.evidenceCount ? engagementDimension.value : null;
  const evidenceCount = Math.max(0, practice?.total_questions || 0) + Object.keys(diagnosis?.mastery_map || {}).length;
  // 后端暂未返回跨周期画像序列。这里仅把服务端已有 mastery_map
  // 画成“当前知识点分布”，不伪装成 12 周成长历史。
  const masterySnapshot = buildMasterySnapshot(diagnosis);
  const resourcePreferences = buildResourcePreferences(diagnosis);
  if (analytics) {
    const colors: Record<string, string> = {
      knowledge_understanding: '#6255e7',
      problem_solving: '#3478f6',
      practice_transfer: '#2bb8d6',
      self_regulation: '#f59e42',
      document: '#6255e7',
      video: '#3478f6',
      quiz: '#2bb8d6',
      case: '#f5a64a',
    };
    const analyticsDimensions = analytics.capabilities
      .filter((item) => item.value !== null)
      .map((item) => ({
        key: item.key,
        label: item.label,
        value: clamp(item.value || 0),
        previous: item.previous === null ? null : clamp(item.previous),
        evidenceCount: item.evidence_count,
      }));
    const measuredCourses = analytics.courses.map((course) => ({
      id: course.id,
      name: course.name,
      score: course.score,
      trend: course.trend,
      focus: course.focus,
      isSample: false,
    }));
    const measuredCourseIds = new Set(measuredCourses.map((course) => course.id));
    const supplementalCourses = buildCourses(courses, practice, [])
      .filter((course) => !measuredCourseIds.has(course.id))
      .map((course) => ({
        ...course,
        score: null,
        trend: null,
        focus: '完成练习后为你分析',
      }));
    const trendLabels = analytics.trend_labels
      .map((label) => `${label || ''}`.trim())
      .filter(Boolean);
    return {
      previewMode: !diagnosis && analytics.evidence_count === 0,
      overallScore: analytics.overall_score,
      growthRate: analytics.growth_30d,
      engagement: analytics.engagement,
      attentionCount: analytics.attention_count,
      confidence: analytics.confidence || 0,
      evidenceCount: analytics.evidence_count,
      updatedAt: analytics.generated_at,
      trendLabels,
      trendSeries: analytics.trend_series.map((item) => ({
        key: item.key,
        label: item.label,
        color: colors[item.key] || '#6255e7',
        values: Array.from({ length: trendLabels.length }, (_, index) =>
          roundTo(item.values[index], 1)
        ),
      })),
      trendEstimated: false,
      dimensions: analyticsDimensions,
      dimensionStatuses: analytics.capabilities.map((item) => ({
        key: item.key,
        label: item.label,
        stateLabel:
          item.value === null
            ? '待积累'
            : item.value >= 80
              ? '表现稳定'
              : item.value >= 65
                ? '稳定推进'
                : '建议补强',
        tone:
          item.value === null
            ? 'neutral'
            : item.value >= 65
              ? 'success'
              : 'warning',
      })),
      rhythm: analytics.rhythm.activity.map((row) =>
        row.map((value) => Math.max(0, roundTo(value, 1) ?? 0))
      ),
      focusCurve: analytics.rhythm.focus_hours.map((value) =>
        Math.max(0, roundTo(value, 1) ?? 0)
      ),
      resourcePreferences: analytics.resource_preferences.map((item) => ({
        key: item.key,
        label: item.label,
        value: roundTo(item.value, 1),
        color: colors[item.key] || '#94a3b8',
        reason: `${item.count} 次真实记录`,
      })),
      resourceInferenceLabel: analytics.resource_preferences.length
        ? '根据实际生成与上传的资源记录统计'
        : '等待生成或上传资源后生成',
      courses: measuredCourses.length
        ? [...measuredCourses, ...supplementalCourses].slice(0, 4)
        : buildCourses(courses, practice, sampleCourses),
      recommendations: buildRecommendations(diagnosis, analyticsDimensions, learningPath),
    };
  }

  return {
    previewMode,
    overallScore,
    growthRate: null,
    engagement,
    attentionCount: diagnosis?.weak_points?.length || 0,
    confidence: 0,
    evidenceCount,
    updatedAt: diagnosis?.generated_at || '',
    trendLabels: masterySnapshot.labels,
    trendSeries: masterySnapshot.series,
    trendEstimated: masterySnapshot.series.length > 0,
    dimensions,
    dimensionStatuses,
    rhythm: [],
    focusCurve: [],
    resourcePreferences,
    resourceInferenceLabel: diagnosis
      ? '来自画像文本的推荐资源类型，不展示伪精确占比'
      : '等待生成或上传学习资源后整理',
    courses: buildCourses(courses, practice, sampleCourses),
    recommendations: buildRecommendations(diagnosis, dimensions, learningPath),
  };
}
