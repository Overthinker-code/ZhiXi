/**
 * 将后端/流式事件里的技术向「思维」文案转为更接近自然语言的展示，不改变业务数据，仅用于 UI。
 */
function mapReasoningLine(trimmed: string): string | null {
  if (
    /正在分析意图/.test(trimmed) ||
    (/识别为/.test(trimmed) && /分配给/.test(trimmed))
  ) {
    return '— 先揣摩一下你的问题大概在问什么，再选一条更对症的说明方式。';
  }
  if (
    /工具开关状态/.test(trimmed) &&
    (/启用/.test(trimmed) || /禁用/.test(trimmed))
  ) {
    return '— 按需准备参考资料与检索；本轮用不上的能力先收起来，避免干扰回答。';
  }
  if (
    /^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$/i.test(trimmed) &&
    trimmed.length < 48
  ) {
    return null;
  }
  return trimmed;
}

export default function humanizeAgentReasoning(raw: string): string {
  if (!raw || !String(raw).trim()) return raw;
  const parts = String(raw)
    .split(/\r?\n+/)
    .map((line) => line.trim())
    .filter((t) => t.length > 0)
    .map(mapReasoningLine)
    .filter((x): x is string => x !== null);
  return parts.join('\n\n');
}
