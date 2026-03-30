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
  import { ref, onMounted, computed } from 'vue';
  import { useI18n } from 'vue-i18n';
  import useLoading from '@/hooks/loading';
  import useChartOption from '@/hooks/chart-option';
  import { queryDashboardCategories, CategoryItem } from '@/api/dashboard';

  const { loading, setLoading } = useLoading(true);
  const { t } = useI18n();
  const total = ref(0);
  const categories = ref<CategoryItem[]>([]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const { data } = await queryDashboardCategories();
      total.value = data.total;
      categories.value = data.categories;
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    } finally {
      setLoading(false);
    }
  };

  const colorPalette = ['#1677ff', '#0f9d8a', '#00b2c9', '#f59e0b', '#86efac', '#f472b6'];

  const { chartOption } = useChartOption((isDark) => {
    return {
      legend: {
        left: 'center',
        data: categories.value.map((item) => item.name),
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
          data: categories.value.map((item, index) => ({
            value: item.value,
            name: item.name,
            itemStyle: {
              color: colorPalette[index % colorPalette.length],
            },
          })),
        },
      ],
    };
  });

  onMounted(() => {
    fetchData();
  });
</script>

<style scoped lang="less"></style>
