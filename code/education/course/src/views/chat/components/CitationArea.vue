<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useSettingStore } from '@/store/setting';
  import { normalizeCitationScope, stripInlineCitationMarkers } from '@/utils/citationDisplay';
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
  const cleanCitationText = (value?: string) =>
    stripInlineCitationMarkers(
      String(value || '')
        .replace(/<hr\s*\/?>/gi, '\n')
    )
      .split('\n')
      .map((line) => line.replace(/[ \t]+$/g, ''))
      .filter((line) => {
        const trimmed = line.trim();
        if (!trimmed) return true;
        if (/^([-*_=])\1{2,}$/.test(trimmed)) return false;
        if (/^[＿_—─━―－﹘﹣]{3,}$/.test(trimmed)) return false;
        if (/^(?:\|\s*:?-{3,}:?\s*)+\|?$/.test(trimmed)) return false;
        return true;
      })
      .join('\n')
      .replace(/\n{3,}/g, '\n\n')
      .replace(/(?:^|\s)(?:[-*_=\u2014\u2015\u2500\u2501\uFF3F]){3,}(?=\s|$)/g, ' ')
      .replace(/\|\s*:?-{3,}:?\s*(?=\|)/g, '| ')
      .replace(/\s{2,}/g, ' ')
      .trim();

  const basename = (value?: string) =>
    String(value || '')
      .replace(/^.*[\\/]/, '')
      .trim();

  const shortId = (value?: string | number) => {
    const text = String(value || '');
    if (text.length <= 12) return text;
    return `${text.slice(0, 6)}…${text.slice(-4)}`;
  };

  const scopeLabel = (item: CitationItem) => {
    const raw = normalizeCitationScope(item.context_scope);
    if (raw === 'uploaded_document') {
      return '当前文件';
    }
    if (raw === 'knowledge_base') {
      return '课程库';
    }
    return item.file_id ? '资料' : '';
  };

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
        const sourceLabel = basename(source) || `来源 ${index + 1}`;
        const snippet = cleanCitationText(item.snippet);
        const reason = cleanCitationText(item.reason);
        const citationId = Number(item.citation_id ?? index + 1);
        return {
          ...item,
          citation_id: Number.isFinite(citationId) && citationId > 0 ? citationId : index + 1,
          sourceLabel,
          locator: locator || '',
          scope: scopeLabel(item),
          snippet,
          reason,
          score: normalizeScore(item),
        };
      })
      .filter((item) => {
        const key = [
          item.file_id || item.sourceLabel,
          item.chunk_id || item.locator,
          item.snippet.slice(0, 90),
        ].join('|');
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
          fileId: item.file_id,
          evidenceCount: 1,
        });
        return;
      }
      if (!current.ids.includes(item.citation_id)) current.ids.push(item.citation_id);
      if (!current.locator && item.locator) current.locator = item.locator;
      if (!current.fileId && item.file_id) current.fileId = item.file_id;
      current.evidenceCount += 1;
      current.score = Math.max(current.score || 0, item.score || 0);
      current.displayIds = current.ids.join(', ');
    });
    return [...grouped.values()].sort((a, b) => {
      if (a.scope === '当前文件' && b.scope !== '当前文件') return -1;
      if (b.scope === '当前文件' && a.scope !== '当前文件') return 1;
      return (b.score || 0) - (a.score || 0);
    });
  });
  const visibleSourceChips = computed(() => compactSources.value.slice(0, 3));
  const hiddenSourceCount = computed(() =>
    Math.max(0, compactSources.value.length - visibleSourceChips.value.length)
  );
  const currentFileCitationCount = computed(
    () => normalizedCitations.value.filter((item) => item.scope === '当前文件').length
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
    stripMarkdownCodeToolbar(renderMarkdown(cleanCitationText(value)));
</script>

<template>
  <div
    v-if="
      hasCitations ||
      (showDiagnostics && metrics?.agent_hops)
    "
    class="citation-area"
  >
    <div class="citation-strip" aria-label="回答引用来源">
      <button
        v-for="source in visibleSourceChips"
        :key="`${source.scope}-${source.sourceLabel}`"
        type="button"
        class="source-chip"
        :aria-expanded="expanded"
        :title="`${source.scope || '资料'} · ${source.sourceLabel}${source.locator ? ` · ${source.locator}` : ''}`"
        @click="expanded = true"
      >
        <span class="source-chip__index">[{{ source.displayIds }}]</span>
        <strong>{{ source.sourceLabel }}</strong>
        <span v-if="source.scope" class="source-chip__scope">{{ source.scope }}</span>
      </button>
      <button
        v-if="hiddenSourceCount"
        type="button"
        class="source-chip source-chip--more"
        :aria-expanded="expanded"
        @click="expanded = true"
      >
        +{{ hiddenSourceCount }}
      </button>
      <button
        v-if="normalizedCitations.length"
        type="button"
        class="source-toggle"
        :aria-expanded="expanded"
        @click="expanded = !expanded"
      >
        {{ expanded ? '收起依据' : `查看 ${normalizedCitations.length} 条依据` }}
      </button>
      <span v-if="currentFileCitationCount" class="current-file-pill">
        当前文件 {{ currentFileCitationCount }}
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

    <div v-if="expanded && normalizedCitations.length" class="citation-detail-list">
      <div class="citation-summary">
        <strong>引用依据</strong>
        <span>{{ groundingLabel(groundingMode) }}</span>
        <span>{{ confidenceLabel(confidence) }}</span>
        <span>{{ compactSources.length }} 个来源 / {{ normalizedCitations.length }} 条片段</span>
      </div>
      <article
        v-for="item in normalizedCitations"
        :key="`${item.citation_id}-${item.source}-${item.chunk_id}`"
        :id="`citation-${item.citation_id}`"
        class="citation-detail"
      >
        <span class="citation-detail__index">{{ item.citation_id }}</span>
        <div class="citation-detail__head">
          <strong>{{ item.sourceLabel }}</strong>
          <span v-if="item.scope">{{ item.scope }}</span>
        </div>
        <div class="citation-meta">
          <small v-if="item.locator">{{ item.locator }}</small>
          <small v-if="item.chunk_id">chunk {{ item.chunk_id }}</small>
          <small v-if="item.file_id">file {{ shortId(item.file_id) }}</small>
          <small v-if="item.score">相关度 {{ item.score.toFixed(2) }}</small>
        </div>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="citation-snippet" v-html="renderCitation(item.snippet)" />
        <details v-if="item.reason" class="citation-reason">
          <summary>匹配原因</summary>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div v-html="renderCitation(item.reason)" />
        </details>
      </article>
    </div>
  </div>
</template>

<style scoped lang="scss">
  .citation-area {
    margin: 0.36rem 0 0 0.2rem;
  }

  .citation-strip {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.32rem;
  }

  .source-toggle,
  .source-chip {
    border: 1px solid rgba(203, 213, 225, 0.72);
    background: rgba(255, 255, 255, 0.82);
    color: #475569;
    cursor: pointer;
    transition: border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
  }

  .source-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.24rem;
    height: 1.42rem;
    max-width: min(15.5rem, 68vw);
    padding: 0 0.48rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 600;

    .source-chip__index {
      color: #4f46e5;
      font-weight: 760;
    }

    strong {
      min-width: 0;
      overflow: hidden;
      color: #334155;
      font-size: 0.68rem;
      font-weight: 620;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .source-chip__scope {
      color: #64748b;
      font-size: 0.64rem;
    }

    &:hover {
      border-color: rgba(79, 70, 229, 0.32);
      background: rgba(248, 250, 255, 0.98);
      color: #334155;
    }
  }

  .source-chip--more,
  .source-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 1.42rem;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 650;
  }

  .source-chip--more {
    min-width: 2rem;
    padding: 0 0.48rem;
    color: #64748b;
  }

  .source-toggle {
    padding: 0 0.5rem;
    color: #64748b;

    &:hover {
      border-color: rgba(79, 70, 229, 0.3);
      background: #fff;
    }
  }

  .meta-pill {
    display: inline-flex;
    align-items: center;
    height: 1.42rem;
    padding: 0 0.52rem;
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.045);
    color: #475569;
    font-size: 0.68rem;
    font-weight: 650;
  }

  .current-file-pill {
    display: inline-flex;
    align-items: center;
    height: 1.42rem;
    padding: 0 0.46rem;
    border-radius: 999px;
    background: #ecfdf5;
    color: #047857;
    font-size: 0.68rem;
    font-weight: 750;
    box-shadow: inset 0 0 0 1px rgba(16, 185, 129, 0.18);
  }

  .citation-detail-list {
    display: flex;
    flex-direction: column;
    gap: 0;
    max-width: min(760px, 100%);
    max-height: 24rem;
    margin-top: 0.48rem;
    overflow: auto;
    border: 1px solid rgba(226, 232, 240, 0.92);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.96);
  }

  .citation-summary {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.32rem;
    padding: 0.56rem 0.68rem;
    border-bottom: 1px solid rgba(226, 232, 240, 0.78);

    strong {
      margin-right: 0.08rem;
      color: #0f172a;
      font-size: 0.76rem;
      font-weight: 760;
    }

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
    display: grid;
    grid-template-columns: 1.32rem minmax(0, 1fr);
    gap: 0.48rem;
    padding: 0.66rem 0.72rem;
    background: #fff;

    & + .citation-detail {
      border-top: 1px solid rgba(226, 232, 240, 0.72);
    }
  }

  .citation-detail__index {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.18rem;
    height: 1.18rem;
    border-radius: 50%;
    background: #f1f5ff;
    color: #4f46e5;
    font-size: 0.66rem;
    font-weight: 780;
  }

  .citation-detail__head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.28rem;
    min-width: 0;
    margin-bottom: 0.2rem;

    strong {
      min-width: 0;
      overflow: hidden;
      color: #0f172a;
      font-size: 0.76rem;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      padding: 0.1rem 0.32rem;
      border-radius: 999px;
      background: #f8fafc;
      color: #475569;
      font-size: 0.62rem;
      font-weight: 650;
    }
  }

  .citation-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.26rem;
    margin-bottom: 0.28rem;

    small {
      max-width: 12rem;
      overflow: hidden;
      padding: 0.08rem 0.3rem;
      border-radius: 999px;
      background: rgba(241, 245, 249, 0.86);
      color: #64748b;
      font-size: 0.62rem;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .citation-snippet {
    color: #334155;
    font-size: 0.76rem;
    line-height: 1.55;
  }

  .citation-reason {
    margin-top: 0.28rem;
    color: #64748b;
    font-size: 0.72rem;

    summary {
      width: fit-content;
      cursor: pointer;
      color: #4f46e5;
      font-size: 0.68rem;
      font-weight: 650;
    }
  }

  .citation-snippet :deep(p),
  .citation-reason :deep(p) {
    margin: 0;
  }

  .citation-snippet :deep(hr),
  .citation-reason :deep(hr) {
    display: none !important;
  }

  .citation-snippet :deep(pre),
  .citation-reason :deep(pre) {
    max-width: 100%;
    overflow-x: auto;
    padding: 0.45rem 0.55rem;
    border-radius: 8px;
    background: #f8fafc;
    color: #334155;
    font-size: 0.68rem;
  }

  .citation-snippet :deep(table),
  .citation-reason :deep(table) {
    display: block;
    max-width: 100%;
    overflow-x: auto;
    border-collapse: collapse;
    font-size: 0.68rem;
  }

  .citation-snippet :deep(th),
  .citation-snippet :deep(td),
  .citation-reason :deep(th),
  .citation-reason :deep(td) {
    padding: 0.24rem 0.36rem;
    border: 1px solid rgba(226, 232, 240, 0.82);
  }
</style>
