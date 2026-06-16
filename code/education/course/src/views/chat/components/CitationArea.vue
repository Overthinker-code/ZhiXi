<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useSettingStore } from '@/store/setting';
  import { renderMarkdown, stripMarkdownCodeToolbar } from '@/utils/markdown';

  type CitationItem = {
    citation_id: number;
    source: string;
    snippet: string;
    reason?: string;
    relevance_score?: number;
    score?: number;
    chunk_id?: number | string;
    file_id?: string;
    file_name?: string;
    context_scope?: string;
    locator?: string;
  };

  const props = defineProps<{
    citations?: CitationItem[];
    confidence?: string;
    groundingMode?: string;
    metrics?: Record<string, any>;
  }>();

  const settingStore = useSettingStore();
  const expanded = ref(false);
  const showDiagnostics = computed(
    () => Boolean(settingStore.settings.debugMode)
  );
  const normalizedCitations = computed(() =>
    (props.citations || []).map((item, index) => {
      const source = item.file_name || item.source || `来源 ${item.citation_id || index + 1}`;
      const chunk = item.chunk_id ? `片段 ${item.chunk_id}` : '';
      const locator = item.locator || chunk;
      const scope =
        item.context_scope === 'uploaded_document'
          ? '上传文件'
          : item.context_scope === 'knowledge_base'
            ? '知识库'
            : '';
      return {
        ...item,
        sourceLabel: source.replace(/^.*[\\/]/, ''),
        locator,
        scope,
        score: Number(item.relevance_score || item.score || 0),
      };
    })
  );

  const confidenceLabel = (value?: string) => {
    const normalized = String(value || '').toLowerCase();
    if (normalized === 'high') return '高可信';
    if (normalized === 'low') return '需复核';
    return '中可信';
  };

  const groundingLabel = (value?: string) => {
    const normalized = String(value || '').toLowerCase();
    if (normalized === 'rag') return '知识库支撑';
    if (normalized === 'mixed') return '知识库 + 通用知识';
    if (normalized === 'tool') return '工具链支撑';
    return '通用模型回答';
  };

  const renderCitation = (value?: string) =>
    stripMarkdownCodeToolbar(renderMarkdown(value || ''));
</script>

<template>
  <div
    v-if="
      (citations && citations.length > 0) ||
      confidence ||
      groundingMode ||
      (showDiagnostics && metrics?.agent_hops)
    "
    class="citation-area"
  >
    <div class="citation-strip">
      <button
        v-if="normalizedCitations.length"
        type="button"
        class="source-toggle"
        @click="expanded = !expanded"
      >
        <span class="source-count">{{ normalizedCitations.length }}</span>
        <span>个来源</span>
        <i>{{ expanded ? '收起' : '查看' }}</i>
      </button>
      <span v-if="groundingMode" class="meta-pill">
        {{ groundingLabel(groundingMode) }}
      </span>
      <span v-if="confidence" class="meta-pill">
        {{ confidenceLabel(confidence) }}
      </span>
      <span
        v-if="showDiagnostics && metrics?.agent_hops"
        class="meta-pill meta-pill--soft"
      >
        {{ metrics.agent_hops }} 跳协作
      </span>
      <span
        v-if="showDiagnostics && metrics?.ttft_ms"
        class="meta-pill meta-pill--soft"
      >
        TTFT {{ metrics.ttft_ms }}ms
      </span>
    </div>

    <div v-if="normalizedCitations.length" class="source-chips">
      <button
        v-for="item in normalizedCitations.slice(0, 4)"
        :key="`${item.citation_id}-${item.sourceLabel}`"
        type="button"
        class="source-chip"
        @click="expanded = true"
      >
        <span>{{ item.citation_id }}</span>
        <strong>{{ item.sourceLabel }}</strong>
        <small v-if="item.locator">{{ item.locator }}</small>
      </button>
    </div>

    <div v-if="expanded && normalizedCitations.length" class="citation-detail-list">
      <article
        v-for="item in normalizedCitations"
        :key="`${item.citation_id}-${item.source}-${item.chunk_id}`"
        class="citation-detail"
      >
        <div class="citation-detail__head">
          <span>{{ item.citation_id }}</span>
          <strong>{{ item.sourceLabel }}</strong>
          <small v-if="item.scope">{{ item.scope }}</small>
          <small v-if="item.locator">{{ item.locator }}</small>
          <small v-if="item.score">相关度 {{ item.score.toFixed(2) }}</small>
        </div>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="citation-snippet" v-html="renderCitation(item.snippet)" />
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div
          v-if="item.reason"
          class="citation-reason"
          v-html="renderCitation(item.reason)"
        />
      </article>
    </div>
  </div>
</template>

<style scoped lang="scss">
  .citation-area {
    margin: 0.48rem 0 0 0.35rem;
  }

  .citation-strip,
  .source-chips {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.36rem;
  }

  .source-toggle,
  .source-chip {
    border: 1px solid rgba(148, 163, 184, 0.24);
    background: rgba(248, 250, 252, 0.88);
    color: #475569;
    cursor: pointer;
    transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
  }

  .source-toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.32rem;
    height: 1.75rem;
    padding: 0 0.52rem 0 0.34rem;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 650;

    .source-count {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.16rem;
      height: 1.16rem;
      border-radius: 999px;
      background: #eef2ff;
      color: #4f46e5;
      font-size: 0.7rem;
    }

    i {
      color: #64748b;
      font-style: normal;
      font-weight: 500;
    }

    &:hover {
      border-color: rgba(79, 70, 229, 0.32);
      background: #fff;
      transform: translateY(-1px);
    }
  }

  .source-chips {
    margin-top: 0.34rem;
  }

  .source-chip {
    display: inline-grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
    gap: 0.28rem;
    max-width: 15rem;
    padding: 0.34rem 0.46rem;
    border-radius: 9px;
    text-align: left;

    span {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.1rem;
      height: 1.1rem;
      border-radius: 50%;
      background: #eef2ff;
      color: #4f46e5;
      font-size: 0.68rem;
      font-weight: 750;
    }

    strong {
      min-width: 0;
      overflow: hidden;
      color: #334155;
      font-size: 0.74rem;
      font-weight: 650;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    small {
      grid-column: 2;
      overflow: hidden;
      color: #94a3b8;
      font-size: 0.66rem;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    &:hover {
      border-color: rgba(79, 70, 229, 0.32);
      background: #fff;
    }
  }

  .meta-pill {
    display: inline-flex;
    align-items: center;
    height: 1.75rem;
    padding: 0 0.52rem;
    border-radius: 999px;
    background: rgba(99, 102, 241, 0.08);
    color: #4f46e5;
    font-size: 0.72rem;
    font-weight: 650;

    &--soft {
      background: rgba(15, 23, 42, 0.06);
      color: #475569;
    }
  }

  .citation-detail-list {
    display: flex;
    flex-direction: column;
    gap: 0.42rem;
    max-width: min(860px, 100%);
    margin-top: 0.46rem;
  }

  .citation-detail {
    padding: 0.62rem 0.72rem;
    border: 1px solid rgba(226, 232, 240, 0.95);
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.92);
  }

  .citation-detail__head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.32rem;
    margin-bottom: 0.26rem;

    span {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.18rem;
      height: 1.18rem;
      border-radius: 50%;
      background: #eef2ff;
      color: #4f46e5;
      font-size: 0.68rem;
      font-weight: 750;
    }

    strong {
      color: #0f172a;
      font-size: 0.78rem;
    }

    small {
      padding: 0.12rem 0.34rem;
      border-radius: 999px;
      background: #f1f5f9;
      color: #64748b;
      font-size: 0.66rem;
    }
  }

  .citation-snippet {
    color: #334155;
    font-size: 0.78rem;
    line-height: 1.55;
  }

  .citation-reason {
    margin-top: 0.28rem;
    color: #64748b;
    font-size: 0.72rem;
  }

  .citation-snippet :deep(p),
  .citation-reason :deep(p) {
    margin: 0;
  }
</style>
