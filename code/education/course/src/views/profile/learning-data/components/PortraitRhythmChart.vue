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
  import { buildRhythmChartAccessibility } from './chartAccessibility';

  const props = withDefaults(
    defineProps<{
      weekLabels: string[];
      dayLabels: string[];
      activity: number[][];
      hourLabels: string[];
      focusHours: number[];
      height?: string;
    }>(),
    { height: '154px' }
  );

  const normalizedFocusHours = computed(() =>
    props.focusHours.map((value) => Math.round((Number(value) || 0) * 10) / 10)
  );
  const focusAxisMax = computed(() => {
    const measuredMax = Math.max(0, ...normalizedFocusHours.value);
    return Math.max(1, Math.ceil((measuredMax + 0.2) * 2) / 2);
  });
  const accessibility = computed(() =>
    buildRhythmChartAccessibility(
      props.weekLabels,
      props.dayLabels,
      props.activity,
      props.hourLabels,
      normalizedFocusHours.value
    )
  );

  const chartOptions = computed(() => {
    const heatmap = props.activity.flatMap((row, rowIndex) =>
      row.map((value, columnIndex) => [columnIndex, rowIndex, value])
    );
    return {
      animationDuration: 620,
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(15, 23, 42, 0.94)',
        borderWidth: 0,
        textStyle: { color: '#fff', fontSize: 11 },
        formatter: (params: any) => {
          if (params.seriesType === 'heatmap') {
            const [dayIndex, weekIndex, value] = params.value;
            return `${props.weekLabels[weekIndex]} 周${props.dayLabels[dayIndex]}<br/>学习活跃度 ${Math.round(value)}`;
          }
          return `${params.name}: ${Number(params.value || 0).toFixed(1)} 小时`;
        },
      },
      grid: [
        { left: 46, top: 28, width: '42%', bottom: 24 },
        { left: '59%', right: 12, top: 28, bottom: 24 },
      ],
      xAxis: [
        {
          type: 'category',
          data: props.dayLabels,
          gridIndex: 0,
          position: 'top',
          axisTick: { show: false },
          axisLine: { show: false },
          axisLabel: { color: '#64748b', fontSize: 10 },
        },
        {
          type: 'category',
          data: props.hourLabels,
          gridIndex: 1,
          boundaryGap: false,
          axisTick: { show: false },
          axisLine: { lineStyle: { color: '#e5eaf2' } },
          axisLabel: { color: '#64748b', fontSize: 9 },
        },
      ],
      yAxis: [
        {
          type: 'category',
          data: props.weekLabels,
          gridIndex: 0,
          inverse: true,
          axisTick: { show: false },
          axisLine: { show: false },
          axisLabel: { color: '#64748b', fontSize: 10 },
        },
        {
          type: 'value',
          gridIndex: 1,
          min: 0,
          max: focusAxisMax.value,
          splitNumber: 3,
          axisTick: { show: false },
          axisLine: { show: false },
          axisLabel: {
            color: '#64748b',
            fontSize: 9,
            formatter: (value: number) =>
              Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1),
          },
          splitLine: { lineStyle: { color: '#eef1f6' } },
        },
      ],
      visualMap: {
        min: 0,
        max: 100,
        show: false,
        inRange: { color: ['#f2f0ff', '#d9d5ff', '#a99ff7', '#6255e7'] },
      },
      graphic: [
        {
          type: 'text',
          left: '59%',
          top: 2,
          style: {
            text: '单次专注时长（小时）',
            fill: '#64748b',
            font: '11px sans-serif',
          },
        },
      ],
      series: [
        {
          type: 'heatmap',
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: heatmap,
          itemStyle: { borderColor: '#ffffff', borderWidth: 4, borderRadius: 3 },
          label: {
            show: true,
            fontSize: 8,
            rich: {
              light: { color: '#334155', fontSize: 8 },
              dark: { color: '#ffffff', fontSize: 8, fontWeight: 600 },
            },
            formatter: (params: any) => {
              const value = Number(params.value?.[2] || 0);
              if (value <= 0) return '';
              return `{${value >= 55 ? 'dark' : 'light'}|${Math.round(value)}}`;
            },
          },
          emphasis: { itemStyle: { shadowBlur: 5, shadowColor: 'rgba(98,85,231,.22)' } },
        },
        {
          type: 'line',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: normalizedFocusHours.value,
          smooth: 0.42,
          symbol: 'circle',
          showSymbol: true,
          symbolSize: 4,
          lineStyle: { width: 2, color: '#6255e7' },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(98,85,231,.18)' },
                { offset: 1, color: 'rgba(98,85,231,.01)' },
              ],
            },
          },
        },
      ],
    };
  });
</script>
