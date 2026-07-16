// chartConfig.js
export const chartData1 = [
  { value: 3.5, name: '计算机组成原理', itemStyle: { color: '#313ca9' } },
  { value: 3.1, name: '计算机网络', itemStyle: { color: '#6399ca' } },
  { value: 2.7, name: '操作系统', itemStyle: { color: '#249eff' } },
  { value: 2.5, name: '算法设计与分析' },
];

export const chartOption1 = {
  tooltip: {
    trigger: 'item',
    formatter: (params) => {
      return `${params.marker} ${params.name} ${params.value}h`;
    },
  },
  series: [
    {
      name: '',
      type: 'pie',
      radius: ['50%', '70%'],
      avoidLabelOverlap: false,
      label: {
        show: true,
        position: 'outside',
        formatter: '\n{name|{b}}\n{percent|{d}%}',
        rich: {
          name: {
            fontSize: 14,
            color: '#333',
            fontFamily: 'Microsoft YaHei',
            align: 'center',
            lineHeight: 15,
          },
          percent: {
            fontSize: 13,
            color: '#888',
            fontFamily: 'Microsoft YaHei',
            align: 'center',
            lineHeight: 20,
          },
          value: {
            fontSize: 13,
            color: '#888',
            fontFamily: 'Microsoft YaHei',
            align: 'center',
            lineHeight: 20,
          },
        },
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 18,
          fontWeight: 'bold',
        },
      },
      labelLine: {
        show: true,
      },
      data: chartData1,
    },
  ],
};
