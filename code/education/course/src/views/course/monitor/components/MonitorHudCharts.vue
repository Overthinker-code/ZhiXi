<template>
  <div class="hud-charts" :class="{ 'hud-charts--alert': alertLowFocus }">
    <div class="hud-charts-head">
      <span class="hud-label">态势 · 专注率 / 抬头率</span>
      <span v-if="alertLowFocus" class="hud-alert-tag">低于阈值</span>
    </div>
    <Chart height="210px" :options="chartOption" />
  </div>
</template>

<script lang="ts" setup>
  import { computed, ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import Chart from '@/components/chart/index.vue';

  const focusSeries = ref([82, 76, 71, 58, 63]);
  const headSeries = ref([74, 72, 69, 64, 66]);
  const xLabels = ref(['T-4', 'T-3', 'T-2', 'T-1', '本课次']);

  const alertLowFocus = computed(() => {
    const last = focusSeries.value[focusSeries.value.length - 1];
    const minRecent = Math.min(...focusSeries.value.slice(-3));
    return minRecent < 60 || last < 60;
  });

  const lineColorFocus = computed(() =>
    alertLowFocus.value ? 'var(--zy-color-coral, #f97316)' : '#6366f1'
  );

  const chartOption = computed<EChartsOption>(() => ({
    backgroundColor: 'transparent',
    textStyle: { color: '#475569' },
    grid: { left: 48, right: 24, top: 28, bottom: 28 },
    legend: {
      data: ['专注率', '抬头率'],
      textStyle: { color: '#64748b', fontSize: 11 },
      top: 0,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: 'rgba(99, 102, 241, 0.25)',
      textStyle: { color: '#1e293b', fontSize: 12 },
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xLabels.value,
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.5)' } },
      axisLabel: { color: '#64748b', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitLine: { lineStyle: { color: 'rgba(226, 232, 240, 0.95)' } },
      axisLabel: {
        color: '#64748b',
        formatter: (v: number) => `${v}%`,
      },
    },
    series: [
      {
        name: '专注率',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        data: focusSeries.value,
        lineStyle: {
          width: 2.5,
          color: lineColorFocus.value,
        },
        itemStyle: { color: lineColorFocus.value },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: alertLowFocus.value
              ? [
                  { offset: 0, color: 'rgba(249, 115, 22, 0.2)' },
                  { offset: 1, color: 'rgba(249, 115, 22, 0)' },
                ]
              : [
                  { offset: 0, color: 'rgba(99, 102, 241, 0.18)' },
                  { offset: 1, color: 'rgba(99, 102, 241, 0)' },
                ],
          },
        },
      },
      {
        name: '抬头率',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: headSeries.value,
        lineStyle: {
          width: 2,
          color: '#0ea5e9',
        },
        itemStyle: { color: '#0ea5e9' },
      },
    ],
  }));
</script>

<style scoped lang="less">
  .hud-charts {
    border-radius: 14px;
    padding: 12px 14px 4px;
    border: 1px solid rgba(99, 102, 241, 0.14);
    background: linear-gradient(
      145deg,
      rgba(255, 255, 255, 0.95) 0%,
      rgba(238, 242, 255, 0.88) 100%
    );
    box-shadow: 0 6px 24px rgba(99, 102, 241, 0.08);
    margin-bottom: 16px;
    transition: box-shadow 0.3s ease;
  }

  .hud-charts--alert {
    animation: alert-pulse-light 2.2s ease-in-out infinite;
  }

  .hud-charts-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
  }

  .hud-label {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #4338ca;
  }

  .hud-alert-tag {
    font-size: 11px;
    font-weight: 700;
    padding: 2px 10px;
    border-radius: 999px;
    color: #fff;
    background: rgba(249, 115, 22, 0.92);
    box-shadow: 0 2px 12px rgba(249, 115, 22, 0.35);
  }

  @keyframes alert-pulse-light {
    0%,
    100% {
      box-shadow: 0 6px 24px rgba(99, 102, 241, 0.08);
    }
    50% {
      box-shadow:
        0 6px 24px rgba(99, 102, 241, 0.08),
        0 0 0 3px rgba(249, 115, 22, 0.12);
    }
  }
</style>
