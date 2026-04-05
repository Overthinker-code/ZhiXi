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
    env.VITE_DEV_API_PROXY_TARGET || 'http://127.0.0.1:18000';

  return mergeConfig(
    {
      mode: 'development',
      server: {
        open: true,
        fs: {
          strict: true,
        },
        proxy: {
          '/api': {
            target: proxyTarget,
            changeOrigin: true,
          },
        },
      },
      plugins: [
        eslint({
          cache: false,
          include: ['src/**/*.ts', 'src/**/*.tsx', 'src/**/*.vue'],
          exclude: ['node_modules'],
        }),
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
