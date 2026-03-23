<template>
  <a-spin :loading="loading" style="width: 100%">
    <a-card
      class="general-card"
      :header-style="{ paddingBottom: '0' }"
      :body-style="{
        padding: '20px',
      }"
    >
      <template #title>
        {{ $t('workplace.categoriesPercent') }}
      </template>
      <Chart height="310px" :option="chartOption" />
    </a-card>
  </a-spin>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import useLoading from '@/hooks/loading';
  import useChartOption from '@/hooks/chart-option';

  const { loading } = useLoading();
  const { t } = useI18n();
  const { chartOption } = useChartOption((isDark) => {
    return {
      legend: {
        left: 'center',
        data: [
          t('workplace.category.sqlBasics'),
          t('workplace.category.indexing'),
          t('workplace.category.transaction'),
          t('workplace.category.design'),
        ],
        bottom: 0,
        icon: 'circle',
        itemWidth: 8,
        textStyle: {
          color: isDark ? 'rgba(255, 255, 255, 0.7)' : '#4E5969',
        },
        itemStyle: {
          borderWidth: 0,
        },
      },
      tooltip: {
        show: true,
        trigger: 'item',
      },
      graphic: {
        elements: [
          {
            type: 'text',
            left: 'center',
            top: '40%',
            style: {
              text: t('workplace.categories.total'),
              textAlign: 'center',
              fill: isDark ? '#ffffffb3' : '#4E5969',
              fontSize: 14,
            },
          },
          {
            type: 'text',
            left: 'center',
            top: '50%',
            style: {
              text: '9,285',
              textAlign: 'center',
              fill: isDark ? '#ffffffb3' : '#1D2129',
              fontSize: 16,
              fontWeight: 500,
            },
          },
        ],
      },
      series: [
        {
          type: 'pie',
          radius: ['50%', '70%'],
          center: ['50%', '50%'],
          label: {
            formatter: '{d}%',
            fontSize: 14,
            color: isDark ? 'rgba(255, 255, 255, 0.7)' : '#4E5969',
          },
          itemStyle: {
            borderColor: isDark ? '#232324' : '#fff',
            borderWidth: 1,
          },
          data: [
            {
              value: [3342],
              name: t('workplace.category.sqlBasics'),
              itemStyle: {
                color: isDark ? '#1677ff' : '#1677ff',
              },
            },
            {
              value: [2420],
              name: t('workplace.category.indexing'),
              itemStyle: {
                color: isDark ? '#0f9d8a' : '#0f9d8a',
              },
            },
            {
              value: [1825],
              name: t('workplace.category.transaction'),
              itemStyle: {
                color: isDark ? '#00b2c9' : '#00b2c9',
              },
            },
            {
              value: [1698],
              name: t('workplace.category.design'),
              itemStyle: {
                color: isDark ? '#f59e0b' : '#f59e0b',
              },
            },
          ],
        },
      ],
    };
  });
</script>

<style scoped lang="less"></style>
