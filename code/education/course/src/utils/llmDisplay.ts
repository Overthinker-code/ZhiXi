const DEFAULT_TEXT_KEYS = [
  'question',
  'prompt',
  'text',
  'content',
  'answer',
  'title',
  'summary',
  'action',
  'recommendation',
  'resource',
  'task',
  'focus',
  'point',
  'name',
  'label',
  'value',
  'desc',
  'description',
  'symptom',
  'evidence',
  'fix_strategy',
];

const QUESTION_KEYS = ['question', 'prompt', 'text', 'content', 'title', 'value', 'label'];

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function objectLikeSlice(raw: string) {
  const text = raw.trim();
  if (text.startsWith('{')) {
    const end = text.lastIndexOf('}');
    return end > 0 ? text.slice(0, end + 1) : text;
  }
  if (text.startsWith('[')) {
    const end = text.lastIndexOf(']');
    return end > 0 ? text.slice(0, end + 1) : text;
  }
  return text;
}

function parseStructuredString(raw: string): unknown {
  const candidate = objectLikeSlice(raw);
  if (!candidate.startsWith('{') && !candidate.startsWith('[')) return undefined;
  try {
    return JSON.parse(candidate);
  } catch {
    try {
      const jsonish = candidate
        .replace(/\bNone\b/g, 'null')
        .replace(/\bTrue\b/g, 'true')
        .replace(/\bFalse\b/g, 'false')
        .replace(/'/g, '"');
      return JSON.parse(jsonish);
    } catch {
      return undefined;
    }
  }
}

function extractKeyedValues(raw: string, keys = DEFAULT_TEXT_KEYS) {
  const keyPattern = keys.map(escapeRegExp).join('|');
  const re = new RegExp(
    "(?:^|[\\{\\[,\\s])[\"']?(?:" +
      keyPattern +
      ")[\"']?\\s*[:：]\\s*[\"']([^\"'\\n\\r]+)[\"']",
    'gi'
  );
  const values: string[] = [];
  let match = re.exec(raw);
  while (match) {
    const value = match[1]?.trim();
    if (value) values.push(value);
    match = re.exec(raw);
  }
  return values;
}

export function normalizeDisplayText(value: unknown, keys = DEFAULT_TEXT_KEYS): string {
  if (value === null || value === undefined) return '';

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  if (typeof value === 'string') {
    const raw = value.trim();
    if (!raw || raw === '[object Object]') return '';

    const keyed = extractKeyedValues(raw, keys)[0];
    if (keyed) return normalizeDisplayText(keyed, keys);

    const parsed = parseStructuredString(raw);
    if (parsed !== undefined) return normalizeDisplayText(parsed, keys);

    return raw
      .replace(/\s+/g, ' ')
      .replace(/([\u4e00-\u9fff])\s+([\u4e00-\u9fff])/g, '$1$2')
      .replace(/^["'`“”‘’]+|["'`“”‘’]+$/g, '')
      .trim();
  }

  if (Array.isArray(value)) {
    return normalizeTextList(value, keys).join('、');
  }

  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;
    for (const key of keys) {
      const text = normalizeDisplayText(record[key], keys);
      if (text) return text;
    }
    const firstText = Object.values(record)
      .map((item) => normalizeDisplayText(item, keys))
      .find(Boolean);
    return firstText || '';
  }

  return '';
}

export function normalizeTextList(value: unknown, keys = DEFAULT_TEXT_KEYS): string[] {
  let source: unknown[] = [];

  if (Array.isArray(value)) {
    source = value;
  } else if (typeof value === 'string') {
    const keyed = extractKeyedValues(value, keys);
    if (keyed.length) {
      source = keyed;
    } else {
      const parsed = parseStructuredString(value);
      source = Array.isArray(parsed) ? parsed : [value];
    }
  } else if (value !== null && value !== undefined) {
    source = [value];
  }

  const seen = new Set<string>();
  const out: string[] = [];
  source.forEach((item) => {
    const text = normalizeDisplayText(item, keys);
    if (!text || seen.has(text)) return;
    seen.add(text);
    out.push(text);
  });
  return out;
}

export function normalizeSuggestionText(value: unknown): string {
  const text = normalizeDisplayText(value, QUESTION_KEYS)
    .replace(/\s+/g, ' ')
    .replace(/([\u4e00-\u9fff])\s+([\u4e00-\u9fff])/g, '$1$2')
    .replace(/^问题\s*\d+[:：.\-、]?\s*/i, '')
    .replace(/^\d+[:：.\-、]\s*/, '')
    .replace(/^我[，,、：:]\s*/, '')
    .replace(/^我\s+(?=(帮我|给我|能不能|可以|需要|应该|该|想|要))/, '')
    .replace(/^(帮我|给我)\s*(帮我|给我)/, '$1')
    .replace(/[。.!！?？]+$/g, '')
    .trim();

  if (!text || /^(?:\{|\[|\[object Object\])/.test(text)) return '';
  return `${text}？`;
}

export function normalizeSuggestionList(value: unknown, limit = 3): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  normalizeTextList(value, QUESTION_KEYS).forEach((item) => {
    const text = normalizeSuggestionText(item);
    if (!text || seen.has(text)) return;
    if (/您|你是否|是否需要|请问你|请问您/.test(text)) return;
    if (!/(吗|么|如何|为什么|怎么|哪|能否|能不能|帮我|给我|可以|应该|\?|？)/.test(text)) {
      return;
    }
    seen.add(text);
    out.push(text);
  });
  return out.slice(0, limit);
}
