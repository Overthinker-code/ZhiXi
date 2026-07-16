export function markdownToPlainText(value: unknown) {
  return String(value || '')
    .replace(/```[^\n]*\n?/g, ' ')
    .replace(/```/g, ' ')
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/^\s{0,3}#{1,6}\s+/gm, '')
    .replace(/^\s{0,3}(?:[-+*]|\d+[.)])\s+/gm, '')
    .replace(/^\s{0,3}>\s?/gm, '')
    .replace(/^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$/gm, ' ')
    .replace(/^\s*\|\s?/gm, '')
    .replace(/\s?\|\s*$/gm, '')
    .replace(/\s*\|\s*/g, ' · ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[*_~`]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

export function artifactSummary(value: unknown, maxLength = 108) {
  const plain = markdownToPlainText(value);
  if (!plain) return '资源已生成，可预览内容并选择下载格式。';
  if (plain.length <= maxLength) return plain;
  return `${plain.slice(0, maxLength).trimEnd()}…`;
}
