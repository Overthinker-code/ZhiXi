const DEFAULT_TITLES = new Set(['', '新对话', '未命名对话', 'new chat']);

export function shouldGenerateConversationTitle(title: unknown) {
  return DEFAULT_TITLES.has(String(title || '').trim().toLowerCase());
}

export function buildConversationTitle(prompt: unknown, maxLength = 26) {
  const normalized = String(prompt || '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/^\s{0,3}#{1,6}\s+/gm, '')
    .replace(/[>*_`~|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  if (!normalized) return '新对话';
  if (normalized.length <= maxLength) return normalized;

  const firstClause = normalized
    .slice(0, maxLength + 1)
    .split(/[。！？!?；;，,]/)[0]
    .trim();
  const base = firstClause.length >= 8 ? firstClause : normalized.slice(0, maxLength).trim();
  return `${base}…`;
}
