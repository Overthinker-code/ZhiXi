<template>
  <div class="chart-panel-root">
    <div v-if="loading" class="zy-panel-skeleton" aria-busy="true">
      <div class="zy-skeleton zy-skeleton--radar zy-bar" style="height: 289px" />
    </div>
    <div v-else-if="error" class="chart-panel-error">
      <span>{{ $t('workplace.loadFailedTip') }}</span>
      <a-button type="primary" size="small" @click="fetchData">{{ $t('workplace.retry') }}</a-button>
    </div>
    <a-card
      v-else
      class="general-card"
      :header-style="{ paddingBottom: 0 }"
      :body-style="{
        paddingTop: '20px',
      }"
      :title="$t('workplace.alertsTrend')"
    >
      <template #extra>
        <a-link>{{ $t('workplace.viewMore') }}</a-link>
      </template>
      <Chart height="289px" :options="chartOption" />
    </a-card>
  </div>
</template>

<script lang="ts" setup>
  import { ref } from 'vue';
  import { graphic } from 'echarts';
  import { useI18n } from 'vue-i18n';
  import { getTeacherAlertsTrend, type AlertsTrendItem } from '@/api/dashboard';
  import useChartOption from '@/hooks/chart-option';
  import { ToolTipFormatterParams } from '@/types/echarts';
  import { AnyObject } from '@/types/global';

  function graphicFactory(side: AnyObject) {
    return {
      type: 'text',
      bottom: '8',
      ...side,
      style: {
        text: '',
        textAlign: 'center',
        fill: '#4E5969',
        fontSize: 12,
      },
    };
  }
  const loading = ref(true);
  const error = ref<string | null>(null);
  const { t } = useI18n();
  const xAxis = ref<string[]>([]);
  const chartsData = ref<number[]>([]);
  const graphicElements = ref([
    graphicFactory({ left: '2.6%' }),
    graphicFactory({ right: 0 }),
  ]);
  const { chartOption } = useChartOption(() => {
    return {
      grid: {
        left: '2.6%',
        right: '0',
        top: '10',
        bottom: '30',
      },
      xAxis: {
        type: 'category',
        offset: 2,
        data: xAxis.value,
        boundaryGap: false,
        axisLabel: {
          color: '#4E5969',
          formatter(value: number, idx: number) {
            if (idx === 0) return '';
            if (idx === xAxis.value.length - 1) return '';
            return `${value}`;
          },
        },
        axisLine: {
          show: false,
        },
        axisTick: {
          show: false,
        },
        splitLine: {
          show: true,
          interval: (idx: number) => {
            if (idx === 0) return false;
            if (idx === xAxis.value.length - 1) return false;
            return true;
          },
          lineStyle: {
            color: '#E5E8EF',
          },
        },
      },
      yAxis: {
        type: 'value',
        axisLine: {
          show: false,
        },
        axisLabel: {
          formatter(value: number) {
            return `${value}`;
          },
        },
        splitLine: {
          show: true,
          lineStyle: {
            type: 'dashed',
            color: '#E5E8EF',
          },
        },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'line',
          lineStyle: {
            color: 'rgba(15, 23, 42, 0.4)',
            width: 1,
          },
          crossStyle: {
            color: 'rgba(15, 23, 42, 0.25)',
          },
        },
        formatter(params) {
          const [firstElement] = params as ToolTipFormatterParams[];
          return `<div>
            <p class="tooltip-title">${firstElement.axisValueLabel}</p>
            <div class="content-panel"><span>${t(
              'workplace.chart.tooltipLabel'
            )}</span><span class="tooltip-value">${Number(
              firstElement.value
            ).toLocaleString()}</span></div>
          </div>`;
        },
        className: 'echarts-tooltip-diy',
      },
      graphic: {
        elements: graphicElements.value,
      },
      series: [
        {
          data: chartsData.value,
          type: 'line',
          smooth: true,
          symbolSize: 12,
          emphasis: {
            focus: 'series',
            itemStyle: {
              borderWidth: 2,
            },
          },
          lineStyle: {
            width: 3,
            color: new graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#6366f1' },
              { offset: 0.45, color: '#8b5cf6' },
              { offset: 1, color: '#0ea5e9' },
            ]),
          },
          showSymbol: false,
          areaStyle: {
            opacity: 0.85,
            color: new graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(99, 102, 241, 0.28)' },
              { offset: 0.5, color: 'rgba(139, 92, 246, 0.12)' },
              { offset: 1, color: 'rgba(14, 165, 233, 0)' },
            ]),
          },
        },
      ],
    };
  });
  const fetchData = async () => {
    loading.value = true;
    error.value = null;
    xAxis.value = [];
    chartsData.value = [];
    try {
      const list: AlertsTrendItem[] = await getTeacherAlertsTrend(7);
      list.forEach((el, idx) => {
        xAxis.value.push(el.date);
        chartsData.value.push(el.alert_count);
        if (idx === 0) {
          graphicElements.value[0].style.text = el.date;
        }
        if (idx === list.length - 1) {
          graphicElements.value[1].style.text = el.date;
        }
      });
    } catch (err) {
      console.error('[content-chart] fetchData failed:', err);
      error.value = 'failed';
    } finally {
      loading.value = false;
    }
  };
  fetchData();
</script>

<style scoped lang="less">
  .chart-panel-root {
    width: 100%;
  }

  .chart-panel-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    height: 289px;
    color: rgb(var(--gray-6));
    font-size: 14px;
  }
</style>
