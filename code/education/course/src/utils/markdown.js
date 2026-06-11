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
  html: true,
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
  allowInlineWithSpace: false,
  throwOnError: false,
  errorColor: '#ef4444',
});

/**
 * During streaming, hide unclosed math blocks so KaTeX never renders half a formula.
 */
export function bufferIncompleteMath(content) {
  if (!content) return '';
  let s = String(content);

  const dblCount = (s.match(/\$\$/g) || []).length;
  if (dblCount % 2 === 1) {
    const last = s.lastIndexOf('$$');
    if (last >= 0) s = s.slice(0, last);
  }

  const withoutDbl = s.replace(/\$\$/g, '\0\0');
  const singleCount = (withoutDbl.match(/\$/g) || []).length;
  if (singleCount % 2 === 1) {
    const last = s.lastIndexOf('$');
    if (last >= 0) s = s.slice(0, last);
  }

  s = s.replace(/\\[a-zA-Z]*$/, '');
  const tail = s.match(/[{(][^})]*$/);
  if (tail && tail[0].length > 48) {
    s = s.slice(0, -tail[0].length);
  }
  return s;
}

export const renderMarkdown = (content, options = {}) => {
  if (!content) return '';
  const streaming = Boolean(options.streaming);
  const raw = streaming ? bufferIncompleteMath(content) : content;
  return md.render(raw);
};

export function stripMarkdownCodeToolbar(html) {
  if (!html) return '';
  return html.replace(/<div class="code-actions">[\s\S]*?<\/div>/g, '');
}

export { md };
