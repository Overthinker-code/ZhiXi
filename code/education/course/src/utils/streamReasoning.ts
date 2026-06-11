/** Align with backend reasoning_stream._SILENT_STAGES — never show as user reasoning. */
export const SILENT_REASONING_STAGES = new Set([
  'pipeline_start',
  'kb_inject',
  'tool_policy',
  'web_policy',
  'cache',
  'tool_run',
  'demo_mode',
  'vision_status',
]);

const PIPELINE_TAG_RE =
  /^【(?:流水线|知识检索|工具策略|联网搜索|工具执行|演示模式)】/;

const SUPERVISOR_THOUGHT_RE =
  /主管正在分析|下一步由|本轮处理完成|已同步至主管|多智能体协作已启动|启用工具|已关闭/;

export function isPipelineThought(content: string, stage?: string): boolean {
  const text = String(content || '').trim();
  const stageKey = String(stage || '').trim();
  if (stageKey && SILENT_REASONING_STAGES.has(stageKey)) return true;
  if (PIPELINE_TAG_RE.test(text)) return true;
  if (SUPERVISOR_THOUGHT_RE.test(text)) return true;
  return false;
}

/** Whether a thought/phase line should be merged into reasoning_content. */
export function shouldAppendThoughtToReasoning(
  content: string,
  stage?: string,
  sawReasoningToken = false
): boolean {
  if (isPipelineThought(content, stage)) return false;
  if (sawReasoningToken && textLooksLikeInternalStep(content)) return false;
  return true;
}

function textLooksLikeInternalStep(content: string): boolean {
  const text = String(content || '').trim();
  if (!text) return true;
  if (text.startsWith('【') && text.includes('】')) return true;
  return SUPERVISOR_THOUGHT_RE.test(text);
}
