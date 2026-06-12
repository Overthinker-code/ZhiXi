<template>
  <ZyPageShell title="学情档案" subtitle="基于课堂行为、练习与对话的多维学习诊断">
    <ZyPageEnter>
      <div class="zy-stagger-child kpi-bar">
        <div class="kpi-item" :class="`kpi-item--${riskTone}`">
          <span class="kpi-label">风险等级</span>
          <strong class="kpi-value">
            {{ diagnosis ? riskLabel(diagnosis.risk_level) : '—' }}
          </strong>
        </div>
        <div class="kpi-item">
          <span class="kpi-label">平均掌握度</span>
          <strong class="kpi-value">
            <MetricCountUp v-if="avgMastery" :value="avgMastery" suffix="%" />
            <template v-else>—</template>
          </strong>
        </div>
        <div class="kpi-item">
          <span class="kpi-label">待办关注</span>
          <strong class="kpi-value">
            <MetricCountUp :value="kpiTodos" suffix=" 项" />
          </strong>
        </div>
        <div class="kpi-actions">
          <a-button type="primary" :loading="loadingDiagnosis" @click="handleRunDiagnosis">
            更新诊断
          </a-button>
          <a-button :loading="loadingPlan" @click="handleGeneratePlan">复习计划</a-button>
          <a-button :loading="loadingMistakes" @click="handleGenerateMistakes">错题复盘</a-button>
        </div>
      </div>

      <section
        class="zy-stagger-child diag-banner"
        :class="{ 'zy-scanning': isScanning }"
      >
        <template v-if="diagnosis">
          <div class="diag-banner__main">
            <a-avatar :size="56" class="diag-avatar">{{ displayName.slice(0, 1) }}</a-avatar>
            <div class="diag-copy">
              <span class="diag-badge">诊断结论</span>
              <h2>{{ diagnosis.weak_points?.[0] ? `优先巩固：${diagnosis.weak_points[0]}` : '学情诊断' }}</h2>
              <p>{{ diagnosis.summary }}</p>
              <ul v-if="personalSuggestions.length" class="suggestion-list">
                <li v-for="item in personalSuggestions" :key="item">{{ item }}</li>
              </ul>
            </div>
          </div>
          <div class="diag-banner__deco" aria-hidden="true">
            <div class="magnifier">
              <div class="magnifier__glass" />
              <div class="magnifier__handle" />
            </div>
            <div class="dim-overlay">
              <span v-for="dim in radarDimensions" :key="dim.label">
                {{ dim.label }} {{ dim.value }}%
              </span>
            </div>
          </div>
        </template>
        <ZyEmptyGuide
          v-else
          title="暂无学情诊断"
          description="完成一次诊断，获取个性化学习建议"
          primary-text="开始学情诊断"
          secondary-text="去伴学中心"
          @primary="handleRunDiagnosis"
          @secondary="jumpTo('/assistant/chat')"
        />
      </section>

      <div class="triple-grid zy-stagger-child">
        <section class="panel-card">
          <h3>学习画像</h3>
          <LoadingState v-if="loadingInitial" skeleton :skeleton-rows="4" />
          <PortraitRadarChart v-else :dimensions="radarDimensions" height="240px" />
        </section>

        <section class="panel-card">
          <h3>课堂专注率</h3>
          <div class="focus-ring-wrap">
            <a-progress
              type="circle"
              :percent="focusRate"
              :width="120"
              :stroke-width="8"
            />
            <span class="focus-label">近 7 日平均专注</span>
          </div>
          <div v-if="diagnosis?.weak_points?.length" class="weak-tags">
            <span
              v-for="item in diagnosis.weak_points.slice(0, 5)"
              :key="item"
              class="weak-tag"
            >
              {{ item }}
            </span>
          </div>
          <span v-else class="muted">完成诊断后展示薄弱点</span>
        </section>

        <section class="panel-card">
          <h3>下一步方向</h3>
          <article v-if="nextDirection" class="direction-card">
            <strong>{{ nextDirection.title }}</strong>
            <p>{{ nextDirection.desc }}</p>
            <a-button type="primary" size="small" @click="jumpToAssistant(nextDirection.topic)">
              去追问
            </a-button>
          </article>
          <EmptyState
            v-else
            compact
            text="暂无方向建议"
            action-text="开始诊断"
            @action="handleRunDiagnosis"
          />
        </section>
      </div>

      <div class="bottom-row zy-stagger-child">
        <section class="panel-card bottom-col">
          <h3>本周优先待办</h3>
          <div v-if="focusItems.length" class="todo-stack">
            <article v-for="item in focusItems.slice(0, 4)" :key="item" class="todo-item">
              <icon-check-circle />
              <span>{{ item }}</span>
              <a-button size="mini" type="text" @click="jumpToAssistant(item)">追问</a-button>
            </article>
          </div>
          <EmptyState v-else compact text="暂无待办" action-text="开始诊断" @action="handleRunDiagnosis" />
        </section>

        <section class="panel-card bottom-col bottom-col--wide">
          <SegmentTabs v-model="activeTab" :tabs="detailTabs">
            <template #default="{ active }">
              <div v-show="active === 'mistakes'">
                <a-spin :loading="loadingMistakes" style="width: 100%">
                  <template v-if="mistakeDigest?.mistakes?.length">
                    <a-table
                      :data="mistakeDigest.mistakes"
                      :pagination="false"
                      size="small"
                      row-key="title"
                    >
                      <template #columns>
                        <a-table-column title="知识点" data-index="title" />
                        <a-table-column title="表现" data-index="symptom" />
                        <a-table-column title="建议" data-index="fix_strategy" />
                      </template>
                    </a-table>
                  </template>
                  <EmptyState
                    v-else
                    compact
                    text="暂无错题复盘"
                    action-text="生成复盘"
                    @action="handleGenerateMistakes"
                  />
                </a-spin>
              </div>
              <div v-show="active === 'plan'">
                <a-spin :loading="loadingPlan" style="width: 100%">
                  <template v-if="reviewPlan">
                    <div class="report-summary">{{ reviewPlan.summary }}</div>
                    <div class="plan-grid">
                      <div
                        v-for="item in reviewPlan.daily_plan"
                        :key="item.day_label"
                        class="plan-card"
                      >
                        <div class="plan-day">{{ item.day_label }}</div>
                        <div class="plan-focus">{{ item.focus }}</div>
                      </div>
                    </div>
                  </template>
                  <EmptyState
                    v-else
                    compact
                    text="暂无复习计划"
                    action-text="生成计划"
                    @action="handleGeneratePlan"
                  />
                </a-spin>
              </div>
            </template>
          </SegmentTabs>
        </section>

        <section class="panel-card bottom-col">
          <h3>错题分布</h3>
          <div class="donut-wrap">
            <a-progress
              type="circle"
              :percent="mistakeDonutPercent"
              :width="110"
              :stroke-width="10"
              color="#6366f1"
            />
            <ul class="donut-legend">
              <li v-for="item in mistakeDistribution" :key="item.label">
                <span class="dot" :style="{ background: item.color }" />
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}%</strong>
              </li>
            </ul>
          </div>
        </section>
      </div>
    </ZyPageEnter>
  </ZyPageShell>
</template>

<script lang="ts" setup>
  import { computed, onMounted } from 'vue';
  import { useUserStore } from '@/store';
  import { useLearningData } from '@/composables/useLearningData';

  const userStore = useUserStore();
  const displayName = computed(() => userStore.name || '同学');

  const {
    diagnosis,
    reviewPlan,
    mistakeDigest,
    loadingDiagnosis,
    loadingPlan,
    loadingMistakes,
    loadingInitial,
    activeTab,
    isScanning,
    riskTone,
    masteryFocus,
    avgMastery,
    radarDimensions,
    focusItems,
    kpiTodos,
    riskLabel,
    jumpToResourceGeneration,
    jumpToAssistant,
    jumpTo,
    loadInitialDiagnosis,
    handleRunDiagnosis,
    handleGeneratePlan,
    handleGenerateMistakes,
  } = useLearningData();

  const detailTabs = [
    { label: '错题复盘', value: 'mistakes' },
    { label: '复习计划', value: 'plan' },
  ];

  const focusRate = computed(() => {
    const summary = diagnosis.value?.classroom_behavior_summary;
    if (typeof summary?.on_task_rate === 'number') {
      return Math.round(summary.on_task_rate * 100);
    }
    if (typeof summary?.recent_avg_lei === 'number') {
      return Math.round(summary.recent_avg_lei * 100);
    }
    return 88;
  });

  const personalSuggestions = computed(() => {
    const actions = diagnosis.value?.recommended_actions || [];
    const questions = diagnosis.value?.follow_up_questions || [];
    return [...actions, ...questions].slice(0, 3);
  });

  const nextDirection = computed(() => {
    const topic = diagnosis.value?.weak_points?.[0] || diagnosis.value?.current_goal;
    if (!topic) return null;
    return {
      topic,
      title: `聚焦：${topic}`,
      desc:
        diagnosis.value?.follow_up_questions?.[0] ||
        diagnosis.value?.recommended_actions?.[0] ||
        '建议先完成概念梳理，再做分层练习。',
    };
  });

  const mistakeDistribution = computed(() => {
    const mistakes = mistakeDigest.value?.mistakes || [];
    if (!mistakes.length) {
      return [
        { label: '概念混淆', value: 35, color: '#6366f1' },
        { label: '计算失误', value: 28, color: '#8b5cf6' },
        { label: '审题偏差', value: 22, color: '#a5b4fc' },
        { label: '其他', value: 15, color: '#c7d2fe' },
      ];
    }
    const colors = ['#6366f1', '#8b5cf6', '#a5b4fc', '#c7d2fe', '#ddd6fe'];
    const total = mistakes.length;
    return mistakes.slice(0, 4).map((item, index) => ({
      label: item.title.slice(0, 8),
      value: Math.round(100 / total),
      color: colors[index % colors.length],
    }));
  });

  const mistakeDonutPercent = computed(() => {
    if (!mistakeDigest.value?.mistakes?.length) return 72;
    return Math.min(95, mistakeDigest.value.mistakes.length * 18);
  });

  onMounted(() => {
    void loadInitialDiagnosis();
  });
</script>

<style scoped lang="less">
  .kpi-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    padding: 18px 22px;
    background: #fff;
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: var(--zy-radius-card);
    box-shadow: var(--zy-shadow-card);
  }

  .kpi-item {
    flex: 1;
    min-width: 100px;
    padding: 4px 8px;
  }

  .kpi-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-left: auto;
  }

  .kpi-label {
    display: block;
    font-size: 12px;
    color: var(--zy-color-text-secondary);
  }

  .kpi-value {
    display: block;
    margin-top: 4px;
    font-size: 24px;
    font-weight: 800;
    color: var(--zy-color-text-primary);
  }

  .kpi-item--high .kpi-value { color: #dc2626; }
  .kpi-item--medium .kpi-value { color: #d97706; }
  .kpi-item--low .kpi-value { color: #16a34a; }
  .kpi-item--neutral .kpi-value { color: var(--zy-color-brand); }

  .diag-banner {
    position: relative;
    display: flex;
    align-items: stretch;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 16px;
    padding: 24px 28px;
    border-radius: 20px;
    background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 50%, #ecfeff 100%);
    border: 1px solid rgba(99, 102, 241, 0.12);
    overflow: hidden;
  }

  .diag-banner__main {
    display: flex;
    gap: 16px;
    flex: 1;
    min-width: 0;
  }

  .diag-avatar {
    flex-shrink: 0;
    background: var(--zy-gradient-brand);
    color: #fff;
    font-weight: 800;
  }

  .diag-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: var(--zy-radius-pill);
    background: rgba(99, 102, 241, 0.12);
    color: var(--zy-color-brand);
    font-size: 11px;
    font-weight: 700;
    margin-bottom: 6px;
  }

  .diag-copy h2 {
    margin: 0 0 8px;
    font-size: 20px;
    font-weight: 800;
    color: var(--zy-color-text-primary);
  }

  .diag-copy p {
    margin: 0 0 12px;
    color: var(--zy-color-text-secondary);
    line-height: 1.7;
    font-size: 14px;
  }

  .suggestion-list {
    margin: 0;
    padding-left: 1.2em;
    color: #475569;
    font-size: 13px;
    line-height: 1.8;
  }

  .diag-banner__deco {
    position: relative;
    width: 200px;
    flex-shrink: 0;
  }

  .magnifier {
    position: absolute;
    top: 10px;
    right: 20px;
    width: 80px;
    height: 80px;
  }

  .magnifier__glass {
    width: 56px;
    height: 56px;
    border: 6px solid #6366f1;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.5);
    box-shadow: inset 0 0 12px rgba(99, 102, 241, 0.2);
  }

  .magnifier__handle {
    position: absolute;
    width: 28px;
    height: 8px;
    bottom: 8px;
    right: -4px;
    border-radius: 4px;
    background: linear-gradient(90deg, #8b5cf6, #6366f1);
    transform: rotate(45deg);
  }

  .dim-overlay {
    position: absolute;
    bottom: 0;
    right: 0;
    display: grid;
    gap: 4px;
    padding: 10px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(99, 102, 241, 0.12);
    font-size: 10px;
    color: var(--zy-color-text-secondary);
    box-shadow: var(--zy-shadow-card);
  }

  .triple-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
    margin-bottom: 16px;
  }

  .panel-card {
    padding: 18px 20px;
    border-radius: var(--zy-radius-card);
    background: #fff;
    border: 1px solid rgba(99, 102, 241, 0.1);
    box-shadow: var(--zy-shadow-card);

    h3 {
      margin: 0 0 14px;
      font-size: 15px;
      font-weight: 700;
      color: var(--zy-color-text-primary);
    }
  }

  .focus-ring-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
  }

  .focus-label {
    font-size: 12px;
    color: var(--zy-color-text-secondary);
  }

  .weak-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .weak-tag {
    padding: 5px 12px;
    border-radius: var(--zy-radius-pill);
    background: rgba(99, 102, 241, 0.1);
    color: var(--zy-color-brand-hover);
    font-size: 12px;
    font-weight: 600;
  }

  .direction-card {
    padding: 14px;
    border-radius: 12px;
    background: linear-gradient(135deg, #fbfaff, #eef2ff);

    strong {
      display: block;
      margin-bottom: 8px;
      color: var(--zy-color-text-primary);
    }

    p {
      margin: 0 0 12px;
      font-size: 13px;
      line-height: 1.6;
      color: var(--zy-color-text-secondary);
    }
  }

  .bottom-row {
    display: grid;
    grid-template-columns: 1fr 1.4fr 1fr;
    gap: 14px;
  }

  .bottom-col--wide {
    min-width: 0;
  }

  .todo-stack {
    display: grid;
    gap: 8px;
  }

  .todo-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    border-radius: 10px;
    background: #f8fafc;
    font-size: 13px;
    color: #334155;

    svg {
      color: var(--zy-color-brand);
      flex-shrink: 0;
    }

    span {
      flex: 1;
      min-width: 0;
    }
  }

  .donut-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  .donut-legend {
    width: 100%;
    margin: 0;
    padding: 0;
    list-style: none;

    li {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 0;
      font-size: 12px;
      color: var(--zy-color-text-secondary);

      strong {
        margin-left: auto;
        color: var(--zy-color-text-primary);
      }
    }
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .muted {
    color: #94a3b8;
    font-size: 13px;
  }

  .report-summary {
    margin-bottom: 12px;
    line-height: 1.75;
    color: #0f172a;
    font-size: 13px;
  }

  .plan-grid {
    display: grid;
    gap: 10px;
  }

  .plan-card {
    padding: 12px;
    background: #f8fafc;
    border-radius: 10px;
  }

  .plan-day {
    font-weight: 700;
    margin-bottom: 4px;
    font-size: 13px;
  }

  .plan-focus {
    font-size: 12px;
    color: var(--zy-color-text-secondary);
  }

  @media (max-width: 900px) {
    .triple-grid,
    .bottom-row {
      grid-template-columns: 1fr;
    }

    .diag-banner {
      flex-direction: column;
    }

    .diag-banner__deco {
      width: 100%;
      height: 100px;
    }

    .kpi-actions {
      width: 100%;
      margin-left: 0;
    }
  }
</style>
