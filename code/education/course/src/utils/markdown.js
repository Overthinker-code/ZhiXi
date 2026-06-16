import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import mdLinkAttributes from 'markdown-it-link-attributes';
import { full as emoji } from 'markdown-it-emoji';
import { katex as mditKatex } from '@mdit/plugin-katex';
import copyIcon from '@/assets/photo/复制.png';
import darkIcon from '@/assets/photo/暗黑模式.png';
import lightIcon from '@/assets/photo/明亮模式.png';
import 'highlight.js/styles/atom-one-dark.css';
import 'katex/dist/katex.min.css';

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        const highlighted = hljs.highlight(str, {
          language: lang,
          ignoreIllegals: true,
        }).value;
        return `<div class="code-block"><div class="code-header"><span class="code-lang">${lang}</span><div class="code-actions"><button class="code-action-btn" data-action="copy" data-tooltip="复制"><img src="${copyIcon}" alt="copy" /></button><button class="code-action-btn" data-action="theme" data-tooltip="切换主题"><img src="${darkIcon}" alt="theme" data-light-icon="${lightIcon}" data-dark-icon="${darkIcon}" /></button></div></div><pre class="hljs"><code>${highlighted}</code></pre></div>`;
      } catch {
        /* ignore */
      }
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`;
  },
});

md.use(mdLinkAttributes, {
  attrs: {
    target: '_blank',
    rel: 'noopener',
  },
});

md.use(emoji);

md.use(mditKatex, {
  delimiters: 'all',
  allowInlineWithSpace: true,
  throwOnError: false,
  errorColor: '#ef4444',
});

const TEX_COMMAND_RE =
  /\\(?:sum|prod|frac|sqrt|lim|int|begin|end|alpha|beta|gamma|theta|lambda|mu|pi|sigma|infty|cdot|times|leq|geq|neq|approx|to|left|right|mathbf|mathrm)\b/;

function mapOutsideCode(content, transform) {
  const source = String(content || '');
  const parts = [];
  let plain = '';
  let index = 0;
  let lineStart = true;

  const flushPlain = () => {
    if (!plain) return;
    parts.push(transform(plain));
    plain = '';
  };

  while (index < source.length) {
    if (lineStart) {
      const fence = source.slice(index).match(/^ {0,3}(`{3,}|~{3,})[^\n]*\n?/);
      if (fence) {
        flushPlain();
        const marker = fence[1][0];
        const size = fence[1].length;
        const closeRe = new RegExp(`^ {0,3}${marker}{${size},}\\s*$`, 'm');
        const bodyStart = index + fence[0].length;
        const rest = source.slice(bodyStart);
        const close = closeRe.exec(rest);
        if (!close) {
          parts.push(source.slice(index));
          index = source.length;
          break;
        }
        const closeEnd =
          bodyStart + close.index + close[0].length +
          (rest[close.index + close[0].length] === '\n' ? 1 : 0);
        parts.push(source.slice(index, closeEnd));
        index = closeEnd;
        lineStart = true;
        continue;
      }

    }

    if (source[index] === '`') {
      const opener = source.slice(index).match(/^`+/)?.[0] || '`';
      const closeAt = source.indexOf(opener, index + opener.length);
      if (closeAt >= 0 && !source.slice(index, closeAt).includes('\n')) {
        flushPlain();
        const end = closeAt + opener.length;
        parts.push(source.slice(index, end));
        index = end;
        lineStart = false;
        continue;
      }
    }

    const char = source[index];
    plain += char;
    index += 1;
    lineStart = char === '\n';
  }
  flushPlain();
  return parts.join('');
}

function looksLikeMath(body) {
  const value = String(body || '').trim();
  if (!value) return false;
  if (TEX_COMMAND_RE.test(value) || /[_^{}=<>≤≥∞∑∏√]/.test(value)) return true;
  return /(?:^|[\s(])(?:[a-zA-Z]\w*\([^)]*\)|[a-zA-Z]\d*)\s*[=+\-*/]/.test(value);
}

function looksLikeStandaloneMath(body) {
  const value = String(body || '').trim();
  if (!value || /[\u3400-\u9fff]/.test(value) || /\*\*|`/.test(value)) {
    return false;
  }
  if (
    /\\(?:frac|lim|sum|int|sqrt|tan|sin|cos|log|text|phi)(?![a-zA-Z])/.test(
      value
    )
  ) {
    return true;
  }
  return /^[a-zA-Z\\][a-zA-Z0-9_{}\\^().,\s]*\s*(?:=|≈|≤|≥|<|>)\s*.+$/.test(
    value
  );
}

function stripNestedInlineDollars(body) {
  const value = String(body || '').trim();
  if (
    value.startsWith('$') &&
    value.endsWith('$') &&
    !value.startsWith('$$') &&
    !value.endsWith('$$')
  ) {
    return value.slice(1, -1).trim();
  }
  return value;
}

function normalizeMalformedMathBlocks(segment) {
  const lines = String(segment || '')
    .replace(/\${3,}/g, () => '$$')
    .split('\n');
  const output = [];
  let block = [];
  let inBlock = false;

  lines.forEach((line) => {
    const sameLine = line.match(/^\s*\$\$(.*?)\$\$\s*$/);
    if (sameLine && inBlock) {
      const previous = stripNestedInlineDollars(block.join('\n'));
      if (previous) {
        if (looksLikeStandaloneMath(previous)) {
          output.push('$$', previous, '$$');
        } else {
          output.push(...block);
        }
      }
      block = [];
      inBlock = false;
      const body = stripNestedInlineDollars(sameLine[1]);
      if (looksLikeStandaloneMath(body)) output.push(`$$${body}$$`);
      else if (body) output.push(body);
      return;
    }

    if (/^\s*\$\$\s*$/.test(line)) {
      if (!inBlock) {
        inBlock = true;
        block = [];
        return;
      }
      const body = stripNestedInlineDollars(block.join('\n'));
      if (body) {
        if (looksLikeStandaloneMath(body)) {
          output.push('$$', body, '$$');
        } else {
          output.push(...block);
        }
      }
      block = [];
      inBlock = false;
      return;
    }

    if (sameLine && !inBlock) {
      const body = stripNestedInlineDollars(sameLine[1]);
      if (looksLikeStandaloneMath(body)) output.push(`$$${body}$$`);
      else if (body) output.push(body);
      return;
    }

    if (inBlock) block.push(line);
    else output.push(line);
  });

  if (inBlock) output.push(...block);
  return output.join('\n');
}

function wrapOrphanMathLines(segment) {
  let inBlock = false;
  return String(segment || '')
    .split('\n')
    .map((line) => {
      if (line.trim() === '$$') {
        inBlock = !inBlock;
        return line;
      }
      if (inBlock || line.includes('$') || !looksLikeStandaloneMath(line)) {
        return line;
      }
      return `$$${line.trim()}$$`;
    })
    .join('\n');
}

function normalizeChatIndentation(segment) {
  const codeLike =
    /^(?:def|class|function|const|let|var|import|from|return|if|else|for|while|switch|case|try|catch|SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|public|private|protected|#include|<\/?[a-zA-Z]|\{|\})\b/;
  return String(segment || '')
    .split('\n')
    .map((line) => {
      const match = line.match(/^(?: {4,}|\t+)(.*)$/);
      if (!match) return line;
      const body = match[1];
      if (codeLike.test(body.trim())) return line;
      return `  ${body}`;
    })
    .join('\n');
}

function removeDecorativeHorizontalRules(segment) {
  return String(segment || '')
    .split('\n')
    .filter((line) => !/^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line))
    .join('\n');
}

function normalizeDollarDelimiters(segment) {
  const source = String(segment || '').replace(/＄/g, '$');
  let output = '';
  let index = 0;
  while (index < source.length) {
    if (source[index] !== '$' || source[index - 1] === '\\') {
      output += source[index];
      index += 1;
      continue;
    }
    const isBlock = source[index + 1] === '$';
    const openerSize = isBlock ? 2 : 1;
    const close = source.indexOf(isBlock ? '$$' : '$', index + openerSize);
    if (close < 0) {
      const prev = source[index - 1] || '';
      const next = source[index + 1] || '';
      const tail = source.slice(index + openerSize);
      if (isBlock || looksLikeMath(tail)) {
        output += source.slice(index);
        break;
      }
      if (/\d/.test(next) || (/\d/.test(prev) && /\d/.test(next))) {
        output += '\\$';
      }
      index += 1;
      continue;
    }
    const body = source.slice(index + openerSize, close);
    if (!isBlock && !looksLikeMath(body)) {
      output += `$${body}$`;
    } else if (isBlock) {
      output += `$$\n${body.trim()}\n$$`;
    } else {
      output += `$${body.trim()}$`;
    }
    index = close + openerSize;
  }
  return output;
}

/**
 * Normalize common LLM math delimiter variants before MarkdownIt sees them.
 * This keeps spaced `$ ... $`, `\\(...\\)` and escaped TeX delimiters from
 * leaking into the final answer as literal source text.
 */
export function normalizeMathMarkdown(content) {
  if (!content) return '';
  return mapOutsideCode(content, (segment) => {
    let text = segment
      .replace(
        /\\\[\s*([\s\S]*?)\s*\\\]/g,
        (_, body) => `\n\n$$\n${body.trim()}\n$$\n\n`
      )
      .replace(/\\\(\s*([\s\S]*?)\s*\\\)/g, (_, body) => `$${body.trim()}$`);

    text = text.replace(
      /\\\$\s*([^$\n]*\\[a-zA-Z][^$\n]*?)\s*\\\$/g,
      (_, body) => `$${body.trim()}$`
    );

    text = normalizeMalformedMathBlocks(text);
    text = wrapOrphanMathLines(text);
    text = normalizeChatIndentation(text);
    text = removeDecorativeHorizontalRules(text);
    return normalizeDollarDelimiters(text);
  });
}

/**
 * During streaming, hide unclosed math blocks so KaTeX never renders half a formula.
 */
export function bufferIncompleteMath(content) {
  if (!content) return '';
  return mapOutsideCode(content, (segment) => {
    let s = String(segment);
    let blockOpen = -1;
    let inlineOpen = -1;
    for (let i = 0; i < s.length; i += 1) {
      if (s[i] !== '$' || s[i - 1] === '\\') continue;
      if (s[i + 1] === '$') {
        blockOpen = blockOpen < 0 ? i : -1;
        i += 1;
      } else if (blockOpen < 0) {
        inlineOpen = inlineOpen < 0 ? i : -1;
      }
    }
    const openAt = blockOpen >= 0 ? blockOpen : inlineOpen;
    if (openAt >= 0) s = s.slice(0, openAt);
    s = s.replace(/\\[a-zA-Z]*$/, '');
    return s;
  });
}

export const renderMarkdown = (content, options = {}) => {
  if (!content) return '';
  const streaming = Boolean(options.streaming);
  const normalized = normalizeMathMarkdown(content);
  const raw = streaming ? bufferIncompleteMath(normalized) : normalized;
  return md.render(raw);
};

export function stripMarkdownCodeToolbar(html) {
  if (!html) return '';
  return html.replace(/<div class="code-actions">[\s\S]*?<\/div>/g, '');
}

export { md };
