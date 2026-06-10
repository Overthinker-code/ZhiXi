<template>
  <div class="container">
    <Breadcrumb :items="['menu.profile', 'menu.profile.learningData']" />

    <ZyPageEnter>
      <!-- KPI 条 -->
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
        <div class="kpi-item kpi-item--actions">
          <a-button type="primary" :loading="loadingDiagnosis" @click="handleRunDiagnosis">
            更新诊断
          </a-button>
          <a-button :loading="loadingPlan" @click="handleGeneratePlan">复习计划</a-button>
          <a-button :loading="loadingMistakes" @click="handleGenerateMistakes">错题复盘</a-button>
        </div>
      </div>

      <!-- 诊断 Banner -->
      <a-card
        class="zy-stagger-child card-block summary-banner"
        :class="{ 'zy-scanning': isScanning }"
      >
        <template v-if="diagnosis">
          <h2 class="summary-title">
            {{ diagnosis.weak_points?.[0] ? `优先巩固：${diagnosis.weak_points[0]}` : '学情诊断' }}
          </h2>
          <p class="summary-desc">{{ diagnosis.summary }}</p>
          <div v-if="diagnosis.weak_points?.length" class="tag-row">
            <div
              v-for="item in diagnosis.weak_points"
              :key="item"
              class="topic-chip zy-flip-in"
            >
              <span class="info-tag">{{ item }}</span>
              <div class="topic-chip__actions">
                <button type="button" @click="jumpToAssistant(item)">追问</button>
                <button type="button" @click="jumpToResourceGeneration(item)">生成资源</button>
              </div>
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
      </a-card>

      <a-row :gutter="16">
        <!-- 左栏：雷达 + 档案 -->
        <a-col :xs="24" :xl="8">
          <a-card title="学习画像" class="zy-stagger-child card-block">
            <LoadingState v-if="loadingInitial" skeleton :skeleton-rows="4" />
            <template v-else>
              <PortraitRadarChart :dimensions="radarDimensions" height="260px" />
              <div class="profile-meta">
                <div><strong>当前目标</strong> {{ diagnosis?.current_goal || '—' }}</div>
                <div><strong>学习偏好</strong> {{ diagnosis?.learning_style || '—' }}</div>
              </div>
              <div v-if="masteryFocus.length" class="mastery-box">
                <div class="section-title">掌握度</div>
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
            </template>
          </a-card>

          <a-card title="本周优先" class="zy-stagger-child card-block">
            <ResultReveal v-if="focusItems.length">
              <div v-for="item in focusItems" :key="item" class="focus-item">
                <strong>{{ item }}</strong>
                <div class="focus-item__actions">
                  <a-button size="mini" type="outline" @click="jumpToAssistant(item)">
                    追问
                  </a-button>
                  <a-button size="mini" type="primary" @click="jumpToResourceGeneration(item)">
                    生成资源
                  </a-button>
                </div>
              </div>
            </ResultReveal>
            <EmptyState v-else compact text="暂无待办" action-text="开始诊断" @action="handleRunDiagnosis" />
          </a-card>
        </a-col>

        <!-- 右栏：Timeline + 诊断详情 + Tabs -->
        <a-col :xs="24" :xl="16">
          <a-card class="zy-stagger-child card-block overview-card">
            <div class="evidence-grid">
              <article v-for="item in evidenceCards" :key="item.label" class="evidence-card">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <a-link v-if="item.value === '—'" @click="jumpTo(item.link)">
                  {{ item.linkText }}
                </a-link>
              </article>
            </div>

            <AiProcessTimeline
              v-if="timelineSteps.length || loadingDiagnosis"
              :steps="timelineSteps.length ? timelineSteps : defaultTimeline"
              compact
            />

            <a-spin :loading="loadingDiagnosis" style="width: 100%">
              <ResultReveal v-if="diagnosis">
                <div class="dual-grid">
                  <div class="insight-box">
                    <div class="box-title">优势表现</div>
                    <ul v-if="diagnosis.strengths?.length" class="plain-list">
                      <li v-for="item in diagnosis.strengths" :key="item">{{ item }}</li>
                    </ul>
                    <span v-else class="muted">—</span>
                  </div>
                  <div class="insight-box">
                    <div class="box-title">建议动作</div>
                    <ul v-if="diagnosis.recommended_actions?.length" class="plain-list">
                      <li v-for="item in diagnosis.recommended_actions" :key="item">
                        {{ item }}
                      </li>
                    </ul>
                    <span v-else class="muted">—</span>
                  </div>
                </div>
              </ResultReveal>
            </a-spin>
          </a-card>

          <a-card class="zy-stagger-child card-block">
            <SegmentTabs v-model="activeTab" :tabs="detailTabs">
              <template #default="{ active }">
                <!-- 错题复盘 -->
                <div v-show="active === 'mistakes'">
                  <a-spin :loading="loadingMistakes" style="width: 100%">
                    <template v-if="mistakeDigest">
                      <div class="report-summary">{{ mistakeDigest.summary }}</div>
                      <div class="mistake-list">
                        <div
                          v-for="item in mistakeDigest.mistakes"
                          :key="item.title"
                          class="mistake-card zy-flip-in"
                        >
                          <div class="mistake-title">{{ item.title }}</div>
                          <div class="mistake-line"><strong>表现：</strong>{{ item.symptom }}</div>
                          <div class="mistake-line"><strong>依据：</strong>{{ item.evidence }}</div>
                          <div class="mistake-line"><strong>建议：</strong>{{ item.fix_strategy }}</div>
                        </div>
                      </div>
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

                <!-- 复习计划 -->
                <div v-show="active === 'plan'">
                  <a-spin :loading="loadingPlan" style="width: 100%">
                    <template v-if="reviewPlan">
                      <div class="report-summary">{{ reviewPlan.summary }}</div>
                      <div class="plan-grid">
                        <div
                          v-for="item in reviewPlan.daily_plan"
                          :key="item.day_label"
                          class="plan-card zy-flip-in"
                        >
                          <div class="plan-day">{{ item.day_label }}</div>
                          <div class="plan-focus">{{ item.focus }}</div>
                          <ul class="plain-list">
                            <li v-for="task in item.tasks" :key="task">{{ task }}</li>
                          </ul>
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

                <!-- 课堂投入 -->
                <div v-show="active === 'behavior'">
                  <template v-if="behaviorCards.length">
                    <a-row :gutter="12">
                      <a-col v-for="item in behaviorCards" :key="item.label" :span="8">
                        <div class="stat-box">
                          <div class="stat-num">{{ item.value }}</div>
                          <div class="stat-label">{{ item.label }}</div>
                        </div>
                      </a-col>
                    </a-row>
                  </template>
                  <EmptyState
                    v-else
                    compact
                    text="暂无课堂数据"
                    action-text="去课堂监控"
                    @action="jumpTo('/course/monitor')"
                  />
                </div>

                <!-- 学习路径 -->
                <div v-show="active === 'path'">
                  <template v-if="learningPath?.nodes?.length">
                    <div class="report-summary">{{ learningPath.summary }}</div>
                    <AiProcessTimeline
                      :steps="
                        learningPath.nodes.map((n, i) => ({
                          key: `path-${i}`,
                          label: n.title,
                          message: n.action || n.topic,
                          status:
                            n.status === 'done'
                              ? 'done'
                              : n.status === 'in_progress'
                                ? 'running'
                                : 'idle',
                        }))
                      "
                      compact
                    />
                  </template>
                  <EmptyState
                    v-else
                    compact
                    text="暂无学习路径"
                    action-text="开始诊断"
                    @action="handleRunDiagnosis"
                  />
                </div>
              </template>
            </SegmentTabs>
          </a-card>
        </a-col>
      </a-row>
    </ZyPageEnter>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted } from 'vue';
  import { useUserStore } from '@/store';
  import { useLearningData } from '@/composables/useLearningData';
  import type { TimelineStep } from '@/components/zy/AiProcessTimeline.vue';

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
    loadInitialDiagnosis,
    handleRunDiagnosis,
    handleGeneratePlan,
    handleGenerateMistakes,
  } = useLearningData();

  const detailTabs = [
    { label: '错题复盘', value: 'mistakes' },
    { label: '三天计划', value: 'plan' },
    { label: '课堂投入', value: 'behavior' },
    { label: '学习路径', value: 'path' },
  ];

  const defaultTimeline: TimelineStep[] = [
    { key: 'profile', label: '读取学习画像', status: 'running' },
    { key: 'behavior', label: '汇总课堂投入', status: 'idle' },
    { key: 'infer', label: '生成诊断结论', status: 'idle' },
  ];

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
    border-radius: var(--zy-radius-card, 14px);
  }

  .kpi-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: stretch;
    margin-bottom: 16px;
    padding: 16px 20px;
    background: var(--zy-bg-card, rgba(255, 255, 255, 0.82));
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: var(--zy-radius-card, 16px);
    box-shadow: var(--zy-shadow-card);
  }

  .kpi-item {
    flex: 1;
    min-width: 100px;
    padding: 8px 12px;
  }

  .kpi-item--actions {
    flex: 2;
    min-width: 240px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    justify-content: flex-end;
  }

  .kpi-label {
    display: block;
    font-size: 12px;
    color: var(--zy-color-text-secondary, #64748b);
  }

  .kpi-value {
    display: block;
    margin-top: 4px;
    font-size: 22px;
    font-weight: 700;
    color: var(--zy-color-text-primary, #0f172a);
  }

  .kpi-item--high .kpi-value {
    color: #dc2626;
  }
  .kpi-item--medium .kpi-value {
    color: #d97706;
  }
  .kpi-item--low .kpi-value {
    color: #16a34a;
  }
  .kpi-item--neutral .kpi-value {
    color: var(--zy-color-brand, #6366f1);
  }

  .summary-banner {
    background:
      radial-gradient(circle at left top, rgba(99, 102, 241, 0.1), transparent 40%),
      linear-gradient(180deg, #f8fafc 0%, #fff 100%);
  }

  .summary-title {
    margin: 0 0 8px;
    font-size: 22px;
    font-weight: 700;
    color: #0f172a;
  }

  .summary-desc {
    margin: 0 0 16px;
    color: #475569;
    line-height: 1.75;
  }

  .profile-meta {
    margin-top: 16px;
    line-height: 1.9;
    font-size: 14px;
  }

  .section-title,
  .box-title {
    margin-bottom: 8px;
    font-weight: 600;
  }

  .mastery-box {
    margin-top: 16px;
    padding: 14px;
    background: #f8fafc;
    border-radius: 12px;
  }

  .mastery-list {
    display: grid;
    gap: 10px;
  }

  .mastery-head {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    color: #334155;
  }

  .focus-item {
    padding: 12px 14px;
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: 12px;
    background: #fff;
  }

  .focus-item__actions {
    display: flex;
    gap: 8px;
    margin-top: 10px;
  }

  .overview-card {
    background:
      radial-gradient(circle at top left, rgba(99, 102, 241, 0.08), transparent 38%),
      #fff;
  }

  .evidence-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 16px;
  }

  .evidence-card {
    padding: 14px;
    background: #f8fafc;
    border-radius: 12px;

    span,
    strong {
      display: block;
    }

    span {
      font-size: 12px;
      color: #64748b;
    }

    strong {
      margin-top: 6px;
      font-size: 16px;
      color: #0f172a;
      line-height: 1.4;
    }
  }

  .tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .info-tag {
    padding: 6px 12px;
    color: #4338ca;
    font-size: 12px;
    font-weight: 600;
    background: rgba(99, 102, 241, 0.12);
    border-radius: 999px;
  }

  .topic-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 4px 8px 4px 4px;
    background: #fff;
    border: 1px solid rgba(99, 102, 241, 0.15);
    border-radius: 999px;
  }

  .topic-chip__actions button {
    border: none;
    border-radius: 999px;
    padding: 4px 10px;
    background: rgba(99, 102, 241, 0.08);
    color: #6366f1;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: background var(--zy-duration-fast, 150ms) ease;

    &:hover {
      background: rgba(99, 102, 241, 0.16);
    }
  }

  .dual-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-top: 16px;
  }

  .insight-box {
    padding: 14px;
    background: #f8fafc;
    border-radius: 12px;
  }

  .plain-list {
    margin: 0;
    padding-left: 1.2em;
    color: #475569;
    line-height: 1.75;
  }

  .muted {
    color: #94a3b8;
  }

  .report-summary {
    margin-bottom: 12px;
    line-height: 1.75;
    color: #0f172a;
  }

  .mistake-list,
  .plan-grid {
    display: grid;
    gap: 12px;
  }

  .mistake-card,
  .plan-card {
    padding: 14px;
    background: #f8fafc;
    border-radius: 12px;
  }

  .mistake-title,
  .plan-day {
    font-weight: 600;
    margin-bottom: 6px;
  }

  .mistake-line {
    color: #475569;
    line-height: 1.7;
    font-size: 13px;
  }

  .plan-focus {
    margin-bottom: 8px;
    color: #334155;
    font-weight: 500;
  }

  .stat-box {
    padding: 14px;
    text-align: center;
    background: #f8fafc;
    border-radius: 12px;
  }

  .stat-num {
    font-size: 22px;
    font-weight: 700;
    color: var(--zy-color-brand, #6366f1);
  }

  .stat-label {
    margin-top: 4px;
    font-size: 12px;
    color: #64748b;
  }

  @media (max-width: 768px) {
    .kpi-bar {
      flex-direction: column;
    }

    .kpi-item--actions {
      justify-content: flex-start;
    }

    .evidence-grid,
    .dual-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
