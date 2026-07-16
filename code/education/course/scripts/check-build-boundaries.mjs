import { readFileSync, statSync } from 'node:fs';
import { resolve } from 'node:path';

const distDir = resolve(process.cwd(), 'dist');
const html = readFileSync(resolve(distDir, 'index.html'), 'utf8');
const assetPaths = [
  ...html.matchAll(/(?:src|href)="(\/assets\/[^"?]+\.js)"/g),
].map((match) => match[1]);
const uniqueAssets = [...new Set(assetPaths)];
const forbiddenPreloads = uniqueAssets.filter((asset) =>
  /\/(?:chart|markdown)\./.test(asset)
);

if (forbiddenPreloads.length) {
  throw new Error(
    `Heavy lazy-route chunks leaked into initial HTML: ${forbiddenPreloads.join(', ')}`
  );
}

const initialJsBytes = uniqueAssets.reduce(
  (total, asset) => total + statSync(resolve(distDir, asset.slice(1))).size,
  0
);
const maxInitialJsBytes = 1_500_000;
if (initialJsBytes > maxInitialJsBytes) {
  throw new Error(
    `Initial JavaScript is ${initialJsBytes} bytes; budget is ${maxInitialJsBytes}`
  );
}

console.log(
  JSON.stringify(
    {
      status: 'passed',
      initialJsBytes,
      maxInitialJsBytes,
      initialAssets: uniqueAssets,
      lazyHeavyChunks: ['chart', 'markdown'],
    },
    null,
    2
  )
);
