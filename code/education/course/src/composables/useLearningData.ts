import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { Message } from '@arco-design/web-vue';
import {
  fetchLearningReport,
  generateMistakeDigest,
  generateReviewPlan,
  runLearningDiagnosis,
  type LearningReport,
  type MistakeDigest,
  type ProcessStep,
  type ReviewPlan,
} from '@/api/rag';
import { fetchLearningPath, type LearningPath } from '@/api/learning-path';
import type { RadarDimension } from '@/components/zy/PortraitRadarChart.vue';
import type { TimelineStep } from '@/components/zy/AiProcessTimeline.vue';

export function riskLabel(value: string) {
  if (value === 'high') return '高风险';
  if (value === 'low') return '低风险';
  return '中风险';
}

export function useLearningData() {
  const router = useRouter();
  const diagnosis = ref<LearningReport | null>(null);
  const reviewPlan = ref<ReviewPlan | null>(null);
  const mistakeDigest = ref<MistakeDigest | null>(null);
  const loadingDiagnosis = ref(false);
  const loadingPlan = ref(false);
  const loadingMistakes = ref(false);
  const loadingInitial = ref(false);
  const activeTab = ref('mistakes');
  const timelineSteps = ref<TimelineStep[]>([]);
  const isScanning = ref(false);
  const learningPath = ref<LearningPath | null>(null);

  const riskTone = computed(() => {
    if (!diagnosis.value) return 'neutral';
    if (diagnosis.value.risk_level === 'high') return 'high';
    if (diagnosis.value.risk_level === 'low') return 'low';
    return 'medium';
  });

  const masteryFocus = computed(() =>
    Object.entries(diagnosis.value?.mastery_map || {})
      .map(([topic, value]) => ({
        topic,
        percent: Math.round(Math.max(0, Math.min(1, Number(value) || 0)) * 100),
      }))
      .sort((a, b) => a.percent - b.percent)
      .slice(0, 5)
  );

  const avgMastery = computed(() => {
    if (!masteryFocus.value.length) return 0;
    return Math.round(
      masteryFocus.value.reduce((sum, item) => sum + item.percent, 0) /
        masteryFocus.value.length
    );
  });

  const radarDimensions = computed((): RadarDimension[] => {
    const summary = diagnosis.value?.classroom_behavior_summary;
    const cognitive =
      typeof summary?.cognitive_engagement === 'number'
        ? Math.round(summary.cognitive_engagement * 100)
        : typeof summary?.on_task_rate === 'number'
          ? Math.round(summary.on_task_rate * 100)
          : 0;
    const behavioral =
      typeof summary?.behavioral_engagement === 'number'
        ? Math.round(summary.behavioral_engagement * 100)
        : typeof summary?.recent_avg_lei === 'number'
          ? Math.round(summary.recent_avg_lei * 100)
          : 0;
    const riskScore =
      diagnosis.value?.risk_level === 'high'
        ? 35
        : diagnosis.value?.risk_level === 'low'
          ? 85
          : 60;
    const weakScore = diagnosis.value?.weak_points?.length
      ? Math.max(20, 100 - diagnosis.value.weak_points.length * 15)
      : 50;
    const mistakeScore = mistakeDigest.value?.mistakes?.length
      ? Math.max(25, 100 - mistakeDigest.value.mistakes.length * 12)
      : 60;

    return [
      { label: '知识基础', value: avgMastery.value || 0 },
      { label: '薄弱控制', value: weakScore },
      { label: '风险水平', value: riskScore },
      { label: '认知投入', value: cognitive },
      { label: '行为投入', value: behavioral },
      { label: '错题改善', value: mistakeScore },
    ];
  });

  const focusItems = computed(() => {
    const items = [
      ...(diagnosis.value?.weak_points || []),
      ...(reviewPlan.value?.focus_topics || []),
      ...(mistakeDigest.value?.mistakes?.map((item) => item.title) || []),
    ];
    return Array.from(new Set(items)).slice(0, 6);
  });

  const kpiTodos = computed(() => focusItems.value.length);

  const evidenceCards = computed(() => {
    const summary = diagnosis.value?.classroom_behavior_summary;
    return [
      {
        label: '课堂专注率',
        value:
          typeof summary?.on_task_rate === 'number'
            ? `${Math.round(summary.on_task_rate * 100)}%`
            : '—',
        link: '/course/monitor',
        linkText: '去课堂监控',
      },
      {
        label: '薄弱知识点',
        value: diagnosis.value?.weak_points?.[0] || '—',
        link: '/tutor',
        linkText: '去伴学追问',
      },
      {
        label: '下一步方向',
        value: diagnosis.value?.follow_up_questions?.[0] || '—',
        link: '/tutor',
        linkText: '继续学习',
      },
    ];
  });

  const behaviorCards = computed(() => {
    const summary = diagnosis.value?.classroom_behavior_summary;
    if (!summary) return [];
    const rows: Array<{ label: string; value: string }> = [];
    if (typeof summary.recent_avg_lei === 'number') {
      rows.push({
        label: '学习投入指数',
        value: `${Math.round(summary.recent_avg_lei * 100)}%`,
      });
    }
    if (typeof summary.on_task_rate === 'number') {
      rows.push({
        label: '专注率',
        value: `${Math.round(summary.on_task_rate * 100)}%`,
      });
    }
    if (typeof summary.mind_wandering_rate === 'number') {
      rows.push({
        label: '走神率',
        value: `${Math.round(summary.mind_wandering_rate * 100)}%`,
      });
    }
    return rows.slice(0, 3);
  });

  function mapProcessSteps(steps?: ProcessStep[]): TimelineStep[] {
    if (!steps?.length) return [];
    return steps.map((s) => ({
      key: s.key,
      label: s.label,
      message: s.message,
      status: (s.status as TimelineStep['status']) || 'done',
    }));
  }

  function startClientTimeline() {
    timelineSteps.value = [
      { key: 'profile', label: '读取学习画像', status: 'running', message: '加载画像数据…' },
      { key: 'behavior', label: '汇总课堂投入', status: 'idle' },
      { key: 'infer', label: '生成诊断结论', status: 'idle' },
    ];
    isScanning.value = true;
  }

  function advanceTimeline(stepIndex: number) {
    timelineSteps.value = timelineSteps.value.map((s, i) => {
      if (i < stepIndex) return { ...s, status: 'done' };
      if (i === stepIndex) return { ...s, status: 'running' };
      return { ...s, status: 'idle' };
    });
  }

  function jumpToResourceGeneration(topic: string) {
    router.push({
      path: '/course/resource-generation',
      query: {
        source: 'learning-data',
        topic,
        goal: diagnosis.value?.current_goal || '',
      },
    });
  }

  function jumpToAssistant(topic: string) {
    router.push({
      path: '/tutor',
      query: {
        source: 'learning-data',
        prompt: `我现在在"${topic}"这个知识点上比较薄弱，请先帮我讲清核心概念，再给我两道循序渐进的练习。`,
      },
    });
  }

  function jumpTo(path: string) {
    router.push(path);
  }

  async function loadLearningPath() {
    try {
      learningPath.value = await fetchLearningPath();
    } catch {
      learningPath.value = null;
    }
  }

  async function loadInitialDiagnosis() {
    loadingInitial.value = true;
    try {
      diagnosis.value = await fetchLearningReport(false);
      if (diagnosis.value?.process_steps?.length) {
        timelineSteps.value = mapProcessSteps(diagnosis.value.process_steps);
      }
      await loadLearningPath();
    } catch {
      // keep page interactive
    } finally {
      loadingInitial.value = false;
    }
  }

  async function handleRunDiagnosis() {
    loadingDiagnosis.value = true;
    startClientTimeline();
    const timer1 = window.setTimeout(() => advanceTimeline(1), 600);
    const timer2 = window.setTimeout(() => advanceTimeline(2), 1400);
    try {
      diagnosis.value = await runLearningDiagnosis(true);
      timelineSteps.value = mapProcessSteps(diagnosis.value.process_steps);
      if (!timelineSteps.value.length) {
        timelineSteps.value = [
          { key: 'profile', label: '读取学习画像', status: 'done' },
          { key: 'behavior', label: '汇总课堂投入', status: 'done' },
          { key: 'infer', label: '生成诊断结论', status: 'done', message: diagnosis.value.summary?.slice(0, 60) },
        ];
      }
      Message.success('学情诊断已更新');
      await loadLearningPath();
    } catch (error: any) {
      timelineSteps.value = timelineSteps.value.map((s) =>
        s.status === 'running' ? { ...s, status: 'error' } : s
      );
      Message.error(error?.message || '生成学情诊断失败');
    } finally {
      window.clearTimeout(timer1);
      window.clearTimeout(timer2);
      isScanning.value = false;
      loadingDiagnosis.value = false;
    }
  }

  async function handleGeneratePlan() {
    loadingPlan.value = true;
    try {
      reviewPlan.value = await generateReviewPlan(true);
      activeTab.value = 'plan';
      Message.success('复习计划已生成');
    } catch (error: any) {
      Message.error(error?.message || '生成复习计划失败');
    } finally {
      loadingPlan.value = false;
    }
  }

  async function handleGenerateMistakes() {
    loadingMistakes.value = true;
    try {
      mistakeDigest.value = await generateMistakeDigest(true);
      activeTab.value = 'mistakes';
      Message.success('错题复盘已完成');
    } catch (error: any) {
      Message.error(error?.message || '整理错题失败');
    } finally {
      loadingMistakes.value = false;
    }
  }

  return {
    diagnosis,
    reviewPlan,
    mistakeDigest,
    loadingDiagnosis,
    loadingPlan,
    loadingMistakes,
    loadingInitial,
    activeTab,
    timelineSteps,
    isScanning,
    riskTone,
    masteryFocus,
    avgMastery,
    radarDimensions,
    focusItems,
    kpiTodos,
    evidenceCards,
    behaviorCards,
    riskLabel,
    jumpToResourceGeneration,
    jumpToAssistant,
    jumpTo,
    learningPath,
    loadLearningPath,
    loadInitialDiagnosis,
    handleRunDiagnosis,
    handleGeneratePlan,
    handleGenerateMistakes,
  };
}
