<template>
  <div
    ref="videoLineChart"
    style="width: 100%; height: 400px; margin-bottom: 10px"
  ></div>
</template>

<script>
  import * as echarts from 'echarts';
  import { defineComponent, onMounted, ref } from 'vue';

  export default defineComponent({
    name: 'VideoLineChart',
    setup() {
      const videoLineChart = ref(null);
      const timePoints = [
        '00:00',
        '00:10',
        '00:20',
        '00:30',
        '00:40',
        '00:50',
        '01:10',
        '01:20',
        '01:30',
        '01:40',
        '01:50',
        '02:00',
        '02:10',
        '02:20',
        '02:30',
        '02:40',
        '02:50',
      ];
      const importanceData = [
        10, 20, 30, 25, 35, 45, 50, 40, 55, 60, 70, 40, 55, 60, 70, 35, 45, 50,
      ];
      const videoInfo = [
        { time: '00:00', content: '视频开始', keyInfo: '开场介绍' },
        { time: '00:10', content: '内容介绍', keyInfo: '介绍主题' },
        { time: '00:20', content: '核心观点', keyInfo: '详细讲解' },
        { time: '00:30', content: '案例分析', keyInfo: '实际应用' },
        { time: '00:40', content: '总结回顾', keyInfo: '重点总结' },
        { time: '00:50', content: '视频结束', keyInfo: '结束语' },
      ];

      onMounted(() => {
        const chart = echarts.init(videoLineChart.value);
        const option = {
          tooltip: {
            trigger: 'axis',
            formatter: (params) => {
              const time = params[0].name;
              const info = videoInfo.find((item) => item.time === time) || {};
              return `
                <div>
                  <h4>时间: ${time}</h4>
                  <p>内容: ${info.content || '无具体信息'}</p>
                  <p>关键信息: ${info.keyInfo || '无'}</p>
                </div>
              `;
            },
            backgroundColor: '#fff',
            borderColor: '#ccc',
            borderWidth: 2,
            textStyle: {
              color: '#000',
            },
            padding: [10, 15],
          },
          xAxis: {
            type: 'category',
            data: timePoints,
            boundaryGap: false,
          },
          yAxis: {
            type: 'value',
            min: 0,
            max: 100,
            axisLabel: {
              formatter: '{value} %',
            },
          },
          series: [
            {
              name: '重要度',
              type: 'line',
              smooth: true, // 开启平滑曲线
              data: importanceData,
              areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: '#daebff' },
                  { offset: 1, color: '#ffffff' },
                ]),
              },
              itemStyle: {
                color: '#1890ff',
              },
              lineStyle: {
                width: 4,
              },
            },
          ],
        };
        chart.setOption(option);
      });

      return {
        videoLineChart,
      };
    },
  });
</script>

<style scoped>
  /* 可以根据需要添加样式 */
</style>
