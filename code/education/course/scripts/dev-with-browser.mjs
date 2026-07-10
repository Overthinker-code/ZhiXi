import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const forwardedArgs = process.argv.slice(2);

function hasOption(name) {
  return forwardedArgs.some((arg) => arg === name || arg.startsWith(`${name}=`));
}

function optionValue(name, fallback) {
  const inline = forwardedArgs.find((arg) => arg.startsWith(`${name}=`));
  if (inline) return inline.slice(name.length + 1);
  const index = forwardedArgs.indexOf(name);
  return index >= 0 && forwardedArgs[index + 1] ? forwardedArgs[index + 1] : fallback;
}

const devHost = optionValue('--host', process.env.VITE_DEV_HOST || '127.0.0.1');
const devPort = optionValue('--port', process.env.VITE_DEV_PORT || '5174');
const targetUrl =
  process.env.VITE_DEV_OPEN_URL || `http://localhost:${devPort}/login?force=1`;
const viteArgs = [...forwardedArgs];
if (!hasOption('--host')) viteArgs.push('--host', devHost);
if (!hasOption('--port')) viteArgs.push('--port', devPort);
if (!hasOption('--strictPort')) viteArgs.push('--strictPort');
if (!hasOption('--config')) viteArgs.push('--config', './config/vite.config.dev.ts');
const viteBin = fileURLToPath(
  new URL('../node_modules/vite/bin/vite.js', import.meta.url)
);

let browserOpened = false;

function openBrowser(url) {
  if (browserOpened) return;
  browserOpened = true;

  if (process.platform === 'darwin') {
    spawn('open', ['-a', 'Safari', url], {
      stdio: 'ignore',
      detached: true,
    }).unref();
    return;
  }

  if (process.platform === 'win32') {
    spawn('rundll32', ['url.dll,FileProtocolHandler', url], {
      stdio: 'ignore',
      detached: true,
    }).unref();
    return;
  }

  spawn('xdg-open', [url], { stdio: 'ignore', detached: true }).unref();
}

const child = spawn(process.execPath, [viteBin, ...viteArgs], {
  stdio: 'inherit',
  cwd: process.cwd(),
  env: process.env,
});

child.on('spawn', () => {
  setTimeout(() => openBrowser(targetUrl), 1800);
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});
