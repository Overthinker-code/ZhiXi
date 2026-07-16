/**
 * 将后端/流式事件里的技术向「思维」文案转为更接近自然语言的展示，不改变业务数据，仅用于 UI。
 */
import {
  appendThoughtToReasoning,
  thoughtToNarrative,
} from '@/utils/thoughtToNarrative';
import { isPipelineThought } from '@/utils/streamReasoning';

export default function humanizeAgentReasoning(raw: string): string {
  if (!raw || !String(raw).trim()) return '';
  const text = String(raw).trim();
  if (!/【[^】]+】/.test(text)) return text;
  const lines = text.split(/\r?\n+/).filter((l) => l.trim());
  let out = '';
  for (const line of lines) {
    if (isPipelineThought(line)) continue;
    out = appendThoughtToReasoning(out, line);
  }
  return out || text;
}

export { thoughtToNarrative, appendThoughtToReasoning };
