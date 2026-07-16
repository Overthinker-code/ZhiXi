<template>
  <ZyPageShell
    class="learning-portrait-page"
    title="我的学习画像"
    subtitle="结合课程学习、练习表现和提问记录，持续呈现你的成长变化与学习节律"
    max-width="1360px"
  >
    <ZyPageEnter>
      <div class="portrait-content">
        <div class="portrait-meta zy-stagger-child" aria-label="学习画像更新状态">
          <span>{{ portraitStatusLabel }}</span>
          <i />
          <span>{{ formattedUpdatedAt }}</span>
          <span v-if="portraitRefreshError" class="portrait-meta__error" role="status">
            {{ portraitRefreshError }}
          </span>
          <a-button
            type="text"
            size="mini"
            aria-label="刷新学习建议"
            :loading="loadingDiagnosis || loadingAnalytics"
            @click="refreshPortrait"
          >
            <template #icon><icon-refresh /></template>
            刷新学习建议
          </a-button>
        </div>

        <section class="metric-strip zy-stagger-child" aria-label="学习画像核心指标">
          <article class="metric">
            <span class="metric__icon metric__icon--blue"><icon-dashboard /></span>
            <div>
              <small>综合能力</small>
              <strong>{{ formatNumber(portrait.overallScore) }}<em v-if="portrait.overallScore !== null">/100</em></strong>
            </div>
          </article>
          <article class="metric">
            <span class="metric__icon metric__icon--green"><icon-arrow-rise /></span>
            <div>
              <small>近 30 日成长</small>
              <strong class="metric__positive">{{ formatSigned(portrait.growthRate) }}</strong>
            </div>
          </article>
          <article class="metric">
            <span class="metric__icon metric__icon--purple"><ChartPie :size="24" /></span>
            <div>
              <small>学习投入</small>
              <strong>{{ formatPercent(portrait.engagement) }}</strong>
            </div>
          </article>
          <article class="metric">
            <span class="metric__icon metric__icon--orange"><icon-exclamation-circle /></span>
            <div>
              <small>建议优先提升</small>
              <strong>{{ portrait.attentionCount }}<em> 项</em></strong>
            </div>
          </article>
        </section>

        <div class="portrait-grid zy-stagger-child">
          <section class="portrait-card growth-card">
            <header class="card-heading">
              <h2>能力成长趋势</h2>
              <span class="trend-range">近 12 周</span>
            </header>
            <PortraitGrowthChart
              v-if="portrait.trendSeries.length"
              :labels="portrait.trendLabels"
              :series="portrait.trendSeries"
              height="258px"
            />
            <EmptyState v-else compact text="完成更多练习后，这里会显示你的成长趋势" />
          </section>

          <section class="portrait-card capability-card">
            <header class="card-heading">
              <h2>核心能力画像</h2>
              <div class="radar-legend" aria-hidden="true">
                <span><i />当前</span>
                <span v-if="hasCompletePreviousComparison">
                  <i class="radar-legend__previous" />30 天前
                </span>
              </div>
            </header>
            <PortraitCapabilityChart
              v-if="portrait.dimensions.length >= 3"
              :dimensions="portrait.dimensions"
              height="270px"
            />
            <div v-else-if="portrait.dimensionStatuses.length" class="dimension-statuses">
              <span
                v-for="item in portrait.dimensionStatuses"
                :key="item.key"
                :class="`dimension-statuses__item--${item.tone}`"
              >
                {{ item.label }} · {{ item.stateLabel }}
              </span>
            </div>
            <EmptyState v-else compact text="完成一次学习诊断后，这里会显示你的能力分布" />
          </section>

          <section class="portrait-card rhythm-card">
            <header class="card-heading card-heading--compact">
              <div class="heading-inline">
                <h2>学习节律</h2>
                <a-tooltip content="根据近期学习记录整理">
                  <icon-info-circle aria-hidden="true" focusable="false" tabindex="-1" />
                </a-tooltip>
              </div>
            </header>
            <PortraitRhythmChart
              v-if="hasRhythmData"
              :week-labels="analytics?.rhythm.week_labels || []"
              :day-labels="analytics?.rhythm.day_labels || []"
              :activity="portrait.rhythm"
              :hour-labels="analytics?.rhythm.hour_labels || []"
              :focus-hours="portrait.focusCurve"
              height="156px"
            />
            <EmptyState v-else compact text="暂无可分析的学习时段记录" />
          </section>

          <section class="portrait-card preference-card">
            <header class="card-heading card-heading--compact">
              <div class="heading-inline">
                <h2>{{ resourceSectionTitle }}</h2>
                <a-tooltip :content="portrait.resourceInferenceLabel">
                  <icon-info-circle aria-hidden="true" focusable="false" tabindex="-1" />
                </a-tooltip>
              </div>
            </header>
            <div v-if="portrait.resourcePreferences.length" class="preference-body">
              <Chart
                :options="resourceChartOptions"
                width="128px"
                height="126px"
                :aria-label="resourceChartAccessibility.label"
                :aria-summary="resourceChartAccessibility.summary"
                :accessible-headers="resourceChartAccessibility.headers"
                :accessible-rows="resourceChartAccessibility.rows"
              />
              <ul>
                <li
                  v-for="(item, index) in portrait.resourcePreferences.slice(0, 4)"
                  :key="item.key"
                >
                  <span
                    class="preference-swatch"
                    :class="`preference-swatch--${index % 4}`"
                    :style="{ '--swatch-color': item.color }"
                    aria-hidden="true"
                  />
                  <small>{{ item.label }}</small>
                  <strong>{{ item.value === null ? '—' : `${Math.round(item.value)}%` }}</strong>
                </li>
              </ul>
            </div>
            <EmptyState v-else compact text="使用课程资料后，这里会显示你的偏好" />
            <button
              v-if="portrait.resourcePreferences.length"
              type="button"
              class="preference-insight"
              @click="goToResourceWorkshop"
            >
              <icon-arrow-rise />
              <span>前往生成学习资源</span>
            </button>
          </section>

          <section class="portrait-card recommendation-card">
            <header class="card-heading card-heading--compact">
              <div class="heading-inline">
                <h2>下一步建议</h2>
                <a-tooltip content="结合近期学习进度和当前计划生成">
                  <icon-info-circle aria-hidden="true" focusable="false" tabindex="-1" />
                </a-tooltip>
              </div>
            </header>
            <a-button
              class="path-button"
              type="primary"
              aria-label="生成我的学习路径"
              :loading="loadingPlan"
              @click="generatePath"
            >
              <template #icon><icon-bulb /></template>
              生成我的学习路径
            </a-button>
            <div v-if="portrait.recommendations.length" class="recommendations">
              <button
                v-for="item in portrait.recommendations.slice(0, 3)"
                :key="item.title"
                type="button"
                class="recommendation"
                :class="`recommendation--${item.tone}`"
                @click="jumpToAssistant(item.topic)"
              >
                <span class="recommendation__icon">
                  <icon-exclamation-circle v-if="item.tone === 'warning'" />
                  <icon-check-circle v-else-if="item.tone === 'success'" />
                  <icon-thunderbolt v-else />
                </span>
                <span class="recommendation__copy">
                  <strong>{{ item.title }}</strong>
                  <small>{{ item.description }}</small>
                  <em>根据近期学习情况</em>
                </span>
                <icon-right />
              </button>
            </div>
            <EmptyState
              v-else
              compact
              text="完成一次学习活动后，我们会为你整理下一步建议"
              action-text="刷新建议"
              @action="refreshPortrait"
            />
          </section>

          <section class="portrait-card course-card">
            <header class="card-heading card-heading--compact">
              <h2>分课程查看</h2>
            </header>
            <div v-if="portrait.courses.length" class="course-table">
              <div class="course-table__head" aria-hidden="true">
                <span>课程名称</span>
                <span>掌握情况</span>
                <span>近 30 天变化</span>
                <span>当前重点</span>
                <span>操作</span>
              </div>
              <div class="course-table__body" role="list">
                <div
                  v-for="(course, index) in portrait.courses.slice(0, 4)"
                  :key="course.id"
                  class="course-row-item"
                  role="listitem"
                >
                  <button
                    type="button"
                    class="course-row"
                    :aria-label="`查看${course.name}课程详情`"
                    @click="openCourse(course.id)"
                  >
                    <span class="course-name">
                      <i :class="`course-mark course-mark--${index % 4}`">
                        <icon-storage v-if="index === 0" />
                        <icon-code v-else-if="index === 1" />
                        <icon-computer v-else-if="index === 2" />
                        <icon-file v-else />
                      </i>
                      <strong>{{ course.name }}</strong>
                    </span>
                    <span class="course-mastery">
                      <i><b :style="{ width: `${course.score || 0}%` }" /></i>
                      <small>{{ course.score === null ? '—' : `${Math.round(course.score)}%` }}</small>
                    </span>
                    <span class="course-trend" :class="{ 'course-trend--muted': course.trend === null }">
                      {{ course.trend === null ? '继续学习后更新' : `${course.trend >= 0 ? '↑' : '↓'} ${Math.abs(Math.round(course.trend))}%` }}
                    </span>
                    <span class="course-focus">{{ course.focus }}</span>
                    <span class="course-action">查看课程 <icon-right /></span>
                  </button>
                </div>
              </div>
            </div>
            <EmptyState
              v-else
              compact
              text="还没有可分析的课程"
              action-text="进入课程中心"
              @action="router.push({ name: 'CourseList' })"
            />
          </section>
        </div>
      </div>
    </ZyPageEnter>

    <a-drawer
      v-model:visible="detailDrawerVisible"
      :width="500"
      :footer="false"
      title="个性化学习路径"
      unmount-on-close
    >
      <a-spin :loading="loadingPlan" style="width: 100%">
        <div v-if="reviewPlan" class="drawer-content">
          <p>{{ reviewPlan.summary }}</p>
          <article v-for="(item, index) in reviewPlan.daily_plan" :key="item.day_label">
            <span>{{ index + 1 }}</span>
            <div>
              <small>{{ item.day_label }}</small>
              <strong>{{ item.focus }}</strong>
              <p>{{ item.tasks.join(' · ') }}</p>
            </div>
          </article>
        </div>
        <EmptyState v-else compact text="暂无学习路径" action-text="立即生成" @action="generatePath" />
      </a-spin>
    </a-drawer>
  </ZyPageShell>
</template>

<script lang="ts" setup>
  import { computed, onMounted, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { Message } from '@arco-design/web-vue';
  import { ChartPie } from 'lucide-vue-next';
  import { fetchCourses, type Course } from '@/api/course';
  import {
    fetchPortraitAnalytics,
    type PortraitAnalytics,
  } from '@/api/learning-portrait';
  import { fetchPracticeSummary, type PracticeSummary } from '@/api/student-hub';
  import { useLearningData } from '@/composables/useLearningData';
  import PortraitCapabilityChart from './components/PortraitCapabilityChart.vue';
  import PortraitGrowthChart from './components/PortraitGrowthChart.vue';
  import PortraitRhythmChart from './components/PortraitRhythmChart.vue';
  import { buildResourceChartAccessibility } from './components/chartAccessibility';
  import { buildLearningPortraitViewModel } from './learningPortraitViewModel';

  const router = useRouter();
  const courses = ref<Course[]>([]);
  const practice = ref<PracticeSummary | null>(null);
  const analytics = ref<PortraitAnalytics | null>(null);
  const loadingAnalytics = ref(false);
  const portraitRefreshError = ref('');
  const detailDrawerVisible = ref(false);

  const {
    diagnosis,
    reviewPlan,
    learningPath,
    loadingDiagnosis,
    loadingPlan,
    loadingInitial,
    jumpToAssistant,
    loadInitialDiagnosis,
    handleRunDiagnosis,
    handleGeneratePlan,
  } = useLearningData();

  const portrait = computed(() =>
    buildLearningPortraitViewModel({
      diagnosis: diagnosis.value,
      practice: practice.value,
      courses: courses.value,
      learningPath: learningPath.value,
      analytics: analytics.value,
    })
  );

  const hasRhythmData = computed(
    () =>
      portrait.value.rhythm.some((row) => row.some((value) => value > 0)) ||
      portrait.value.focusCurve.some((value) => value > 0)
  );
  const hasCompletePreviousComparison = computed(
    () =>
      portrait.value.dimensions.length > 0 &&
      portrait.value.dimensions.every((item) => item.previous !== null)
  );
  const portraitStatusLabel = computed(() =>
    portraitRefreshError.value
      ? '当前显示已保存的学习画像'
      : '已根据近期学习记录更新'
  );
  const formattedUpdatedAt = computed(() => {
    const raw = portrait.value.updatedAt;
    if (!raw) return '等待首次画像更新';
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return '画像已更新';
    return `更新于 ${new Intl.DateTimeFormat('zh-CN', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)}`;
  });

  const resourceChartAccessibility = computed(() =>
    buildResourceChartAccessibility(portrait.value.resourcePreferences)
  );
  const resourceSectionTitle = computed(() =>
    portrait.value.resourcePreferences.some((item) => item.value !== null)
      ? '资源类型分布'
      : '推荐资源类型'
  );

  const resourceDecals = [
    { symbol: 'rect', dashArrayX: [1, 0], dashArrayY: [2, 5], rotation: 0 },
    { symbol: 'circle', dashArrayX: [1, 4], dashArrayY: [1, 4], rotation: 0 },
    { symbol: 'rect', dashArrayX: [3, 3], dashArrayY: [1, 0], rotation: Math.PI / 4 },
    { symbol: 'triangle', dashArrayX: [1, 5], dashArrayY: [1, 5], rotation: 0 },
  ];

  const resourceChartOptions = computed(() => ({
    animationDuration: 620,
    tooltip: {
      trigger: 'item',
      formatter: '{b}<br/>{c}%',
      backgroundColor: 'rgba(15, 23, 42, .94)',
      borderWidth: 0,
      textStyle: { color: '#fff', fontSize: 11 },
    },
    series: [
      {
        type: 'pie',
        radius: ['52%', '76%'],
        center: ['50%', '50%'],
        label: { show: false },
        itemStyle: { borderColor: '#fff', borderWidth: 3, borderRadius: 4 },
        data: portrait.value.resourcePreferences.map((item, index) => ({
          name: item.label,
          value: item.value,
          itemStyle: {
            color: item.color,
            decal: resourceDecals[index % resourceDecals.length],
          },
        })),
      },
    ],
  }));

  function formatNumber(value: number | null) {
    return value === null ? '—' : Math.round(value);
  }

  function formatSigned(value: number | null) {
    if (value === null) return '待积累';
    return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
  }

  function formatPercent(value: number | null) {
    return value === null ? '待积累' : `${Math.round(value)}%`;
  }

  async function loadSupportingData() {
    loadingAnalytics.value = true;
    try {
      const [courseResult, practiceResult, analyticsResult] = await Promise.allSettled([
        fetchCourses({ limit: 8 }),
        fetchPracticeSummary(),
        fetchPortraitAnalytics(),
      ]);
      courses.value = courseResult.status === 'fulfilled' ? courseResult.value.data || [] : [];
      practice.value = practiceResult.status === 'fulfilled' ? practiceResult.value : null;
      if (analyticsResult.status === 'fulfilled') {
        analytics.value = analyticsResult.value;
        portraitRefreshError.value = '';
      } else {
        analytics.value = null;
        portraitRefreshError.value = '画像数据暂时无法更新';
      }
    } finally {
      loadingAnalytics.value = false;
    }
  }

  async function refreshPortrait() {
    portraitRefreshError.value = '';
    await handleRunDiagnosis();
    loadingAnalytics.value = true;
    try {
      analytics.value = await fetchPortraitAnalytics();
    } catch {
      portraitRefreshError.value = '更新未完成，当前显示上次结果';
      Message.error('画像分析更新失败，请稍后重试');
    } finally {
      loadingAnalytics.value = false;
    }
  }

  async function generatePath() {
    detailDrawerVisible.value = true;
    if (!reviewPlan.value) await handleGeneratePlan();
  }

  function goToResourceWorkshop() {
    router.push({
      path: '/resource-workshop',
      query: {
        source: 'learning-portrait',
        topic: diagnosis.value?.weak_points?.[0] || diagnosis.value?.current_goal || '',
      },
    });
  }

  function openCourse(courseId: string) {
    router.push({ name: 'CourseContent', params: { courseId } });
  }

  onMounted(async () => {
    await Promise.all([loadInitialDiagnosis(), loadSupportingData()]);
  });
</script>

<style scoped lang="less">
  .learning-portrait-page {
    --portrait-primary: #6255e7;
    --portrait-blue: #3478f6;
    --portrait-cyan: #2bb8d6;
    --portrait-orange: #f59e42;
    --portrait-border: #e5e9f2;
    --portrait-text: #172033;
    --portrait-muted: #7b879b;
    padding-top: 0;
  }

  .learning-portrait-page :deep(.zy-page-shell__head) {
    margin-bottom: 4px;
  }

  .learning-portrait-page :deep(.zy-page-shell__head h1) {
    font-size: 28px;
    letter-spacing: -0.035em;
  }

  .learning-portrait-page :deep(.zy-page-shell__head p) {
    margin-top: 4px;
    font-size: 13px;
  }

  .portrait-content {
    display: flex;
    flex-direction: column;
    gap: 13px;
  }

  .portrait-meta {
    display: flex;
    align-items: center;
    min-height: 20px;
    gap: 9px;
    color: #556070;
    font-size: 11px;
  }

  .portrait-meta i {
    width: 3px;
    height: 3px;
    border-radius: 50%;
    background: #c7ced9;
  }

  .portrait-meta :deep(.arco-btn) {
    height: 22px;
    margin-left: auto;
    color: #667085;
    font-size: 11px;
  }

  .portrait-meta__error {
    color: #b45309;
  }

  .metric-strip,
  .portrait-card {
    border: 1px solid var(--portrait-border);
    background: rgba(255, 255, 255, 0.96);
    box-shadow: 0 8px 24px rgba(64, 72, 109, 0.055);
  }

  .metric-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    min-height: 86px;
    border-radius: 12px;
    padding: 14px 0;
  }

  .metric {
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 0 32px;
    border-right: 1px solid #e9edf4;
  }

  .metric:last-child {
    border-right: 0;
  }

  .metric__icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 52px;
    height: 52px;
    flex: 0 0 52px;
    border-radius: 50%;
    font-size: 25px;
  }

  .metric__icon--blue { color: var(--portrait-blue); background: #eef5ff; }
  .metric__icon--green { color: #20ae59; background: #eefaf2; }
  .metric__icon--purple { color: var(--portrait-primary); background: #f3f0ff; }
  .metric__icon--orange { color: #f28c20; background: #fff5eb; }

  .metric small {
    display: block;
    margin-bottom: 3px;
    color: #556070;
    font-size: 12px;
  }

  .metric strong {
    color: var(--portrait-text);
    font-size: 25px;
    line-height: 1;
    font-weight: 700;
  }

  .metric strong em {
    margin-left: 3px;
    color: #556070;
    font-size: 11px;
    font-style: normal;
    font-weight: 500;
  }

  .metric .metric__positive {
    color: #16a34a;
    font-size: 22px;
  }

  .portrait-grid {
    display: grid;
    grid-template-columns:
      minmax(0, 600fr)
      minmax(0, 224fr)
      minmax(0, 51fr)
      minmax(0, 389fr);
    grid-template-rows: 330px 202px 204px;
    gap: 16px;
  }

  .portrait-card {
    min-width: 0;
    overflow: hidden;
    border-radius: 12px;
  }

  .growth-card { grid-column: 1 / 3; grid-row: 1; padding: 18px 16px 8px; }
  .capability-card { grid-column: 3 / 5; grid-row: 1; padding: 18px 16px 8px; }
  .rhythm-card { grid-column: 1; grid-row: 2; padding: 14px 14px 6px; }
  .preference-card { grid-column: 2 / 4; grid-row: 2; padding: 14px 14px 10px; }
  .recommendation-card { grid-column: 4; grid-row: 2 / 4; padding: 14px; }
  .course-card { grid-column: 1 / 4; grid-row: 3; padding: 12px 14px 8px; }

  .card-heading {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    min-height: 45px;
  }

  .card-heading--compact {
    min-height: 31px;
  }

  .growth-card > .card-heading,
  .capability-card > .card-heading {
    min-height: 39px;
  }

  .card-heading h2 {
    margin: 0;
    color: var(--portrait-text);
    font-size: 15px;
    line-height: 1.25;
    font-weight: 700;
  }

  .trend-range {
    display: inline-flex;
    align-items: center;
    height: 28px;
    padding: 0 10px;
    border: 1px solid #e2e7f1;
    border-radius: 6px;
    color: #556070;
    background: #fff;
    font-size: 12px;
  }

  .card-heading p {
    margin: 5px 0 0;
    color: #9aa5b6;
    font-size: 10px;
    line-height: 1.4;
  }

  .heading-inline {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .heading-inline > svg {
    color: #98a2b3;
    font-size: 13px;
  }

  .radar-legend {
    display: flex;
    align-items: center;
    gap: 18px;
    color: #7d8798;
    font-size: 10px;
  }

  .radar-legend span {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
  }

  .radar-legend i {
    display: block;
    width: 16px;
    border-top: 2px solid #6255e7;
  }

  .radar-legend .radar-legend__previous {
    border-top: 2px dashed #a7b1c2;
  }

  .dimension-statuses {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    padding: 20px 4px;
  }

  .dimension-statuses span {
    padding: 10px;
    border-radius: 8px;
    color: #667085;
    background: #f7f8fb;
    font-size: 11px;
  }

  .dimension-statuses__item--success { color: #16864d !important; background: #f0fbf4 !important; }
  .dimension-statuses__item--warning { color: #b96813 !important; background: #fff8ee !important; }

  .preference-body {
    display: grid;
    grid-template-columns: 128px minmax(0, 1fr);
    align-items: center;
    gap: 4px;
    margin-top: -4px;
  }

  .preference-body ul {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .preference-body li {
    display: grid;
    grid-template-columns: 8px minmax(0, 1fr) auto;
    align-items: center;
    gap: 7px;
  }

  .preference-swatch {
    width: 8px;
    height: 8px;
    border: 1px solid color-mix(in srgb, var(--swatch-color) 72%, #172033);
    background: var(--swatch-color);
  }

  .preference-swatch--0 {
    border-radius: 50%;
  }

  .preference-swatch--1 {
    border-radius: 1px;
    background: repeating-linear-gradient(
      45deg,
      var(--swatch-color) 0 2px,
      #ffffff 2px 3px
    );
  }

  .preference-swatch--2 {
    border-radius: 1px;
    transform: rotate(45deg) scale(0.82);
  }

  .preference-swatch--3 {
    border-radius: 50% 50% 1px 50%;
    transform: rotate(45deg) scale(0.88);
  }

  .preference-body li small {
    overflow: hidden;
    color: #667085;
    font-size: 10px;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .preference-body li strong {
    color: #596579;
    font-size: 10px;
    font-weight: 600;
  }

  .preference-insight {
    display: flex;
    align-items: center;
    width: 100%;
    height: 28px;
    margin-top: -2px;
    padding: 0 9px;
    border: 1px solid #d9dcff;
    border-radius: 6px;
    color: #6255e7;
    background: #f8f7ff;
    font-size: 10px;
    cursor: pointer;
  }

  .preference-insight span {
    margin-left: 6px;
  }

  .path-button {
    display: block;
    width: 250px;
    height: 38px;
    margin: 8px auto 15px;
    border: 0;
    border-radius: 6px;
    background: #6255e7;
    box-shadow: 0 6px 16px rgba(98, 85, 231, 0.18);
  }

  .recommendations {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .recommendation {
    display: grid;
    grid-template-columns: 38px minmax(0, 1fr) 14px;
    align-items: center;
    min-height: 86px;
    padding: 10px 8px;
    border: 1px solid #e3e7ef;
    border-radius: 7px;
    color: inherit;
    background: #fff;
    text-align: left;
    cursor: pointer;
    transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
  }

  .recommendation:hover {
    border-color: #cbc8fb;
    box-shadow: 0 7px 18px rgba(70, 77, 110, .08);
    transform: translateY(-1px);
  }

  .recommendation__icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    color: #6255e7;
    background: #f0eeff;
    font-size: 16px;
  }

  .recommendation--warning .recommendation__icon { color: #f28c20; background: #fff2e4; }
  .recommendation--success .recommendation__icon { color: #3478f6; background: #edf5ff; }
  .recommendation--primary .recommendation__icon { color: #22aaca; background: #eafafe; }

  .recommendation__copy {
    min-width: 0;
  }

  .recommendation__copy strong,
  .recommendation__copy small,
  .recommendation__copy em {
    display: block;
  }

  .recommendation__copy strong {
    overflow: hidden;
    color: #253047;
    font-size: 12px;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .recommendation__copy small {
    display: -webkit-box;
    overflow: hidden;
    margin-top: 4px;
    color: #556070;
    font-size: 10px;
    line-height: 1.45;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .recommendation__copy em {
    margin-top: 5px;
    color: #556070;
    font-size: 9px;
    font-style: normal;
  }

  .recommendation > svg {
    color: #8f9bad;
  }

  .course-table {
    margin-top: 2px;
  }

  .course-row-item {
    margin: 0;
  }

  .course-table__head,
  .course-row {
    display: grid;
    grid-template-columns: 1.4fr .82fr .8fr 1.18fr .46fr;
    align-items: center;
    column-gap: 14px;
  }

  .course-table__head {
    height: 24px;
    padding: 0 10px;
    border-bottom: 1px solid #e7ebf2;
    color: #7f8999;
    font-size: 10px;
  }

  .course-row {
    width: 100%;
    height: 32px;
    padding: 0 10px;
    border: 0;
    border-bottom: 1px solid #edf0f5;
    color: inherit;
    background: transparent;
    text-align: left;
    cursor: pointer;
  }

  .course-row-item:last-child .course-row {
    border-bottom: 0;
  }

  .course-row:hover {
    background: #fafaff;
  }

  .course-name {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 9px;
  }

  .course-name strong {
    overflow: hidden;
    color: #283247;
    font-size: 11px;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .course-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    flex: 0 0 24px;
    border-radius: 5px;
    color: #fff;
    font-style: normal;
    font-size: 13px;
  }

  .course-mark--0 { background: #6255e7; }
  .course-mark--1 { background: #20b486; }
  .course-mark--2 { background: #3478f6; }
  .course-mark--3 { background: #f28c20; }

  .course-mastery {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .course-mastery > i {
    display: block;
    width: 82px;
    height: 4px;
    overflow: hidden;
    border-radius: 99px;
    background: #eceff5;
  }

  .course-mastery b {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: #6255e7;
  }

  .course-mastery small {
    color: #7d8798;
    font-size: 10px;
  }

  .course-trend {
    color: #1ab15b;
    font-size: 10px;
    font-weight: 600;
  }

  .course-trend--muted {
    color: #9aa4b4;
    font-weight: 400;
  }

  .course-focus {
    overflow: hidden;
    color: #596579;
    font-size: 10px;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .course-action {
    display: inline-flex;
    align-items: center;
    justify-content: flex-end;
    color: #6255e7;
    font-size: 10px;
    white-space: nowrap;
  }

  .drawer-content > p {
    padding: 14px;
    border-radius: 10px;
    color: #596579;
    background: #f7f8fc;
    line-height: 1.65;
  }

  .drawer-content article {
    display: grid;
    grid-template-columns: 32px 1fr;
    gap: 10px;
    padding: 12px 0;
    border-bottom: 1px solid #edf0f5;
  }

  .drawer-content article > span {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    color: #6255e7;
    background: #f0eeff;
  }

  .drawer-content article small,
  .drawer-content article strong {
    display: block;
  }

  .drawer-content article p {
    margin: 5px 0 0;
    color: #7b8799;
  }

  @media (max-width: 1180px) {
    .metric {
      padding: 0 18px;
    }

    .portrait-grid {
      grid-template-columns: minmax(0, 1.45fr) minmax(240px, .8fr);
      grid-template-rows: 330px 280px auto auto;
    }

    .growth-card { grid-column: 1; grid-row: 1; }
    .capability-card { grid-column: 2; grid-row: 1; }
    .rhythm-card { grid-column: 1; grid-row: 2; }
    .preference-card { grid-column: 2; grid-row: 2; }
    .recommendation-card { grid-column: 1 / 3; grid-row: 3; }
    .course-card { grid-column: 1 / 3; grid-row: 4; }
  }

  @media (max-width: 820px) {
    .metric-strip {
      grid-template-columns: 1fr 1fr;
    }

    .metric:nth-child(2) {
      border-right: 0;
    }

    .metric:nth-child(-n + 2) {
      border-bottom: 1px solid #e9edf4;
    }

    .metric {
      min-height: 76px;
    }

    .portrait-grid {
      display: flex;
      flex-direction: column;
    }

    .portrait-card {
      min-height: 250px;
    }

    .recommendation-card {
      min-height: auto;
    }
  }

  @media (max-width: 560px) {
    .learning-portrait-page :deep(.zy-page-shell) {
      padding-right: 14px;
      padding-left: 14px;
    }

    .portrait-meta {
      flex-wrap: wrap;
    }

    .portrait-meta :deep(.arco-btn) {
      margin-left: 0;
    }

    .metric-strip {
      grid-template-columns: 1fr;
    }

    .metric {
      border-right: 0;
      border-bottom: 1px solid #e9edf4;
    }

    .metric:last-child {
      border-bottom: 0;
    }

    .course-table__head {
      display: none;
    }

    .course-row {
      grid-template-columns: minmax(0, 1fr) auto;
      height: auto;
      min-height: 58px;
      row-gap: 5px;
    }

    .course-mastery,
    .course-trend,
    .course-focus {
      display: none;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .recommendation {
      transition: none;
    }
  }

  :global(.layout-content:has(.learning-portrait-page)) {
    background: linear-gradient(180deg, #f7f8ff 0%, #fbfcff 50%, #f8f7ff 100%);
  }

  :global(.layout:has(.learning-portrait-page) > .float-btn) {
    display: none;
  }
</style>
