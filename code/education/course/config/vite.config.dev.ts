import { resolve } from 'path';
import AutoImport from 'unplugin-auto-import/vite';
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers';
import Components from 'unplugin-vue-components/vite';
import { defineConfig, loadEnv, mergeConfig } from 'vite';
import eslint from 'vite-plugin-eslint';
import baseConfig from './vite.config.base';

/** 开发时 API 走同源 /api → 代理到 SSH 隧道本地端口，避免直连 127.0.0.1:端口 的跨源与连接问题 */
export default defineConfig(({ mode }) => {
  const root = resolve(__dirname, '..');
  const env = loadEnv(mode, root, '');
  const proxyTarget =
    env.VITE_DEV_API_PROXY_TARGET || 'http://127.0.0.1:8001';
  const proxyToApiV1 = (path: string) => `/api/v1${path}`;
  const rewriteApiPath = (path: string) =>
    path.startsWith('/api/v1/') ? path : path.replace(/^\/api/, '/api/v1');
  const apiV1Prefixes = [
    '/rag',
    '/chat',
    '/file',
    '/login',
    '/users',
    '/password-recovery',
    '/reset-password',
    '/dashboard',
    '/behavior',
    '/digital-human',
    '/learning-report',
    '/ai-metrics',
    '/resource-generation',
    '/resource-workshop',
    '/alerts',
    '/education',
  ];
  const proxy: Record<string, any> = {
    '/api': {
      target: proxyTarget,
      changeOrigin: true,
      ws: true,
      rewrite: rewriteApiPath,
    },
  };
  for (const prefix of apiV1Prefixes) {
    proxy[prefix] = {
      target: proxyTarget,
      changeOrigin: true,
      ws: true,
      rewrite: (path: string) => proxyToApiV1(path),
    };
  }

  console.log(
    `[vite-dev] API proxy enabled: /api -> ${proxyTarget.replace(/\/$/, '')}/api/v1`
  );

  return mergeConfig(
    {
      mode: 'development',
      server: {
        open: false,
        fs: {
          strict: true,
        },
        proxy,
      },
      plugins: [
        // 开发环境禁用 ESLint 避免格式警告
        // eslint({
        //   cache: false,
        //   include: ['src/**/*.ts', 'src/**/*.tsx', 'src/**/*.vue'],
        //   exclude: ['node_modules'],
        // }),
        AutoImport({
          resolvers: [ElementPlusResolver()],
        }),
        Components({
          resolvers: [ElementPlusResolver()],
        }),
      ],
    },
    baseConfig
  );
});
