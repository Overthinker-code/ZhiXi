import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(resolve(here, '../src/components/chat/ChatLayout.vue'), 'utf8');

assert.match(
  source,
  /courseContext:\s*courseContext\.value\.courseId\s*\?\s*\{\s*\.\.\.courseContext\.value,\s*useCourseRag:\s*autoCourseRag\s*\}/s,
  'selected course context must be preserved even when course RAG is disabled'
);
assert.match(
  source,
  /courseRag:\s*autoCourseRag/,
  'course RAG remains an independent retrieval switch'
);

console.log('chat course context contract tests passed');
