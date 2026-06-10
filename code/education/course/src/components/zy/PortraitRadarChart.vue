<template>
  <Chart :options="chartOptions" :height="height" />
</template>

<script setup lang="ts">
  import { computed } from 'vue';

  export interface RadarDimension {
    label: string;
    value: number;
    max?: number;
  }

  const props = withDefaults(
    defineProps<{
      dimensions: RadarDimension[];
      height?: string;
    }>(),
    {
      height: '280px',
    }
  );

  const chartOptions = computed(() => {
    const indicators = props.dimensions.map((d) => ({
      name: d.label,
      max: d.max ?? 100,
    }));
    const values = props.dimensions.map((d) => Math.max(0, Math.min(d.max ?? 100, d.value)));

    return {
      tooltip: { trigger: 'item' },
      radar: {
        indicator: indicators,
        radius: '62%',
        splitNumber: 4,
        axisName: {
          color: '#64748b',
          fontSize: 11,
        },
        splitArea: {
          areaStyle: {
            color: ['rgba(99, 102, 241, 0.02)', 'rgba(99, 102, 241, 0.06)'],
          },
        },
        axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.35)' } },
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.25)' } },
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: values,
              name: '学习画像',
              areaStyle: {
                color: 'rgba(99, 102, 241, 0.25)',
              },
              lineStyle: {
                color: '#6366f1',
                width: 2,
              },
              itemStyle: {
                color: '#6366f1',
              },
            },
          ],
          animationDuration: 800,
          animationEasing: 'cubicOut',
        },
      ],
    };
  });
</script>
