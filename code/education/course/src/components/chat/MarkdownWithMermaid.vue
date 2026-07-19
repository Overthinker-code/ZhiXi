<script setup lang="ts">
  import { computed } from 'vue';
  import { renderMarkdown } from '@/utils/markdown';
  import MermaidDiagramViewer from './MermaidDiagramViewer.vue';

  const props = withDefaults(
    defineProps<{
      content: string;
      streaming?: boolean;
    }>(),
    { streaming: false }
  );

  type Segment =
    | { type: 'markdown'; value: string; html: string }
    | { type: 'mermaid'; value: string; html?: never };

  const segments = computed<Segment[]>(() => {
    const source = String(props.content || '');
    // Keep an unfinished fence as ordinary streaming text. It becomes a
    // diagram only after the model has emitted the closing fence.
    const fence = /```mermaid\s*\r?\n([\s\S]*?)```/gi;
    const result: Segment[] = [];
    let cursor = 0;
    let match: RegExpExecArray | null;
    while ((match = fence.exec(source)) !== null) {
      const before = source.slice(cursor, match.index);
      if (before.trim()) {
        result.push({
          type: 'markdown',
          value: before,
          html: renderMarkdown(before, { streaming: props.streaming }),
        });
      }
      const code = String(match[1] || '').trim();
      if (code) result.push({ type: 'mermaid', value: code });
      cursor = match.index + match[0].length;
    }
    const after = source.slice(cursor);
    if (after.trim() || !result.length) {
      result.push({
        type: 'markdown',
        value: after,
        html: renderMarkdown(after, { streaming: props.streaming }),
      });
    }
    return result;
  });
</script>

<template>
  <div class="markdown-with-mermaid">
    <template v-for="(segment, index) in segments" :key="`${segment.type}-${index}`">
      <MermaidDiagramViewer
        v-if="segment.type === 'mermaid'"
        class="markdown-with-mermaid__diagram"
        :code="segment.value"
      />
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div v-else class="markdown-with-mermaid__text" v-html="segment.html" />
    </template>
  </div>
</template>

<style scoped>
  .markdown-with-mermaid__diagram {
    margin: 14px 0;
  }

  .markdown-with-mermaid__text:empty {
    display: none;
  }
</style>
