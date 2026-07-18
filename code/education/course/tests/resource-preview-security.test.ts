import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  cachePreviewBlob,
  clearPreviewBlobCache,
  getCachedPreviewBlob,
  previewBlobCacheSize,
} from '../src/components/resource/previewBlobCache';
import type { ResourceRecord } from '../src/api/resources';

const resource = (id: string): ResourceRecord => ({
  id,
  title: id,
  type: 'mind_map',
  subject: 'test',
  file_name: `${id}.mmd`,
  file_size: 1,
  content_type: 'text/html',
  favorite: false,
  top: false,
  upload_time: '2026-07-17T00:00:00.000Z',
  uploader_id: 'uploader',
});

clearPreviewBlobCache();
const privateBlob = new Blob(['private preview']);
cachePreviewBlob('account-a', resource('one'), privateBlob);
assert.equal(getCachedPreviewBlob('account-a', resource('one')), privateBlob);
assert.equal(getCachedPreviewBlob('account-b', resource('one')), undefined, 'blob cache must be account-scoped');

for (let index = 2; index <= 10; index += 1) {
  cachePreviewBlob('account-a', resource(String(index)), new Blob([String(index)]));
}
assert.equal(previewBlobCacheSize(), 8, 'the module cache remains bounded to eight blobs');
clearPreviewBlobCache();
assert.equal(previewBlobCacheSize(), 0, 'logout callback can clear all private previews');

const maliciousSvg = '<svg><script>globalThis.executed=true</script><a href="javascript:globalThis.executed=true">x</a><foreignObject><button onclick="globalThis.executed=true">x</button></foreignObject></svg>';
const inertImagePayload = new Blob([maliciousSvg], { type: 'image/svg+xml' });
assert.equal(inertImagePayload.type, 'image/svg+xml');

const dialogSource = readFileSync(
  resolve(process.cwd(), 'src/components/resource/ResourcePreviewDialog.vue'),
  'utf8'
);
assert.equal(dialogSource.includes('v-html'), false, 'Mermaid SVG must not be inserted as executable DOM');
assert.match(dialogSource, /<img v-if="mermaidSvgUrl" :src="mermaidSvgUrl"/);
assert.match(dialogSource, /new Blob\(\[result\.svg\], \{ type: 'image\/svg\+xml' \}\)/);
assert.match(dialogSource, /function normalizeMindmapRoots\(source: string\)/);
assert.match(dialogSource, /Mermaid mindmaps permit exactly one root/);
assert.match(dialogSource, /previewHtml\.value = await blob\.text\(\)/);
assert.match(dialogSource, /v-else-if="mode === 'document'"[\s\S]*?:srcdoc="previewHtml"[\s\S]*?sandbox="allow-same-origin"/);
assert.match(dialogSource, /v-else-if="mode === 'pdf'"[\s\S]*?:src="objectUrl"/);
assert.doesNotMatch(
  dialogSource,
  /sandbox=(?:"[^"]*\ballow-scripts\b[^"]*"|'[^']*\ballow-scripts\b[^']*')/,
  'server-converted HTML must remain scriptless in its iframe sandbox'
);

const userStoreSource = readFileSync(resolve(process.cwd(), 'src/store/modules/user/index.ts'), 'utf8');
assert.match(userStoreSource, /logoutCallBack\(\)[\s\S]*?clearPreviewBlobCache\(\)/);

console.log('resource preview security tests passed');
