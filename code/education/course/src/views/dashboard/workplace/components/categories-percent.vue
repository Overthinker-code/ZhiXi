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
  import { computed, ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import useLoading from '@/hooks/loading';
  import useChartOption from '@/hooks/chart-option';
  import { queryContentDistribution } from '@/api/dashboard';

  const { loading } = useLoading();
  const { t } = useI18n();
  const total = ref(9285);
  const distribution = ref({
    resources: 5179,
    courses: 2301,
    homework: 1116,
    discussions: 689,
  });

  const chartItems = computed(() => [
    {
      value: [distribution.value.resources],
      name: t('workplace.category.resources'),
      itemStyle: {
        color: '#1677ff',
      },
    },
    {
      value: [distribution.value.courses],
      name: t('workplace.category.courses'),
      itemStyle: {
        color: '#0f9d8a',
      },
    },
    {
      value: [distribution.value.homework],
      name: t('workplace.category.homework'),
      itemStyle: {
        color: '#00b2c9',
      },
    },
    {
      value: [distribution.value.discussions],
      name: t('workplace.category.discussions'),
      itemStyle: {
        color: '#f59e0b',
      },
    },
  ]);

  const fetchDistribution = async () => {
    try {
      const { data } = await queryContentDistribution();
      total.value = data.total;
      data.items.forEach((item) => {
        if (item.name === 'resources') distribution.value.resources = item.value;
        if (item.name === 'courses') distribution.value.courses = item.value;
        if (item.name === 'homework') distribution.value.homework = item.value;
        if (item.name === 'discussions')
          distribution.value.discussions = item.value;
      });
    } catch (error) {
      // keep fallback values for demo stability
    }
  };

  fetchDistribution();

  const { chartOption } = useChartOption((isDark) => {
    return {
      legend: {
        left: 'center',
        data: [
          t('workplace.category.resources'),
          t('workplace.category.courses'),
          t('workplace.category.homework'),
          t('workplace.category.discussions'),
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
              text: total.value.toLocaleString(),
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
          data: chartItems.value,
        },
      ],
    };
  });
</script>

<style scoped lang="less"></style>
