import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const source = readFileSync(
  resolve(process.cwd(), 'src/components/chat/ArtifactCards.vue'),
  'utf8'
);

assert.match(source, /preview_url \|\| item\?\.image_url \|\| item\?\.download_url/);
assert.match(source, /responseType: 'blob'/);
assert.match(source, /Authorization: `Bearer \$\{token\}`/);
assert.match(source, /URL\.createObjectURL\(response\.data\)/);
assert.match(source, /URL\.revokeObjectURL\(previewObjectUrl\.value\)/);
assert.match(source, /<video[\s\S]*?controls/);
assert.match(source, /<iframe[\s\S]*?sandbox/);
assert.doesNotMatch(source, /:src="selectedArtifact\.image_url"/);

console.log('chat artifact preview contract tests passed');
