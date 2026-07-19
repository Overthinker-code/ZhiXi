import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const layout = fs.readFileSync(
  path.resolve(__dirname, '../src/components/chat/ChatLayout.vue'),
  'utf8'
);

function extractFunction(name: string) {
  const start = layout.indexOf(`function ${name}`);
  assert.notEqual(start, -1, `缺少 ${name}`);
  const bodyStart = layout.indexOf('{', start);
  let depth = 0;
  for (let index = bodyStart; index < layout.length; index += 1) {
    if (layout[index] === '{') depth += 1;
    if (layout[index] === '}') depth -= 1;
    if (depth === 0) return layout.slice(start, index + 1);
  }
  throw new Error(`${name} 未闭合`);
}

const source = [
  extractFunction('agentTaskCapability').replace('(task: Record<string, any>)', '(task)'),
  extractFunction('userFacingAgentText').replace('(value: unknown, capability: string)', '(value, capability)'),
  extractFunction('agentTaskTitle')
    .replace('(task: Record<string, any>)', '(task)')
    .replace('const fixedLabels: Record<string, string> =', 'const fixedLabels ='),
  'return { agentTaskCapability, userFacingAgentText, agentTaskTitle };',
].join('\n');
const { agentTaskCapability, userFacingAgentText, agentTaskTitle } = new Function(source)() as {
  agentTaskCapability: (task: Record<string, unknown>) => string;
  userFacingAgentText: (value: unknown, capability: string) => string;
  agentTaskTitle: (task: Record<string, unknown>) => string;
};

const animationTask = { task_key: 'animation', agent_name: 'Qwen Manim Agent' };
const illustrationTask = { task_key: 'image_generation', agent_name: 'Qwen Image Generation Agent' };

assert.equal(agentTaskCapability(animationTask), '教学动画智能体');
assert.equal(agentTaskTitle(animationTask), '教学动画智能体');
assert.equal(
  userFacingAgentText('已路由到 Qwen Manim Agent', agentTaskCapability(animationTask)),
  '已选择教学动画智能体',
  '路由结果不能向学生暴露供应商或模型名'
);
assert.equal(
  userFacingAgentText('已路由到 Qwen Manim Agent', agentTaskCapability({ task_key: 'planner' })),
  '已选择教学动画智能体',
  '任务身份不是动画时也必须从路由文案映射内部动画名'
);
assert.equal(agentTaskTitle(illustrationTask), '教学插图智能体');
assert.equal(
  userFacingAgentText('Qwen Image Generation Agent 正在生成示意图', agentTaskCapability(illustrationTask)),
  '教学插图智能体 正在生成示意图'
);
assert.equal(agentTaskTitle({ task_key: 'planner', agent_name: 'Planner Agent' }), '任务规划智能体');

console.log('chat agent display contract tests passed');
