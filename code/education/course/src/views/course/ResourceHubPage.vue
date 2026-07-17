<script setup lang="ts">
  import { computed, onMounted, ref, watch } from 'vue';
  import { useRouter } from 'vue-router';
  import { Message, Modal } from '@arco-design/web-vue';
  import {
    BookOpen,
    Download,
    Eye,
    ExternalLink,
    Pin,
    Plus,
    RefreshCw,
    RotateCw,
    Search,
    Sparkles,
    Star,
    Trash2,
    X,
  } from 'lucide-vue-next';
  import {
    downloadResource,
    queryResources,
    removeResourceFromLibrary,
    setResourceFavorite,
    setResourceTop,
    type ResourceRecord,
  } from '@/api/resources';
  import ResourcePreviewDialog from '@/components/resource/ResourcePreviewDialog.vue';
  import RecommendationPreviewDialog from '@/components/resource/RecommendationPreviewDialog.vue';
  import {
    addRecommendationToLibrary,
    dismissResourceRecommendation,
    favoriteResourceRecommendation,
    fetchResourceRecommendations,
    regenerateResourceRecommendation,
    reportRecommendationSourceOpened,
    type ResourceRecommendationItem,
  } from '@/api/resource-hub';

  const router = useRouter();
  const resources = ref<ResourceRecord[]>([]);
  const recommendations = ref<ResourceRecommendationItem[]>([]);
  const resourceCount = ref(0);
  const keyword = ref('');
  const activeType = ref('');
  const visibleLimit = ref(12);
  const loadingResources = ref(true);
  const loadingRecommendations = ref(true);
  const refreshingRecommendations = ref(false);
  const resourceBusy = ref<Record<string, string>>({});
  const recommendationBusy = ref<Record<string, string>>({});
  const previewingResource = ref<ResourceRecord | null>(null);
  const previewingRecommendation = ref<ResourceRecommendationItem | null>(null);

  const typeLabels: Record<string, string> = {
    pdf: 'PDF',
    ppt: 'PPT',
    pptx: 'PPT',
    doc: 'Word',
    docx: 'Word',
    lecture_markdown: '讲义',
    lecture_docx: '讲义',
    lecture_pdf: '讲义',
    practice_markdown: '练习',
    practice_docx: '练习',
    practice_pdf: '练习',
    question: '在线练习',
    mind_map: '思维导图',
    reading_list: '拓展阅读',
    case_project: '实践案例',
    video_script: '视频脚本',
    knowledge_graph: '知识图谱',
    lecture_note: '讲义',
    quiz: '在线练习',
    reading: '拓展阅读',
    code_case: '代码案例',
    quality_checklist: '质量核验报告',
    image: '图解卡片',
    markdown: 'Markdown 文档',
    md: 'Markdown 文档',
    txt: '文本资料',
    document: '个性化讲解',
    video: '视频讲解',
    code: '代码案例',
    external: '网络资料',
    lecture: '讲义',
    practice: '练习',
    word: 'Word',
    presentation: 'PPT',
    other: '其他资料',
  };

  const filteredResources = computed(() => {
    const normalized = keyword.value.trim().toLowerCase();
    return resources.value.filter((resource) => {
      if (activeType.value && typeFamily(resource.type) !== activeType.value) return false;
      if (!normalized) return true;
      return [resource.title, resource.subject, resource.knowledge_point, resource.file_name]
        .some((value) => String(value || '').toLowerCase().includes(normalized));
    });
  });

  const availableTypes = computed(() =>
    Array.from(new Set(resources.value.map((resource) => typeFamily(resource.type))))
      .filter(Boolean)
      .sort((a, b) => typeLabel(a).localeCompare(typeLabel(b), 'zh-CN'))
  );
  const visibleResources = computed(() =>
    filteredResources.value.slice(0, visibleLimit.value)
  );

  function typeLabel(type: string) {
    return typeLabels[type] || typeLabels[typeFamily(type)] || '其他资料';
  }

  function typeFamily(type: string) {
    if (type.startsWith('lecture_')) return 'lecture';
    if (type.startsWith('practice_')) return 'practice';
    if (['doc', 'docx'].includes(type)) return 'word';
    if (['ppt', 'pptx'].includes(type)) return 'presentation';
    return typeLabels[type] ? type : 'other';
  }

  function formatSize(value: number) {
    const size = Number(value || 0);
    if (!size) return '已入库';
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / 1024 / 1024).toFixed(1)} MB`;
  }

  function formatDate(value: string) {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '最近更新';
    return parsed.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' });
  }

  function toggleResourcePage() {
    if (visibleResources.value.length < filteredResources.value.length) {
      visibleLimit.value += 12;
    } else {
      visibleLimit.value = 12;
    }
  }

  function setResourceBusy(id: string, action = '') {
    resourceBusy.value = { ...resourceBusy.value, [id]: action };
  }

  function setRecommendationBusy(id: string, action = '') {
    recommendationBusy.value = { ...recommendationBusy.value, [id]: action };
  }

  function recommendationGenerationErrorMessage(error: unknown) {
    const detail = (error as { response?: { data?: { detail?: unknown } } })
      ?.response?.data?.detail;
    if (
      typeof detail === 'string' &&
      (detail.includes('题目质量') ||
        detail.includes('结构化题目生成失败') ||
        detail.includes('质量审查'))
    ) {
      return '内容审查未通过，已阻止不合格资料入库。请再次生成。';
    }
    return '重新生成失败，请稍后重试';
  }

  async function loadResources() {
    loadingResources.value = true;
    try {
      const response = await queryResources({ limit: 100 });
      resources.value = response.data.data || [];
      resourceCount.value = response.data.count || resources.value.length;
      visibleLimit.value = 12;
    } catch (error) {
      Message.error(error instanceof Error ? error.message : '资料库加载失败');
    } finally {
      loadingResources.value = false;
    }
  }

  async function loadRecommendations(refresh = false) {
    if (refresh) refreshingRecommendations.value = true;
    else loadingRecommendations.value = true;
    try {
      const response = await fetchResourceRecommendations(6, refresh);
      recommendations.value = response.data.items || [];
      if (refresh) Message.success('已根据最新学习状态更新推荐');
    } catch (error) {
      Message.error(error instanceof Error ? error.message : '个性化推荐加载失败');
    } finally {
      loadingRecommendations.value = false;
      refreshingRecommendations.value = false;
    }
  }

  async function toggleFavorite(resource: ResourceRecord) {
    if (resourceBusy.value[resource.id]) return;
    setResourceBusy(resource.id, 'favorite');
    try {
      const favorite = !resource.favorite;
      await setResourceFavorite(resource.id, favorite);
      resource.favorite = favorite;
      Message.success(favorite ? '已加入收藏' : '已取消收藏');
    } catch {
      Message.error('收藏状态更新失败');
    } finally {
      setResourceBusy(resource.id);
    }
  }

  async function toggleTop(resource: ResourceRecord) {
    if (resourceBusy.value[resource.id]) return;
    setResourceBusy(resource.id, 'top');
    try {
      await setResourceTop(resource.id, !resource.top);
      await loadResources();
      Message.success(resource.top ? '已取消置顶' : '已置顶');
    } catch {
      Message.error('置顶状态更新失败');
    } finally {
      setResourceBusy(resource.id);
    }
  }

  async function download(resource: ResourceRecord) {
    if (resourceBusy.value[resource.id]) return;
    setResourceBusy(resource.id, 'download');
    try {
      const response = await downloadResource(resource.id);
      const blobUrl = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = resource.file_name || resource.title || '学习资料';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(blobUrl);
    } catch {
      Message.error('下载失败，请稍后重试');
    } finally {
      setResourceBusy(resource.id);
    }
  }

  function canPreview(resource: ResourceRecord) {
    if (resource.url || ['question', 'quiz'].includes(resource.type)) return false;
    const name = resource.file_name.toLowerCase();
    return ['.pdf', '.png', '.jpg', '.jpeg', '.docx', '.pptx', '.md', '.markdown', '.txt']
      .some((extension) => name.endsWith(extension));
  }

  function preview(resource: ResourceRecord) {
    if (!canPreview(resource)) return;
    previewingResource.value = resource;
  }

  function previewRecommendation(item: ResourceRecommendationItem) {
    previewingRecommendation.value = item;
  }

  function trackRecommendationSourceOpened(item: ResourceRecommendationItem) {
    // The source must open immediately; feedback persistence is deliberately
    // non-blocking so a slow API never interferes with the user's click.
    void reportRecommendationSourceOpened(item.id).catch(() => undefined);
  }

  function updateRecommendation(item: ResourceRecommendationItem) {
    const index = recommendations.value.findIndex((entry) => entry.id === item.id);
    if (index >= 0) recommendations.value[index] = item;
    if (previewingRecommendation.value?.id === item.id) previewingRecommendation.value = item;
  }

  function safeExternalUrl(value?: string | null) {
    if (!value) return '';
    try {
      const url = new URL(value);
      return ['http:', 'https:'].includes(url.protocol) ? url.toString() : '';
    } catch {
      return '';
    }
  }

  function sourceMatchesDomain(item: ResourceRecommendationItem) {
    return Boolean(
      item.source_domain && item.source.trim().toLowerCase() === item.source_domain.trim().toLowerCase()
    );
  }

  function removeFromLibrary(resource: ResourceRecord) {
    Modal.confirm({
      title: '从资料库移除',
      content: `确定移除“${resource.title}”吗？后续仍可通过课程或推荐重新添加。`,
      okText: '移除',
      cancelText: '取消',
      async onOk() {
        setResourceBusy(resource.id, 'remove');
        try {
          await removeResourceFromLibrary(resource.id);
          resources.value = resources.value.filter((item) => item.id !== resource.id);
          resourceCount.value = Math.max(0, resourceCount.value - 1);
          Message.success('已从资料库移除');
        } catch {
          Message.error('移除失败，请稍后重试');
          throw new Error('remove failed');
        } finally {
          setResourceBusy(resource.id);
        }
      },
    });
  }

  function openResource(resource: ResourceRecord) {
    if (['question', 'quiz'].includes(resource.type)) {
      router.push({ name: 'QuizPage', params: { resourceId: resource.id } });
      return;
    }
    if (resource.url) {
      try {
        const url = new URL(resource.url);
        if (!['http:', 'https:'].includes(url.protocol)) throw new Error('unsupported protocol');
        window.open(url.toString(), '_blank', 'noopener,noreferrer');
      } catch {
        Message.error('资源链接无效');
      }
      return;
    }
    void download(resource);
  }

  async function toggleRecommendationFavorite(item: ResourceRecommendationItem) {
    if (recommendationBusy.value[item.id]) return;
    setRecommendationBusy(item.id, 'favorite');
    try {
      const response = await favoriteResourceRecommendation(item.id, !item.favorite);
      const index = recommendations.value.findIndex((entry) => entry.id === item.id);
      if (index >= 0) recommendations.value[index] = response.data;
    } catch {
      Message.error('推荐收藏状态更新失败');
    } finally {
      setRecommendationBusy(item.id);
    }
  }

  async function dismissRecommendation(item: ResourceRecommendationItem) {
    if (recommendationBusy.value[item.id]) return;
    setRecommendationBusy(item.id, 'dismiss');
    try {
      await dismissResourceRecommendation(item.id);
      recommendations.value = recommendations.value.filter((entry) => entry.id !== item.id);
    } catch {
      Message.error('暂时无法忽略该推荐');
    } finally {
      setRecommendationBusy(item.id);
    }
  }

  async function regenerateRecommendation(item: ResourceRecommendationItem) {
    if (recommendationBusy.value[item.id]) return;
    setRecommendationBusy(item.id, 'regenerate');
    try {
      const response = await regenerateResourceRecommendation(item.id);
      const index = recommendations.value.findIndex((entry) => entry.id === item.id);
      if (index >= 0) recommendations.value[index] = response.data.recommendation;
      Message.success(response.data.message || '已重新生成推荐');
    } catch (error) {
      Message.error(recommendationGenerationErrorMessage(error));
    } finally {
      setRecommendationBusy(item.id);
    }
  }

  async function addToLibrary(item: ResourceRecommendationItem) {
    if (recommendationBusy.value[item.id]) return;
    setRecommendationBusy(item.id, 'add');
    try {
      const response = await addRecommendationToLibrary(item.id);
      const index = recommendations.value.findIndex((entry) => entry.id === item.id);
      if (index >= 0) recommendations.value[index] = response.data.recommendation;
      await loadResources();
      Message.success(response.data.message || '已加入资料库');
    } catch {
      Message.error('加入资料库失败');
    } finally {
      setRecommendationBusy(item.id);
    }
  }

  onMounted(() => {
    void Promise.all([loadResources(), loadRecommendations()]);
  });

  watch([keyword, activeType], () => {
    visibleLimit.value = 12;
  });
</script>

<template>
  <main class="resource-hub-page">
    <header class="resource-hub-hero">
      <div>
        <span><Sparkles :size="15" /> AI 资料中心</span>
        <h1>把当前需要的学习资料，收在一处</h1>
        <p>管理已入库资料，并根据你的课程进度获取下一步推荐。</p>
      </div>
      <nav aria-label="资料中心快捷操作">
        <button type="button" class="secondary" @click="router.push({ name: 'WrongQuestionBook' })">
          <BookOpen :size="16" /> 我的错题本
        </button>
        <button type="button" class="primary" @click="router.push({ name: 'CourseResourceGeneration' })">
          <Plus :size="16" /> 生成学习资料
        </button>
      </nav>
    </header>

    <section class="resource-section recommendation-section" aria-labelledby="recommendation-title">
      <header class="section-heading">
        <div>
          <span>个性化推荐</span>
          <h2 id="recommendation-title">建议你接着看</h2>
          <p>推荐会随学习记录和最近反馈持续更新。</p>
        </div>
        <button
          type="button"
          class="quiet-action"
          :disabled="refreshingRecommendations"
          @click="loadRecommendations(true)"
        >
          <RefreshCw :size="15" :class="{ spinning: refreshingRecommendations }" />
          {{ refreshingRecommendations ? '正在更新…' : '换一批' }}
        </button>
      </header>

      <div v-if="loadingRecommendations" class="section-state">正在整理个性化推荐…</div>
      <div v-else-if="!recommendations.length" class="section-state">
        完成一次课程学习或练习后，这里会出现更精准的资料建议。
      </div>
      <div v-else class="recommendation-grid">
        <article v-for="item in recommendations" :key="item.id" class="recommendation-card">
          <header>
            <span>{{ typeLabel(item.type) }}</span>
            <div>
              <button
                type="button"
                :class="{ active: item.favorite }"
                :aria-label="item.favorite ? '取消收藏推荐' : '收藏推荐'"
                :disabled="Boolean(recommendationBusy[item.id])"
                @click="toggleRecommendationFavorite(item)"
              ><Star :size="15" :fill="item.favorite ? 'currentColor' : 'none'" />{{ item.favorite ? '已收藏' : '收藏' }}</button>
              <button
                type="button"
                aria-label="忽略该推荐"
                :disabled="Boolean(recommendationBusy[item.id])"
                @click="dismissRecommendation(item)"
              ><X :size="15" />不感兴趣</button>
            </div>
          </header>
          <strong>{{ item.title }}</strong>
          <p>{{ item.reason || item.preview }}</p>
          <small>{{ item.subject || '通用学习' }}<template v-if="item.knowledge_point"> · {{ item.knowledge_point }}</template></small>
          <div class="recommendation-source">
            <template v-if="item.origin === 'external' && safeExternalUrl(item.url)">
              <span>来源：</span>
              <a
                :href="safeExternalUrl(item.url)"
                target="_blank"
                rel="noopener noreferrer"
                :aria-label="`在新窗口打开${item.source}原文`"
                @click="trackRecommendationSourceOpened(item)"
              >
                {{ item.source }}<template v-if="!sourceMatchesDomain(item)"> · {{ item.source_domain }}</template> <ExternalLink :size="12" />
              </a>
            </template>
            <template v-else>来源：{{ item.source || '来源暂不可用' }}</template>
          </div>
          <footer>
            <button
              type="button"
              class="secondary"
              :disabled="Boolean(recommendationBusy[item.id])"
              @click="previewRecommendation(item)"
            >
              <Eye :size="14" /> 预览
            </button>
            <button
              type="button"
              class="secondary"
              :disabled="Boolean(recommendationBusy[item.id])"
              @click="regenerateRecommendation(item)"
            >
              <RotateCw :size="14" />
              {{ recommendationBusy[item.id] === 'regenerate' ? '正在重新生成…' : '重新生成' }}
            </button>
            <button
              type="button"
              class="primary"
              :disabled="Boolean(recommendationBusy[item.id]) || item.status === 'added'"
              @click="addToLibrary(item)"
            >
              <Plus :size="14" />
              {{ item.status === 'added' ? '已在资料库' : recommendationBusy[item.id] === 'add' ? '正在加入…' : '加入资料库' }}
            </button>
          </footer>
        </article>
      </div>
    </section>

    <section class="resource-section library-section" aria-labelledby="library-title">
      <header class="section-heading library-heading">
        <div>
          <span>我的资料</span>
          <h2 id="library-title">资料库</h2>
          <p>已加入 {{ resourceCount }} 项，置顶内容会优先显示。</p>
        </div>
        <form class="resource-search" role="search" @submit.prevent>
          <Search :size="16" aria-hidden="true" />
          <input v-model="keyword" aria-label="搜索资料库" placeholder="搜索资料、课程或知识点" />
          <select v-model="activeType" aria-label="按类型筛选资料">
            <option value="">全部类型</option>
            <option v-for="type in availableTypes" :key="type" :value="type">{{ typeLabel(type) }}</option>
          </select>
        </form>
      </header>

      <div v-if="loadingResources" class="section-state">正在加载资料库…</div>
      <div v-else-if="!filteredResources.length" class="section-state">
        <strong>{{ resources.length ? '没有找到匹配资料' : '资料库还是空的' }}</strong>
        <p>{{ resources.length ? '试试更换搜索词或类型。' : '可以从上方推荐加入，或生成一份个性化学习资料。' }}</p>
      </div>
      <div v-else class="resource-list">
        <article v-for="resource in visibleResources" :key="resource.id" :class="{ 'is-top': resource.top }">
          <div class="resource-kind">{{ typeLabel(resource.type) }}</div>
          <div class="resource-copy">
            <div>
              <strong>{{ resource.title }}</strong>
              <span v-if="resource.top"><Pin :size="12" fill="currentColor" /> 已置顶</span>
            </div>
            <p>{{ resource.subject || '通用学习' }}<template v-if="resource.knowledge_point"> · {{ resource.knowledge_point }}</template></p>
          </div>
          <small>{{ formatSize(resource.file_size) }} · {{ formatDate(resource.upload_time) }}</small>
          <div class="resource-actions">
            <button
              type="button"
              :class="{ active: resource.favorite }"
              :aria-label="resource.favorite ? `取消收藏${resource.title}` : `收藏${resource.title}`"
              :disabled="Boolean(resourceBusy[resource.id])"
              @click="toggleFavorite(resource)"
            ><Star :size="15" :fill="resource.favorite ? 'currentColor' : 'none'" />{{ resource.favorite ? '取消收藏' : '收藏' }}</button>
            <button
              type="button"
              :class="{ active: resource.top }"
              :aria-label="resource.top ? `取消置顶${resource.title}` : `置顶${resource.title}`"
              :disabled="Boolean(resourceBusy[resource.id])"
              @click="toggleTop(resource)"
            ><Pin :size="15" :fill="resource.top ? 'currentColor' : 'none'" />{{ resource.top ? '取消置顶' : '置顶' }}</button>
            <button
              v-if="canPreview(resource)"
              type="button"
              :aria-label="`预览${resource.title}`"
              :disabled="Boolean(resourceBusy[resource.id])"
              @click="preview(resource)"
            ><Eye :size="15" />预览</button>
            <button
              type="button"
              :aria-label="['question', 'quiz'].includes(resource.type) ? `开始${resource.title}` : resource.url ? `打开${resource.title}` : `下载${resource.title}`"
              :disabled="Boolean(resourceBusy[resource.id])"
              @click="openResource(resource)"
            >
              <BookOpen v-if="['question', 'quiz'].includes(resource.type)" :size="15" />
              <ExternalLink v-else-if="resource.url" :size="15" />
              <Download v-else :size="15" />
              {{ ['question', 'quiz'].includes(resource.type) ? '开始练习' : resource.url ? '打开来源' : '下载' }}
            </button>
            <button
              type="button"
              class="danger"
              :aria-label="`从资料库移除${resource.title}`"
              :disabled="Boolean(resourceBusy[resource.id])"
              @click="removeFromLibrary(resource)"
            ><Trash2 :size="15" />移除</button>
          </div>
        </article>
      </div>
      <footer v-if="filteredResources.length" class="library-pagination">
        <span aria-live="polite">已显示 {{ visibleResources.length }} / {{ filteredResources.length }} 项</span>
        <div>
          <button
            v-if="filteredResources.length > 12"
            type="button"
            @click="toggleResourcePage"
          >
            {{ visibleResources.length < filteredResources.length ? '加载更多' : '收起' }}
          </button>
        </div>
      </footer>
    </section>
    <ResourcePreviewDialog
      :resource="previewingResource"
      @close="previewingResource = null"
      @download="download"
    />
    <RecommendationPreviewDialog
      :item="previewingRecommendation"
      @close="previewingRecommendation = null"
      @download="download"
      @updated="updateRecommendation"
    />
  </main>
</template>

<style scoped lang="scss">
  .resource-hub-page {
    min-height: calc(100vh - 64px);
    padding: 34px clamp(24px, 5vw, 72px) 70px;
    color: #1d2939;
    background: #f7f8fc;
  }

  button,
  input,
  select {
    font: inherit;
  }

  button {
    cursor: pointer;
  }

  button:disabled {
    cursor: wait;
    opacity: 0.58;
  }

  .resource-hub-hero {
    max-width: 1240px;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 32px;
    margin: 0 auto 24px;

    > div {
      max-width: 760px;
    }

    span {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      color: #4f46e5;
      font-size: 13px;
      font-weight: 750;
    }

    h1 {
      margin: 8px 0 7px;
      color: #101828;
      font-size: clamp(27px, 2.6vw, 38px);
      line-height: 1.2;
      letter-spacing: -0.025em;
    }

    p {
      margin: 0;
      color: #667085;
      font-size: 15px;
      line-height: 1.7;
    }

    nav {
      display: flex;
      flex: 0 0 auto;
      gap: 10px;
    }
  }

  .primary,
  .secondary,
  .quiet-action {
    display: inline-flex;
    height: 38px;
    align-items: center;
    justify-content: center;
    gap: 7px;
    padding: 0 14px;
    border: 1px solid rgba(15, 23, 42, 0.1);
    border-radius: 11px;
    color: #475467;
    background: #fff;
  }

  .primary {
    border-color: #4f46e5;
    color: #fff;
    background: #4f46e5;
  }

  .resource-section {
    max-width: 1240px;
    margin: 0 auto 22px;
    padding: 24px;
    border: 1px solid rgba(15, 23, 42, 0.07);
    border-radius: 22px;
    background: #fff;
    box-shadow: 0 12px 34px rgba(15, 23, 42, 0.035);
  }

  .section-heading {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;
    margin-bottom: 18px;

    span {
      color: #6366f1;
      font-size: 12px;
      font-weight: 750;
    }

    h2 {
      margin: 3px 0;
      color: #101828;
      font-size: 20px;
    }

    p {
      margin: 0;
      color: #667085;
      font-size: 13px;
    }
  }

  .quiet-action {
    border-color: transparent;
    background: #f5f6ff;
    color: #4f46e5;
  }

  .spinning {
    animation: spin 0.9s linear infinite;
  }

  .section-state {
    min-height: 120px;
    display: grid;
    align-content: center;
    justify-items: center;
    gap: 6px;
    padding: 24px;
    border: 1px dashed #dfe3eb;
    border-radius: 16px;
    color: #667085;
    text-align: center;

    p {
      margin: 0;
      font-size: 13px;
    }
  }

  .recommendation-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .recommendation-card {
    min-width: 0;
    display: flex;
    min-height: 234px;
    flex-direction: column;
    padding: 16px;
    border: 1px solid #e8eaf1;
    border-radius: 16px;
    background: #fff;

    > header,
    > footer,
    > header div {
      display: flex;
      align-items: center;
    }

    > header {
      justify-content: space-between;
    }

    > header > span {
      padding: 3px 8px;
      border-radius: 999px;
      color: #4f46e5;
      background: #eef2ff;
      font-size: 11px;
      font-weight: 700;
    }

    > header div {
      gap: 3px;
    }

    > header button {
      display: inline-flex;
      min-height: 30px;
      height: 32px;
      align-items: center;
      justify-content: center;
      gap: 4px;
      padding: 0 7px;
      border: 0;
      border-radius: 9px;
      color: #667085;
      background: transparent;
      font-size: 11px;

      &:hover,
      &.active {
        color: #4f46e5;
        background: #f2f4ff;
      }
    }

    > strong {
      margin-top: 12px;
      overflow: hidden;
      color: #1d2939;
      font-size: 15px;
      line-height: 1.45;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    > p {
      display: -webkit-box;
      margin: 7px 0 8px;
      overflow: hidden;
      color: #667085;
      font-size: 12px;
      line-height: 1.6;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }

    > small {
      color: #98a2b3;
      font-size: 11px;
    }

    .recommendation-source {
      min-height: 18px;
      margin-top: 7px;
      overflow: hidden;
      color: #667085;
      font-size: 11px;
      line-height: 1.45;
      text-overflow: ellipsis;
      white-space: nowrap;

      a {
        display: inline-flex;
        max-width: calc(100% - 28px);
        align-items: center;
        gap: 3px;
        overflow: hidden;
        color: #4f46e5;
        text-decoration: none;
        text-overflow: ellipsis;
        vertical-align: bottom;

        &:hover { text-decoration: underline; }
      }
    }

    > footer {
      gap: 8px;
      margin-top: auto;
      padding-top: 14px;

      button {
        min-width: 0;
        flex: 1;
        height: 34px;
        padding-inline: 9px;
        font-size: 12px;
      }
    }
  }

  .library-heading {
    align-items: flex-end;
  }

  .resource-search {
    width: min(520px, 50%);
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 8px;
    padding: 5px 6px 5px 12px;
    border: 1px solid #e1e4eb;
    border-radius: 13px;
    color: #98a2b3;
    background: #fafbfc;

    input,
    select {
      min-width: 0;
      height: 32px;
      border: 0;
      outline: none !important;
      box-shadow: none !important;
      color: #344054;
      background: transparent;

      &:focus,
      &:focus-visible {
        outline: none !important;
        box-shadow: none !important;
      }
    }

    select {
      padding: 0 8px;
      border-left: 1px solid #e1e4eb;
      color: #667085;
      font-size: 12px;
    }

    &:focus-within {
      border-color: #94a3b8;
      box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.08);
    }
  }

  .resource-list {
    display: grid;
  }

  .resource-list > article {
    min-width: 0;
    display: grid;
    grid-template-columns: 78px minmax(0, 1fr) 120px auto;
    align-items: center;
    gap: 14px;
    min-height: 70px;
    padding: 10px 4px;
    border-top: 1px solid #eef0f4;

    &:first-child {
      border-top: 0;
    }

    &.is-top {
      margin-inline: -8px;
      padding-inline: 12px;
      border-radius: 12px;
      background: #fbfbff;
    }

    > small {
      color: #98a2b3;
      font-size: 11px;
      text-align: right;
    }
  }

  .resource-kind {
    width: 68px;
    padding: 8px 6px;
    border-radius: 10px;
    color: #4f46e5;
    background: #eef2ff;
    font-size: 11px;
    font-weight: 700;
    text-align: center;
  }

  .resource-copy {
    min-width: 0;

    > div {
      display: flex;
      min-width: 0;
      align-items: center;
      gap: 8px;
    }

    strong {
      overflow: hidden;
      color: #1d2939;
      font-size: 14px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      display: inline-flex;
      flex: 0 0 auto;
      align-items: center;
      gap: 3px;
      color: #6366f1;
      font-size: 10px;
    }

    p {
      margin: 4px 0 0;
      overflow: hidden;
      color: #667085;
      font-size: 12px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .resource-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;

    button {
      display: inline-flex;
      min-height: 32px;
      align-items: center;
      justify-content: center;
      gap: 4px;
      padding: 0 7px;
      border: 0;
      border-radius: 8px;
      color: #667085;
      background: transparent;
      font-size: 11px;

      &:hover,
      &.active {
        color: #4f46e5;
        background: #f2f4ff;
      }
    }

    button.danger:hover {
      color: #d92d20;
      background: #fff1f0;
    }
  }

  .library-pagination {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-top: 12px;
    padding-top: 16px;
    border-top: 1px solid #eef0f4;

    > span {
      color: #667085;
      font-size: 12px;
      font-variant-numeric: tabular-nums;
    }

    > div {
      display: flex;
      gap: 8px;
    }

    button {
      min-width: 88px;
      height: 34px;
      padding: 0 14px;
      border: 1px solid #4f46e5;
      border-radius: 10px;
      color: #fff;
      background: #4f46e5;
      font-size: 12px;
      font-weight: 650;

      &.secondary {
        border-color: #e1e4eb;
        color: #475467;
        background: #fff;
      }

      &:focus-visible {
        outline: 2px solid #818cf8;
        outline-offset: 2px;
      }
    }
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  @media (max-width: 1080px) {
    .recommendation-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .resource-list > article {
      grid-template-columns: 78px minmax(0, 1fr) auto;
    }

    .resource-list > article > small {
      display: none;
    }
  }

  @media (max-width: 820px) {
    .resource-hub-page {
      padding-inline: 20px;
    }

    .resource-hub-hero,
    .section-heading {
      align-items: stretch;
      flex-direction: column;
    }

    .resource-hub-hero nav,
    .resource-search {
      width: 100%;
    }

    .recommendation-grid {
      grid-template-columns: 1fr;
    }

    .resource-list > article {
      grid-template-columns: 68px minmax(0, 1fr);
    }

    .resource-actions {
      grid-column: 2;
    }

    .library-pagination {
      align-items: stretch;
      flex-direction: column;

      > div,
      button {
        width: 100%;
      }
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .spinning {
      animation: none;
    }
  }
</style>
