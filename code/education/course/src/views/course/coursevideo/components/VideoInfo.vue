<template>
  <div
    ref="chartContainer"
    class="focus-chart"
    role="img"
    aria-label="全天专注度曲线"
  ></div>
</template>

<script setup lang="ts">
  import * as echarts from 'echarts';
  import type { EChartsOption, EChartsType } from 'echarts';
  import { onBeforeUnmount, onMounted, ref } from 'vue';

  interface TooltipItem {
    axisValueLabel?: string;
    marker?: string;
    value?: number;
  }

  const chartContainer = ref<HTMLDivElement | null>(null);
  let chart: EChartsType | null = null;
  let resizeObserver: ResizeObserver | null = null;
  let initialFrame = 0;

  const timePoints = Array.from({ length: 96 }, (_, index) => {
    const totalMinutes = index * 15;
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(
      2,
      '0'
    )}`;
  });

  const focusAnchors = [
    8, 23, 49, 38, 55, 72, 78, 51, 76, 94, 50, 72, 75, 92, 51, 66, 36, 49,
  ];

  const focusData = timePoints.map((_, index) => {
    const position =
      (index / (timePoints.length - 1)) * (focusAnchors.length - 1);
    const leftIndex = Math.floor(position);
    const rightIndex = Math.min(leftIndex + 1, focusAnchors.length - 1);
    const progress = position - leftIndex;
    const easedProgress = (1 - Math.cos(Math.PI * progress)) / 2;
    return Math.round(
      focusAnchors[leftIndex] +
        (focusAnchors[rightIndex] - focusAnchors[leftIndex]) * easedProgress
    );
  });

  const visibleTimeLabels = new Set([
    '00:00',
    '02:30',
    '05:00',
    '07:30',
    '10:00',
    '12:30',
    '15:00',
    '17:30',
    '20:00',
    '22:30',
    '23:45',
  ]);

  const option: EChartsOption = {
    animationDuration: 700,
    animationEasing: 'cubicOut',
    grid: {
      top: 8,
      right: 14,
      bottom: 24,
      left: 44,
      containLabel: false,
    },
    tooltip: {
      trigger: 'axis',
      confine: true,
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderColor: '#dce3f4',
      borderWidth: 1,
      padding: [7, 10],
      extraCssText:
        'border-radius: 7px; box-shadow: 0 6px 18px rgba(47, 70, 132, 0.12);',
      textStyle: {
        color: '#26324b',
        fontSize: 11,
      },
      axisPointer: {
        type: 'line',
        snap: true,
        lineStyle: {
          color: '#8c9df7',
          width: 1,
          type: 'dashed',
        },
      },
      formatter: (params) => {
        const item = (
          Array.isArray(params) ? params[0] : params
        ) as TooltipItem;
        return [
          `<div style="color:#8992a8;font-size:10px;line-height:16px">${
            item.axisValueLabel ?? ''
          }</div>`,
          `<div style="display:flex;align-items:center;gap:6px;white-space:nowrap;font-weight:600;line-height:18px">`,
          `${
            item.marker ?? ''
          }<span>专注度</span><span style="margin-left:6px;color:#5665e8">${
            item.value ?? 0
          }%</span>`,
          '</div>',
        ].join('');
      },
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: timePoints,
      axisLine: {
        lineStyle: {
          color: '#dfe5f1',
          width: 1,
        },
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        interval: 0,
        color: '#8791a8',
        fontSize: 9,
        margin: 8,
        formatter: (value: string) =>
          visibleTimeLabels.has(value) ? value : '',
      },
      splitLine: {
        show: true,
        interval: 9,
        lineStyle: {
          color: '#edf1f8',
          width: 1,
          type: 'dashed',
        },
      },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      interval: 25,
      axisLine: {
        show: false,
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        color: '#8791a8',
        fontSize: 9,
        margin: 8,
        formatter: '{value}%',
      },
      splitLine: {
        lineStyle: {
          color: '#e9edf5',
          width: 1,
        },
      },
    },
    series: [
      {
        name: '专注度',
        type: 'line',
        data: focusData,
        smooth: 0.42,
        symbol: 'circle',
        symbolSize: 3,
        showSymbol: false,
        emphasis: {
          scale: 1.8,
          itemStyle: {
            borderColor: '#ffffff',
            borderWidth: 2,
          },
        },
        lineStyle: {
          color: '#5969ef',
          width: 2,
          cap: 'round',
          shadowColor: 'rgba(93, 105, 239, 0.18)',
          shadowBlur: 4,
          shadowOffsetY: 2,
        },
        itemStyle: {
          color: '#5969ef',
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(99, 116, 239, 0.28)' },
            { offset: 0.7, color: 'rgba(128, 153, 246, 0.08)' },
            { offset: 1, color: 'rgba(255, 255, 255, 0)' },
          ]),
        },
      },
    ],
  };

  const renderChart = () => {
    const container = chartContainer.value;
    if (!container || container.clientWidth <= 0 || container.clientHeight <= 0) return;
    if (!chart) {
      chart = echarts.init(container);
      chart.setOption(option);
      return;
    }
    chart.resize();
  };

  onMounted(() => {
    if (!chartContainer.value) return;
    resizeObserver = new ResizeObserver(renderChart);
    resizeObserver.observe(chartContainer.value);
    initialFrame = window.requestAnimationFrame(renderChart);
  });

  onBeforeUnmount(() => {
    resizeObserver?.disconnect();
    resizeObserver = null;
    window.cancelAnimationFrame(initialFrame);
    chart?.dispose();
    chart = null;
  });
</script>

<style scoped>
  .focus-chart {
    width: 100%;
    height: 142px;
    min-width: 0;
  }
</style>
