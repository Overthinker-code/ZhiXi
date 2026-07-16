<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import axios from 'axios';
  import { Message } from '@arco-design/web-vue';
  import { getToken } from '@/utils/auth';
  import { setResourceFavorite } from '@/api/resources';
  import KnowledgeGraphViewer from './KnowledgeGraphViewer.vue';

  defineProps<{
    artifacts: Array<Record<string, any>>;
    packageId?: string;
  }>();

  const selected = ref<Record<string, any> | null>(null);
  const router = useRouter();

  const labelMap: Record<string, string> = {
    knowledge_graph: '知识图谱',
    lecture_markdown: '讲义',
    lecture_note: '讲义',
    practice_markdown: '练习题',
    quiz: '练习题',
    question: '专项练习',
    mind_map: '思维导图',
    reading_list: '拓展阅读',
    reading: '拓展阅读',
    case_project: '代码案例',
    code_case: '代码案例',
    video_script: '视频脚本',
  };

  const selectedLabel = computed(() =>
    selected.value ? labelMap[selected.value.kind] || selected.value.kind || '资源' : ''
  );

  const selectedIsKnowledgeGraph = computed(
    () => selected.value?.kind === 'knowledge_graph' || selected.value?.resource_type === 'knowledge_graph'
  );

  function formatGeneratedAt(value: unknown) {
    if (!value) return '刚刚生成';
    const date = new Date(String(value));
    return Number.isNaN(date.getTime()) ? '刚刚生成' : date.toLocaleString('zh-CN');
  }

  function openResource(item: Record<string, any>) {
    if ((item.kind === 'question' || item.resource_type === 'question') && item.resource_id) {
      router.push({ name: 'QuizPage', params: { resourceId: String(item.resource_id) } });
      return;
    }
    selected.value = item;
  }

  function enterLibrary(item: Record<string, any>) {
    router.push({
      name: 'ResourceHub',
      query: item.resource_id ? { resourceId: String(item.resource_id) } : undefined,
    });
  }

  async function toggleFavorite(item: Record<string, any>) {
    if (!item.resource_id) return;
    const next = !item.favorite;
    try {
      await setResourceFavorite(String(item.resource_id), next);
      item.favorite = next;
      Message.success(next ? '已收藏到资料库' : '已取消收藏');
    } catch {
      Message.error('收藏状态更新失败');
    }
  }

  async function downloadArtifact(item: Record<string, any>) {
    const url = String(item.download_url || '');
    if (!url) return;
    try {
      const token = getToken();
      const response = await axios.get(url, {
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
</script>

<template>
  <section v-if="artifacts.length" class="artifact-cards">
    <header>
      <span>资源包</span>
      <strong v-if="packageId">{{ packageId }}</strong>
    </header>
    <div class="artifact-cards__grid">
      <article
        v-for="item in artifacts"
        :key="item.resource_id || item.file_name || item.title || item.kind"
        class="artifact-card"
      >
        <span>{{ labelMap[item.kind] || item.kind || '资源' }}</span>
        <strong>{{ item.title || item.file_name || '生成资源' }}</strong>
        <p>{{ item.knowledge_point || item.root || '当前学习主题' }}</p>
        <small>{{ formatGeneratedAt(item.generated_at) }}</small>
        <div class="artifact-card__actions">
          <button type="button" @click="openResource(item)">
            {{ item.kind === 'knowledge_graph' ? '查看知识图谱' : item.kind === 'question' ? '开始答题' : '查看' }}
          </button>
          <button type="button" @click="enterLibrary(item)">进入资料库</button>
          <button
            v-if="item.download_url"
            type="button"
            @click="downloadArtifact(item)"
          >
            下载 Word
          </button>
          <button
            v-if="item.resource_id"
            type="button"
            @click="toggleFavorite(item)"
          >
            {{ item.favorite ? '取消收藏' : '收藏' }}
          </button>
        </div>
      </article>
    </div>

    <Teleport to="body">
      <Transition name="artifact-preview">
        <div v-if="selected" class="artifact-preview" role="dialog" aria-modal="true">
          <button class="artifact-preview__backdrop" type="button" @click="selected = null" />
          <article
            class="artifact-preview__panel"
            :class="{ 'is-knowledge-graph': selectedIsKnowledgeGraph }"
          >
            <header>
              <span>{{ selectedLabel }}</span>
              <strong>{{ selected.title || selected.file_name || '生成资源' }}</strong>
              <small>{{ selected.file_name || packageId || '资源包预览' }}</small>
            </header>
            <div v-if="selectedIsKnowledgeGraph" class="artifact-preview__graph">
              <KnowledgeGraphViewer :graph-json="selected.graph_json" />
            </div>
            <div v-else class="artifact-preview__content">
              {{ selected.preview || '当前资源包已生成，但后端未返回可展示摘要。你可以下载后查看完整内容。' }}
            </div>
            <footer>
              <button type="button" @click="selected = null">关闭</button>
              <button
                v-if="selected.download_url && !selectedIsKnowledgeGraph"
                type="button"
                class="primary"
                @click="downloadArtifact(selected)"
              >
                下载
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

    small {
      display: block;
      margin-top: 5px;
      color: #98a2b3;
      font-size: 11px;
    }

    em {
      display: inline-block;
      margin-top: 8px;
      color: #4f46e5;
      font-size: 12px;
      font-style: normal;
      font-weight: 700;
    }
  }

  .artifact-card__actions {
    display: flex;
    gap: 8px;
    margin-top: 10px;

    button {
      padding: 5px 9px;
      border: 1px solid rgba(99, 102, 241, 0.18);
      border-radius: 8px;
      background: #f5f3ff;
      color: #4f46e5;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
    }
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
    overflow: hidden;
    border: 1px solid rgba(15, 23, 42, 0.1);
    border-radius: 20px;
    background: #fff;
    box-shadow: 0 28px 80px rgba(15, 23, 42, 0.2);

    &.is-knowledge-graph {
      width: min(1080px, calc(100vw - 40px));
    }

    header,
    footer {
      padding: 18px 20px;
    }

    header {
      border-bottom: 1px solid rgba(15, 23, 42, 0.08);
    }

    header span,
    header strong,
    header small {
      display: block;
    }

    header span {
      color: #4f46e5;
      font-size: 12px;
      font-weight: 800;
    }

    header strong {
      margin-top: 5px;
      color: #101828;
      font-size: 18px;
    }

    header small {
      margin-top: 4px;
      color: #667085;
      font-size: 12px;
    }

    footer {
      display: flex;
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
    max-height: min(52vh, 420px);
    overflow: auto;
    padding: 18px 20px;
    color: #344054;
    font-size: 14px;
    line-height: 1.8;
    white-space: pre-wrap;
  }

  .artifact-preview__graph {
    padding: 14px;
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
  }
</style>
