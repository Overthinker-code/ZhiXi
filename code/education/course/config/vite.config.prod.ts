import { mergeConfig } from 'vite';
import baseConfig from './vite.config.base';
import configCompressPlugin from './plugin/compress';
import configVisualizerPlugin from './plugin/visualizer';
import configArcoResolverPlugin from './plugin/arcoResolver';

export default mergeConfig(
  {
    mode: 'production',
    plugins: [
      configCompressPlugin('gzip'),
      configVisualizerPlugin(),
      configArcoResolverPlugin(),
    ],
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            // Keep the UI library isolated so dependencies shared with lazy
            // chart/Markdown routes cannot pull those heavy chunks into HTML preload.
            arco: ['@arco-design/web-vue'],
            chart: ['echarts', 'vue-echarts'],
            markdown: [
              'markdown-it',
              'markdown-it-emoji',
              'markdown-it-link-attributes',
              'highlight.js',
              'katex',
              '@mdit/plugin-katex',
            ],
            vue: ['vue', 'vue-router', 'pinia', '@vueuse/core', 'vue-i18n'],
          },
        },
      },
      chunkSizeWarningLimit: 1000,
    },
  },
  baseConfig
);
