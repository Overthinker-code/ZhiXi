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
  import type { PortraitDimension } from '../learningPortraitViewModel';
  import { buildCapabilityChartAccessibility } from './chartAccessibility';

  const props = withDefaults(
    defineProps<{
      dimensions: PortraitDimension[];
      height?: string;
    }>(),
    {
      height: '300px',
    }
  );

  const accessibility = computed(() => buildCapabilityChartAccessibility(props.dimensions));
  const hasCompletePreviousComparison = computed(
    () => props.dimensions.length > 0 && props.dimensions.every((item) => item.previous !== null)
  );

  const chartOptions = computed(() => ({
    animationDuration: 700,
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15, 23, 42, 0.94)',
      borderWidth: 0,
      textStyle: { color: '#ffffff', fontSize: 12 },
    },
    legend: {
      show: false,
    },
    radar: {
      center: ['50%', '43%'],
      radius: '76%',
      splitNumber: 4,
      indicator: props.dimensions.map((item) => ({
        name: `${item.label}\n${Math.round(item.value)}`,
        max: 100,
      })),
      axisName: {
        color: '#334155',
        fontSize: 11,
        fontWeight: 600,
        lineHeight: 17,
      },
      splitArea: {
        areaStyle: {
          color: [
            'rgba(99, 102, 241, 0.018)',
            'rgba(99, 102, 241, 0.035)',
            'rgba(99, 102, 241, 0.055)',
            'rgba(99, 102, 241, 0.075)',
          ],
        },
      },
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.24)' } },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.22)' } },
    },
    series: [
      {
        type: 'radar',
        symbolSize: 5,
        data: [
          {
            name: '当前画像',
            value: props.dimensions.map((item) => item.value),
            symbol: 'circle',
            lineStyle: { color: '#6366f1', width: 2.2 },
            itemStyle: { color: '#6366f1' },
            areaStyle: { color: 'rgba(99, 102, 241, 0.2)' },
          },
          ...(hasCompletePreviousComparison.value
            ? [
                {
                  name: '30 天前',
                  value: props.dimensions.map((item) => item.previous),
                  symbol: 'diamond',
                  symbolSize: 4,
                  lineStyle: { color: '#a7b1c2', width: 1.4, type: 'dashed' },
                  itemStyle: { color: '#a7b1c2' },
                  areaStyle: { color: 'rgba(148, 163, 184, 0.04)' },
                },
              ]
            : []),
        ],
      },
    ],
  }));
</script>
