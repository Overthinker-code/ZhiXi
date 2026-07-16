<template>
  <figure
    class="zy-chart"
    :style="{ width, height }"
    :role="hasAccessibleAlternative ? 'group' : undefined"
    :aria-label="ariaLabel || undefined"
  >
    <VCharts
      v-if="renderChart"
      class="zy-chart__canvas"
      :option="options"
      :autoresize="autoResize"
      :aria-hidden="hasAccessibleAlternative ? 'true' : undefined"
    />
    <figcaption v-if="ariaSummary" class="zy-chart__sr-only">
      {{ ariaSummary }}
    </figcaption>
    <table v-if="accessibleHeaders.length && accessibleRows.length" class="zy-chart__sr-only">
      <caption>{{ tableCaption || `${ariaLabel}数据表` }}</caption>
      <thead>
        <tr>
          <th v-for="header in accessibleHeaders" :key="header" scope="col">
            {{ header }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, rowIndex) in accessibleRows" :key="rowIndex">
          <th scope="row">{{ row[0] }}</th>
          <td v-for="(cell, cellIndex) in row.slice(1)" :key="cellIndex">
            {{ cell }}
          </td>
        </tr>
      </tbody>
    </table>
  </figure>
</template>

<script lang="ts" setup>
  import { computed, ref, nextTick, type PropType } from 'vue';
  import { use } from 'echarts/core';
  import { CanvasRenderer } from 'echarts/renderers';
  import { BarChart, HeatmapChart, LineChart, PieChart, RadarChart } from 'echarts/charts';
  import {
    GridComponent,
    TooltipComponent,
    LegendComponent,
    DataZoomComponent,
    GraphicComponent,
    VisualMapComponent,
  } from 'echarts/components';
  import VCharts from 'vue-echarts';
  // import { useAppStore } from '@/store';

  use([
    CanvasRenderer,
    BarChart,
    LineChart,
    PieChart,
    RadarChart,
    HeatmapChart,
    GridComponent,
    TooltipComponent,
    LegendComponent,
    DataZoomComponent,
    GraphicComponent,
    VisualMapComponent,
  ]);

  type ChartTableCell = string | number;

  const props = defineProps({
    options: {
      type: Object,
      default() {
        return {};
      },
    },
    autoResize: {
      type: Boolean,
      default: true,
    },
    width: {
      type: String,
      default: '100%',
    },
    height: {
      type: String,
      default: '100%',
    },
    ariaLabel: {
      type: String,
      default: '',
    },
    ariaSummary: {
      type: String,
      default: '',
    },
    tableCaption: {
      type: String,
      default: '',
    },
    accessibleHeaders: {
      type: Array as PropType<string[]>,
      default: () => [],
    },
    accessibleRows: {
      type: Array as PropType<ChartTableCell[][]>,
      default: () => [],
    },
  });
  const hasAccessibleAlternative = computed(
    () => Boolean(props.ariaLabel || props.ariaSummary || props.accessibleRows.length)
  );
  // const appStore = useAppStore();
  // const theme = computed(() => {
  //   if (appStore.theme === 'dark') return 'dark';
  //   return '';
  // });
  const renderChart = ref(false);
  // wait container expand
  nextTick(() => {
    renderChart.value = true;
  });
</script>

<style scoped lang="less">
  .zy-chart {
    position: relative;
    display: block;
    min-width: 0;
    margin: 0;
  }

  .zy-chart__canvas {
    width: 100%;
    height: 100%;
  }

  .zy-chart__sr-only {
    position: absolute !important;
    width: 1px !important;
    height: 1px !important;
    padding: 0 !important;
    margin: -1px !important;
    overflow: hidden !important;
    clip: rect(0, 0, 0, 0) !important;
    white-space: nowrap !important;
    border: 0 !important;
  }

</style>
