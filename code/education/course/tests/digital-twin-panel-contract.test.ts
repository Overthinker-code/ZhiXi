import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const panel = fs.readFileSync(
  path.resolve(
    __dirname,
    '../src/views/profile/learning-data/components/DigitalTwinPanel.vue'
  ),
  'utf8'
);

for (const internalTerm of [
  'Profile Agent',
  'planner agent',
  'resource agent',
  'evaluator agent',
  'profile_version',
  'agent_links',
]) {
  assert.doesNotMatch(panel, new RegExp(internalTerm, 'i'), `数字分身不应暴露内部词：${internalTerm}`);
}

assert.match(panel, /practice_pdf:\s*'偏好练习与讲义的结构化学习者'/, '学习风格枚举必须映射为自然语言');
assert.match(panel, /practice_\(\?:pdf\|docx\)/, '复合练习格式枚举必须统一中文化');
assert.match(panel, /lecture_\(\?:pdf\|docx\)/, '复合讲义格式枚举必须统一中文化');
assert.match(panel, /looksLikeInternalStyle/, '仅学习类型字段可对未知整体枚举做兜底');
assert.match(panel, /\^\[a-z\]\[a-z0-9_-\]\*\(\?:驱动型学习者\)\?\$/i, '未知整体学习类型枚举不得原样回显');
assert.doesNotMatch(panel, /\\b\[a-z\]\{4,\}\b/i, '不得全局替换英文技术缩写');

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

const sanitizerSource = [
  extractFunction('humanizeLearningEnum').replace('(value: string)', '(value)'),
  extractFunction('cleanStudentText').replace('(value: unknown, fallback = \'\')', '(value, fallback = \'\')'),
  'return { humanizeLearningEnum, cleanStudentText };',
].join('\n');
const { cleanStudentText } = new Function(sanitizerSource)() as {
  cleanStudentText: (value: unknown, fallback?: string) => string;
};

assert.equal(cleanStudentText('范式与 BCNF'), '范式与 BCNF', '技术缩写 BCNF 必须原样保留');
assert.equal(cleanStudentText('LIFO / push / pop'), 'LIFO / push / pop', '栈操作术语必须原样保留');
assert.equal(cleanStudentText('SQL 基础'), 'SQL 基础', 'SQL 术语必须原样保留');
assert.equal(
  cleanStudentText('practice_pdf驱动型学习者'),
  '偏好练习与讲义的结构化学习者',
  'practice_pdf驱动型学习者必须映射为中文学习类型'
);
assert.equal(
  cleanStudentText('当前更偏好practice_pdf驱动型学习者类资源'),
  '当前更偏好练习与讲义类资源',
  '嵌入资源偏好句的枚举不能重复输出偏好或学习者'
);
assert.match(panel, /weaknesses\.value\.slice\(0, 3\)/, '待提升方向默认最多展示三项');
assert.match(panel, /dimensions\.slice\(0, 4\)/, '能力维度默认最多展示四项');
assert.match(panel, /\.slice\(0, 2\)/, '近期变化默认最多展示两项');
assert.match(panel, /展开查看完整知识网络/, '知识网络必须提供完整预览入口');
assert.match(panel, /@click\.self="closeGraphPreview"/, '知识网络预览必须支持背景关闭');
assert.match(panel, /event\.key === 'Escape'/, '知识网络预览必须支持 Esc 关闭');
assert.match(panel, /event\.key !== 'Tab'/, '知识网络预览必须处理 Tab 键');
assert.match(panel, /getDialogFocusableElements/, '知识网络预览必须圈定模态焦点');
assert.match(panel, /event\.shiftKey/, '知识网络预览必须支持 Shift\+Tab 焦点循环');
assert.match(panel, /@wheel="onGraphWheel"/, '知识网络预览必须支持滚轮缩放');
assert.match(panel, /@pointerdown="startGraphDrag"/, '知识网络预览必须支持拖动');
assert.match(panel, /fitGraphView/, '知识网络预览必须支持适配视图');
assert.match(panel, /height:min\(760px,calc\(100vh - 32px\)\)/, '预览弹窗必须有明确可用高度');
assert.match(panel, /\.graph-preview-canvas\) \{ width:100%; height:100%; min-height:0;/, '默认画布必须使用完整可用高度');
assert.match(panel, /\.graph-preview-canvas \.mermaid-viewer\) \{ width:100%; height:100%; box-sizing:border-box;.*padding:0 !important;/, '共享 Mermaid 容器不能额外挤占预览高度');
assert.match(panel, /svg\) \{ display:block; width:100% !important; height:100% !important; max-width:100%; max-height:100%;/, '默认 SVG 必须按容器完整适配，不裁切节点');
assert.doesNotMatch(panel, /RotateCcw/, '不应保留与适配视图同义的重复重置按钮');
assert.match(panel, /prefers-reduced-motion:reduce/, '数字分身必须处理减少动态效果偏好');
assert.match(panel, /button:focus-visible/, '数字分身交互按钮必须提供可见焦点');

console.log('digital twin panel contract tests passed');
