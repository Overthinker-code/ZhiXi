import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const panel = fs.readFileSync(
  path.resolve(__dirname, '../src/components/chat/LiveProcessPanel.vue'),
  'utf8'
);

function extractFunction(name: string) {
  const start = panel.indexOf(`function ${name}`);
  assert.notEqual(start, -1, `缺少 ${name}`);
  const bodyStart = panel.indexOf('{', start);
  let depth = 0;
  for (let index = bodyStart; index < panel.length; index += 1) {
    if (panel[index] === '{') depth += 1;
    if (panel[index] === '}') depth -= 1;
    if (depth === 0) return panel.slice(start, index + 1);
  }
  throw new Error(`${name} 未闭合`);
}

const timeSource = [
  extractFunction('timestamp').replace('(value: unknown)', '(value)'),
  extractFunction('elapsedDurationMs')
    .replace('currentStatus: ProcessStatus', 'currentStatus')
    .replace(/: number/g, '')
    .replace('currentDurationMs: unknown', 'currentDurationMs'),
  'return { timestamp, elapsedDurationMs };',
].join('\n');

const { timestamp, elapsedDurationMs } = new Function(timeSource)() as {
  timestamp: (value: unknown) => number;
  elapsedDurationMs: (
    status: string,
    startedAt: number,
    finishedAt: number,
    durationMs: unknown,
    now: number
  ) => number;
};

const unixSeconds = 1_710_000_000;
assert.equal(timestamp(unixSeconds), 1_710_000_000_000, '秒级 Unix 时间必须转为毫秒');
assert.equal(timestamp(String(unixSeconds)), 1_710_000_000_000, '数字字符串 Unix 时间必须转为毫秒');
assert.equal(
  timestamp('2024-03-09T16:00:00.000Z'),
  Date.parse('2024-03-09T16:00:00.000Z'),
  'ISO 时间必须保持可解析的毫秒时间'
);

const startedAt = 1_710_000_000_000;
assert.equal(
  elapsedDurationMs('done', startedAt, startedAt + 6_000, 4_000, startedAt + 99_999_000),
  4_000,
  '完成态优先使用声明时长，不能随当前时间增长'
);
assert.equal(
  elapsedDurationMs('done', startedAt, startedAt + 6_000, 0, startedAt + 99_999_000),
  6_000,
  '完成态没有时长时必须固定在 finishedAt'
);
assert.equal(
  elapsedDurationMs('running', startedAt, 0, 0, startedAt + 6_000),
  6_000,
  '运行态才可以使用当前时间递增'
);

console.log('live process panel time tests passed');
