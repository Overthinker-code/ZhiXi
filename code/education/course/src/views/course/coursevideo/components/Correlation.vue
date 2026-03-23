<template>
  <div
    ref="barChart"
    style=" width: 430px;height: 500px; margin-left: 35px"
  ></div>
</template>

<script>
  import * as echarts from 'echarts';

  export default {
    name: 'BarChart',
    props: {
      values: {
        type: Array,
        required: true,
      },
    },
    data() {
      return {
        chart: null,
        categories: ['清晰度', '互动性', '正确性', '内容深度', '全面度'], // 固定的类别
      };
    },
    mounted() {
      this.initChart();
    },
    methods: {
      initChart() {
        const chartDom = this.$refs.barChart;
        this.chart = echarts.init(chartDom);

        this.chart.setOption({
          xAxis: {
            type: 'value',
            min: 0,
            max: 10,
            interval: 1,
            axisLabel: {
              formatter: '{value}',
            },
          },
          yAxis: {
            type: 'category',
            data: this.categories,
            axisTick: {
              show: false,
            },
          },
          series: [
            {
              color: '#4086ff',
              data: this.values,
              type: 'bar',
              barWidth: '50%', // 条形图宽度
              itemStyle: {
                barBorderRadius: 10, // 四个角都有相同的圆角
              },

              label: {
                show: true,
                position: 'right',
              },
            },
          ],
        });
      },
      updateChart() {
        if (this.chart) {
          this.chart.setOption({
            series: [
              {
                data: this.values,
              },
            ],
          });
        }
      },
    },
    watch: {
      values: {
        deep: true,
        handler() {
          this.updateChart();
        },
      },
    },
  };
</script>

<style scoped>
  /* 可以根据需要添加样式 */
</style>
