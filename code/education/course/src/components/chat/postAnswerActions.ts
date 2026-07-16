export interface GeneratePracticeFollowUp {
  type: 'generate_practice';
  sourcePrompt: string;
}

export function normalizePracticeTarget(sourcePrompt: string) {
  const normalized = String(sourcePrompt || '')
    .replace(/\s+/g, ' ')
    .trim();
  return (normalized || '上一轮学习内容').slice(0, 120);
}

export function buildPracticeFollowUp(sourcePrompt: string) {
  const target = normalizePracticeTarget(sourcePrompt);
  return {
    target,
    message: `请基于上一轮问答，围绕“${target}”生成一组针对性练习题，并提供答案、解析和常见错误提示。`,
  };
}
