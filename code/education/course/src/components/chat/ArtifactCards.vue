<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
  import { useRouter } from 'vue-router';
  import axios from 'axios';
  import { Message } from '@arco-design/web-vue';
  import { getToken } from '@/utils/auth';
  import { resolveTrustedApiAssetUrl } from '@/api/resource-run-url';
  import { renderMarkdown } from '@/utils/markdown';
  import KnowledgeGraphViewer, {
    type KnowledgeGraphJson,
  } from './KnowledgeGraphViewer.vue';
  import MermaidDiagramViewer from './MermaidDiagramViewer.vue';
  import { artifactSummary, markdownToPlainText } from './artifactPresentation';

  const props = defineProps<{
    artifacts: Array<Record<string, any>>;
    packageId?: string;
  }>();
  const router = useRouter();

  interface ArtifactGroup {
    key: string;
    primary: Record<string, any>;
    downloads: Record<string, any>[];
  }

  const selected = ref<ArtifactGroup | null>(null);
  const previewPanel = ref<HTMLElement | null>(null);
  let previouslyFocused: HTMLElement | null = null;

  const labelMap: Record<string, string> = {
    lecture_markdown: '讲义',
    lecture_docx: '讲义',
    lecture_pdf: '讲义',
    lecture_note: '讲义',
    practice_markdown: '练习题',
    practice_docx: '练习题',
    practice_pdf: '练习题',
    quiz: '练习题',
    question: '练习题',
    knowledge_graph: '知识图谱',
    mind_map: '思维导图',
    reading_list: '拓展阅读',
    reading: '拓展阅读',
    case_project: '代码案例',
    code_case: '代码案例',
    video_script: '视频脚本',
    video: '讲解视频',
    ppt: 'PPT 课件',
    image: '教学图片',
    diagram: '结构图表',
  };

  function family(item: Record<string, any>) {
    const kind = String(item.kind || '');
    if (kind.startsWith('lecture_')) return 'lecture';
    if (kind.startsWith('practice_') || ['quiz', 'question'].includes(kind)) return 'practice';
    return String(item.file_name || item.title || kind || 'resource');
  }

  function formatRank(item: Record<string, any>) {
    const name = String(item.file_name || '').toLowerCase();
    if (name.endsWith('.docx')) return 0;
    if (name.endsWith('.pdf')) return 1;
    if (name.endsWith('.md')) return 2;
    return 3;
  }

  function formatLabel(item: Record<string, any>) {
    if (String(item.kind || '') === 'image') return '图片';
    if (String(item.kind || '') === 'video') return 'MP4';
    if (String(item.kind || '') === 'ppt') return 'PPTX';
    if (isQuiz(item)) return '在线答题';
    if (String(item.kind || item.resource_type || '') === 'knowledge_graph') {
      return '交互式图谱';
    }
    const name = String(item.file_name || '').toLowerCase();
    if (name.endsWith('.docx')) return 'Word';
    if (name.endsWith('.pdf')) return 'PDF';
    if (name.endsWith('.md')) return 'Markdown';
    return item.download_url ? '文件' : '在线查看';
  }

  const artifactGroups = computed<ArtifactGroup[]>(() => {
    const groups = new Map<string, Record<string, any>[]>();
    props.artifacts.forEach((item) => {
      const key = family(item);
      groups.set(key, [...(groups.get(key) || []), item]);
    });
    return Array.from(groups.entries()).map(([key, items]) => {
      const downloads = [...items].sort((a, b) => formatRank(a) - formatRank(b));
      const primary =
        items.find((item) => String(item.file_name || '').endsWith('.md')) || items[0];
      return { key, primary, downloads };
    });
  });

  const selectedArtifact = computed(() => selected.value?.primary || null);
  const selectedGraph = computed<KnowledgeGraphJson | null>(() => {
    const graph = selectedArtifact.value?.graph_json;
    if (!graph || !Array.isArray(graph.nodes) || !Array.isArray(graph.edges)) return null;
    return graph as KnowledgeGraphJson;
  });
  const selectedMermaidCode = computed(() => String(selectedArtifact.value?.mermaid_code || '').trim());
  const selectedDiagramDescription = computed(() =>
    String(selectedArtifact.value?.preview || '')
      .replace(/```mermaid\s*[\s\S]*?```/gi, '')
      .trim()
  );
  const selectedLabel = computed(() => {
    const item = selectedArtifact.value;
    return item ? labelMap[item.kind] || item.kind || '资源' : '';
  });

  function displayTitle(item: Record<string, any>) {
    return markdownToPlainText(item.title || item.file_name || '生成资源');
  }

  function isQuiz(item: Record<string, any>) {
    return ['quiz', 'question'].includes(String(item.kind || item.resource_type || ''));
  }

  async function openArtifact(group: ArtifactGroup, trigger: HTMLElement | null) {
    const artifact = group.primary;
    if (isQuiz(artifact)) {
      const resourceId = String(artifact.resource_id || '').trim();
      if (!resourceId) {
        Message.error('练习资源信息不完整，暂时无法进入答题');
        return;
      }
      await router.push({ name: 'QuizPage', params: { resourceId } });
      return;
    }
    previouslyFocused = trigger || (document.activeElement as HTMLElement | null);
    selected.value = group;
  }

  function closePreview() {
    selected.value = null;
  }

  function previewFocusableElements() {
    const panel = previewPanel.value;
    if (!panel) return [];
    return Array.from(
      panel.querySelectorAll<HTMLElement>(
        'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter((element) => !element.hasAttribute('hidden'));
  }

  function handlePreviewKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.preventDefault();
      closePreview();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = previewFocusableElements();
    if (!focusable.length) {
      event.preventDefault();
      previewPanel.value?.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  async function downloadArtifact(item: Record<string, any>) {
    const url = String(item.download_url || '');
    if (!url) return;
    try {
      const token = getToken();
      const trustedUrl = resolveTrustedApiAssetUrl(
        url,
        window.location.origin,
        axios.defaults.baseURL || import.meta.env.VITE_API_BASE_URL
      );
      const response = await axios.get(trustedUrl, {
        responseType: 'blob',
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      const blobUrl = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = String(item.file_name || item.title || '学习资源');
      link.click();
      URL.revokeObjectURL(blobUrl);
    } catch {
      Message.error('资源下载失败，请稍后重试');
    }
  }

  watch(selected, async (group) => {
    if (group) {
      await nextTick();
      const firstFocusable = previewFocusableElements()[0];
      if (firstFocusable) {
        firstFocusable.focus();
      } else {
        previewPanel.value?.focus();
      }
      return;
    }
    const focusTarget = previouslyFocused;
    previouslyFocused = null;
    await nextTick();
    focusTarget?.focus();
  });

  onBeforeUnmount(() => {
    previouslyFocused?.focus();
  });
</script>

<template>
  <section v-if="artifacts.length" class="artifact-cards">
    <header>
      <span>学习资源</span>
      <strong>{{ artifacts.length }} 项</strong>
    </header>
    <div class="artifact-cards__grid">
      <button
        v-for="group in artifactGroups"
        :key="group.key"
        type="button"
        class="artifact-card"
        @click="openArtifact(group, $event.currentTarget as HTMLElement)"
      >
        <span>{{ labelMap[group.primary.kind] || group.primary.kind || '资源' }}</span>
        <strong>{{ displayTitle(group.primary) }}</strong>
        <p>{{ artifactSummary(group.primary.preview) }}</p>
        <small>{{ group.downloads.map(formatLabel).join(' · ') }}</small>
      </button>
    </div>

    <Teleport to="body">
      <Transition name="artifact-preview">
        <div
          v-if="selected"
          class="artifact-preview"
          role="dialog"
          aria-modal="true"
          aria-labelledby="artifact-preview-title"
          @keydown="handlePreviewKeydown"
        >
          <button
            class="artifact-preview__backdrop"
            type="button"
            aria-label="关闭资源预览"
            @click="closePreview"
          />
          <article ref="previewPanel" class="artifact-preview__panel" tabindex="-1">
            <header>
              <span>{{ selectedLabel }}</span>
              <h2 id="artifact-preview-title">
                {{ displayTitle(selectedArtifact || {}) }}
              </h2>
              <small>内容摘要预览</small>
            </header>
            <KnowledgeGraphViewer
              v-if="selectedGraph"
              class="artifact-preview__graph"
              :graph-json="selectedGraph"
            />
            <div v-else-if="selectedMermaidCode" class="artifact-preview__diagram">
              <MermaidDiagramViewer :code="selectedMermaidCode" />
              <div
                class="artifact-preview__content markdown-body"
                v-html="renderMarkdown(selectedDiagramDescription)"
              />
            </div>
            <div
              v-else-if="selectedArtifact?.image_url"
              class="artifact-preview__image-wrap"
            >
              <img
                class="artifact-preview__image"
                :src="selectedArtifact.image_url"
                :alt="displayTitle(selectedArtifact || {})"
              />
              <div
                class="artifact-preview__content markdown-body"
                v-html="renderMarkdown(selectedArtifact?.preview || '')"
              />
            </div>
            <div
              v-else
              class="artifact-preview__content markdown-body"
              v-html="renderMarkdown(selectedArtifact?.preview || '暂无可用内容摘要，可下载查看完整文件。')"
            />
            <footer>
              <button type="button" @click="closePreview">关闭</button>
              <button
                v-for="item in selected.downloads.filter((entry) => entry.download_url)"
                :key="item.file_name"
                type="button"
                :class="{ primary: ['Word', 'PDF'].includes(formatLabel(item)) }"
                @click="downloadArtifact(item)"
              >
                下载 {{ formatLabel(item) }}
              </button>
            </footer>
          </article>
        </div>
      </Transition>
    </Teleport>
  </section>
</template>

<style scoped lang="scss">
  .artifact-cards {
    margin-top: 14px;

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: #667085;
      font-size: 13px;

      strong {
        color: #4f46e5;
        font-weight: 700;
      }
    }
  }

  .artifact-cards__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-top: 8px;
  }

  .artifact-card {
    min-height: 96px;
    width: 100%;
    padding: 12px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 16px;
    background: #fff;
    text-align: left;
    text-decoration: none;
    cursor: pointer;
    transition: box-shadow 0.18s ease, transform 0.18s ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
    }

    span {
      color: #6366f1;
      font-size: 12px;
      font-weight: 700;
    }

    strong {
      display: block;
      margin-top: 5px;
      color: #101828;
      font-size: 14px;
    }

    p {
      display: -webkit-box;
      margin: 6px 0 0;
      overflow: hidden;
      color: #667085;
      font-size: 12px;
      line-height: 1.5;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }

    > small {
      display: block;
      margin-top: 8px;
      color: #98a2b3;
      font-size: 11px;
    }
  }

  .artifact-preview__image-wrap {
    display: grid;
    gap: 14px;
  }

  .artifact-preview__image {
    width: 100%;
    max-height: 58vh;
    object-fit: contain;
    border-radius: 18px;
    background: #f8fafc;
    border: 1px solid rgba(15, 23, 42, 0.08);
  }

  .artifact-preview {
    position: fixed;
    inset: 0;
    z-index: 3000;
    display: grid;
    padding: 32px;
    place-items: center;
  }

  .artifact-preview__backdrop {
    position: absolute;
    inset: 0;
    border: 0;
    background: rgba(15, 23, 42, 0.22);
    backdrop-filter: blur(2px);
  }

  .artifact-preview__panel {
    position: relative;
    width: min(620px, calc(100vw - 40px));
    max-height: min(82vh, 760px);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid rgba(15, 23, 42, 0.1);
    border-radius: 20px;
    background: #fff;
    box-shadow: 0 28px 80px rgba(15, 23, 42, 0.2);

    header,
    footer {
      padding: 18px 20px;
    }

    header {
      border-bottom: 1px solid rgba(15, 23, 42, 0.08);
    }

    header span,
    header h2,
    header small {
      display: block;
    }

    header span {
      color: #4f46e5;
      font-size: 12px;
      font-weight: 800;
    }

    header h2 {
      margin-top: 5px;
      margin-bottom: 0;
      color: #101828;
      font-size: 18px;
      font-weight: 700;
      line-height: 1.45;
    }

    header small {
      margin-top: 4px;
      color: #667085;
      font-size: 12px;
    }

    footer {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 10px;
      border-top: 1px solid rgba(15, 23, 42, 0.08);
    }

    footer button,
    footer a {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 74px;
      height: 36px;
      border: 1px solid rgba(15, 23, 42, 0.1);
      border-radius: 999px;
      color: #344054;
      background: #fff;
      text-decoration: none;
      cursor: pointer;
    }

    footer .primary {
      border-color: transparent;
      color: #fff;
      background: #4f46e5;
    }
  }

  .artifact-preview__content {
    min-height: 0;
    flex: 1;
    overflow: auto;
    padding: 18px 20px;
    color: #344054;
    font-size: 14px;
    line-height: 1.72;
    white-space: normal;
    overflow-wrap: anywhere;
    scrollbar-gutter: stable;
  }

  .artifact-preview__graph {
    min-height: 0;
    flex: 1;
    margin: 18px 20px;
  }

  .artifact-preview__graph :deep(.knowledge-graph-viewer__viewport) {
    height: min(54vh, 500px);
    min-height: 340px;
  }

  .artifact-preview__content :deep(h1:first-of-type) {
    display: none;
  }

  .artifact-preview__content :deep(h1),
  .artifact-preview__content :deep(h2),
  .artifact-preview__content :deep(h3),
  .artifact-preview__content :deep(h4) {
    color: #1d2939;
    font-weight: 700;
    line-height: 1.4;
  }

  .artifact-preview__content :deep(h1) {
    margin: 0 0 14px;
    font-size: 21px;
  }

  .artifact-preview__content :deep(h2) {
    margin: 22px 0 10px;
    font-size: 17px;
  }

  .artifact-preview__content :deep(h3),
  .artifact-preview__content :deep(h4) {
    margin: 18px 0 8px;
    font-size: 15px;
  }

  .artifact-preview__content :deep(p) {
    margin: 0 0 12px;
  }

  .artifact-preview__content :deep(ul),
  .artifact-preview__content :deep(ol) {
    margin: 8px 0 14px;
    padding-left: 1.6em;
  }

  .artifact-preview__content :deep(li) {
    margin: 5px 0;
  }

  .artifact-preview__content :deep(blockquote) {
    margin: 14px 0;
    padding: 10px 14px;
    border-left: 3px solid #818cf8;
    border-radius: 0 10px 10px 0;
    background: #f8f9ff;
  }

  .artifact-preview__content :deep(table) {
    width: 100%;
    margin: 14px 0;
    border-collapse: collapse;
    font-size: 13px;
  }

  .artifact-preview__content :deep(th),
  .artifact-preview__content :deep(td) {
    padding: 8px 10px;
    border: 1px solid #e4e7ec;
    text-align: left;
    vertical-align: top;
  }

  .artifact-preview__content :deep(th) {
    background: #f8fafc;
    color: #344054;
    font-weight: 700;
  }

  .artifact-preview__content :deep(pre) {
    max-width: 100%;
    overflow-x: auto;
  }

  .artifact-preview-enter-active,
  .artifact-preview-leave-active {
    transition: opacity 160ms ease;
  }

  .artifact-preview-enter-from,
  .artifact-preview-leave-to {
    opacity: 0;
  }

  @media (max-width: 760px) {
    .artifact-cards__grid {
      grid-template-columns: 1fr;
    }

    .artifact-preview {
      padding: 12px;
      align-items: end;
    }

    .artifact-preview__panel {
      width: 100%;
      max-height: 88vh;
      border-radius: 18px;
    }

    .artifact-preview__panel header,
    .artifact-preview__panel footer,
    .artifact-preview__content {
      padding-right: 16px;
      padding-left: 16px;
    }
  }
</style>
