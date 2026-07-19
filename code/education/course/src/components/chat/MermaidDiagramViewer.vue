<script setup lang="ts">
  import mermaid from 'mermaid';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';

  const props = defineProps<{
    code: string;
  }>();

  const html = ref('');
  const error = ref('');
  const renderId = computed(() => `zy-mermaid-${Math.random().toString(36).slice(2)}`);

  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    theme: 'base',
    themeVariables: {
      primaryColor: '#eef2ff',
      primaryTextColor: '#172033',
      primaryBorderColor: '#6366f1',
      lineColor: '#4f46e5',
      secondaryColor: '#f8fafc',
      tertiaryColor: '#ffffff',
      fontFamily: 'Inter, "Microsoft YaHei", sans-serif',
    },
  });

  async function render() {
    const code = String(props.code || '').trim();
    html.value = '';
    error.value = '';
    if (!code) return;
    try {
      await nextTick();
      const result = await mermaid.render(renderId.value, code);
      html.value = result.svg;
    } catch (err: any) {
      error.value = err?.message || 'Mermaid 图表渲染失败';
    }
  }

  onMounted(render);
  watch(() => props.code, render);
</script>

<template>
  <div class="mermaid-viewer">
    <div v-if="html" class="mermaid-viewer__canvas" v-html="html" />
    <pre v-else-if="error" class="mermaid-viewer__fallback">{{ error }}&#10;&#10;{{ code }}</pre>
    <div v-else class="mermaid-viewer__loading">正在渲染图表…</div>
  </div>
</template>

<style scoped>
  .mermaid-viewer {
    overflow: auto;
    padding: 18px;
    border: 1px solid rgba(99, 102, 241, 0.14);
    border-radius: 16px;
    background: #ffffff;
  }

  .mermaid-viewer__canvas {
    min-width: 620px;
  }

  .mermaid-viewer__canvas :deep(svg) {
    max-width: 100%;
    height: auto;
  }

  .mermaid-viewer__fallback,
  .mermaid-viewer__loading {
    margin: 0;
    color: #475467;
    white-space: pre-wrap;
  }
</style>
