<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
  import mermaid from 'mermaid';

  export interface KnowledgeGraphNode {
    id: string;
    name: string;
    mastery_score?: number | null;
  }

  export interface KnowledgeGraphEdge {
    source: string;
    target: string;
    label?: string | null;
  }

  export interface KnowledgeGraphJson {
    nodes: KnowledgeGraphNode[];
    edges: KnowledgeGraphEdge[];
  }

  const props = defineProps<{ graphJson: KnowledgeGraphJson }>();

  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    theme: 'base',
    flowchart: { curve: 'basis', useMaxWidth: false },
    themeVariables: {
      primaryColor: '#eef2ff',
      primaryTextColor: '#1f2937',
      primaryBorderColor: '#818cf8',
      lineColor: '#98a2b3',
      fontFamily: 'Inter, "PingFang SC", "Microsoft YaHei", sans-serif',
    },
  });

  const svg = ref('');
  const error = ref('');
  const loading = ref(false);
  const scale = ref(1);
  const offsetX = ref(0);
  const offsetY = ref(0);
  const dragging = ref(false);
  let pointerStart = { x: 0, y: 0, offsetX: 0, offsetY: 0 };
  let renderVersion = 0;

  const transformStyle = computed(() => ({
    transform: `translate(${offsetX.value}px, ${offsetY.value}px) scale(${scale.value})`,
  }));

  function safeLabel(value: unknown) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/[\[\]{}]/g, '')
      .replace(/\r?\n/g, ' ')
      .slice(0, 120);
  }

  function toMermaid(graph: KnowledgeGraphJson) {
    const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
    const edges = Array.isArray(graph?.edges) ? graph.edges : [];
    const idMap = new Map(nodes.map((node, index) => [String(node.id), `n${index}`]));
    const lines = [
      'graph TD',
      'classDef weak fill:#fff1f0,stroke:#f04438,color:#7a271a;',
      'classDef learning fill:#fffaeb,stroke:#f79009,color:#7a2e0e;',
      'classDef mastered fill:#ecfdf3,stroke:#12b76a,color:#05603a;',
      'classDef neutral fill:#eef2ff,stroke:#818cf8,color:#344054;',
    ];
    nodes.forEach((node, index) => {
      const localId = `n${index}`;
      lines.push(`${localId}["${safeLabel(node.name)}"]`);
      const score = typeof node.mastery_score === 'number' ? node.mastery_score : null;
      const className = score === null ? 'neutral' : score < 0.4 ? 'weak' : score >= 0.75 ? 'mastered' : 'learning';
      lines.push(`class ${localId} ${className};`);
    });
    edges.forEach((edge) => {
      const source = idMap.get(String(edge.source));
      const target = idMap.get(String(edge.target));
      if (!source || !target || source === target) return;
      const label = safeLabel(edge.label);
      lines.push(label ? `${source} -->|"${label}"| ${target}` : `${source} --> ${target}`);
    });
    return lines.join('\n');
  }

  async function renderGraph() {
    const version = ++renderVersion;
    loading.value = true;
    error.value = '';
    try {
      await nextTick();
      const result = await mermaid.render(
        `knowledge-graph-${Date.now()}-${version}`,
        toMermaid(props.graphJson)
      );
      if (version === renderVersion) svg.value = result.svg;
    } catch (reason) {
      if (version === renderVersion) {
        error.value = reason instanceof Error ? reason.message : '知识图谱渲染失败';
        svg.value = '';
      }
    } finally {
      if (version === renderVersion) loading.value = false;
    }
  }

  function setScale(value: number) {
    scale.value = Math.min(2.4, Math.max(0.45, Number(value.toFixed(2))));
  }

  function resetView() {
    scale.value = 1;
    offsetX.value = 0;
    offsetY.value = 0;
  }

  function onWheel(event: WheelEvent) {
    setScale(scale.value + (event.deltaY < 0 ? 0.1 : -0.1));
  }

  function onPointerDown(event: PointerEvent) {
    dragging.value = true;
    pointerStart = {
      x: event.clientX,
      y: event.clientY,
      offsetX: offsetX.value,
      offsetY: offsetY.value,
    };
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  }

  function onPointerMove(event: PointerEvent) {
    if (!dragging.value) return;
    offsetX.value = pointerStart.offsetX + event.clientX - pointerStart.x;
    offsetY.value = pointerStart.offsetY + event.clientY - pointerStart.y;
  }

  function onPointerUp(event: PointerEvent) {
    dragging.value = false;
    const target = event.currentTarget as HTMLElement;
    if (target.hasPointerCapture(event.pointerId)) target.releasePointerCapture(event.pointerId);
  }

  watch(() => props.graphJson, renderGraph, { deep: true, immediate: true });
  onBeforeUnmount(() => { renderVersion += 1; });
</script>

<template>
  <section class="knowledge-graph-viewer">
    <header>
      <span>拖动画布查看 · 滚轮缩放</span>
      <div>
        <button type="button" aria-label="缩小" @click="setScale(scale - 0.15)">−</button>
        <strong>{{ Math.round(scale * 100) }}%</strong>
        <button type="button" aria-label="放大" @click="setScale(scale + 0.15)">＋</button>
        <button type="button" @click="resetView">复位</button>
      </div>
    </header>
    <div
      class="knowledge-graph-viewer__viewport"
      :class="{ 'is-dragging': dragging }"
      @wheel.prevent="onWheel"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
    >
      <div v-if="loading" class="knowledge-graph-viewer__state">正在绘制知识图谱…</div>
      <div v-else-if="error" class="knowledge-graph-viewer__state is-error">{{ error }}</div>
      <div v-else class="knowledge-graph-viewer__canvas" :style="transformStyle" v-html="svg" />
    </div>
  </section>
</template>

<style scoped lang="scss">
  .knowledge-graph-viewer {
    overflow: hidden;
    border: 1px solid rgba(99, 102, 241, 0.16);
    border-radius: 14px;
    background: #fbfbff;

    > header {
      display: flex;
      min-height: 44px;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 0 12px;
      border-bottom: 1px solid rgba(15, 23, 42, 0.07);
      color: #667085;
      background: #fff;
      font-size: 12px;

      div { display: flex; align-items: center; gap: 6px; }
      strong { min-width: 42px; color: #4f46e5; text-align: center; }
      button {
        min-width: 30px;
        height: 28px;
        padding: 0 8px;
        border: 1px solid #e4e7ec;
        border-radius: 7px;
        color: #475467;
        background: #fff;
        cursor: pointer;
      }
    }
  }

  .knowledge-graph-viewer__viewport {
    position: relative;
    height: min(62vh, 560px);
    min-height: 360px;
    overflow: hidden;
    cursor: grab;
    touch-action: none;
    user-select: none;

    &.is-dragging { cursor: grabbing; }
  }

  .knowledge-graph-viewer__canvas {
    width: max-content;
    min-width: 100%;
    min-height: 100%;
    display: grid;
    padding: 32px;
    place-items: center;
    transform-origin: center center;
    transition: transform 80ms ease-out;

    :deep(svg) {
      display: block;
      max-width: none !important;
      height: auto;
    }
  }

  .knowledge-graph-viewer__state {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    color: #667085;
    font-size: 13px;

    &.is-error { color: #b42318; }
  }
</style>
