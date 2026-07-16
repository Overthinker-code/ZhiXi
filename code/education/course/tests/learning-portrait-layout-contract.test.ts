import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const portraitPage = fs.readFileSync(
  path.resolve(
    __dirname,
    '../src/views/profile/learning-data/index.vue'
  ),
  'utf8'
);

const requiredLayoutRegions = [
  'class="metric-strip',
  'class="portrait-card growth-card"',
  'class="portrait-card capability-card"',
  'class="portrait-card rhythm-card"',
  'class="portrait-card preference-card"',
  'class="portrait-card recommendation-card"',
  'class="portrait-card course-card"',
];

let previousIndex = -1;
for (const region of requiredLayoutRegions) {
  const currentIndex = portraitPage.indexOf(region);
  assert.notEqual(currentIndex, -1, `学习画像页面缺少布局区域：${region}`);
  assert.ok(
    currentIndex > previousIndex,
    `学习画像页面的布局区域顺序发生了非预期变化：${region}`
  );
  previousIndex = currentIndex;
}

for (const heading of [
  '我的学习画像',
  '能力成长趋势',
  '核心能力画像',
  '学习节律',
  '下一步建议',
  '分课程查看',
]) {
  assert.match(portraitPage, new RegExp(heading), `学习画像页面缺少“${heading}”`);
}
assert.match(
  portraitPage,
  /resourceSectionTitle/,
  '学习画像页面缺少资源偏好/资源类型分布区块'
);

assert.doesNotMatch(
  portraitPage,
  /画像版本\s*V|证据\s*\d+\s*条|可信度\s*\d+%/,
  '学习画像页面不应向学生暴露内部版本、证据计数或可信度字段'
);

console.log('learning portrait layout contract tests passed');
