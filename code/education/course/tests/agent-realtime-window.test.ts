import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import type { CourseAgentContractSummary } from '../src/api/ai-chat';
import {
  agentProcessStatusFromPhase,
  isAgentStreamTokenCurrent,
  markAgentMessageInterrupted,
  type AgentWindowMessage,
} from '../src/components/float-ai/agentRealtimeState';
import {
  createCourseAgentWindowSession,
  isCourseAgentWindowSessionCurrent,
} from '../src/components/float-ai/courseAgentWindowSession';

function contract(
  key: string,
  executionKind: CourseAgentContractSummary['executionKind'] = 'chat'
): CourseAgentContractSummary {
  return {
    key,
    label: key,
    category: '学习助手',
    description: `${key} contract`,
    executionKind,
    mode: key === 'research' ? 'deep_research' : 'tutor',
    outputs: ['结果'],
    starterActions: ['开始任务'],
    requirements: { courseContext: true, attachment: false },
    capabilities: ['knowledge_base'],
  };
}

const research = createCourseAgentWindowSession({
  agent: contract('research'),
  courseId: ' course-1 ',
  courseTitle: '数据库系统',
  initialPrompt: ' 核验事务隔离级别 ',
});
const practice = createCourseAgentWindowSession({
  agent: contract('practice'),
  courseId: 'course-1',
  courseTitle: '数据库系统',
});

assert.equal(research.courseId, 'course-1');
assert.equal(research.initialPrompt, '核验事务隔离级别');
assert.notEqual(research.token, practice.token);
assert.equal(isCourseAgentWindowSessionCurrent(research.token, research.token), true);
assert.equal(isCourseAgentWindowSessionCurrent(practice.token, research.token), false);
assert.throws(
  () =>
    createCourseAgentWindowSession({
      agent: contract('resource', 'resource_workflow'),
      courseId: 'course-1',
      courseTitle: '数据库系统',
    }),
  /Only chat agents/
);

assert.equal(
  isAgentStreamTokenCurrent(research.token, 3, {
    sessionToken: research.token,
    requestId: 3,
  }),
  true
);
assert.equal(
  isAgentStreamTokenCurrent(practice.token, 4, {
    sessionToken: research.token,
    requestId: 3,
  }),
  false,
  'an event from a closed or switched Agent window must be ignored'
);
assert.equal(agentProcessStatusFromPhase('failed'), 'error');
assert.equal(agentProcessStatusFromPhase('cancelled'), 'cancelled');
assert.equal(agentProcessStatusFromPhase('done'), 'done');

const interrupted: AgentWindowMessage = {
  id: 'assistant-1',
  role: 'assistant',
  content: '已收到一部分回答',
  loading: true,
  interrupted: false,
  currentStage: '生成内容',
  processOpen: true,
  process: [
    { key: 'compose', title: '生成内容', detail: '', status: 'running' },
    { key: 'retrieve', title: '检索课程资料', detail: '', status: 'done' },
  ],
  suggestions: [],
};
markAgentMessageInterrupted(interrupted);
assert.equal(interrupted.loading, false);
assert.equal(interrupted.interrupted, true);
assert.equal(interrupted.currentStage, '已中断显示');
assert.deepEqual(
  interrupted.process.map((step) => step.status),
  ['cancelled', 'done']
);

const componentSource = readFileSync(
  'src/components/float-ai/AgentRealtimeChat.vue',
  'utf8'
);
assert.match(componentSource, /role="log" aria-live="off"/);
assert.match(componentSource, /role="status" aria-live="polite">\{\{ liveAnnouncement \}\}/);
assert.equal(
  (componentSource.match(/event === 'phase_finished'/g) || []).length,
  1,
  'phase_finished must have a single event branch'
);

console.log('agent realtime window state tests passed');
