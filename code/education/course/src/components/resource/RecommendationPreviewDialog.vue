<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
  import { useRouter } from 'vue-router';
  import { BookOpen, ExternalLink, FileText, LoaderCircle, PlayCircle, Video, X } from 'lucide-vue-next';
  import {
    previewRecommendation,
    type RecommendationContentPreview,
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
  import {
    sourceActionLabel,
    sourceCategory,
    sourceReferenceFrom,
    studentFacingReason,
  } from './sourceReference';

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
  const instantPreview = ref<RecommendationContentPreview | null>(null);
  const quiz = ref<QuizResource | null>(null);
  const quizError = ref('');
  const quizLoading = ref(false);
  const showingFilePreview = ref(false);
  const showThumbnail = ref(true);
  let requestVersion = 0;
  let previousBodyOverflow = '';
  let previouslyFocused: HTMLElement | null = null;

  const isPractice = computed(() => ['question', 'quiz'].includes(props.item?.type || ''));
  const isKnowledgeGraph = computed(() => props.item?.type === 'knowledge_graph');
  const sourceReference = computed(() => sourceReferenceFrom(props.item, {
    provider: props.item?.source,
    url: props.item?.url,
    domain: props.item?.source_domain,
    summary: studentFacingReason(props.item?.preview, props.item?.reason, props.item?.evidence?.[0]),
  }));
  const sourceSummary = computed(() => sourceReference.value.summary || '这是一项与当前学习主题相关的开放学习参考。');
  const sourceCategoryLabel = computed(() => sourceCategory(sourceReference.value.kind));
  const sourceAction = computed(() => sourceActionLabel(sourceReference.value.kind));
  const sourceIcon = computed(() => {
    if (sourceReference.value.kind === 'video') return Video;
    if (sourceReference.value.kind === 'paper') return FileText;
    return BookOpen;
  });
  const generatedPreviewHeading = computed(() => {
    if (isPractice.value) return '练习概览';
    if (isKnowledgeGraph.value) return '学习结构';
    if (props.item?.type === 'video') return '讲解结构';
    return '学习方案';
  });
  const generatedPreviewSummary = computed(() => studentFacingReason(
    props.item?.reason,
    props.item?.evidence?.[0],
    instantPreview.value?.reason
  ));
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
    return ['.pdf', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.docx', '.pptx', '.md', '.markdown', '.mmd', '.txt', '.mp4', '.webm', '.mp3', '.wav', '.m4a']
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
      if (isCurrentPreview(version, recommendationId)) quizError.value = '题目暂时无法载入，请稍后重试。';
    } finally {
      if (isCurrentPreview(version, recommendationId)) quizLoading.value = false;
    }
  }

  async function prepare(item: ResourceRecommendationItem) {
    const currentVersion = ++requestVersion;
    state.value = 'loading';
    message.value = '';
    preparedResource.value = null;
    instantPreview.value = null;
    showThumbnail.value = true;
    quiz.value = null;
    quizError.value = '';
    if (item.origin === 'external') {
      state.value = 'ready';
      message.value = '';
      return;
    }
    try {
      const response = await previewRecommendation(item.id);
      if (!isCurrentPreview(currentVersion, item.id)) return;
      emit('updated', response.data.recommendation);
      message.value = response.data.message;
      preparedResource.value = response.data.resource ? resourceRecord(response.data.resource) : null;
      instantPreview.value = response.data.content_preview || null;
      if (!preparedResource.value) {
        state.value = instantPreview.value ? 'ready' : 'error';
        if (!instantPreview.value) message.value = '暂时无法查看这项内容，请稍后再试。';
        return;
      }
      state.value = 'ready';
      if (isPractice.value) {
        await loadQuizPreview(preparedResource.value.id, currentVersion, item.id);
      } else if (canOpenFilePreview.value) {
        await nextTick();
        if (isCurrentPreview(currentVersion, item.id)) showingFilePreview.value = true;
      }
    } catch {
      if (!isCurrentPreview(currentVersion, item.id)) return;
      message.value = '暂时无法查看这项内容，请稍后再试。';
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
            <div v-if="state === 'loading'" class="preview-state"><LoaderCircle :size="22" class="spinning" /><strong>正在准备{{ item.title }}</strong><span>{{ item.subject || '通用学习' }}<template v-if="item.knowledge_point"> · {{ item.knowledge_point }}</template></span></div>
            <template v-else-if="item.origin === 'external'">
              <section class="source-card">
                <img v-if="sourceReference.thumbnailUrl && showThumbnail" :src="sourceReference.thumbnailUrl" :alt="`${item.title} 封面`" @error="showThumbnail = false" />
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
              <a v-if="sourceReference.canonicalUrl" class="primary-link" :href="sourceReference.canonicalUrl" target="_blank" rel="noopener noreferrer" :aria-label="`在新窗口${sourceAction}${item.title}`" @click="reportSourceOpened"><ExternalLink :size="16" />{{ sourceAction }}</a>
              <p v-else class="source-note">该来源链接暂不可用。</p>
            </template>
            <template v-else-if="state === 'ready' && instantPreview">
              <div class="generated-preview-intro"><span>{{ generatedPreviewHeading }}</span><p>{{ generatedPreviewSummary }}</p></div>
              <section v-for="section in instantPreview.sections" :key="String(section.title)" class="instant-section">
                <strong>{{ String(section.title || '预览内容') }}</strong>
                <p v-if="typeof section.prompt === 'string'">{{ section.prompt }}</p>
                <p v-if="typeof section.task === 'string'">{{ section.task }}</p>
                <ul v-if="Array.isArray(section.options)"><li v-for="(option, index) in section.options" :key="String(option)">{{ String.fromCharCode(65 + index) }}. {{ option }}</li></ul>
                <ul v-if="Array.isArray(section.points)"><li v-for="point in section.points" :key="String(point)">{{ point }}</li></ul>
                <div v-if="Array.isArray(section.nodes)" class="graph-skeleton"><span v-for="node in section.nodes" :key="String(node)">{{ node }}</span></div>
              </section>
            </template>
            <template v-else-if="state === 'ready' && preparedResource && isPractice">
              <p>练习概览</p>
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
              <p>学习结构</p>
              <KnowledgeGraphViewer v-if="graphJson" :graph-json="graphJson" />
              <div v-else class="preview-state compact is-error"><strong>知识图谱暂不可预览</strong><span>图谱数据不完整或格式无效，可重新生成后再试。</span></div>
            </template>
            <div v-else-if="state === 'ready'" class="preview-state is-error"><strong>当前内容暂不支持预览</strong><span>可返回资料中心继续选择其他学习内容。</span></div>
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
  .source-note { color: #667085; font-size: 13px; }
  .source-card { display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px; margin-bottom: 16px; padding: 14px; border: 1px solid #e4e7ec; border-radius: 12px; background: #fafbff; } .source-card:has(img) { grid-template-columns: 92px minmax(0, 1fr); } .source-card img { width: 92px; height: 116px; border-radius: 8px; object-fit: cover; background: #eaecf0; } .source-card__copy > p { margin: 7px 0 10px; color: #475467; } .source-kind { display: inline-flex; align-items: center; gap: 5px; color: #4338ca; font-size: 12px; font-weight: 700; } .source-card dl { margin-bottom: 0; font-size: 13px; } .source-card dl div { grid-template-columns: 72px minmax(0, 1fr); }
  .preview-state { display: grid; min-height: 130px; place-content: center; justify-items: center; gap: 10px; text-align: center; } .preview-state.compact { min-height: 82px; } .preview-state.is-error strong { color: #344054; } .preview-state.is-error span { color: #667085; font-size: 13px; }
  .generated-preview-intro { margin-bottom: 14px; } .generated-preview-intro span { color: #4f46e5; font-size: 12px; font-weight: 750; } .generated-preview-intro p { margin: 4px 0 0; color: #475467; }
  .instant-section { margin: 0 0 12px; padding: 12px 14px; border: 1px solid #e4e7ec; border-radius: 10px; background: #fafbff; }
  .instant-section > strong { color: #344054; } .instant-section p { margin: 5px 0; color: #1d2939; } .instant-section ul { display: grid; gap: 3px; margin: 7px 0 0; padding-left: 20px; color: #667085; font-size: 13px; }
  .graph-skeleton { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 9px; } .graph-skeleton span { padding: 4px 8px; border: 1px solid #c7d2fe; border-radius: 999px; color: #4338ca; background: #eef2ff; font-size: 12px; }
  .quiz-preview { display: grid; gap: 10px; margin-bottom: 16px; } .quiz-preview > strong { color: #344054; font-size: 13px; } .quiz-preview article { padding: 11px 13px; border: 1px solid #e4e7ec; border-radius: 10px; background: #fafbff; } .quiz-preview article > span { color: #4f46e5; font-size: 12px; font-weight: 700; } .quiz-preview p { margin: 4px 0; color: #1d2939; } .quiz-preview ul { display: grid; gap: 2px; margin: 0; padding-left: 20px; color: #667085; font-size: 13px; }
  button, .primary-link { display: inline-flex; min-height: 36px; align-items: center; justify-content: center; gap: 7px; padding: 0 14px; border: 1px solid #d0d5dd; border-radius: 9px; color: #344054; background: #fff; font: inherit; cursor: pointer; text-decoration: none; } .primary-link { border-color: #4f46e5; color: #fff; background: #4f46e5; } .icon-button { width: 36px; padding: 0; }
  .spinning { animation: spin 0.8s linear infinite; } .recommendation-preview-enter-active, .recommendation-preview-leave-active { transition: opacity 0.16s ease; } .recommendation-preview-enter-from, .recommendation-preview-leave-to { opacity: 0; } @keyframes spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .spinning { animation: none; } .recommendation-preview-enter-active, .recommendation-preview-leave-active { transition: none; } }
</style>
