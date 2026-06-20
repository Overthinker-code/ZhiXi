<template>
  <div
    v-show="visible"
    class="selection-ai-answer-panel"
    :class="{ 'selection-ai-answer-panel--enter': enterKick }"
    :style="panelCss"
    @mousedown.stop
  >
    <div class="ai-head" @mousedown.prevent="startDrag">
      <span>AI 解答</span>
      <button type="button" class="x" @click="$emit('close')">✕</button>
    </div>
    <div class="ai-body" :class="{ loading: loading }">
      <div v-if="loading" class="ai-loading-skel" aria-busy="true">
        <div class="zy-skeleton zy-skeleton--radar sk-line" />
        <div class="zy-skeleton zy-skeleton--radar sk-line short" />
        <div class="zy-skeleton zy-skeleton--radar sk-line" />
        <p class="ai-loading-tip">正在生成…</p>
      </div>
      <template v-else>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div
          v-if="html"
          class="md markdown-body"
          v-html="html"
        />
        <span v-if="typing" class="tw-caret">▍</span>
        <CitationArea
          v-if="html && !typing"
          class="selection-citation-area"
          :citations="citations"
          :citation-hints="citationHints"
          :confidence="confidence"
          :grounding-mode="groundingMode"
          :metrics="metrics"
          :show-empty-state="true"
        />
      </template>
    </div>
    <span
      class="resize-handle right selection-ai-resize-handle"
      @mousedown.prevent.stop="startResize($event, 'right')"
    />
    <span
      class="resize-handle bottom selection-ai-resize-handle"
      @mousedown.prevent.stop="startResize($event, 'bottom')"
    />
    <span
      class="resize-handle corner selection-ai-resize-handle"
      @mousedown.prevent.stop="startResize($event, 'bottom-right')"
    />
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
  import type { ChatMetrics, CitationItem } from '@/api/rag';
  import CitationArea from '@/views/chat/components/CitationArea.vue';

  type Bounds = { left: number; top: number; width: number; height: number };

  const props = defineProps<{
    visible: boolean;
    session: number;
    initialBounds: Bounds | null;
    html: string;
    loading: boolean;
    typing: boolean;
    citations?: CitationItem[];
    citationHints?: CitationItem[];
    confidence?: string;
    groundingMode?: string;
    metrics?: ChatMetrics;
  }>();

  defineEmits<{ close: [] }>();

  const MIN_W = 280;
  const MIN_H = 200;
  const MAX_W = 720;
  const MAX_H = 640;

  const enterKick = ref(false);

  const left = ref(0);
  const top = ref(0);
  const width = ref(400);
  const height = ref(360);

  const panelCss = computed(() => ({
    left: `${left.value}px`,
    top: `${top.value}px`,
    width: `${width.value}px`,
    height: `${height.value}px`,
  }));

  function applyInitial() {
    const b = props.initialBounds;
    if (b) {
      left.value = b.left;
      top.value = b.top;
      width.value = b.width;
      height.value = b.height;
    }
  }

  watch(
    () => props.session,
    () => {
      if (props.visible) applyInitial();
      enterKick.value = false;
      requestAnimationFrame(() => {
        enterKick.value = true;
        setTimeout(() => {
          enterKick.value = false;
        }, 520);
      });
    }
  );

  watch(
    () => props.visible,
    (v) => {
      if (v) {
        applyInitial();
        enterKick.value = false;
        requestAnimationFrame(() => {
          enterKick.value = true;
          setTimeout(() => {
            enterKick.value = false;
          }, 520);
        });
      }
    }
  );

  onMounted(() => {
    if (props.visible && props.initialBounds) applyInitial();
  });

  const drag = ref<{
    active: boolean;
    ox: number;
    oy: number;
  }>({ active: false, ox: 0, oy: 0 });

  const resize = ref<{
    active: boolean;
    mode: 'right' | 'bottom' | 'bottom-right' | null;
    sx: number;
    sy: number;
    sw: number;
    sh: number;
  }>({
    active: false,
    mode: null,
    sx: 0,
    sy: 0,
    sw: 0,
    sh: 0,
  });

  function startDrag(e: MouseEvent) {
    if ((e.target as HTMLElement).closest('.x')) return;
    drag.value = {
      active: true,
      ox: e.clientX - left.value,
      oy: e.clientY - top.value,
    };
  }

  function startResize(
    e: MouseEvent,
    mode: 'right' | 'bottom' | 'bottom-right'
  ) {
    resize.value = {
      active: true,
      mode,
      sx: e.clientX,
      sy: e.clientY,
      sw: width.value,
      sh: height.value,
    };
  }

  function onMove(e: MouseEvent) {
    if (resize.value.active && resize.value.mode) {
      const dx = e.clientX - resize.value.sx;
      const dy = e.clientY - resize.value.sy;
      let w = resize.value.sw;
      let h = resize.value.sh;
      if (
        resize.value.mode === 'right' ||
        resize.value.mode === 'bottom-right'
      ) {
        w = Math.min(
          MAX_W,
          Math.max(MIN_W, resize.value.sw + dx),
          window.innerWidth - left.value - 8
        );
      }
      if (
        resize.value.mode === 'bottom' ||
        resize.value.mode === 'bottom-right'
      ) {
        h = Math.min(
          MAX_H,
          Math.max(MIN_H, resize.value.sh + dy),
          window.innerHeight - top.value - 8
        );
      }
      width.value = w;
      height.value = h;
      return;
    }
    if (!drag.value.active) return;
    left.value = Math.max(
      0,
      Math.min(window.innerWidth - width.value, e.clientX - drag.value.ox)
    );
    top.value = Math.max(
      60,
      Math.min(window.innerHeight - height.value, e.clientY - drag.value.oy)
    );
  }

  function onUp() {
    drag.value.active = false;
    resize.value.active = false;
    resize.value.mode = null;
  }

  onMounted(() => {
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  });
  onUnmounted(() => {
    window.removeEventListener('mousemove', onMove);
    window.removeEventListener('mouseup', onUp);
  });
</script>

<style scoped lang="less">
  .selection-ai-answer-panel {
    position: fixed;
    z-index: 10002;
    background:
      linear-gradient(
        145deg,
        rgba(37, 99, 235, 0.88) 0%,
        rgba(6, 182, 212, 0.74) 46%,
        rgba(124, 58, 237, 0.84) 100%
      );
    backdrop-filter: blur(18px) saturate(1.25);
    -webkit-backdrop-filter: blur(18px) saturate(1.25);
    border-radius: 14px;
    border: 1px solid rgba(186, 230, 253, 0.72);
    box-shadow:
      0 0 0 1px rgba(255, 255, 255, 0.18) inset,
      0 22px 58px rgba(37, 99, 235, 0.36),
      0 0 34px rgba(6, 182, 212, 0.28);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-sizing: border-box;
    transform-origin: top left;
    transition:
      opacity 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275),
      transform 0.45s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  }

  .selection-ai-answer-panel--enter {
    animation: sel-panel-spring 0.48s cubic-bezier(0.175, 0.885, 0.32, 1.275) both;
  }

  @keyframes sel-panel-spring {
    from {
      opacity: 0;
      transform: scale(0.86) translateY(10px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }

  .ai-head {
    flex-shrink: 0;
    height: 40px;
    padding: 0 10px 0 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(
      90deg,
      rgba(29, 78, 216, 0.98),
      rgba(14, 165, 233, 0.9),
      rgba(124, 58, 237, 0.96)
    );
    border-bottom: 1px solid rgba(224, 242, 254, 0.35);
    cursor: grab;
    font-weight: 600;
    color: #f8fbff;
    user-select: none;

    &:active {
      cursor: grabbing;
    }
  }

  .x {
    border: none;
    background: none;
    cursor: pointer;
    color: rgba(255, 255, 255, 0.82);
    padding: 4px 8px;
    font-size: 16px;
    line-height: 1;
  }

  .ai-body {
    flex: 1;
    min-height: 0;
    padding: 10px 14px 12px;
    overflow: auto;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    background: linear-gradient(
      180deg,
      rgba(8, 13, 30, 0.42),
      rgba(8, 13, 30, 0.26)
    );

    &.loading {
      align-items: stretch;
      justify-content: flex-start;
    }
  }

  .ai-loading-skel {
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: 100%;
    padding: 8px 0;
  }

  .sk-line {
    height: 14px;
    border-radius: 8px;
  }

  .sk-line.short {
    width: 55%;
  }

  .ai-loading-tip {
    margin: 8px 0 0;
    font-size: 12px;
    color: #e0f2fe;
    text-align: center;
  }

  .md {
    width: 100%;
    box-sizing: border-box;
    padding-left: 6px;
    font-size: 13px;
    line-height: 1.7;
    color: #f8fbff;
  }

  :deep(.markdown-body ol),
  :deep(.markdown-body ul) {
    margin-left: 0;
    padding-left: 1.55em;
  }

  :deep(.markdown-body li) {
    padding-left: 0.2em;
  }

  .tw-caret {
    color: #67e8f9;
    animation: blink 1s step-end infinite;
    margin-left: 2px;
    align-self: flex-start;
  }

  .selection-citation-area {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid rgba(226, 232, 240, 0.24);
  }

  :deep(.citation-strip) {
    gap: 6px;
  }

  :deep(.citation-strip__label) {
    color: rgba(226, 232, 240, 0.82);
  }

  :deep(.source-chip),
  :deep(.source-toggle),
  :deep(.meta-pill),
  :deep(.current-file-pill),
  :deep(.context-hint-pill) {
    max-width: 100%;
    min-height: 24px;
    font-size: 11px;
  }

  :deep(.source-chip strong) {
    font-size: 11px;
  }

  :deep(.source-chip__scope) {
    font-size: 10px;
  }

  :deep(.citation-detail-list) {
    width: 100%;
    max-height: min(260px, 44vh);
    border-color: rgba(226, 232, 240, 0.42);
    background: rgba(255, 255, 255, 0.94);
  }

  @keyframes blink {
    50% {
      opacity: 0;
    }
  }

  :deep(.markdown-body .code-block) {
    margin: 10px 0;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid rgba(100, 116, 139, 0.35);
  }

  :deep(.markdown-body .code-header) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 10px;
    background: #334155;
    color: #e2e8f0;
    font-size: 11px;
  }

  :deep(.markdown-body .code-lang) {
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  :deep(.markdown-body pre.hljs) {
    margin: 0;
    padding: 12px;
    font-size: 12px;
    line-height: 1.5;
    overflow-x: auto;
  }

  :deep(.markdown-body pre) {
    max-width: 100%;
  }

  .resize-handle {
    position: absolute;
    z-index: 3;
  }

  .resize-handle.right {
    top: 0;
    right: 0;
    width: 8px;
    height: 100%;
    cursor: ew-resize;
  }

  .resize-handle.bottom {
    left: 0;
    bottom: 0;
    width: 100%;
    height: 8px;
    cursor: ns-resize;
  }

  .resize-handle.corner {
    right: 0;
    bottom: 0;
    width: 14px;
    height: 14px;
    cursor: nwse-resize;
  }
</style>
