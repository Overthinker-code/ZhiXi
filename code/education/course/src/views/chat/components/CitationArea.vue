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
  const normalizeScore = (item: CitationItem) => {
    const raw = Number(item.relevance_score || item.score || 0);
    if (!Number.isFinite(raw) || raw <= 0) return 0;
    return Math.min(1, raw > 1 ? raw / 100 : raw);
  };
  const normalizedCitations = computed(() => {
    const seen = new Set<string>();
    return (props.citations || [])
      .map((item, index) => {
        const source = item.file_name || item.source || `来源 ${item.citation_id || index + 1}`;
        const chunk = item.chunk_id ? `片段 ${item.chunk_id}` : '';
        const locator = item.locator || chunk;
        const scope =
          item.context_scope === 'uploaded_document'
            ? '当前文件'
            : item.context_scope === 'knowledge_base'
              ? '课程库'
              : '';
        const sourceLabel = source.replace(/^.*[\\/]/, '');
        return {
          ...item,
          citation_id: item.citation_id || index + 1,
          sourceLabel,
          locator,
          scope,
          score: normalizeScore(item),
        };
      })
      .filter((item) => {
        const key = `${item.citation_id}-${item.sourceLabel}-${item.locator}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
  });
  const hasCitations = computed(() => normalizedCitations.value.length > 0);
  const compactSources = computed(() => {
    const grouped = new Map<string, any>();
    normalizedCitations.value.forEach((item) => {
      const key = `${item.scope || '资料'}-${item.sourceLabel}`;
      const current = grouped.get(key);
      if (!current) {
        grouped.set(key, {
          sourceLabel: item.sourceLabel,
          scope: item.scope,
          locator: item.locator,
          ids: [item.citation_id],
          displayIds: String(item.citation_id),
          score: item.score,
        });
        return;
      }
      if (!current.ids.includes(item.citation_id)) current.ids.push(item.citation_id);
      if (!current.locator && item.locator) current.locator = item.locator;
      current.score = Math.max(current.score || 0, item.score || 0);
      current.displayIds = current.ids.join(', ');
    });
    return [...grouped.values()].sort((a, b) => {
      if (a.scope === '当前文件' && b.scope !== '当前文件') return -1;
      if (b.scope === '当前文件' && a.scope !== '当前文件') return 1;
      return (b.score || 0) - (a.score || 0);
    });
  });
  const citationMarkers = computed(() =>
    normalizedCitations.value.slice(0, 5).map((item) => ({
      id: item.citation_id,
      scope: item.scope,
      sourceLabel: item.sourceLabel,
      locator: item.locator,
    }))
  );
  const primarySourceSummary = computed(() => {
    const first = compactSources.value[0];
    if (!first) return '';
    const suffix =
      compactSources.value.length > 1 ? ` 等 ${compactSources.value.length} 个来源` : '';
    return `${first.sourceLabel}${suffix}`;
  });

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
      hasCitations ||
      (showDiagnostics && metrics?.agent_hops)
    "
    class="citation-area"
  >
    <div class="citation-strip">
      <button
        v-if="normalizedCitations.length"
        type="button"
        class="source-toggle"
        :aria-expanded="expanded"
        @click="expanded = !expanded"
      >
        <span class="source-count">{{ normalizedCitations.length }}</span>
        <span>引用</span>
        <strong>{{ primarySourceSummary }}</strong>
      </button>
      <div v-if="citationMarkers.length" class="citation-markers">
        <button
          v-for="item in citationMarkers"
          :key="item.id"
          type="button"
          :title="`${item.scope || '资料'} · ${item.sourceLabel}${item.locator ? ` · ${item.locator}` : ''}`"
          @click="expanded = !expanded"
        >
          {{ item.id }}
        </button>
        <span v-if="normalizedCitations.length > citationMarkers.length">
          +{{ normalizedCitations.length - citationMarkers.length }}
        </span>
      </div>
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

    <div v-if="expanded && normalizedCitations.length" class="citation-detail-list">
      <div class="citation-summary">
        <span>{{ groundingLabel(groundingMode) }}</span>
        <span>{{ confidenceLabel(confidence) }}</span>
        <span>{{ normalizedCitations.length }} 条证据片段</span>
      </div>
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
    margin: 0.42rem 0 0 0.35rem;
  }

  .citation-strip {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.32rem;
  }

  .source-toggle,
  .citation-markers button {
    border: 1px solid rgba(148, 163, 184, 0.22);
    background: rgba(248, 250, 252, 0.82);
    color: #475569;
    cursor: pointer;
    transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
  }

  .source-toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    height: 1.52rem;
    max-width: min(19rem, 72vw);
    padding: 0 0.52rem 0 0.28rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 650;

    .source-count {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.02rem;
      height: 1.02rem;
      border-radius: 999px;
      background: #eef2ff;
      color: #4f46e5;
      font-size: 0.66rem;
    }

    strong {
      min-width: 0;
      overflow: hidden;
      color: #64748b;
      font-size: 0.68rem;
      font-weight: 550;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    &:hover {
      border-color: rgba(79, 70, 229, 0.32);
      background: #fff;
      transform: translateY(-1px);
    }
  }

  .citation-markers {
    display: inline-flex;
    align-items: center;
    gap: 0.18rem;

    button {
      display: inline-grid;
      width: 1.32rem;
      height: 1.32rem;
      place-items: center;
      padding: 0;
      border-radius: 50%;
      color: #4f46e5;
      background: #fff;
      font-size: 0.66rem;
      font-weight: 750;
    }

    button:hover {
      border-color: rgba(79, 70, 229, 0.32);
      background: #fff;
    }

    span {
      color: #94a3b8;
      font-size: 0.68rem;
      font-weight: 700;
    }
  }

  .meta-pill {
    display: inline-flex;
    align-items: center;
    height: 1.52rem;
    padding: 0 0.52rem;
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.06);
    color: #475569;
    font-size: 0.72rem;
    font-weight: 650;
  }

  .citation-detail-list {
    display: flex;
    flex-direction: column;
    gap: 0.42rem;
    max-width: min(860px, 100%);
    margin-top: 0.46rem;
  }

  .citation-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 0.32rem;

    span {
      padding: 0.12rem 0.42rem;
      border-radius: 999px;
      background: #f8fafc;
      color: #64748b;
      font-size: 0.68rem;
      font-weight: 650;
    }
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

  .citation-snippet :deep(hr),
  .citation-reason :deep(hr) {
    display: none !important;
  }
</style>
