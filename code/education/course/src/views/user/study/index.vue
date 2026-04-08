<template>
  <div class="study-page">
    <Breadcrumb :items="['menu.user', 'menu.user.study']" />

    <div class="study-layout" v-if="!loading">
      <!-- ========== 左侧主区域 ========== -->
      <div class="study-left">

        <!-- 学生画像卡片 -->
        <a-card class="profile-card" :bordered="false">
          <div class="profile-inner">
            <div class="avatar-area">
              <a-avatar :size="72" :style="{ backgroundColor: '#165DFF', fontSize: '28px' }">
                {{ profile.name?.charAt(0) || '学' }}
              </a-avatar>
              <div class="profile-tag">
                <a-tag color="arcoblue" size="small">在读</a-tag>
              </div>
            </div>
            <div class="profile-info">
              <h2 class="profile-name">{{ profile.name }}</h2>
              <div class="profile-meta">
                <span class="meta-item">
                  <icon-idcard class="meta-icon" />{{ profile.studentId }}
                </span>
                <span class="meta-item">
                  <icon-book class="meta-icon" />{{ profile.major }}
                </span>
                <span class="meta-item">
                  <icon-user-group class="meta-icon" />{{ profile.grade }}
                </span>
              </div>
              <div class="course-tags">
                <span class="course-tag-label">本学期选修：</span>
                <a-tag v-for="c in profile.courses" :key="c" size="small">{{ c }}</a-tag>
              </div>
            </div>
          </div>
        </a-card>

        <!-- 学情概况数据卡片 -->
        <a-card class="overview-card" title="学情概况" :bordered="false">
          <div class="overview-grid">
            <div
              v-for="item in overviewItems"
              :key="item.label"
              class="overview-item"
              :style="{ '--accent': item.color }"
            >
              <div class="overview-icon-wrap">
                <component :is="item.icon" class="overview-icon" />
              </div>
              <div class="overview-data">
                <span class="overview-value">{{ item.value }}</span>
                <span class="overview-unit">{{ item.unit }}</span>
              </div>
              <span class="overview-label">{{ item.label }}</span>
            </div>
          </div>
        </a-card>

        <!-- 学习时长分布 -->
        <a-card class="chart-card" title="学习时长分布" :bordered="false">
          <div class="chart-wrapper">
            <div ref="donutChartRef" class="donut-chart"></div>
            <div class="chart-legend">
              <div
                v-for="(item, i) in timeDistribution"
                :key="item.name"
                class="legend-item"
              >
                <span class="legend-dot" :style="{ background: donutColors[i] }"></span>
                <span class="legend-name">{{ item.name }}</span>
                <span class="legend-val">{{ item.value }}h</span>
                <span class="legend-pct">{{ getPercent(item.value) }}%</span>
              </div>
            </div>
          </div>
        </a-card>
      </div>

      <!-- ========== 右侧区域 ========== -->
      <div class="study-right">

        <!-- 学情预警列表 -->
        <a-card class="alert-card" :bordered="false">
          <template #title>
            <span class="alert-title">
              <icon-exclamation-circle-fill class="alert-title-icon" />
              学情预警
            </span>
          </template>
          <template #extra>
            <a-tag color="red" size="small">{{ alerts.length }} 条</a-tag>
          </template>

          <div v-if="alerts.length === 0" class="empty-alerts">
            <icon-check-circle-fill style="color: #00b42a; font-size: 24px;" />
            <p>暂无预警，学习状态良好！</p>
          </div>

          <div v-else class="alert-list">
            <div
              v-for="alert in alerts"
              :key="alert.id"
              class="alert-item"
              :class="`alert-${alert.level}`"
            >
              <div class="alert-dot"></div>
              <div class="alert-content">
                <div class="alert-header">
                  <span class="alert-course">{{ alert.course }}</span>
                  <a-tag :color="alert.level === 'error' ? 'red' : 'orange'" size="small">
                    {{ alert.level === 'error' ? '严重' : '提醒' }}
                  </a-tag>
                </div>
                <p class="alert-reason">{{ alert.reason }}</p>
                <span class="alert-date">{{ alert.date }}</span>
              </div>
            </div>
          </div>
        </a-card>

        <!-- 日历提醒 -->
        <a-card class="calendar-card" title="日程提醒" :bordered="false">
          <a-calendar
            v-model="currentDate"
            :panel-only="true"
            class="study-calendar"
          >
            <template #date="{ date }">
              <div class="calendar-cell">
                <span class="date-num">{{ date.date() }}</span>
                <div class="event-dots">
                  <span
                    v-for="ev in getEventsForDate(date)"
                    :key="ev.id"
                    class="event-dot"
                    :class="`ev-${ev.type}`"
                  >
                    <a-tooltip :content="ev.title">
                      <span class="dot-inner"></span>
                    </a-tooltip>
                  </span>
                </div>
              </div>
            </template>
          </a-calendar>

          <!-- 本月事件列表 -->
          <div class="upcoming-list">
            <div class="upcoming-header">即将到期</div>
            <div
              v-for="ev in upcomingEvents"
              :key="ev.id"
              class="upcoming-item"
              :class="`ev-bg-${ev.type}`"
            >
              <div class="upcoming-meta">
                <span class="upcoming-type-dot" :class="`ev-${ev.type}`"></span>
                <span class="upcoming-title">{{ ev.title }}</span>
              </div>
              <span class="upcoming-date">{{ ev.dueDate }}</span>
            </div>
          </div>
        </a-card>
      </div>
    </div>

    <!-- 全局加载态 -->
    <div v-else class="page-loading">
      <a-spin size="large" />
      <p>加载学情数据...</p>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { ref, computed, onMounted, onUnmounted } from 'vue';
  import dayjs, { Dayjs } from 'dayjs';
  import * as echarts from 'echarts';
  import {
    queryStudyOverview,
    queryStudyAlerts,
    queryTimeDistribution,
    queryStudyCalendar,
  } from '@/api/user-center';
  import {
    IconIdcard,
    IconBook,
    IconUserGroup,
    IconClockCircle,
    IconMessage,
    IconInteraction,
    IconTrophy,
    IconCheckCircleFill,
    IconExclamationCircleFill,
    IconCalendar,
  } from '@arco-design/web-vue/es/icon';

  // ========== 类型 ==========
  interface Alert {
    id: string;
    course: string;
    reason: string;
    date: string;
    level: 'warning' | 'error';
  }

  interface CalendarEvent {
    id: string;
    title: string;
    dueDate: string;
    type: 'assignment' | 'exam' | 'experiment';
    dueDayjs: Dayjs;
  }

  // ========== 状态 ==========
  const loading = ref(false);
  const currentDate = ref(dayjs());
  const donutChartRef = ref<HTMLElement | null>(null);
  let donutChart: echarts.ECharts | null = null;

  // ========== 学生画像（TODO: 替换为 GET /api/v1/users/me + /api/v1/user-center/overview） ==========
  const profile = ref({
    name: '卡布奇',
    studentId: '2021012345',
    major: '计算机科学与技术',
    grade: '大三',
    courses: ['计算机组成原理', '操作系统', '计算机网络', '算法设计'],
  });

  // ========== 学情概况数据 ==========
  const overview = ref({
    cloudTime: 42,
    discussions: 8,
    interactions: 17,
    avgScore: 91,
    attendance: 15,
    alerts: 3,
  });

  const overviewItems = computed(() => [
    {
      label: '云端时长',
      value: overview.value.cloudTime,
      unit: 'h',
      icon: IconClockCircle,
      color: '#165DFF',
    },
    {
      label: '讨论次数',
      value: overview.value.discussions,
      unit: '次',
      icon: IconMessage,
      color: '#0fc6c2',
    },
    {
      label: '互动次数',
      value: overview.value.interactions,
      unit: '次',
      icon: IconInteraction,
      color: '#9254de',
    },
    {
      label: '平均成绩',
      value: overview.value.avgScore,
      unit: '分',
      icon: IconTrophy,
      color: '#f5a623',
    },
    {
      label: '考勤次数',
      value: overview.value.attendance,
      unit: '次',
      icon: IconCalendar,
      color: '#00b42a',
    },
    {
      label: '预警条数',
      value: overview.value.alerts,
      unit: '条',
      icon: IconExclamationCircleFill,
      color: '#f53f3f',
    },
  ]);

  // ========== 学习时长分布（TODO: GET /api/v1/user-center/study/time-distribution） ==========
  const timeDistribution = ref([
    { name: '视频学习', value: 18 },
    { name: 'AI助手', value: 10 },
    { name: '课堂签到', value: 8 },
    { name: '作业讨论', value: 6 },
  ]);

  const donutColors = ['#165DFF', '#0fc6c2', '#9254de', '#f5a623'];

  function getPercent(val: number): number {
    const total = timeDistribution.value.reduce((s, i) => s + i.value, 0);
    return Math.round((val / total) * 100);
  }

  function initDonutChart() {
    if (!donutChartRef.value) return;
    donutChart = echarts.init(donutChartRef.value);
    donutChart.setOption({
      tooltip: {
        trigger: 'item',
        backgroundColor: '#1d1d1f',
        borderColor: 'transparent',
        textStyle: { color: '#fff', fontSize: 12 },
        formatter: '{b}: {c}h ({d}%)',
        extraCssText: 'border-radius: 8px; padding: 8px 14px;',
      },
      legend: { show: false },
      series: [
        {
          type: 'pie',
          radius: ['52%', '78%'],
          center: ['50%', '50%'],
          avoidLabelOverlap: false,
          label: {
            show: true,
            position: 'center',
            formatter: () => {
              const total = timeDistribution.value.reduce(
                (s, i) => s + i.value,
                0
              );
              return `{total|${total}}{unit|h}`;
            },
            rich: {
              total: {
                fontSize: 28,
                fontWeight: 700,
                color: '#1d1d1f',
                letterSpacing: -1,
              },
              unit: {
                fontSize: 13,
                color: '#86909c',
                padding: [0, 0, 0, 2],
              },
            },
          },
          emphasis: {
            label: { show: true },
            scaleSize: 8,
          },
          data: timeDistribution.value.map((item, i) => ({
            ...item,
            itemStyle: { color: donutColors[i], borderRadius: 4 },
          })),
        },
      ],
    });
  }

  // ========== 学情预警（TODO: GET /api/v1/user-center/study/alerts） ==========
  const alerts = ref<Alert[]>([
    {
      id: '1',
      course: '操作系统',
      reason: '上课无故缺席',
      date: '2025.4.27',
      level: 'error',
    },
    {
      id: '2',
      course: '计算机网络',
      reason: '实验作业未提交',
      date: '2025.4.23',
      level: 'warning',
    },
    {
      id: '3',
      course: '算法设计与分析',
      reason: '未发布讨论',
      date: '2025.3.15',
      level: 'warning',
    },
  ]);

  // ========== 日历事件（TODO: GET /api/v1/user-center/study/calendar） ==========
  const calendarEvents = ref<CalendarEvent[]>([
    {
      id: 'e1',
      title: '计算机网络 - Task4 截止',
      dueDate: '4月8日',
      type: 'assignment',
      dueDayjs: dayjs().date(8),
    },
    {
      id: 'e2',
      title: '计算机组成原理 - 实验1 截止',
      dueDate: '4月10日',
      type: 'experiment',
      dueDayjs: dayjs().date(10),
    },
    {
      id: 'e3',
      title: '操作系统 - 期中考试',
      dueDate: '4月18日',
      type: 'exam',
      dueDayjs: dayjs().date(18),
    },
    {
      id: 'e4',
      title: '算法设计 - 作业3 截止',
      dueDate: '4月22日',
      type: 'assignment',
      dueDayjs: dayjs().date(22),
    },
  ]);

  function getEventsForDate(date: Dayjs): CalendarEvent[] {
    return calendarEvents.value.filter(
      (ev) =>
        ev.dueDayjs.month() === date.month() &&
        ev.dueDayjs.date() === date.date()
    );
  }

  const upcomingEvents = computed(() =>
    calendarEvents.value
      .filter((ev) => ev.dueDayjs.isAfter(dayjs().subtract(1, 'day')))
      .sort((a, b) => a.dueDayjs.valueOf() - b.dueDayjs.valueOf())
      .slice(0, 4)
  );

  const resizeObserver = new ResizeObserver(() => donutChart?.resize());

  onMounted(async () => {
    loading.value = true;
    try {
      const [overviewRes, alertRes, distRes, calRes] = await Promise.all([
        queryStudyOverview(),
        queryStudyAlerts(),
        queryTimeDistribution(),
        queryStudyCalendar(),
      ]);
      overview.value = overviewRes.data;
      alerts.value = alertRes.data;
      timeDistribution.value = distRes.data;
      calendarEvents.value = calRes.data.map((ev: any) => ({
        ...ev,
        dueDayjs: dayjs(ev.dueDayjs || undefined)
      }));
    } catch {
      // 真实后端暂时不可用时的降级策略，留存预设的假数据
      await new Promise((r) => setTimeout(r, 300));
    } finally {
      loading.value = false;
    }
    // 等 DOM 渲染后初始化图表
    setTimeout(initDonutChart, 50);
    if (donutChartRef.value) resizeObserver.observe(donutChartRef.value);
  });

  onUnmounted(() => {
    donutChart?.dispose();
    resizeObserver.disconnect();
  });
</script>

<style scoped lang="less">
  .study-page {
    padding: 0 20px 20px;
    min-height: 100%;
    background: var(--color-bg-1);
  }

  .study-layout {
    display: grid;
    grid-template-columns: 1fr 360px;
    gap: 16px;
    margin-top: 12px;
  }

  .study-left,
  .study-right {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  // ========== 画像卡片 ==========
  .profile-card {
    background: linear-gradient(135deg, #165dff 0%, #0fc6c2 100%);
    border-radius: 12px;
    color: #fff;

    :deep(.arco-card-body) {
      padding: 20px 24px;
    }
  }

  .profile-inner {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .avatar-area {
    position: relative;
    flex-shrink: 0;
  }

  .profile-tag {
    position: absolute;
    bottom: -4px;
    left: 50%;
    transform: translateX(-50%);
    white-space: nowrap;
  }

  .profile-name {
    font-size: 22px;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.3px;
    margin: 0 0 8px;
  }

  .profile-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 10px;
  }

  .meta-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.85);
  }

  .meta-icon {
    font-size: 13px;
    opacity: 0.7;
  }

  .course-tags {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 5px;
  }

  .course-tag-label {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.7);
  }

  :deep(.profile-card .arco-tag) {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.3);
    color: #fff;
  }

  // ========== 概况网格 ==========
  .overview-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }

  .overview-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 14px 10px;
    background: var(--color-fill-1);
    border-radius: 10px;
    border: 1px solid var(--color-border-1);
    transition: box-shadow 0.2s ease, transform 0.15s ease;

    &:hover {
      box-shadow: rgba(0, 0, 0, 0.08) 0 4px 16px;
      transform: translateY(-2px);
    }
  }

  .overview-icon-wrap {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: color-mix(in srgb, var(--accent) 12%, transparent);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 8px;
  }

  .overview-icon {
    font-size: 18px;
    color: var(--accent);
  }

  .overview-data {
    display: flex;
    align-items: baseline;
    gap: 2px;
    margin-bottom: 3px;
  }

  .overview-value {
    font-size: 24px;
    font-weight: 700;
    color: var(--color-text-1);
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.5px;
    line-height: 1;
  }

  .overview-unit {
    font-size: 12px;
    color: var(--color-text-3);
  }

  .overview-label {
    font-size: 11px;
    color: var(--color-text-3);
  }

  // ========== 图表 ==========
  .chart-wrapper {
    display: flex;
    gap: 20px;
    align-items: center;
  }

  .donut-chart {
    width: 180px;
    height: 180px;
    flex-shrink: 0;
  }

  .chart-legend {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }

  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 3px;
    flex-shrink: 0;
  }

  .legend-name {
    flex: 1;
    color: var(--color-text-2);
  }

  .legend-val {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    color: var(--color-text-1);
    min-width: 32px;
    text-align: right;
  }

  .legend-pct {
    font-size: 11px;
    color: var(--color-text-3);
    min-width: 34px;
    text-align: right;
  }

  // ========== 预警列表 ==========
  .alert-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
    font-weight: 600;
  }

  .alert-title-icon {
    color: #f53f3f;
    font-size: 15px;
  }

  .alert-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .alert-item {
    display: flex;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 8px;
    border-left: 3px solid;
    transition: box-shadow 0.15s;

    &.alert-error {
      border-left-color: #f53f3f;
      background: rgba(245, 63, 63, 0.05);
    }

    &.alert-warning {
      border-left-color: #ff7d00;
      background: rgba(255, 125, 0, 0.06);
    }

    &:hover {
      box-shadow: rgba(0, 0, 0, 0.08) 0 2px 10px;
    }
  }

  .alert-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-top: 4px;
    flex-shrink: 0;
    background: currentColor;

    .alert-error & { color: #f53f3f; }
    .alert-warning & { color: #ff7d00; }
  }

  .alert-content {
    flex: 1;
    min-width: 0;
  }

  .alert-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 3px;
  }

  .alert-course {
    font-size: 13px;
    font-weight: 600;
    color: var(--color-text-1);
  }

  .alert-reason {
    margin: 0;
    font-size: 12px;
    color: var(--color-text-2);
  }

  .alert-date {
    font-size: 11px;
    color: var(--color-text-4);
    margin-top: 3px;
    display: block;
  }

  .empty-alerts {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 20px 0;
    gap: 8px;
    color: var(--color-text-3);
    font-size: 13px;
  }

  // ========== 日历 ==========
  .study-calendar {
    :deep(.arco-calendar-header) {
      padding: 8px 12px;
    }

    :deep(.arco-calendar-cell) {
      padding: 2px;
    }
  }

  .calendar-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-height: 28px;
    padding: 2px 0;
  }

  .date-num {
    font-size: 12px;
    color: var(--color-text-2);
    line-height: 1;
    margin-bottom: 2px;
  }

  .event-dots {
    display: flex;
    gap: 2px;
    flex-wrap: wrap;
    justify-content: center;
  }

  .event-dot .dot-inner {
    display: block;
    width: 5px;
    height: 5px;
    border-radius: 50%;
  }

  .ev-assignment .dot-inner { background: #165dff; }
  .ev-exam .dot-inner { background: #f53f3f; }
  .ev-experiment .dot-inner { background: #9254de; }

  // 即将到期列表
  .upcoming-list {
    margin-top: 14px;
    border-top: 1px solid var(--color-border-1);
    padding-top: 12px;
  }

  .upcoming-header {
    font-size: 12px;
    font-weight: 600;
    color: var(--color-text-3);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }

  .upcoming-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 10px;
    border-radius: 7px;
    margin-bottom: 5px;
    font-size: 12px;
  }

  .ev-bg-assignment { background: rgba(22, 93, 255, 0.07); }
  .ev-bg-exam { background: rgba(245, 63, 63, 0.07); }
  .ev-bg-experiment { background: rgba(146, 84, 222, 0.07); }

  .upcoming-meta {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .upcoming-type-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .upcoming-title {
    color: var(--color-text-1);
    font-weight: 500;
    letter-spacing: -0.1px;
  }

  .upcoming-date {
    color: var(--color-text-3);
    white-space: nowrap;
  }

  // ========== 全页加载 ==========
  .page-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 0;
    gap: 16px;
    color: var(--color-text-3);
    font-size: 14px;
  }

  // ========== 响应式 ==========
  @media (max-width: 900px) {
    .study-layout {
      grid-template-columns: 1fr;
    }
  }
</style>
