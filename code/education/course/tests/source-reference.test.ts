import assert from 'node:assert/strict';
import {
  safeWebUrl,
  sourceActionLabel,
  sourceCategory,
  sourceDateLabel,
  sourceLanguageLabel,
  sourceReferenceFrom,
  studentFacingReason,
} from '../src/components/resource/sourceReference';

assert.equal(safeWebUrl('https://open.example.org/reading?q=1'), 'https://open.example.org/reading?q=1');
assert.equal(safeWebUrl('javascript:alert(1)'), '');
assert.equal(safeWebUrl('data:text/html,unsafe'), '');
assert.equal(safeWebUrl('https://user:password@example.org/private'), '');

const reference = sourceReferenceFrom({
  sourceMetadata: {
    provider: 'open_library',
    providerName: 'Open Library',
    kind: 'book',
    summary: '一本开放阅读材料',
    authors: ['Ada Lovelace', 'Grace Hopper'],
    year: 2024,
    licenseStatus: '开放访问',
    canonicalUrl: 'https://openlibrary.org/works/OL1W',
    coverUrl: 'javascript:alert(1)',
  },
}, { url: 'https://fallback.example.org' });
assert.equal(reference.provider, 'Open Library');
assert.equal(reference.kind, 'book');
assert.equal(reference.authors, 'Ada Lovelace · Grace Hopper');
assert.equal(reference.year, '2024');
assert.equal(reference.canonicalUrl, 'https://openlibrary.org/works/OL1W');
assert.equal(reference.thumbnailUrl, '');
assert.equal(reference.domain, 'openlibrary.org');
assert.equal(sourceCategory(reference.kind), '开放图书');
assert.equal(sourceActionLabel(reference.kind), '在原站阅读');
assert.equal(studentFacingReason('这是基于推荐主题的即时预览', '围绕事务隔离安排复习'), '围绕事务隔离安排复习');
assert.equal(sourceLanguageLabel('zh-CN'), '中文');
assert.equal(sourceLanguageLabel('en_US'), '英文');
assert.equal(sourceLanguageLabel('unknown-tag'), '');
assert.equal(sourceLanguageLabel(''), '');
assert.equal(sourceDateLabel('2026-07-19T15:30:00+08:00'), '2026年7月19日');
assert.equal(sourceDateLabel('2026-07-19'), '2026年7月19日');
assert.equal(sourceDateLabel('not-a-date'), '');

console.log('source reference tests passed');
