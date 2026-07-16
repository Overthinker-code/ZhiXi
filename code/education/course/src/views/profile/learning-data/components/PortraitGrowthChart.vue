<template>
  <Chart
    :options="chartOptions"
    :height="height"
    :aria-label="accessibility.label"
    :aria-summary="accessibility.summary"
    :accessible-headers="accessibility.headers"
    :accessible-rows="accessibility.rows"
  />
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import type { PortraitTrendSeries } from '../learningPortraitViewModel';
  import { buildGrowthChartAccessibility } from './chartAccessibility';

  const props = withDefaults(
    defineProps<{
      labels: string[];
      series: PortraitTrendSeries[];
      height?: string;
    }>(),
    {
      height: '300px',
    }
  );

  const accessibility = computed(() =>
    buildGrowthChartAccessibility(props.labels, props.series)
  );
  const symbolTypes = ['circle', 'rect', 'triangle', 'diamond'];
  const lineTypes = ['solid', 'dashed', 'dotted', 'solid'];

  const chartOptions = computed(() => ({
    color: props.series.map((item) => item.color),
    animationDuration: 700,
    animationEasing: 'cubicOut',
    grid: {
      top: 34,
      right: 10,
      bottom: 50,
      left: 42,
      containLabel: false,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.94)',
      borderWidth: 0,
      padding: [10, 12],
      textStyle: { color: '#ffffff', fontSize: 12 },
      axisPointer: {
        type: 'line',
        lineStyle: { color: 'rgba(99, 102, 241, 0.28)' },
      },
    },
    legend: {
      top: 4,
      left: 0,
      itemWidth: 13,
      itemHeight: 8,
      itemGap: 22,
      textStyle: { color: '#64748b', fontSize: 12 },
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: props.labels,
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.22)' } },
      axisTick: { show: false },
      axisLabel: {
        color: '#64748b',
        fontSize: 10,
        interval: props.labels.length > 10 ? 1 : 0,
        hideOverlap: true,
        margin: 12,
      },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      interval: 25,
      axisLabel: { color: '#64748b', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.15)' } },
    },
    series: props.series.map((item, index) => ({
      name: item.label,
      type: 'line',
      data: item.values,
      smooth: 0.38,
      connectNulls: false,
      symbol: symbolTypes[index % symbolTypes.length],
      showSymbol: true,
      symbolSize: index % 2 === 0 ? 5 : 6,
      lineStyle: {
        width: index === 0 ? 2.6 : 2.2,
        color: item.color,
        type: lineTypes[index % lineTypes.length],
      },
      itemStyle: {
        color: '#ffffff',
        borderColor: item.color,
        borderWidth: 2,
      },
      emphasis: { focus: 'series' },
      endLabel: { show: false },
    })),
  }));
</script>
