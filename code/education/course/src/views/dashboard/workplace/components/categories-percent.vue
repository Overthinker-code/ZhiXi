<template>
  <div class="chart-panel-root">
    <div v-if="loading" class="zy-panel-skeleton" aria-busy="true">
      <div class="zy-skeleton zy-skeleton--radar zy-bar" style="height: 310px" />
    </div>
    <a-card
      v-show="!loading"
      class="general-card"
      :header-style="{ paddingBottom: '0' }"
      :body-style="{
        padding: '20px',
      }"
    >
      <template #title>
        {{ $t('workplace.categoriesPercent') }}
      </template>
      <Chart height="310px" :options="chartOption" />
    </a-card>
  </div>
</template>

<script lang="ts" setup>
  import { ref, computed, onMounted } from 'vue';
  import { useI18n } from 'vue-i18n';
  import useLoading from '@/hooks/loading';
  import useChartOption from '@/hooks/chart-option';
  import { queryContentDistribution } from '@/api/dashboard';
  import { demoResourceDistribution } from '@/mock/demoData';

  const { loading, setLoading } = useLoading(true);
  const { t } = useI18n();
  const total = ref(demoResourceDistribution.total);
  const distribution = ref({
    resources:
      demoResourceDistribution.items.find((x) => x.name === 'resources')?.value ||
      5179,
    courses:
      demoResourceDistribution.items.find((x) => x.name === 'courses')?.value ||
      2301,
    homework:
      demoResourceDistribution.items.find((x) => x.name === 'homework')?.value ||
      1116,
    discussions:
      demoResourceDistribution.items.find((x) => x.name === 'discussions')
        ?.value || 689,
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
        color: '#8b5cf6',
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
    setLoading(true);
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
    } catch (err) {
      // keep demo fallback values
    } finally {
      setLoading(false);
    }
  };

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

  onMounted(() => {
    fetchDistribution();
  });
</script>

<style scoped lang="less">
  .chart-panel-root {
    width: 100%;
  }
</style>
