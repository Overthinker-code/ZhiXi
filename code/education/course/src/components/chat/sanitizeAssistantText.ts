const THINK_BLOCK_RE = /<think>[\s\S]*?<\/think>/gi;
const OPEN_THINK_RE = /<think>[\s\S]*$/gi;
const CLOSE_THINK_RE = /<\/think>/gi;
const INTERNAL_LINE_RE =
  /(intent_classifier|course_context|reasoning_content|系统消息|上下文注入|协作线程|首条系统消息|Supervisor|intermediate_steps|tool_policy|route_trace|【(?:流水线|知识检索|工具策略|工具执行|联网搜索|多智能体协作)】)/i;

export function sanitizeAssistantText(input: unknown, options: { preserveEdges?: boolean } = {}) {
  const raw = String(input || '');
  if (!raw) return '';
  const withoutThink = raw
    .replace(THINK_BLOCK_RE, '')
    .replace(OPEN_THINK_RE, '')
    .replace(CLOSE_THINK_RE, '');
  const cleaned = withoutThink
    .split(/\r?\n/)
    .filter((line) => {
      const trimmed = line.trim();
      return !trimmed || !INTERNAL_LINE_RE.test(trimmed);
    })
    .join('\n');
  return options.preserveEdges ? cleaned : cleaned.trim();
}
