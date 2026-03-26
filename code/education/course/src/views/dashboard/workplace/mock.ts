import { GetParams } from '@/types/global';
import setupMock, { successResponseWrap } from '@/utils/setup-mock';
import dayjs from 'dayjs';
import Mock from 'mockjs';
import qs from 'query-string';

const textList = [
  {
    key: 1,
    clickNumber: '346',
    title: '计算机组成原理',
    increases: 35,
  },
  {
    key: 2,
    clickNumber: '324',
    title: '操作系统',
    increases: 22,
  },
  {
    key: 3,
    clickNumber: '300',
    title: '数据结构',
    increases: 9,
  },
  {
    key: 4,
    clickNumber: '257+',
    title: '广告学概论',
    increases: 17,
  },
  {
    key: 5,
    clickNumber: '124',
    title: '学术英语写作',
    increases: 37,
  },
];
const imageList = [
  {
    key: 1,
    clickNumber: '153',
    title: 'AI设计广告',
    increases: 15,
  },
  {
    key: 2,
    clickNumber: '122',
    title: '多种算法解决...',
    increases: 26,
  },
  {
    key: 3,
    clickNumber: '89',
    title: 'XSS漏洞修复',
    increases: 9,
  },
  {
    key: 4,
    clickNumber: '79',
    title: 'Sequelize bug排查',
    increases: 0,
  },
  {
    key: 5,
    clickNumber: '52',
    title: '二分贪心详解…',
    increases: 4,
  },
];
const videoList = [
  {
    key: 1,
    clickNumber: '367',
    title: 'MySQL入门教程',
    increases: 5,
  },
  {
    key: 2,
    clickNumber: '352',
    title: 'Ollama本地部署...',
    increases: 17,
  },
  {
    key: 3,
    clickNumber: '340',
    title: 'MCP从入门到实战',
    increases: 30,
  },
  {
    key: 4,
    clickNumber: '308',
    title: '前端安全教程',
    increases: 12,
  },
  {
    key: 5,
    clickNumber: '271',
    title: 'Rust语法',
    increases: 2,
  },
];
const homeworkList = [
  {
    key: 1,
    clickNumber: '411',
    title: '数据库原理第一章课后作业',
    increases: 16,
  },
  {
    key: 2,
    clickNumber: '388',
    title: '事务并发控制练习',
    increases: 12,
  },
  {
    key: 3,
    clickNumber: '364',
    title: '索引优化实验报告',
    increases: 9,
  },
  {
    key: 4,
    clickNumber: '350',
    title: 'SQL 查询性能分析',
    increases: 6,
  },
  {
    key: 5,
    clickNumber: '329',
    title: 'MySQL 锁机制作业',
    increases: 4,
  },
];
setupMock({
  setup() {
    Mock.mock(new RegExp('/api/content-data'), () => {
      const presetData = [1234, 1380, 1498, 1572, 1641, 1703, 1766, 1820];
      const start = dayjs('2025-05-23');
      const lineData = presetData.map((value, idx) => ({
        x: start.add(idx, 'day').format('YYYY-MM-DD'),
        y: value,
      }));
      return successResponseWrap(lineData);
    });
    Mock.mock(new RegExp('/api/popular/list'), (params: GetParams) => {
      const { type = 'text' } = qs.parseUrl(params.url).query;
      if (type === 'image') {
        return successResponseWrap([...imageList]);
      }
      if (type === 'video') {
        return successResponseWrap([...videoList]);
      }
      if (type === 'homework') {
        return successResponseWrap([...homeworkList]);
      }
      return successResponseWrap([...textList]);
    });
  },
});
