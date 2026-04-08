<template>
  <div class="mindmap-wrapper">
    <!-- 工具栏 -->
    <div class="mindmap-toolbar">
      <div class="toolbar-left">
        <icon-mind-mapping class="toolbar-icon" />
        <span class="toolbar-title">{{ title }}</span>
        <a-tag color="arcoblue" size="small">思维导图</a-tag>
      </div>
      <a-space :size="8">
        <a-tooltip content="适应屏幕">
          <a-button size="mini" @click="fitView">
            <template #icon><icon-expand /></template>
          </a-button>
        </a-tooltip>
        <a-tooltip content="放大">
          <a-button size="mini" @click="zoom(1.2)">
            <template #icon><icon-zoom-in /></template>
          </a-button>
        </a-tooltip>
        <a-tooltip content="缩小">
          <a-button size="mini" @click="zoom(0.8)">
            <template #icon><icon-zoom-out /></template>
          </a-button>
        </a-tooltip>
        <a-tooltip content="下载 SVG">
          <a-button size="mini" @click="downloadSVG">
            <template #icon><icon-download /></template>
          </a-button>
        </a-tooltip>
        <a-button v-if="editable" size="mini" type="primary" @click="showEditor = !showEditor">
          <template #icon><icon-code /></template>
          {{ showEditor ? '隐藏编辑' : '编辑 Markdown' }}
        </a-button>
      </a-space>
    </div>

    <div class="mindmap-body" :class="{ 'with-editor': showEditor && editable }">
      <!-- SVG 容器 -->
      <div class="mindmap-canvas" ref="canvasRef">
        <svg ref="svgRef" class="markmap-svg"></svg>
        <div v-if="isLoading" class="mindmap-loading">
          <a-spin size="large" />
          <p>生成思维导图中...</p>
        </div>
        <div v-if="!isLoading && !markdown" class="mindmap-empty">
          <icon-mind-mapping class="empty-icon" />
          <p>暂无思维导图内容</p>
          <p class="empty-sub">请提供 Markdown 格式的知识点大纲</p>
        </div>
      </div>

      <!-- Markdown 编辑面板 -->
      <transition name="editor-slide">
        <div v-if="showEditor && editable" class="markdown-editor">
          <div class="editor-header">
            <span>Markdown 源码</span>
            <a-button size="mini" type="primary" @click="applyMarkdown">应用</a-button>
          </div>
          <a-textarea
            v-model="editingMarkdown"
            class="editor-textarea"
            :auto-size="{ minRows: 12, maxRows: 28 }"
            placeholder="# 根节点&#10;## 子节点一&#10;### 叶子节点&#10;## 子节点二"
          />
        </div>
      </transition>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue';
  import { Transformer } from 'markmap-lib';
  import { Markmap, loadCSS, loadJS } from 'markmap-view';

  // ========== Props ==========
  const props = withDefaults(
    defineProps<{
      markdown?: string;
      title?: string;
      editable?: boolean;
      isLoading?: boolean;
    }>(),
    {
      markdown: '',
      title: '知识点思维导图',
      editable: true,
      isLoading: false,
    }
  );

  const emit = defineEmits<{
    (e: 'update:markdown', val: string): void;
  }>();

  // ========== 内部状态 ==========
  const svgRef = ref<SVGSVGElement | null>(null);
  const canvasRef = ref<HTMLElement | null>(null);
  const showEditor = ref(false);
  const editingMarkdown = ref(props.markdown);

  let mm: Markmap | null = null;
  const transformer = new Transformer();

  // ========== 渲染 ==========
  async function renderMarkmap(md: string) {
    if (!svgRef.value || !md) return;
    try {
      const { root, features } = transformer.transform(md);
      const { styles, scripts } = transformer.getUsedAssets(features);
      if (styles?.length) await loadCSS(styles);
      if (scripts?.length) await loadJS(scripts, { getMarkmap: () => ({ Markmap }) });

      if (!mm) {
        mm = Markmap.create(svgRef.value, {
          duration: 300,
          maxWidth: 260,
          color: (node: any) => {
            const palette = ['#165DFF', '#0fc6c2', '#9254de', '#f5a623', '#00b42a', '#f53f3f'];
            return palette[node.state?.depth % palette.length] || '#165DFF';
          },
        });
      }
      await mm.setData(root);
      mm.fit();
    } catch (e) {
      // ignore render errors (incomplete markdown)
    }
  }

  function fitView() {
    mm?.fit();
  }

  function zoom(factor: number) {
    if (!mm) return;
    const svg = svgRef.value;
    if (!svg) return;
    // access markmap internal transform
    const g = svg.querySelector('g');
    if (!g) return;
    const transform = g.getAttribute('transform') || '';
    const scaleMatch = transform.match(/scale\(([^)]+)\)/);
    const currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1;
    const newScale = currentScale * factor;
    const newTransform = transform.replace(
      /scale\([^)]+\)/,
      `scale(${newScale})`
    );
    g.setAttribute('transform', newTransform.includes('scale') ? newTransform : `${transform} scale(${newScale})`);
  }

  function downloadSVG() {
    if (!svgRef.value) return;
    const svgData = new XMLSerializer().serializeToString(svgRef.value);
    const blob = new Blob([svgData], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${props.title || 'mindmap'}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function applyMarkdown() {
    emit('update:markdown', editingMarkdown.value);
    renderMarkmap(editingMarkdown.value);
  }

  // ========== Watchers ==========
  watch(
    () => props.markdown,
    async (val) => {
      editingMarkdown.value = val;
      await nextTick();
      renderMarkmap(val);
    }
  );

  const resizeObserver = new ResizeObserver(() => mm?.fit());

  onMounted(async () => {
    if (props.markdown) {
      await nextTick();
      renderMarkmap(props.markdown);
    }
    if (canvasRef.value) resizeObserver.observe(canvasRef.value);
  });

  onUnmounted(() => {
    resizeObserver.disconnect();
    mm?.destroy();
  });

  // Expose fit for parent components
  defineExpose({ fitView, renderMarkmap });
</script>

<style scoped lang="less">
  .mindmap-wrapper {
    display: flex;
    flex-direction: column;
    background: var(--color-bg-2);
    border-radius: 12px;
    border: 1px solid var(--color-border-1);
    overflow: hidden;
  }

  // 工具栏
  .mindmap-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    background: var(--color-bg-2);
    border-bottom: 1px solid var(--color-border-1);
  }

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .toolbar-icon {
    font-size: 16px;
    color: #165dff;
  }

  .toolbar-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--color-text-1);
    letter-spacing: -0.1px;
  }

  // 主体
  .mindmap-body {
    display: flex;
    flex: 1;
    min-height: 0;
    position: relative;

    &.with-editor {
      .mindmap-canvas {
        flex: 1;
      }
    }
  }

  .mindmap-canvas {
    width: 100%;
    position: relative;
    min-height: 400px;
    background: radial-gradient(circle at 50% 50%, rgba(22, 93, 255, 0.025) 0%, transparent 60%);
  }

  .markmap-svg {
    width: 100%;
    height: 100%;
    min-height: 400px;

    :deep(text) {
      font-family: -apple-system, 'SF Pro Text', 'PingFang SC', sans-serif !important;
      font-size: 13px !important;
    }

    :deep(circle) {
      cursor: pointer;
    }

    :deep(path) {
      stroke-width: 1.5px;
    }
  }

  // 加载/空态
  .mindmap-loading,
  .mindmap-empty {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    color: var(--color-text-3);
    font-size: 14px;
  }

  .empty-icon {
    font-size: 48px;
    opacity: 0.25;
  }

  .empty-sub {
    font-size: 12px;
    opacity: 0.6;
  }

  // Markdown 编辑器
  .markdown-editor {
    width: 280px;
    flex-shrink: 0;
    border-left: 1px solid var(--color-border-1);
    display: flex;
    flex-direction: column;
    background: var(--color-fill-1);
  }

  .editor-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
    color: var(--color-text-2);
    border-bottom: 1px solid var(--color-border-1);
    background: var(--color-bg-2);
  }

  .editor-textarea {
    flex: 1;
    padding: 8px;
    border: none;
    border-radius: 0;
    font-family: ui-monospace, 'SF Mono', Menlo, monospace;
    font-size: 12px;
    resize: none;

    :deep(.arco-textarea) {
      font-family: inherit;
      background: transparent;
      border: none !important;
      min-height: 100%;
    }
  }

  // 过渡
  .editor-slide-enter-active,
  .editor-slide-leave-active {
    transition: width 0.25s ease, opacity 0.2s ease;
    overflow: hidden;
  }

  .editor-slide-enter-from,
  .editor-slide-leave-to {
    width: 0 !important;
    opacity: 0;
  }
</style>
