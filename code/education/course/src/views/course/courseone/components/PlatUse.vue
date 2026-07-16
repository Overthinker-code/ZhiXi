<template>
  <div
    class="linechart"
    ref="lineChart"
    style="
      align-items: center;
      justify-content: center;
      width: 90%;
      height: 90%;
      margin: 0 auto;
      padding-bottom: 100px;
    "
  >
  </div>
</template>

<script>
  import * as echarts from 'echarts';
  import { defineComponent, onMounted, ref } from 'vue';

  export default defineComponent({
    name: 'LineChart',
    setup() {
      const lineChart = ref(null);

      onMounted(() => {
        const chart = echarts.init(lineChart.value);
        const today = new Date();
        const dates = Array.from({ length: 7 }, (_, i) => {
          const date = new Date(today);
          date.setDate(today.getDate() - (6 - i)); // 倒序排过去7天
          return date.toISOString().split('T')[0]; // 保留 yyyy-mm-dd 格式
        });

        const hours = [100, 105, 103, 108, 102, 91, 126]; // 示例数据

        const option = {
          tooltip: {
            trigger: 'item',
            padding: 5,
            textStyle: {
              fontSize: 12, // 小一点
              color: '#333',
              fontFamily: 'Microsoft YaHei',
            },
          },
          grid: {
            left: '3%',
            right: '5%',
            bottom: '3%',
            containLabel: true,
            backgroundColor: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                {
                  offset: 0,
                  color: '#1fdbff', // 渐变色的起始颜色
                },
                {
                  offset: 1,
                  color: '#6f42fb', // 渐变色的结束颜色
                },
              ],
              global: false, // 缺省为 false
            },
          },
          xAxis: {
            type: 'category',
            boundaryGap: false,
            data: dates,
            name: '日期',
            nameLocation: 'end', // 将单位显示在x轴的末端
            nameTextStyle: {
              // 单位的样式
              padding: [0, 0, 0, 20], // 上右下左的内边距
            },
          },
          yAxis: {
            type: 'value',
            axisLabel: {
              formatter: '{value} ',
            },
            name: '小时',
            nameLocation: 'end', // 将单位显示在y轴的末端
            nameTextStyle: {
              // 单位的样式
              padding: [0, 20, 0, 0], // 上右下左的内边距
              fontSize: 12,
              color: '#888',
              fontFamily: 'Microsoft YaHei',
              align: 'center',
            },
            interval: 20,
          },
          series: [
            {
              name: '平台使用时间',
              type: 'line',
              smooth: true, // 开启平滑曲线
              data: hours,
              itemStyle: {
                color: '#ff6347', // 点的颜色
              },
              areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: '#daebff' },
                  { offset: 1, color: '#ffffff' },
                ]),
              },
              lineStyle: {
                width: 2,
                color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  {
                    offset: 0,
                    color: '#1fdbff', // 渐变色的起始颜色
                  },
                  {
                    offset: 1,
                    color: '#6f42fb', // 渐变色的结束颜色
                  },
                ]), // 渐变色的设置
              },
            },
          ],
        };
        chart.setOption(option);
      });

      return {
        lineChart,
      };
    },
  });
</script>

<style>
  .linechart > canvas {
    width: 90% !important;
  }

  /* .linechart>div {
  width: 100% !important;
} */
</style>
