<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
  import { useRouter } from 'vue-router';
  import { ExternalLink, LoaderCircle, PlayCircle, X } from 'lucide-vue-next';
  import {
    previewRecommendation,
    reportRecommendationSourceOpened,
    type RecommendationPreviewResource,
    type ResourceRecommendationItem,
  } from '@/api/resource-hub';
  import { getQuiz, type QuizResource } from '@/api/quiz';
  import type { ResourceRecord } from '@/api/resources';
  import KnowledgeGraphViewer, {
    type KnowledgeGraphJson,
  } from '@/components/chat/KnowledgeGraphViewer.vue';
  import ResourcePreviewDialog from './ResourcePreviewDialog.vue';
  import {
    isRecommendationPreviewCurrent,
    shouldPrepareRecommendation,
  } from './recommendationPreviewSession';

  const props = defineProps<{ item: ResourceRecommendationItem | null }>();
  const emit = defineEmits<{
    close: [];
    download: [resource: ResourceRecord];
    updated: [item: ResourceRecommendationItem];
  }>();

  const router = useRouter();
  const panel = ref<HTMLElement | null>(null);
  const state = ref<'loading' | 'ready' | 'error'>('loading');
  const message = ref('');
  const preparedResource = ref<ResourceRecord | null>(null);
  const quiz = ref<QuizResource | null>(null);
  const quizError = ref('');
  const quizLoading = ref(false);
  const showingFilePreview = ref(false);
  let requestVersion = 0;
  let previousBodyOverflow = '';
  let previouslyFocused: HTMLElement | null = null;

  const isPractice = computed(() => ['question', 'quiz'].includes(props.item?.type || ''));
  const isKnowledgeGraph = computed(() => props.item?.type === 'knowledge_graph');
  const safeExternalUrl = computed(() => {
    if (props.item?.origin !== 'external' || !props.item.url) return '';
    try {
      const url = new URL(props.item.url);
      return ['http:', 'https:'].includes(url.protocol) ? url.toString() : '';
    } catch {
      return '';
    }
  });
  const graphJson = computed<KnowledgeGraphJson | null>(() => {
    const content = preparedResource.value?.content;
    if (!content || !Array.isArray(content.nodes) || !Array.isArray(content.edges)) return null;
    if (!content.nodes.every((node) => node && typeof node.id === 'string' && typeof node.name === 'string')) {
      return null;
    }
    if (!content.edges.every((edge) => edge && typeof edge.source === 'string' && typeof edge.target === 'string')) {
      return null;
    }
    return content as KnowledgeGraphJson;
  });
  const canOpenFilePreview = computed(() => {
    const resource = preparedResource.value;
    if (!resource || isPractice.value || isKnowledgeGraph.value || resource.url) return false;
    const name = resource.file_name.toLowerCase();
    return ['.pdf', '.png', '.jpg', '.jpeg', '.docx', '.pptx', '.md', '.markdown', '.txt']
      .some((extension) => name.endsWith(extension));
  });

  function resourceRecord(resource: RecommendationPreviewResource): ResourceRecord {
    return {
      id: resource.id,
      title: resource.title,
      type: resource.type,
      subject: '',
      file_name: resource.file_name,
      file_size: resource.file_size,
      content_type: resource.content_type,
      content: resource.content,
      knowledge_point: resource.knowledge_point,
      difficulty: resource.difficulty,
      favorite: false,
      top: false,
      upload_time: '',
      uploader_id: '',
    };
  }

  function focusableElements() {
    if (!panel.value) return [];
    return Array.from(
      panel.value.querySelectorAll<HTMLElement>(
        'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
      )
    ).filter((element) => !element.hasAttribute('hidden'));
  }

  function close() {
    emit('close');
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

  function isCurrentPreview(version: number, recommendationId: string) {
    return isRecommendationPreviewCurrent(
      requestVersion,
      version,
      props.item?.id,
      recommendationId
    );
  }

  async function loadQuizPreview(resourceId: string, version: number, recommendationId: string) {
    quizLoading.value = true;
    quizError.value = '';
    try {
      const response = await getQuiz(resourceId);
      if (isCurrentPreview(version, recommendationId)) quiz.value = response.data;
    } catch {
      if (isCurrentPreview(version, recommendationId)) quizError.value = '练习已生成，但题目暂时无法载入；请稍后重试。';
    } finally {
      if (isCurrentPreview(version, recommendationId)) quizLoading.value = false;
    }
  }

  async function prepare(item: ResourceRecommendationItem) {
    const currentVersion = ++requestVersion;
    state.value = 'loading';
    message.value = '';
    preparedResource.value = null;
    quiz.value = null;
    quizError.value = '';
    if (item.origin === 'external') {
      state.value = 'ready';
      message.value = safeExternalUrl.value
        ? '将在新窗口打开原文，本站不会加载或代理该内容。'
        : '来源暂不可用，请换一条推荐或稍后重试。';
      return;
    }
    try {
      const response = await previewRecommendation(item.id);
      if (!isCurrentPreview(currentVersion, item.id)) return;
      emit('updated', response.data.recommendation);
      message.value = response.data.message;
      preparedResource.value = response.data.resource ? resourceRecord(response.data.resource) : null;
      if (!preparedResource.value) {
        state.value = 'error';
        message.value = '资料已生成，但暂时没有可预览内容；你可以加入资料库后查看。';
        return;
      }
      state.value = 'ready';
      if (isPractice.value) {
        await loadQuizPreview(preparedResource.value.id, currentVersion, item.id);
      } else if (canOpenFilePreview.value) {
        await nextTick();
        if (isCurrentPreview(currentVersion, item.id)) showingFilePreview.value = true;
      }
    } catch (error) {
      if (!isCurrentPreview(currentVersion, item.id)) return;
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      message.value = detail || '暂时无法准备预览，请稍后重试或重新生成推荐。';
      state.value = 'error';
    }
  }

  function startFullPractice() {
    if (!preparedResource.value) return;
    void router.push({ name: 'QuizPage', params: { resourceId: preparedResource.value.id } });
    close();
  }

  function reportSourceOpened() {
    // Do not await this: the browser must retain the user gesture and open the
    // validated link even if telemetry is unavailable.
    if (props.item?.id) void reportRecommendationSourceOpened(props.item.id).then((response) => {
      emit('updated', response.data);
    }).catch(() => undefined);
  }

  watch(
    () => props.item?.id ?? null,
    async (nextId, previousId) => {
      if (!nextId) {
        requestVersion += 1;
        showingFilePreview.value = false;
        document.body.style.overflow = previousBodyOverflow;
        const focusTarget = previouslyFocused;
        previouslyFocused = null;
        await nextTick();
        focusTarget?.focus();
        return;
      }
      if (!shouldPrepareRecommendation(previousId, nextId)) return;
      requestVersion += 1;
      showingFilePreview.value = false;
      const item = props.item;
      if (!item || item.id !== nextId) return;
      previouslyFocused = document.activeElement as HTMLElement | null;
      previousBodyOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      await nextTick();
      focusableElements()[0]?.focus();
      void prepare(item);
    }
  );

  onBeforeUnmount(() => {
    requestVersion += 1;
    document.body.style.overflow = previousBodyOverflow;
  });
</script>

<template>
  <Teleport to="body">
    <Transition name="recommendation-preview">
      <section
        v-if="item && !showingFilePreview"
        class="recommendation-preview"
        role="dialog"
        aria-modal="true"
        aria-labelledby="recommendation-preview-title"
        @keydown="onKeydown"
      >
        <button type="button" class="recommendation-preview__backdrop" aria-label="关闭推荐预览" @click="close" />
        <article ref="panel" class="recommendation-preview__panel" :class="{ 'is-graph': isKnowledgeGraph }" tabindex="-1">
          <header>
            <div><span>推荐预览</span><h2 id="recommendation-preview-title">{{ item.title }}</h2></div>
            <button type="button" class="icon-button" aria-label="关闭推荐预览" @click="close"><X :size="19" /></button>
          </header>

          <main aria-live="polite">
            <div v-if="state === 'loading'" class="preview-state"><LoaderCircle :size="22" class="spinning" />正在准备个性化资料…</div>
            <template v-else-if="item.origin === 'external'">
              <p>{{ item.preview || item.reason }}</p>
              <dl>
                <div><dt>来源名称</dt><dd>{{ item.source }}</dd></div>
                <div><dt>来源域名</dt><dd>{{ item.source_domain || '来源暂不可用' }}</dd></div>
                <div><dt>原文链接</dt><dd><a v-if="safeExternalUrl" class="url-link" :href="safeExternalUrl" target="_blank" rel="noopener noreferrer">{{ safeExternalUrl }}</a><span v-else>来源暂不可用</span></dd></div>
              </dl>
              <p class="source-note">{{ message }}</p>
              <a v-if="safeExternalUrl" class="primary-link" :href="safeExternalUrl" target="_blank" rel="noopener noreferrer" aria-label="在新窗口打开外部资料原文" @click="reportSourceOpened"><ExternalLink :size="16" />打开原文</a>
            </template>
            <template v-else-if="state === 'ready' && preparedResource && isPractice">
              <p>{{ message }}</p>
              <div v-if="quizLoading" class="preview-state compact"><LoaderCircle :size="20" class="spinning" />正在载入练习题…</div>
              <div v-else-if="quiz" class="quiz-preview">
                <strong>共 {{ quiz.questions.length }} 题 · 预览前 {{ Math.min(3, quiz.questions.length) }} 题</strong>
                <article v-for="(question, index) in quiz.questions.slice(0, 3)" :key="question.id">
                  <span>第 {{ index + 1 }} 题</span><p>{{ question.content }}</p>
                  <ul><li v-for="option in question.options" :key="option.key">{{ option.key }}. {{ option.text }}</li></ul>
                </article>
              </div>
              <div v-else class="preview-state compact is-error"><strong>题目预览暂不可用</strong><span>{{ quizError }}</span></div>
              <button type="button" class="primary-link" @click="startFullPractice"><PlayCircle :size="16" />开始完整练习</button>
            </template>
            <template v-else-if="state === 'ready' && preparedResource && isKnowledgeGraph">
              <p>{{ message }}</p>
              <KnowledgeGraphViewer v-if="graphJson" :graph-json="graphJson" />
              <div v-else class="preview-state compact is-error"><strong>知识图谱暂不可预览</strong><span>图谱数据不完整或格式无效，可重新生成后再试。</span></div>
            </template>
            <div v-else-if="state === 'ready'" class="preview-state is-error"><strong>当前资料暂不支持在线预览</strong><span>该类型没有可安全展示的内容；你可以加入资料库后下载或查看。</span></div>
            <div v-else class="preview-state is-error"><strong>预览暂未准备好</strong><span>{{ message }}</span></div>
          </main>
          <footer><button type="button" @click="close">关闭</button></footer>
        </article>
      </section>
    </Transition>
    <ResourcePreviewDialog :resource="showingFilePreview ? preparedResource : null" @close="close" @download="emit('download', $event)" />
  </Teleport>
</template>

<style scoped lang="scss">
  .recommendation-preview { position: fixed; inset: 0; z-index: 3190; display: grid; place-items: center; padding: 24px; }
  .recommendation-preview__backdrop { position: absolute; inset: 0; border: 0; background: rgba(15, 23, 42, 0.34); }
  .recommendation-preview__panel { position: relative; width: min(560px, calc(100vw - 32px)); max-height: calc(100vh - 32px); display: flex; flex-direction: column; overflow: hidden; border: 1px solid rgba(15, 23, 42, 0.12); border-radius: 18px; background: #fff; box-shadow: 0 28px 80px rgba(15, 23, 42, 0.28); }
  .recommendation-preview__panel.is-graph { width: min(920px, calc(100vw - 32px)); }
  header, footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 15px 20px; }
  header { border-bottom: 1px solid #eaecf0; } footer { justify-content: flex-end; border-top: 1px solid #eaecf0; }
  header span { color: #4f46e5; font-size: 12px; font-weight: 750; } h2 { margin: 3px 0 0; color: #101828; font-size: 17px; line-height: 1.35; }
  main { min-height: 170px; overflow: auto; padding: 20px; color: #475467; font-size: 14px; line-height: 1.7; } main > p { margin: 0 0 14px; }
  dl { display: grid; gap: 7px; margin: 0 0 16px; } dl div { display: grid; grid-template-columns: 78px minmax(0, 1fr); gap: 10px; } dt { color: #667085; } dd { min-width: 0; margin: 0; color: #1d2939; overflow-wrap: anywhere; }
  .url-link { display: block; overflow: hidden; color: #4f46e5; text-overflow: ellipsis; white-space: nowrap; } .source-note { color: #667085; font-size: 13px; }
  .preview-state { display: grid; min-height: 130px; place-content: center; justify-items: center; gap: 10px; text-align: center; } .preview-state.compact { min-height: 82px; } .preview-state.is-error strong { color: #344054; } .preview-state.is-error span { color: #667085; font-size: 13px; }
  .quiz-preview { display: grid; gap: 10px; margin-bottom: 16px; } .quiz-preview > strong { color: #344054; font-size: 13px; } .quiz-preview article { padding: 11px 13px; border: 1px solid #e4e7ec; border-radius: 10px; background: #fafbff; } .quiz-preview article > span { color: #4f46e5; font-size: 12px; font-weight: 700; } .quiz-preview p { margin: 4px 0; color: #1d2939; } .quiz-preview ul { display: grid; gap: 2px; margin: 0; padding-left: 20px; color: #667085; font-size: 13px; }
  button, .primary-link { display: inline-flex; min-height: 36px; align-items: center; justify-content: center; gap: 7px; padding: 0 14px; border: 1px solid #d0d5dd; border-radius: 9px; color: #344054; background: #fff; font: inherit; cursor: pointer; text-decoration: none; } .primary-link { border-color: #4f46e5; color: #fff; background: #4f46e5; } .icon-button { width: 36px; padding: 0; }
  .spinning { animation: spin 0.8s linear infinite; } .recommendation-preview-enter-active, .recommendation-preview-leave-active { transition: opacity 0.16s ease; } .recommendation-preview-enter-from, .recommendation-preview-leave-to { opacity: 0; } @keyframes spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .spinning { animation: none; } .recommendation-preview-enter-active, .recommendation-preview-leave-active { transition: none; } }
</style>
