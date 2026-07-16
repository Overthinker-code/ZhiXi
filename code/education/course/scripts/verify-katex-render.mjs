/**
 * Real KaTeX render verification (no mocks).
 * Run: node scripts/verify-katex-render.mjs
 */
import MarkdownIt from 'markdown-it';
import { katex } from '@mdit/plugin-katex';

function bufferIncompleteMath(content) {
  if (!content) return '';
  let s = String(content);
  if ((s.match(/\$\$/g) || []).length % 2 === 1) {
    const last = s.lastIndexOf('$$');
    if (last >= 0) s = s.slice(0, last);
  }
  const withoutDbl = s.replace(/\$\$/g, '\0\0');
  if ((withoutDbl.match(/\$/g) || []).length % 2 === 1) {
    const last = s.lastIndexOf('$');
    if (last >= 0) s = s.slice(0, last);
  }
  s = s.replace(/\\[a-zA-Z]*$/, '');
  const tail = s.match(/[{(][^})]*$/);
  if (tail && tail[0].length > 48) s = s.slice(0, -tail[0].length);
  return s;
}

const md = MarkdownIt({ html: true, breaks: true }).use(katex, {
  delimiters: 'all',
  throwOnError: false,
});

const renderMarkdown = (content, { streaming = false } = {}) => {
  const raw = streaming ? bufferIncompleteMath(content) : content;
  return md.render(raw || '');
};

const samples = [
  "导数定义：\n\n$$f'(x) = \\lim_{h \\to 0} \\frac{f(x+h)-f(x)}{h}$$\n",
  "展开：$(x+h)^2 - x^2 = 2xh + h^2$",
  "行内：$\\tan x$ 与 $\\frac{a}{b}$",
];

const hasCorruptFrac = (html) =>
  html.includes('□rac') || /\bext\{lim/.test(html);

let failed = 0;
for (const raw of samples) {
  const html = renderMarkdown(raw);
  const ok =
    html.includes('katex') &&
    !html.includes('katex-error') &&
    !hasCorruptFrac(html);
  console.log(ok ? 'PASS' : 'FAIL', raw.slice(0, 60));
  if (!ok) {
    failed += 1;
    console.log(html.slice(0, 300));
  }
}

const partial = "公式：$$f'(x)=\\lim_{h \\to 0}\\frac";
const htmlPartial = renderMarkdown(partial, { streaming: true });
if (htmlPartial.includes('katex-error')) {
  console.log('FAIL partial stream should not katex-error');
  failed += 1;
} else {
  console.log('PASS partial stream buffered without error');
}

process.exit(failed ? 1 : 0);
