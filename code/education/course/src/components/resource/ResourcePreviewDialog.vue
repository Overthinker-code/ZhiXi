<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
  import { useRouter } from 'vue-router';
  import mermaid from 'mermaid';
  import { BookOpen, Download, ExternalLink, FileText, LoaderCircle, PlayCircle, Video, X } from 'lucide-vue-next';
  import { previewResource, type ResourceRecord } from '@/api/resources';
  import { getQuiz, type QuizResource } from '@/api/quiz';
  import KnowledgeGraphViewer, { type KnowledgeGraphJson } from '@/components/chat/KnowledgeGraphViewer.vue';
  import { cachePreviewBlob, getCachedPreviewBlob } from './previewBlobCache';
  import {
    sourceActionLabel,
    sourceCategory,
    sourceReferenceFrom,
  } from './sourceReference';
  import useUserStore from '@/store/modules/user';

  const props = defineProps<{
    resource: ResourceRecord | null;
  }>();
  const emit = defineEmits<{
    close: [];
    download: [resource: ResourceRecord];
  }>();

  const router = useRouter();
  const userStore = useUserStore();
  const panel = ref<HTMLElement | null>(null);
  const previewFrame = ref<HTMLIFrameElement | null>(null);
  const objectUrl = ref('');
  const previewHtml = ref('');
  const mermaidSvgUrl = ref('');
  const state = ref<'loading' | 'ready' | 'error'>('loading');
  const mode = ref<'pdf' | 'image' | 'document' | 'video' | 'audio' | 'mermaid' | 'quiz' | 'graph' | 'external'>('document');
  const errorMessage = ref('');
  const quiz = ref<QuizResource | null>(null);
  const mermaidSource = ref('');
  const mermaidError = ref('');
  const showThumbnail = ref(true);
  let previouslyFocused: HTMLElement | null = null;
  let requestVersion = 0;
  let previousBodyOverflow = '';
  let iframeWindow: Window | null = null;
  let windowKeyListenerActive = false;

  const title = computed(() => props.resource?.title || '资料预览');
  const fileName = computed(() => props.resource?.file_name || title.value);
  const isQuiz = computed(() => ['question', 'quiz'].includes(props.resource?.type || ''));
  const isGraph = computed(() => props.resource?.type === 'knowledge_graph');
  const isExternal = computed(() => Boolean(props.resource?.url));
  const isMermaid = computed(() => props.resource?.file_name.toLowerCase().endsWith('.mmd'));
  const sourceReference = computed(() => sourceReferenceFrom(props.resource, {
    provider: props.resource?.source,
    url: props.resource?.url,
    summary: props.resource?.knowledge_point
      ? `与“${props.resource.knowledge_point}”相关的学习参考。`
      : props.resource?.subject ? `与${props.resource.subject}相关的学习参考。` : '',
  }));
  const sourceSummary = computed(() => sourceReference.value.summary || '这是一项已加入资料库的开放学习参考。');
  const sourceCategoryLabel = computed(() => sourceCategory(sourceReference.value.kind));
  const sourceAction = computed(() => sourceActionLabel(sourceReference.value.kind));
  const sourceIcon = computed(() => {
    if (sourceReference.value.kind === 'video') return Video;
    if (sourceReference.value.kind === 'paper') return FileText;
    return BookOpen;
  });
  const graphJson = computed<KnowledgeGraphJson | null>(() => {
    const content = props.resource?.content;
    if (!content || !Array.isArray(content.nodes) || !Array.isArray(content.edges)) return null;
    if (!content.nodes.every((node) => node && typeof node.id === 'string' && typeof node.name === 'string')) return null;
    if (!content.edges.every((edge) => edge && typeof edge.source === 'string' && typeof edge.target === 'string')) return null;
    return content as KnowledgeGraphJson;
  });
  const canDownload = computed(() => Boolean(
    props.resource?.file_name && !isQuiz.value && !isGraph.value && !isExternal.value
      && !['quiz', 'graph', 'external'].includes(mode.value)
  ));

  function revokePreviewUrls() {
    if (objectUrl.value) URL.revokeObjectURL(objectUrl.value);
    objectUrl.value = '';
    previewHtml.value = '';
    if (mermaidSvgUrl.value) URL.revokeObjectURL(mermaidSvgUrl.value);
    mermaidSvgUrl.value = '';
  }

  function startPractice() {
    if (!props.resource) return;
    void router.push({ name: 'QuizPage', params: { resourceId: props.resource.id } });
    close();
  }

  function sourceFromPreviewHtml(html: string) {
    const document = new DOMParser().parseFromString(html, 'text/html');
    return document.querySelector('pre')?.textContent || html;
  }

  async function previewErrorDetail(error: unknown) {
    const data = (error as { response?: { data?: unknown } })?.response?.data;
    if (data instanceof Blob && data.size <= 16 * 1024) {
      try {
        const parsed = JSON.parse((await data.text()).slice(0, 4096)) as { detail?: unknown };
        if (typeof parsed.detail === 'string' && parsed.detail.trim()) return parsed.detail.trim().slice(0, 320);
      } catch {
        // Do not surface a proxy page or raw server response in the dialog.
      }
    }
    const detail = (data as { detail?: unknown } | undefined)?.detail;
    return typeof detail === 'string' && detail.trim()
      ? detail.trim().slice(0, 320)
      : '预览准备失败，请下载原文件后查看。';
  }

  function normalizeMindmapRoots(source: string) {
    const lines = source.split(/\r?\n/);
    const mindmapLine = lines.findIndex((line) => /^\s*mindmap(?:\s|$)/.test(line));
    if (mindmapLine < 0) return source;

    let rootIndent: number | undefined;
    let foundRoot = false;
    return lines.map((line, index) => {
      if (index <= mindmapLine) return line;
      const node = /^( *)(\S.*)$/.exec(line);
      if (!node) return line;

      const indent = node[1].length;
      if (!foundRoot && /^root(?:\s|[([{]|$)/.test(node[2])) {
        rootIndent = indent;
        foundRoot = true;
        return line;
      }
      // Mermaid mindmaps permit exactly one root.  Older generated packages
      // appended a same-level “资源包索引” section after the tree; make each
      // such sibling a branch of the declared root while preserving its
      // descendants' relative indentation.
      if (foundRoot && rootIndent !== undefined && indent === rootIndent) {
        return `${' '.repeat(Math.max(rootIndent, 2))}${line}`;
      }
      return line;
    }).join('\n');
  }

  async function renderMermaid(source: string, version: number) {
    mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'base' });
    try {
      const result = await mermaid.render(
        `resource-mermaid-${Date.now()}-${version}`,
        normalizeMindmapRoots(source)
      );
      if (version === requestVersion) {
        if (mermaidSvgUrl.value) URL.revokeObjectURL(mermaidSvgUrl.value);
        mermaidSvgUrl.value = URL.createObjectURL(
          new Blob([result.svg], { type: 'image/svg+xml' })
        );
      }
    } catch {
      if (version === requestVersion) mermaidError.value = '图形语法无法渲染，已保留原始文本供查看。';
    }
  }

  function focusableElements() {
    if (!panel.value) return [];
    return Array.from(
      panel.value.querySelectorAll<HTMLElement>(
        'iframe, button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter((element) => !element.hasAttribute('hidden'));
  }

  function close() {
    emit('close');
  }

  function onWindowKeydown(event: KeyboardEvent) {
    if (event.key !== 'Escape') return;
    event.preventDefault();
    event.stopPropagation();
    close();
  }

  function addEscapeListeners() {
    if (!windowKeyListenerActive) {
      window.addEventListener('keydown', onWindowKeydown, true);
      windowKeyListenerActive = true;
    }
  }

  function removeEscapeListeners() {
    if (windowKeyListenerActive) {
      window.removeEventListener('keydown', onWindowKeydown, true);
      windowKeyListenerActive = false;
    }
    iframeWindow?.removeEventListener('keydown', onWindowKeydown, true);
    iframeWindow = null;
  }

  function bindFrameEscape() {
    iframeWindow?.removeEventListener('keydown', onWindowKeydown, true);
    try {
      iframeWindow = previewFrame.value?.contentWindow || null;
      iframeWindow?.addEventListener('keydown', onWindowKeydown, true);
    } catch {
      iframeWindow = null;
    }
  }

  function onKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = focusableElements();
    if (!focusable.length) {
      event.preventDefault();
      panel.value?.focus();
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

  async function loadPreview(resource: ResourceRecord) {
    const currentVersion = ++requestVersion;
    revokePreviewUrls();
    state.value = 'loading';
    errorMessage.value = '';
    showThumbnail.value = true;
    quiz.value = null;
    mermaidSource.value = '';
    mermaidError.value = '';
    if (isQuiz.value) {
      mode.value = 'quiz';
      try {
        const response = await getQuiz(resource.id);
        if (currentVersion === requestVersion) quiz.value = response.data;
      } catch {
        if (currentVersion === requestVersion) errorMessage.value = '练习题暂时无法载入，请稍后重试或直接开始练习。';
      }
      if (currentVersion === requestVersion) state.value = 'ready';
      return;
    }
    if (isGraph.value) {
      mode.value = 'graph';
      state.value = 'ready';
      return;
    }
    if (isExternal.value) {
      mode.value = 'external';
      state.value = 'ready';
      return;
    }
    try {
      const accountId = userStore.accountId;
      const cachedBlob = getCachedPreviewBlob(accountId, resource);
      let blob: Blob;
      if (cachedBlob) {
        blob = cachedBlob;
      } else {
        const response = await previewResource(resource.id);
        const responseBlob = response.data;
        if (!responseBlob) throw new Error('预览响应缺少文件内容');
        // Do not let an in-flight request from a logged-out account repopulate
        // a cache after another account has become active.
        if (accountId !== userStore.accountId) return;
        cachePreviewBlob(accountId, resource, responseBlob);
        blob = responseBlob;
      }
      if (currentVersion !== requestVersion) return;
      const contentType = String(blob.type || resource.content_type || '').toLowerCase();
      mode.value = isMermaid.value
        ? 'mermaid'
        : contentType.includes('pdf')
        ? 'pdf'
        : contentType.startsWith('image/')
        ? 'image'
        : contentType.startsWith('video/')
        ? 'video'
        : contentType.startsWith('audio/')
        ? 'audio'
        : 'document';
      if (mode.value === 'mermaid') {
        mermaidSource.value = sourceFromPreviewHtml(await blob.text());
        if (currentVersion !== requestVersion) return;
        void renderMermaid(mermaidSource.value, currentVersion);
      } else if (mode.value === 'document') {
        // Office and text previews are server-converted, escaped HTML with an
        // inert CSP.  srcdoc avoids the cross-browser blank iframe behaviour
        // seen when that HTML is first wrapped in a blob URL.  The iframe
        // remains sandboxed and grants no script permission.
        previewHtml.value = await blob.text();
        if (currentVersion !== requestVersion) return;
      } else {
        objectUrl.value = URL.createObjectURL(blob);
      }
      state.value = 'ready';
    } catch (error) {
      if (currentVersion === requestVersion) {
        errorMessage.value = await previewErrorDetail(error);
        state.value = 'error';
      }
    }
  }

  watch(
    () => props.resource,
    async (resource) => {
      requestVersion += 1;
      revokePreviewUrls();
      if (!resource) {
        removeEscapeListeners();
        document.body.style.overflow = previousBodyOverflow;
        const focusTarget = previouslyFocused;
        previouslyFocused = null;
        await nextTick();
        focusTarget?.focus();
        return;
      }
      previouslyFocused = document.activeElement as HTMLElement | null;
      previousBodyOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      addEscapeListeners();
      await nextTick();
      const firstFocusable = focusableElements()[0];
      if (firstFocusable) firstFocusable.focus();
      else panel.value?.focus();
      void loadPreview(resource);
    }
  );

  onBeforeUnmount(() => {
    requestVersion += 1;
    revokePreviewUrls();
    removeEscapeListeners();
    document.body.style.overflow = previousBodyOverflow;
  });
</script>

<template>
  <Teleport to="body">
    <Transition name="resource-preview">
      <section
        v-if="resource"
        class="resource-preview"
        role="dialog"
        aria-modal="true"
        aria-labelledby="resource-preview-title"
        @keydown="onKeydown"
      >
        <button
          type="button"
          class="resource-preview__backdrop"
          aria-label="关闭资料预览"
          @click="close"
        />
        <article ref="panel" class="resource-preview__panel" tabindex="-1">
          <header>
            <div>
              <span>资料预览</span>
              <h2 id="resource-preview-title">{{ title }}</h2>
              <small>{{ fileName }}</small>
            </div>
            <button
              type="button"
              class="icon-button"
              aria-label="关闭资料预览"
              @click="close"
              ><X :size="19"
            /></button>
          </header>
          <div
            class="resource-preview__canvas"
            :class="`is-${mode}`"
            aria-live="polite"
          >
            <div v-if="state === 'loading'" class="resource-preview__state">
              <LoaderCircle :size="22" class="spinning" />
              <strong>正在准备{{ title }}</strong><span>{{ fileName }} · {{ resource?.type || '学习资料' }}</span>
            </div>
            <div
              v-else-if="state === 'error'"
              class="resource-preview__state is-error"
            >
              <strong>暂时无法在线预览此资料</strong>
              <span>{{ errorMessage || '你仍可下载原文件后查看完整内容。' }}</span>
            </div>
            <div v-else-if="mode === 'quiz'" class="resource-preview__content">
              <p v-if="errorMessage" class="inline-error">{{ errorMessage }}</p>
              <template v-else-if="quiz">
                <strong>共 {{ quiz.questions.length }} 题 · 预览前 {{ Math.min(3, quiz.questions.length) }} 题</strong>
                <article v-for="(question, index) in quiz.questions.slice(0, 3)" :key="question.id"><span>第 {{ index + 1 }} 题</span><p>{{ question.content }}</p><ul><li v-for="option in question.options" :key="option.key">{{ option.key }}. {{ option.text }}</li></ul></article>
              </template>
              <button type="button" class="inline-primary" @click="startPractice"><PlayCircle :size="15" />开始练习</button>
            </div>
            <div v-else-if="mode === 'graph'" class="resource-preview__content">
              <KnowledgeGraphViewer v-if="graphJson" :graph-json="graphJson" />
              <div v-else class="resource-preview__state is-error"><strong>知识图谱数据暂不可用</strong><span>该资源没有有效的图谱节点和关系。</span></div>
            </div>
            <div v-else-if="mode === 'external'" class="resource-preview__content">
              <section class="source-card">
                <img v-if="sourceReference.thumbnailUrl && showThumbnail" :src="sourceReference.thumbnailUrl" :alt="`${title} 封面`" @error="showThumbnail = false" />
                <div class="source-card__copy">
                  <span class="source-kind"><component :is="sourceIcon" :size="14" />{{ sourceCategoryLabel }}</span>
                  <p>{{ sourceSummary }}</p>
                  <dl>
                    <div><dt>{{ sourceReference.verifiedAt ? '已核验来源' : '来源提供方' }}</dt><dd>{{ sourceReference.provider }}</dd></div>
                    <div v-if="sourceReference.authors || sourceReference.year"><dt>作者 / 年份</dt><dd>{{ [sourceReference.authors, sourceReference.year].filter(Boolean).join(' · ') }}</dd></div>
                    <div v-if="sourceReference.language"><dt>语言</dt><dd>{{ sourceReference.language }}</dd></div>
                    <div v-if="sourceReference.accessLabel"><dt>访问方式</dt><dd>{{ sourceReference.accessLabel }}</dd></div>
                    <div><dt>来源域名</dt><dd>{{ sourceReference.domain || '链接暂不可用' }}</dd></div>
                    <div v-if="sourceReference.verifiedAt"><dt>核验信息</dt><dd>{{ sourceReference.verifiedAt }}</dd></div>
                  </dl>
                </div>
              </section>
              <a v-if="sourceReference.canonicalUrl" class="inline-primary" :href="sourceReference.canonicalUrl" target="_blank" rel="noopener noreferrer" :aria-label="`在新窗口${sourceAction}${title}`"><ExternalLink :size="15" />{{ sourceAction }}</a>
              <p v-else class="inline-error">该来源链接暂不可用。</p>
            </div>
            <div v-else-if="mode === 'mermaid'" class="resource-preview__mermaid">
              <img v-if="mermaidSvgUrl" :src="mermaidSvgUrl" :alt="`${title} 图形`" />
              <p v-if="mermaidError" class="inline-error">{{ mermaidError }}</p>
              <pre v-if="mermaidError || !mermaidSvgUrl">{{ mermaidSource }}</pre>
            </div>
            <iframe
              v-else-if="mode === 'document'"
              ref="previewFrame"
              :srcdoc="previewHtml"
              :title="`${title}预览`"
              tabindex="0"
              sandbox="allow-same-origin"
              @load="bindFrameEscape"
            />
            <iframe
              v-else-if="mode === 'pdf'"
              ref="previewFrame"
              :src="objectUrl"
              :title="`${title}预览`"
              tabindex="0"
              @load="bindFrameEscape"
            />
            <video v-else-if="mode === 'video'" :src="objectUrl" controls playsinline :title="title" />
            <audio v-else-if="mode === 'audio'" :src="objectUrl" controls :title="title" />
            <img v-else :src="objectUrl" :alt="title" />
          </div>
          <footer>
            <button type="button" @click="close">关闭</button>
            <button
              v-if="canDownload"
              type="button"
              class="primary"
              @click="emit('download', resource)"
              ><Download :size="15" /> 下载</button
            >
          </footer>
        </article>
      </section>
    </Transition>
  </Teleport>
</template>

<style scoped lang="scss">
  .resource-preview {
    position: fixed;
    inset: 0;
    z-index: 3200;
    display: grid;
    place-items: center;
    padding: 24px;
  }
  .resource-preview__backdrop {
    position: absolute;
    inset: 0;
    border: 0;
    background: rgba(15, 23, 42, 0.34);
    backdrop-filter: blur(2px);
  }
  .resource-preview__panel {
    position: relative;
    display: flex;
    width: min(1180px, calc(100vw - 32px));
    height: min(88vh, 940px);
    flex-direction: column;
    overflow: hidden;
    border: 1px solid rgba(15, 23, 42, 0.12);
    border-radius: 18px;
    background: #fff;
    box-shadow: 0 28px 80px rgba(15, 23, 42, 0.28);
  }
  header,
  footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 15px 20px;
    background: #fff;
  }
  header {
    border-bottom: 1px solid #eaecf0;
  }
  footer {
    border-top: 1px solid #eaecf0;
    justify-content: flex-end;
  }
  header span,
  header small {
    display: block;
    color: #667085;
    font-size: 12px;
  }
  header span {
    color: #4f46e5;
    font-weight: 750;
  }
  h2 {
    margin: 3px 0;
    color: #101828;
    font-size: 17px;
    line-height: 1.35;
  }
  .resource-preview__canvas {
    min-height: 0;
    flex: 1;
    overflow: hidden;
    padding: 24px;
    background: #edf0f4;
    scrollbar-gutter: stable;
  }
  .resource-preview__canvas iframe {
    display: block;
    width: 100%;
    height: 100%;
    min-height: 0;
    margin: 0 auto;
    border: 0;
    background: #fff;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.12);
  }
  .resource-preview__canvas.is-pdf iframe {
    width: 100%;
    height: 100%;
    min-height: 0;
    box-shadow: none;
  }
  .resource-preview__canvas.is-image { overflow: auto; }
  .resource-preview__canvas img {
    display: block;
    max-width: 100%;
    max-height: calc(88vh - 150px);
    margin: 0 auto;
    object-fit: contain;
  }
  .resource-preview__canvas video {
    display: block;
    width: min(100%, 1080px);
    max-height: 100%;
    margin: 0 auto;
    background: #101828;
  }
  .resource-preview__canvas audio {
    display: block;
    width: min(680px, 100%);
    margin: 28vh auto;
  }
  .resource-preview__content {
    display: grid;
    gap: 12px;
    max-width: 820px;
    margin: 0 auto;
    color: #344054;
  }
  .resource-preview__content article {
    padding: 12px 14px;
    border: 1px solid #dfe3eb;
    border-radius: 10px;
    background: #fff;
  }
  .resource-preview__content article > span { color: #4f46e5; font-size: 12px; font-weight: 700; }
  .resource-preview__content p { margin: 4px 0; }
  .resource-preview__content ul { margin: 0; padding-left: 20px; color: #667085; }
  .source-card { display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px; padding: 14px; border: 1px solid #dfe3eb; border-radius: 12px; background: #fff; } .source-card:has(img) { grid-template-columns: 112px minmax(0, 1fr); } .source-card img { width: 112px; height: 142px; border-radius: 9px; object-fit: cover; background: #eaecf0; } .source-card__copy > p { margin: 7px 0 10px; color: #475467; } .source-kind { display: inline-flex; align-items: center; gap: 5px; color: #4338ca; font-size: 12px; font-weight: 700; } .source-card dl { display: grid; gap: 6px; margin: 0; font-size: 13px; } .source-card dl div { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 10px; } .source-card dt { color: #667085; } .source-card dd { min-width: 0; margin: 0; color: #1d2939; overflow-wrap: anywhere; }
  .resource-preview__mermaid { overflow: auto; min-height: 100%; padding: 20px; background: #fff; }
  .resource-preview__mermaid img { display: block; max-width: 100%; margin: 0 auto; }
  .resource-preview__mermaid pre { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; font: 13px/1.65 ui-monospace, SFMono-Regular, Menlo, monospace; }
  .inline-primary { display: inline-flex; width: fit-content; align-items: center; gap: 7px; min-height: 36px; padding: 0 14px; border: 1px solid #4f46e5; border-radius: 9px; color: #fff; background: #4f46e5; cursor: pointer; }
  .inline-primary:disabled { cursor: not-allowed; opacity: .55; }
  .inline-error { color: #b42318; }
  .source-url { overflow-wrap: anywhere; color: #667085; }
  .resource-preview__state {
    display: grid;
    min-height: 100%;
    place-content: center;
    justify-items: center;
    gap: 10px;
    color: #667085;
    text-align: center;
  }
  .resource-preview__state.is-error strong {
    color: #344054;
  }
  .resource-preview__state.is-error span {
    font-size: 14px;
  }
  button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    min-height: 36px;
    padding: 0 14px;
    border: 1px solid #d0d5dd;
    border-radius: 9px;
    color: #344054;
    background: #fff;
    cursor: pointer;
  }
  .icon-button {
    width: 36px;
    padding: 0;
  }
  .primary {
    border-color: #4f46e5;
    color: #fff;
    background: #4f46e5;
  }
  .spinning {
    animation: spin 0.8s linear infinite;
  }
  .resource-preview-enter-active,
  .resource-preview-leave-active {
    transition: opacity 0.16s ease;
  }
  .resource-preview-enter-from,
  .resource-preview-leave-to {
    opacity: 0;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  @media (max-width: 640px) {
    .resource-preview {
      padding: 10px;
    }
    .resource-preview__panel {
      width: 100%;
      height: 88vh;
    }
    .resource-preview__canvas {
      padding: 12px;
    }
    .resource-preview__canvas iframe {
      min-height: 500px;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .spinning {
      animation: none;
    }
    .resource-preview-enter-active,
    .resource-preview-leave-active {
      transition: none;
    }
  }
</style>
