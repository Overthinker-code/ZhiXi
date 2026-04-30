import { spawn } from 'node:child_process';

const devHost = process.env.VITE_DEV_HOST || '127.0.0.1';
const devPort = process.env.VITE_DEV_PORT || '5174';
const targetUrl =
  process.env.VITE_DEV_OPEN_URL || `http://localhost:${devPort}/login?force=1`;
const viteArgs = [
  'vite',
  '--host',
  devHost,
  '--port',
  devPort,
  '--strictPort',
  '--config',
  './config/vite.config.dev.ts',
];
const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';

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
    spawn('cmd', ['/c', 'start', '', url], {
      stdio: 'ignore',
      detached: true,
    }).unref();
    return;
  }

  spawn('xdg-open', [url], { stdio: 'ignore', detached: true }).unref();
}

const child = spawn(npmCmd, ['exec', '--', ...viteArgs], {
  stdio: 'inherit',
  cwd: process.cwd(),
  env: process.env,
  shell: true,
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
