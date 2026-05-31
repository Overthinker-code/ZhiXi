<template>
  <div class="container">
    <Breadcrumb :items="['menu.profile', 'menu.profile.learningData']" />
    <a-card class="card-block summary-banner">
      <div class="summary-banner__main">
        <div class="summary-banner__eyebrow">当前学习判断</div>
        <h2>{{ headlineSummary }}</h2>
        <p>{{ headlineDescription }}</p>
      </div>
      <div class="summary-banner__side">
        <div class="summary-banner__risk" :class="`summary-banner__risk--${riskTone}`">
          <span>风险等级</span>
          <strong>{{ diagnosis ? riskLabel(diagnosis.risk_level) : '待诊断' }}</strong>
        </div>
        <div class="summary-banner__actions">
          <a-button type="primary" :loading="loadingDiagnosis" @click="handleRunDiagnosis">
            更新最新诊断
          </a-button>
          <a-button status="warning" :loading="loadingPlan" @click="handleGeneratePlan">
            生成复习计划
          </a-button>
          <a-button status="success" :loading="loadingMistakes" @click="handleGenerateMistakes">
            错题复盘
          </a-button>
        </div>
      </div>
    </a-card>

    <a-row :gutter="16">
      <a-col :xs="24" :xl="8">
        <a-card title="学情档案" class="card-block">
          <div class="profile-row">
            <a-avatar :size="72">
              {{ displayName.slice(0, 1) }}
            </a-avatar>
            <div class="profile-meta">
              <div><strong>姓名</strong> {{ displayName }}</div>
              <div>
                <strong>当前目标</strong>
                {{ diagnosis?.current_goal || '继续提问或完成一轮练习后自动收敛' }}
              </div>
              <div>
                <strong>学习偏好</strong>
                {{ diagnosis?.learning_style || '系统将结合互动方式持续识别' }}
              </div>
            </div>
          </div>
          <a-divider />
          <div class="portrait-grid">
            <div v-for="item in portraitDimensions" :key="item.label" class="portrait-card">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
          <div v-if="masteryFocus.length" class="mastery-box">
            <div class="section-title">掌握度关注点</div>
            <div class="mastery-list">
              <div v-for="item in masteryFocus" :key="item.topic" class="mastery-row">
                <div class="mastery-head">
                  <span>{{ item.topic }}</span>
                  <span>{{ item.percent }}%</span>
                </div>
                <a-progress :percent="item.percent" size="small" :show-text="false" />
              </div>
            </div>
          </div>
        </a-card>

        <a-card title="本周优先处理" class="card-block">
          <template v-if="focusItems.length">
            <div class="focus-list">
              <div v-for="item in focusItems" :key="item" class="focus-item">
                <div class="focus-item__copy">
                  <strong>{{ item }}</strong>
                  <span>可以直接生成针对性资源，或回到伴学中心继续追问。</span>
                </div>
                <div class="focus-item__actions">
                  <a-button size="mini" type="outline" @click="jumpToAssistant(item)">
                    去伴学追问
                  </a-button>
                  <a-button size="mini" type="primary" @click="jumpToResourceGeneration(item)">
                    生成针对性资源
                  </a-button>
                </div>
              </div>
            </div>
          </template>
          <a-empty v-else description="完成一轮诊断或练习后，这里会自动汇总近期关注点" />
        </a-card>
      </a-col>

      <a-col :xs="24" :xl="16">
        <a-card class="card-block overview-card">
          <div class="overview-head">
            <div class="overview-copy">
              <div class="overview-eyebrow">诊断依据</div>
              <h3>本次结论不是静态标签，而是由近期问答、练习与课堂投入共同形成</h3>
              <p>
                诊断结果会结合最近的问答、练习表现和课堂投入摘要持续更新，用于推动后续资源推荐与学习路径调整。
              </p>
            </div>
            <div class="evidence-grid">
              <article v-for="item in evidenceCards" :key="item.label" class="evidence-card">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <small>{{ item.hint }}</small>
              </article>
            </div>
          </div>

          <a-spin :loading="loadingDiagnosis" style="width: 100%">
            <template v-if="diagnosis">
              <div class="report-summary">{{ diagnosis.summary }}</div>
              <div class="meta-line">
                <span class="meta-pill">{{ riskLabel(diagnosis.risk_level) }}</span>
                <span v-if="diagnosis.current_goal" class="meta-pill meta-pill--soft">
                  当前目标：{{ diagnosis.current_goal }}
                </span>
                <span
                  v-if="diagnosis.learning_style"
                  class="meta-pill meta-pill--soft"
                >
                  学习偏好：{{ diagnosis.learning_style }}
                </span>
              </div>
              <div v-if="diagnosis.weak_points.length" class="tag-row">
                <div v-for="item in diagnosis.weak_points" :key="item" class="topic-chip">
                  <span class="info-tag">{{ item }}</span>
                  <div class="topic-chip__actions">
                    <button type="button" @click="jumpToAssistant(item)">追问</button>
                    <button type="button" @click="jumpToResourceGeneration(item)">生成资源</button>
                  </div>
                </div>
              </div>
              <div class="dual-grid">
                <div class="insight-box">
                  <div class="box-title">优势表现</div>
                  <ul class="plain-list">
                    <li v-for="item in diagnosis.strengths" :key="item">{{ item }}</li>
                  </ul>
                </div>
                <div class="insight-box">
                  <div class="box-title">建议动作</div>
                  <ul class="plain-list">
                    <li v-for="item in diagnosis.recommended_actions" :key="item">
                      {{ item }}
                    </li>
                  </ul>
                </div>
              </div>
            </template>
            <a-empty v-else description="点击“更新诊断”生成最新学情结论" />
          </a-spin>
        </a-card>

        <a-card v-if="behaviorCards.length" title="课堂投入摘要" class="card-block">
          <a-row :gutter="12">
            <a-col v-for="item in behaviorCards" :key="item.label" :span="8">
              <div class="stat-box">
                <div class="stat-num">{{ item.value }}</div>
                <div class="stat-label">{{ item.label }}</div>
              </div>
            </a-col>
          </a-row>
          <div v-if="behaviorInsight" class="behavior-note">
            {{ behaviorInsight }}
          </div>
        </a-card>

        <a-row :gutter="16">
          <a-col :xs="24" :lg="12">
            <a-card title="错题复盘" class="card-block fill-card">
              <a-spin :loading="loadingMistakes" style="width: 100%">
                <template v-if="mistakeDigest">
                  <div class="report-summary">{{ mistakeDigest.summary }}</div>
                  <div class="mistake-list">
                    <div
                      v-for="item in mistakeDigest.mistakes"
                      :key="item.title"
                      class="mistake-card"
                    >
                      <div class="mistake-title">{{ item.title }}</div>
                      <div class="mistake-line">
                        <strong>常见表现：</strong>{{ item.symptom }}
                      </div>
                      <div class="mistake-line">
                        <strong>诊断依据：</strong>{{ item.evidence }}
                      </div>
                      <div class="mistake-line">
                        <strong>修正建议：</strong>{{ item.fix_strategy }}
                      </div>
                    </div>
                  </div>
                  <div v-if="mistakeDigest.flashcards.length" class="flashcard-box">
                    <div class="box-title">速记卡片</div>
                    <ul class="plain-list">
                      <li v-for="item in mistakeDigest.flashcards" :key="item">{{ item }}</li>
                    </ul>
                  </div>
                </template>
                <a-empty v-else description="完成一轮错题复盘后，这里会汇总典型失分点" />
              </a-spin>
            </a-card>
          </a-col>

          <a-col :xs="24" :lg="12">
            <a-card title="三天复习计划" class="card-block fill-card">
              <a-spin :loading="loadingPlan" style="width: 100%">
                <template v-if="reviewPlan">
                  <div class="report-summary">{{ reviewPlan.summary }}</div>
                  <div v-if="reviewPlan.focus_topics.length" class="tag-row">
                    <span
                      v-for="item in reviewPlan.focus_topics"
                      :key="item"
                      class="info-tag info-tag--warm"
                    >
                      {{ item }}
                    </span>
                  </div>
                  <div class="plan-grid">
                    <div
                      v-for="item in reviewPlan.daily_plan"
                      :key="item.day_label"
                      class="plan-card"
                    >
                      <div class="plan-day">{{ item.day_label }}</div>
                      <div class="plan-focus">{{ item.focus }}</div>
                      <ul class="plain-list">
                        <li v-for="task in item.tasks" :key="task">{{ task }}</li>
                      </ul>
                    </div>
                  </div>
                  <div v-if="reviewPlan.checkpoints.length" class="flashcard-box">
                    <div class="box-title">检查点</div>
                    <ul class="plain-list">
                      <li v-for="item in reviewPlan.checkpoints" :key="item">{{ item }}</li>
                    </ul>
                  </div>
                </template>
                <a-empty v-else description="生成复习计划后，这里会给出接下来三天的学习安排" />
              </a-spin>
            </a-card>
          </a-col>
        </a-row>
      </a-col>
    </a-row>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { Message } from '@arco-design/web-vue';
  import { useUserStore } from '@/store';
  import {
    fetchLearningReport,
    generateMistakeDigest,
    generateReviewPlan,
    runLearningDiagnosis,
    type LearningReport,
    type MistakeDigest,
    type ReviewPlan,
  } from '@/api/rag';

  const userStore = useUserStore();
  const router = useRouter();
  const displayName = computed(() => userStore.name || '同学');

  const diagnosis = ref<LearningReport | null>(null);
  const reviewPlan = ref<ReviewPlan | null>(null);
  const mistakeDigest = ref<MistakeDigest | null>(null);
  const loadingDiagnosis = ref(false);
  const loadingPlan = ref(false);
  const loadingMistakes = ref(false);

  const riskLabel = (value: string) => {
    if (value === 'high') return '高风险';
    if (value === 'low') return '低风险';
    return '中风险';
  };

  const riskTone = computed(() => {
    if (!diagnosis.value) return 'neutral';
    if (diagnosis.value.risk_level === 'high') return 'high';
    if (diagnosis.value.risk_level === 'low') return 'low';
    return 'medium';
  });

  const headlineSummary = computed(() => {
    if (!diagnosis.value) return '先生成一次学情诊断，再决定下一步该补什么';
    const weakPoint = diagnosis.value.weak_points?.[0] || '当前薄弱点';
    return `当前处于${riskLabel(diagnosis.value.risk_level)}阶段，优先处理 ${weakPoint}`;
  });

  const headlineDescription = computed(() => {
    if (!diagnosis.value) {
      return '诊断完成后，这里会把当前状态、课堂投入和建议动作汇总成一句清晰结论。';
    }
    return diagnosis.value.summary;
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

  const portraitDimensions = computed(() => {
    const masteryAvg = masteryFocus.value.length
      ? `${Math.round(
          masteryFocus.value.reduce((sum, item) => sum + item.percent, 0) /
            masteryFocus.value.length
        )}%`
      : '诊断后更新';
    return [
      { label: '知识基础', value: masteryAvg },
      { label: '薄弱点', value: diagnosis.value?.weak_points?.[0] || '待识别' },
      {
        label: '风险等级',
        value: diagnosis.value ? riskLabel(diagnosis.value.risk_level) : '待评估',
      },
      {
        label: '认知投入',
        value:
          typeof diagnosis.value?.classroom_behavior_summary?.cognitive_engagement === 'number'
            ? `${Math.round(
                diagnosis.value.classroom_behavior_summary.cognitive_engagement * 100
              )}%`
            : '待课堂数据接入',
      },
      {
        label: '易错偏好',
        value: mistakeDigest.value?.mistakes?.[0]?.title || '待从错题复盘更新',
      },
      {
        label: '下一步动作',
        value:
          diagnosis.value?.recommended_actions?.[0] ||
          reviewPlan.value?.daily_plan?.[0]?.focus ||
          '先完成一轮诊断或练习',
      },
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

  const evidenceCards = computed(() => {
    const summary = diagnosis.value?.classroom_behavior_summary;
    const latestMistake = mistakeDigest.value?.mistakes?.[0];
    return [
      {
        label: '课堂专注率',
        value:
          typeof summary?.on_task_rate === 'number'
            ? `${Math.round(summary.on_task_rate * 100)}%`
            : '待课堂数据接入',
        hint: typeof summary?.mind_wandering_rate === 'number'
          ? `走神率 ${Math.round(summary.mind_wandering_rate * 100)}%`
          : '课堂投入会自动纳入诊断参考',
      },
      {
        label: '最近一次薄弱点',
        value: diagnosis.value?.weak_points?.[0] || '待诊断',
        hint: latestMistake?.title || '完成错题复盘后会同步更新',
      },
      {
        label: '下一步追问方向',
        value: diagnosis.value?.follow_up_questions?.[0] || '完成一轮诊断后生成',
        hint: '可直接跳到伴学中心继续追问',
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

  const behaviorInsight = computed(() => {
    const summary = diagnosis.value?.classroom_behavior_summary;
    if (!summary) return '';
    if (typeof summary.recent_avg_lei === 'number' && summary.recent_avg_lei < 0.5) {
      return '近期课堂投入偏低，建议先从短时复盘和分步练习开始，降低重新进入状态的门槛。';
    }
    if (typeof summary.on_task_rate === 'number' && summary.on_task_rate >= 0.75) {
      return '近期课堂专注度较稳定，适合在当前节奏上增加一轮针对薄弱点的强化练习。';
    }
    return '课堂投入会作为诊断参考，与问答和练习结果一起更新学习建议。';
  });

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
      path: '/assistant/chat',
      query: {
        source: 'learning-data',
        prompt: `我现在在“${topic}”这个知识点上比较薄弱，请先帮我讲清核心概念，再给我两道循序渐进的练习。`,
      },
    });
  }

  async function loadInitialDiagnosis() {
    try {
      diagnosis.value = await fetchLearningReport(false);
    } catch {
      // keep page interactive even when backend response is temporarily unavailable
    }
  }

  async function handleRunDiagnosis() {
    loadingDiagnosis.value = true;
    try {
      diagnosis.value = await runLearningDiagnosis(true);
      Message.success('已生成最新学情诊断');
    } catch (error: any) {
      Message.error(error?.message || '生成学情诊断失败');
    } finally {
      loadingDiagnosis.value = false;
    }
  }

  async function handleGeneratePlan() {
    loadingPlan.value = true;
    try {
      reviewPlan.value = await generateReviewPlan(true);
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
      Message.success('错题复盘已完成');
    } catch (error: any) {
      Message.error(error?.message || '整理错题失败');
    } finally {
      loadingMistakes.value = false;
    }
  }

  onMounted(() => {
    void loadInitialDiagnosis();
  });
</script>

<style scoped lang="less">
  .container {
    padding: 0 20px 24px;
  }

  .card-block {
    margin-bottom: 16px;
    border-radius: 14px;
  }

  .summary-banner {
    display: grid;
    grid-template-columns: minmax(0, 1.7fr) minmax(280px, 0.9fr);
    gap: 18px;
    align-items: stretch;
    background:
      radial-gradient(circle at left top, rgba(59, 92, 204, 0.14), transparent 34%),
      linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  }

  .summary-banner__main h2 {
    margin: 6px 0 10px;
    color: #0f172a;
    font-size: 28px;
    line-height: 1.35;
  }

  .summary-banner__main p {
    margin: 0;
    color: #475569;
    line-height: 1.8;
  }

  .summary-banner__eyebrow {
    color: #3b5ccc;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .summary-banner__side {
    display: grid;
    gap: 14px;
    align-content: start;
  }

  .summary-banner__risk {
    padding: 16px 18px;
    border-radius: 14px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: rgba(255, 255, 255, 0.86);
  }

  .summary-banner__risk span,
  .summary-banner__risk strong {
    display: block;
  }

  .summary-banner__risk span {
    color: #64748b;
    font-size: 12px;
  }

  .summary-banner__risk strong {
    margin-top: 8px;
    font-size: 24px;
    line-height: 1.2;
  }

  .summary-banner__risk--high strong {
    color: #dc2626;
  }

  .summary-banner__risk--medium strong {
    color: #d97706;
  }

  .summary-banner__risk--low strong {
    color: #16a34a;
  }

  .summary-banner__risk--neutral strong {
    color: #3b5ccc;
  }

  .summary-banner__actions {
    display: grid;
    gap: 10px;
  }

  .profile-row {
    display: flex;
    gap: 16px;
    align-items: center;
  }

  .profile-meta {
    line-height: 1.9;
    font-size: 14px;
  }

  .portrait-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .portrait-card {
    min-height: 82px;
    padding: 12px;
    background: linear-gradient(180deg, #f8fbff, #fff);
    border: 1px solid rgba(37, 99, 235, 0.12);
    border-radius: 12px;

    span,
    strong {
      display: block;
    }

    span {
      color: #64748b;
      font-size: 12px;
    }

    strong {
      margin-top: 10px;
      color: #0f172a;
      line-height: 1.6;
    }
  }

  .section-title,
  .box-title {
    margin-bottom: 8px;
    font-weight: 600;
  }

  .mastery-box {
    margin-top: 18px;
    padding: 14px;
    background: #fbfdff;
    border: 1px solid rgba(37, 99, 235, 0.1);
    border-radius: 12px;
  }

  .mastery-list {
    display: grid;
    gap: 10px;
  }

  .mastery-row {
    display: grid;
    gap: 6px;
  }

  .mastery-head {
    display: flex;
    justify-content: space-between;
    color: #334155;
    font-size: 13px;
  }

  .focus-list {
    display: grid;
    gap: 10px;
  }

  .focus-item {
    padding: 12px 14px;
    border: 1px solid rgba(37, 99, 235, 0.12);
    border-radius: 12px;
    background: linear-gradient(180deg, #f8fbff, #fff);
  }

  .focus-item__copy {
    display: grid;
    gap: 4px;
    color: #334155;
  }

  .focus-item__copy strong {
    color: #0f172a;
  }

  .focus-item__copy span {
    font-size: 13px;
    line-height: 1.7;
    color: #64748b;
  }

  .focus-item__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
  }

  .overview-card {
    background:
      radial-gradient(circle at top left, rgba(99, 102, 241, 0.12), transparent 38%),
      linear-gradient(180deg, #f8fbff, #fff);
  }

  .overview-head {
    display: flex;
    gap: 16px;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
  }

  .overview-copy {
    max-width: 620px;
  }

  .evidence-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    min-width: min(100%, 380px);
    flex: 1;
  }

  .evidence-card {
    min-height: 120px;
    padding: 14px;
    background: rgba(255, 255, 255, 0.82);
    border: 1px solid rgba(59, 92, 204, 0.1);
    border-radius: 12px;
    display: grid;
    align-content: start;
    gap: 8px;
  }

  .evidence-card span,
  .evidence-card strong,
  .evidence-card small {
    display: block;
  }

  .evidence-card span {
    color: #64748b;
    font-size: 12px;
  }

  .evidence-card strong {
    color: #0f172a;
    font-size: 18px;
    line-height: 1.45;
  }

  .evidence-card small {
    color: #64748b;
    line-height: 1.6;
  }

  .overview-eyebrow {
    margin-bottom: 10px;
    color: #2563eb;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.04em;
  }

  .overview-copy h3 {
    margin: 0 0 6px;
    color: #0f172a;
    font-size: 22px;
    line-height: 1.45;
  }

  .overview-copy p {
    margin: 0;
    color: #64748b;
    line-height: 1.75;
  }

  .action-row {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    justify-content: flex-end;
  }

  .report-summary {
    margin-bottom: 16px;
    color: #0f172a;
    font-size: 15px;
    line-height: 1.8;
  }

  .meta-line {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 14px;
  }

  .meta-pill {
    display: inline-flex;
    align-items: center;
    padding: 6px 12px;
    color: #1d4ed8;
    font-size: 12px;
    font-weight: 600;
    background: rgba(59, 130, 246, 0.1);
    border-radius: 999px;
  }

  .meta-pill--soft {
    color: #475569;
    background: #eef2ff;
  }

  .tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 16px;
  }

  .info-tag {
    padding: 7px 12px;
    color: #4338ca;
    font-size: 12px;
    font-weight: 600;
    background: rgba(99, 102, 241, 0.12);
    border-radius: 999px;
  }

  .info-tag--warm {
    color: #b45309;
    background: rgba(245, 158, 11, 0.14);
  }

  .topic-chip {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    padding: 6px 8px 6px 6px;
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: 999px;
  }

  .topic-chip__actions {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .topic-chip__actions button {
    border: none;
    border-radius: 999px;
    padding: 5px 10px;
    background: rgba(59, 92, 204, 0.08);
    color: #3b5ccc;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s ease, color 0.2s ease;
  }

  .topic-chip__actions button:hover {
    background: rgba(59, 92, 204, 0.14);
    color: #2646ab;
  }

  .dual-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .insight-box {
    padding: 14px 16px;
    background: rgba(255, 255, 255, 0.76);
    border: 1px solid rgba(37, 99, 235, 0.1);
    border-radius: 12px;
  }

  .plain-list {
    margin: 0;
    padding-left: 1.2em;
    color: #475569;
    line-height: 1.8;
  }

  .stat-box {
    padding: 14px 8px;
    border: 1px solid rgba(37, 99, 235, 0.12);
    border-radius: 12px;
    background: linear-gradient(180deg, #eff6ff, #fff);
    text-align: center;
  }

  .stat-num {
    color: #2563eb;
    font-size: 22px;
    font-weight: 700;
  }

  .stat-label {
    margin-top: 6px;
    color: #64748b;
    font-size: 13px;
  }

  .behavior-note {
    margin-top: 14px;
    color: #475569;
    line-height: 1.8;
  }

  .fill-card {
    height: 100%;
  }

  .mistake-list,
  .plan-grid {
    display: grid;
    gap: 12px;
  }

  .mistake-card,
  .plan-card,
  .flashcard-box {
    padding: 14px 16px;
    background: #fbfdff;
    border: 1px solid rgba(37, 99, 235, 0.1);
    border-radius: 12px;
  }

  .mistake-title,
  .plan-day {
    margin-bottom: 8px;
    color: #0f172a;
    font-weight: 600;
  }

  .mistake-line {
    color: #475569;
    line-height: 1.75;
  }

  .plan-focus {
    margin-bottom: 8px;
    color: #334155;
    font-weight: 500;
  }

  @media (max-width: 1200px) {
    .summary-banner {
      grid-template-columns: 1fr;
    }

    .overview-head {
      flex-direction: column;
    }

    .evidence-grid {
      width: 100%;
      grid-template-columns: 1fr;
    }

    .action-row {
      justify-content: flex-start;
    }
  }

  @media (max-width: 768px) {
    .container {
      padding: 0 12px 20px;
    }

    .portrait-grid,
    .dual-grid {
      grid-template-columns: 1fr;
    }

    .overview-copy h3 {
      font-size: 19px;
    }
  }
</style>
