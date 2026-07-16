/** Human-readable agent role labels for UI. */

export const AGENT_LABELS: Record<string, string> = {
  supervisor: '协作主管',
  code_tutor: '代码导师',
  knowledge_mentor: '学科讲师',
  planner: '学习规划师',
  analyst: '学习分析师',
  doc_researcher: '文档研究员',
  quiz_master: '测验官',
  profile_agent: '画像分析师',
  retrieval_agent: '证据检索员',
  web_research_agent: '联网研究员',
  tutor_agent: '多模态辅导',
  grading_agent: '练习批改',
  safety_review_agent: '安全审查',
};

export function mergeAgentPhases(
  existing: Array<{
    phase: string;
    agent: string;
    summary: string;
    status?: string;
  }>,
  incoming: {
    phase?: string;
    agent?: string;
    summary?: string;
    status?: string;
  }
) {
  const phase = incoming.phase || 'process';
  const agent = incoming.agent || 'supervisor';
  const summary = (incoming.summary || '').trim();
  if (!summary) return existing;
  const last = existing[existing.length - 1];
  if (
    last &&
    last.phase === phase &&
    last.agent === agent &&
    last.summary === summary
  ) {
    return existing;
  }
  const next = [...existing, { phase, agent, summary, status: incoming.status || 'running' }];
  return next.slice(-8);
}
