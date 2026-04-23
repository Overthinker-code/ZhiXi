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

  console.log(
    `[vite-dev] API proxy enabled: /api -> ${proxyTarget.replace(/\/$/, '')}/api/v1`
  );

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
            ws: true,
            // 将 /api 映射到后端的 /api/v1
            rewrite: (path) => path.replace(/^\/api/, '/api/v1'),
          },
        },
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
