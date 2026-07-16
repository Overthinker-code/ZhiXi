import assert from 'node:assert/strict';
import {
  buildCapabilityChartAccessibility,
  buildGrowthChartAccessibility,
  buildResourceChartAccessibility,
  buildRhythmChartAccessibility,
  formatChartValue,
} from '../src/views/profile/learning-data/components/chartAccessibility';

assert.equal(formatChartValue(0.30000000000000004, ' 小时'), '0.3 小时');
assert.equal(formatChartValue(null, '分'), '暂无数据');

const growth = buildGrowthChartAccessibility(
  ['第1周', '第2周'],
  [
    {
      key: 'knowledge',
      label: '知识理解',
      color: '#6255e7',
      values: [60.1, 70.3],
    },
  ]
);
assert.equal(growth.label, '能力成长趋势图');
assert.deepEqual(growth.headers, ['周期', '知识理解']);
assert.deepEqual(growth.rows[1], ['第2周', '70.3分']);
assert.match(growth.summary, /知识理解从 60\.1分 变化至 70\.3分/);

const capability = buildCapabilityChartAccessibility([
  {
    key: 'knowledge',
    label: '知识理解',
    value: 76,
    previous: 70,
    evidenceCount: 3,
  },
  {
    key: 'transfer',
    label: '实践迁移',
    value: 65,
    previous: null,
    evidenceCount: 2,
  },
]);
assert.match(capability.summary, /表现较好的是知识理解/);
assert.match(capability.summary, /优先关注实践迁移/);
assert.match(capability.summary, /部分维度已积累/);
assert.deepEqual(capability.rows[1], ['实践迁移', '65分', '暂无数据']);

const rhythm = buildRhythmChartAccessibility(
  ['第1周'],
  ['一', '二'],
  [[20, 80]],
  ['08:00', '12:00'],
  [0.3, 1.8]
);
assert.match(rhythm.summary, /第1周·周二/);
assert.match(rhythm.summary, /12:00/);
assert.ok(rhythm.rows.every((row) => !String(row[2]).includes('000000000')));

const resource = buildResourceChartAccessibility([
  {
    key: 'document',
    label: '图文讲义',
    value: 66.7,
    color: '#6255e7',
    reason: '真实记录',
  },
  {
    key: 'quiz',
    label: '测验练习',
    value: 33.3,
    color: '#2bb8d6',
    reason: '真实记录',
  },
]);
assert.match(resource.summary, /图文讲义/);
assert.match(resource.summary, /已生成和上传/);
assert.deepEqual(resource.rows[0], ['图文讲义', '66.7%']);

const mismatchedGrowth = buildGrowthChartAccessibility(
  ['第1周', '第2周', '第3周'],
  [
    {
      key: 'knowledge',
      label: '知识理解',
      color: '#6255e7',
      values: [Number.NaN, Number.POSITIVE_INFINITY],
    },
  ]
);
assert.equal(mismatchedGrowth.rows.length, 3);
assert.deepEqual(mismatchedGrowth.rows[0], ['第1周', '暂无数据']);
assert.deepEqual(mismatchedGrowth.rows[2], ['第3周', '暂无数据']);
assert.doesNotMatch(mismatchedGrowth.summary, /NaN|Infinity/);

console.log('learning portrait chart accessibility tests passed');
