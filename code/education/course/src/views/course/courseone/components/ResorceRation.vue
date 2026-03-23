<template>
  <div
    ref="doughnutChart"
    style="
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      height: 90%;
      margin-bottom: 140px;
    "
  >
  </div>
</template>

<script>
  import * as echarts from 'echarts';
  import { defineComponent, onMounted, ref } from 'vue';

  export default defineComponent({
    name: 'DoughnutChart',
    setup() {
      const doughnutChart = ref(null);

      onMounted(() => {
        const chart = echarts.init(doughnutChart.value);
        const option = {
          tooltip: {
            trigger: 'item',
            formatter: '{a} <br/>{b} : {c} ({d}%)',
          },
          legend: {
            orient: 'horizontal', // 设置图例布局方式为水平
            left: 'center', // 设置图例水平居中
            bottom: '0', // 设置图例显示在底部
            data: ['文档', '作业', '视频', '图片'],
          },
          series: [
            {
              name: '平台实时动态',
              type: 'pie',
              radius: ['40%', '55%'], // 外圆环半径
              center: ['50%', '50%'],
              label: {
                show: true,
                position: 'outside',
                formatter: '{name|{b}}\n{percent|{d}%}',
                rich: {
                  name: {
                    fontSize: 14,
                    color: '#333',
                    fontWeight: 'bold',
                    fontFamily: 'Microsoft YaHei',
                    align: 'center',
                    lineHeight: 20,
                  },
                  percent: {
                    fontSize: 13,
                    color: '#888',
                    fontFamily: 'Microsoft YaHei',
                    align: 'center',
                    lineHeight: 20,
                  },
                },
              },
              data: [
                { value: 20.33, name: '文档', itemStyle: { color: '#249eff' } },
                { value: 10, name: '作业', itemStyle: { color: '#6399ca' } },
                { value: 60.23, name: '视频', itemStyle: { color: '#21ccff' } },
                { value: 10.17, name: '图片', itemStyle: { color: '#313ca9' } },
              ],
              emphasis: {
                itemStyle: {
                  shadowBlur: 10,
                  shadowOffsetX: 0,
                  shadowColor: 'rgba(0, 0, 0, 0.5)',
                },
              },
            },
          ],
        };
        chart.setOption(option);
      });

      return {
        doughnutChart,
      };
    },
  });
</script>
