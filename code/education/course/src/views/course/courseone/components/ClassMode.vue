<template>
  <div
    ref="radarChart"
    style=" width: 90%;height: 400px; margin-bottom: 100px"
  ></div>
</template>

<script>
  import * as echarts from 'echarts';

  export default {
    name: 'RadarChart',
    data() {
      return {
        chart: null,
        radarIndicator: [
          { name: '测验', max: 240 },
          { name: '讨论', max: 240 },
          { name: '其它', max: 240 },
          { name: '实验', max: 240 },
          { name: '提问', max: 240 },
        ],
        actualSpendingData: [100, 230, 100, 100, 130],
      };
    },
    mounted() {
      this.initChart();
    },
    methods: {
      initChart() {
        const chartDom = this.$refs.radarChart;
        this.chart = echarts.init(chartDom);
        this.setOptions();
      },
      setOptions() {
        const option = {
          title: {},
          legend: {
            data: ['Allocated Budget', 'Actual Spending'],
          },
          radar: {
            indicator: this.radarIndicator,
          },
          series: [
            {
              type: 'radar',
              data: [
                {
                  value: this.actualSpendingData,
                },
              ],
            },
          ],
        };
        this.chart.setOption(option);
      },
    },
  };
</script>

<style scoped>
  /* 可以根据需要添加样式 */
</style>
