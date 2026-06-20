<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useSettingStore } from '@/store/setting';
  import {
    isCitationHintScope,
    normalizeCitationScope,
    stripInlineCitationMarkers,
  } from '@/utils/citationDisplay';
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
    citationHints?: CitationItem[];
    confidence?: string;
    groundingMode?: string;
    metrics?: Record<string, any>;
    showEmptyState?: boolean;
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

  const evidenceLabel = (count: number) => `${count} 段证据`;

  const scopeLabel = (item: CitationItem) => {
    const raw = normalizeCitationScope(item.context_scope);
    if (raw === 'uploaded_document') {
      return '当前文件';
    }
    if (raw === 'knowledge_base') {
      return '课程库';
    }
    if (raw === 'course_resource') {
      return '课程资料';
    }
    if (raw === 'resource_hint') {
      return '入口线索';
    }
    if (raw === 'route_file_hint') {
      return '文件线索';
    }
    if (raw === 'course') {
      return '课程上下文';
    }
    if (raw === 'route_context') {
      return '入口上下文';
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
    return [...(props.citations || []), ...(props.citationHints || [])]
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
          isHint: isCitationHintScope(item.context_scope),
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
  const realCitations = computed(() =>
    normalizedCitations.value.filter((item) => !item.isHint)
  );
  const contextHints = computed(() =>
    normalizedCitations.value.filter((item) => item.isHint)
  );
  const hasOnlyHints = computed(
    () => contextHints.value.length > 0 && !realCitations.value.length
  );
  const hasMixedEvidence = computed(
    () => contextHints.value.length > 0 && realCitations.value.length > 0
  );
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
          isHint: item.isHint,
          evidenceCount: 1,
          sourceKey: item.file_id || item.sourceLabel,
        });
        return;
      }
      if (!current.ids.includes(item.citation_id)) current.ids.push(item.citation_id);
      if (!current.locator && item.locator) current.locator = item.locator;
      if (!current.fileId && item.file_id) current.fileId = item.file_id;
      current.isHint = current.isHint && item.isHint;
      current.evidenceCount += 1;
      current.score = Math.max(current.score || 0, item.score || 0);
      current.displayIds = current.ids.join(', ');
    });
    return [...grouped.values()].sort((a, b) => {
      if (!a.isHint && b.isHint) return -1;
      if (a.isHint && !b.isHint) return 1;
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
    () => realCitations.value.filter((item) => item.scope === '当前文件').length
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

  const detailSummary = computed(() => {
    if (!normalizedCitations.value.length) return '';
    if (hasOnlyHints.value) {
      return `${contextHints.value.length} 条定位线索 / 非原文片段`;
    }
    const current = currentFileCitationCount.value
      ? `当前文件 ${currentFileCitationCount.value} 条`
      : '';
    const realSourceCount = new Set(
      realCitations.value.map((item) => `${item.scope || '资料'}-${item.sourceLabel}`)
    ).size;
    const sourceCount = `${realSourceCount} 个真实来源`;
    const evidenceCount = `${realCitations.value.length} 条原文片段`;
    const hintCount = contextHints.value.length
      ? `${contextHints.value.length} 条入口线索另列`
      : '';
    return [current, sourceCount, evidenceCount, hintCount].filter(Boolean).join(' / ');
  });

  const stripLabel = computed(() => {
    if (!normalizedCitations.value.length) return '未检索到可展示来源';
    if (hasOnlyHints.value) {
      const hasFileHint = contextHints.value.some(
        (item) => normalizeCitationScope(item.context_scope) === 'route_file_hint'
      );
      return hasFileHint ? '仅文件线索' : '仅入口线索';
    }
    if (hasMixedEvidence.value) return `真实引用 ${realCitations.value.length} 条 + 线索`;
    return `真实引用 ${realCitations.value.length} 条`;
  });

  const detailTitle = computed(() =>
    hasOnlyHints.value ? '入口线索' : '引用依据'
  );

  const detailModeLabel = computed(() => {
    if (hasOnlyHints.value) return '后端检索 0 条 · 非原文 · 需复核';
    if (hasMixedEvidence.value) return '真实引用优先';
    return groundingLabel(props.groundingMode);
  });

  const toggleLabel = computed(() => {
    if (expanded.value) return '收起';
    return hasOnlyHints.value ? '展开线索' : '展开依据';
  });

  const renderCitation = (value?: string) =>
    stripMarkdownCodeToolbar(renderMarkdown(cleanCitationText(value)));
</script>

<template>
  <div
    v-if="
      hasCitations ||
      showEmptyState ||
      (showDiagnostics && metrics?.agent_hops)
    "
    class="citation-area"
  >
    <div class="citation-strip" aria-label="回答引用来源">
      <span v-if="normalizedCitations.length" class="citation-strip__label">
        {{ stripLabel }}
      </span>
      <span v-else class="citation-strip__label citation-strip__label--empty">
        未检索到可展示来源
      </span>
      <button
        v-for="source in visibleSourceChips"
        :key="`${source.scope}-${source.sourceLabel}`"
        type="button"
        class="source-chip"
        :class="{ 'source-chip--hint': source.isHint }"
        :aria-expanded="expanded"
        :title="`${source.scope || '资料'} · ${source.sourceLabel}${source.isHint ? ' · 非原文 · 需复核' : ''}${source.locator ? ` · ${source.locator}` : ''}${source.fileId ? ` · file ${source.fileId}` : ''}`"
        @click="expanded = true"
      >
        <span class="source-chip__index">{{ source.displayIds }}</span>
        <strong>{{ source.sourceLabel }}</strong>
        <span class="source-chip__scope">
          <template v-if="source.isHint">
            {{ source.scope || '线索' }} · 非原文 · 需复核
          </template>
          <template v-else>
            {{ source.scope || '资料' }} · {{ evidenceLabel(source.evidenceCount) }}
          </template>
        </span>
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
        {{ toggleLabel }}
      </button>
      <span v-if="currentFileCitationCount" class="current-file-pill">
        当前文件 {{ currentFileCitationCount }}
      </span>
      <span v-if="hasOnlyHints" class="context-hint-pill">
        线索非原文
      </span>
      <span v-else-if="hasMixedEvidence" class="context-hint-pill context-hint-pill--soft">
        含入口线索
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
      <span v-if="showEmptyState && !normalizedCitations.length" class="meta-pill meta-pill--review">
        需复核
      </span>
    </div>

    <div v-if="expanded && normalizedCitations.length" class="citation-detail-list">
      <div class="citation-summary">
        <strong>{{ detailTitle }}</strong>
        <span>{{ detailModeLabel }}</span>
        <span>{{ confidenceLabel(confidence) }}</span>
        <span>{{ detailSummary }}</span>
      </div>
      <article
        v-for="item in normalizedCitations"
        :key="`${item.citation_id}-${item.source}-${item.chunk_id}`"
        :id="`citation-${item.citation_id}`"
        class="citation-detail"
        :class="{ 'citation-detail--hint': item.isHint }"
      >
        <span class="citation-detail__index">{{ item.citation_id }}</span>
        <div class="citation-detail__body">
          <div class="citation-detail__head">
            <strong>{{ item.sourceLabel }}</strong>
            <span v-if="item.scope">{{ item.scope }}</span>
          </div>
          <div v-if="item.isHint" class="citation-warning">
            此项是定位线索或文件预览，未作为 RAG 原文检索，不是后端检索到的完整原文片段。
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
        </div>
      </article>
    </div>
  </div>
</template>

<style scoped lang="scss">
  .citation-area {
    margin: 0.22rem 0 0 0.1rem;
  }

  .citation-strip {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.24rem;
  }

  .citation-strip__label {
    color: #9aa5b5;
    font-size: 0.64rem;
    font-weight: 650;
  }

  .citation-strip__label--empty {
    padding: 0.12rem 0.38rem;
    border-radius: 999px;
    background: #f8fafc;
    color: #8a94a6;
    box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.74);
  }

  .source-toggle,
  .source-chip {
    border: 0;
    background: transparent;
    color: #64748b;
    cursor: pointer;
    transition: background 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
  }

  .source-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.26rem;
    min-height: 1.28rem;
    max-width: min(18rem, 72vw);
    padding: 0.12rem 0.34rem;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 600;
    background: #f7f8fb;
    box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.7);

    .source-chip__index {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 0.96rem;
      height: 0.96rem;
      border-radius: 999px;
      background: #fff;
      color: #526071;
      font-size: 0.62rem;
      font-weight: 760;
      box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.75);
    }

    strong {
      min-width: 0;
      overflow: hidden;
      color: #475569;
      font-size: 0.68rem;
      font-weight: 620;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .source-chip__scope {
      color: #94a3b8;
      font-size: 0.62rem;
      white-space: nowrap;
    }

    &:hover {
      background: #eef2ff;
      color: #334155;
      box-shadow: inset 0 0 0 1px rgba(199, 210, 254, 0.9);
    }
  }

  .source-chip--hint {
    background: #fff7ed;
    box-shadow: inset 0 0 0 1px rgba(251, 191, 36, 0.28);

    .source-chip__index {
      color: #9a571d;
      background: #fffaf0;
      box-shadow: inset 0 0 0 1px rgba(251, 191, 36, 0.28);
    }

    .source-chip__scope {
      color: #b45309;
      font-weight: 760;
    }
  }

  .source-chip--more,
  .source-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 1.28rem;
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
    padding: 0.12rem 0.38rem;
    color: #64748b;
    background: transparent;

    &:hover {
      background: #eef2ff;
      color: #4f46e5;
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

  .meta-pill--review {
    height: 1.28rem;
    background: #fff7ed;
    color: #9a571d;
    box-shadow: inset 0 0 0 1px rgba(251, 191, 36, 0.24);
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

  .context-hint-pill {
    display: inline-flex;
    align-items: center;
    height: 1.28rem;
    padding: 0 0.48rem;
    border-radius: 999px;
    background: #fff7ed;
    color: #9a571d;
    font-size: 0.66rem;
    font-weight: 760;
    box-shadow: inset 0 0 0 1px rgba(251, 191, 36, 0.24);
  }

  .context-hint-pill--soft {
    background: #fffbeb;
    color: #a16207;
  }

  .citation-detail-list {
    display: flex;
    flex-direction: column;
    gap: 0;
    width: min(720px, calc(100vw - 56px));
    max-width: none;
    box-sizing: border-box;
    max-height: 22rem;
    margin-top: 0.34rem;
    overflow: auto;
    border: 1px solid rgba(226, 232, 240, 0.78);
    border-radius: 12px;
    background: rgba(248, 250, 252, 0.7);
  }

  @media (max-width: 640px) {
    .citation-area {
      margin-left: 0;
    }

    .citation-strip {
      align-items: flex-start;
    }

    .source-chip {
      max-width: 100%;
      min-height: 1.6rem;
    }

    .citation-detail-list {
      width: calc(100vw - 48px);
      max-height: min(18rem, 52vh);
      border-radius: 10px;
    }

    .citation-meta small {
      max-width: min(100%, 14rem);
    }
  }

  .citation-summary {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.32rem;
    padding: 0.48rem 0.62rem;
    border-bottom: 1px solid rgba(226, 232, 240, 0.78);

    strong {
      margin-right: 0.08rem;
      color: #1f2937;
      font-size: 0.74rem;
      font-weight: 760;
    }

    span {
      padding: 0.12rem 0.42rem;
      border-radius: 999px;
      background: #fff;
      color: #64748b;
      font-size: 0.68rem;
      font-weight: 650;
    }
  }

  .citation-detail {
    display: grid;
    grid-template-columns: 1.08rem minmax(0, 1fr);
    gap: 0.44rem;
    padding: 0.58rem 0.66rem;
    background: rgba(255, 255, 255, 0.92);

    & + .citation-detail {
      border-top: 1px solid rgba(226, 232, 240, 0.72);
    }
  }

  .citation-detail--hint {
    background: #fffaf3;
  }

  .citation-warning {
    margin: 0.12rem 0 0.28rem;
    padding: 0.28rem 0.42rem;
    border-radius: 8px;
    color: #9a571d;
    background: rgba(255, 247, 237, 0.9);
    font-size: 0.68rem;
    font-weight: 650;
    line-height: 1.45;
    box-shadow: inset 0 0 0 1px rgba(251, 191, 36, 0.22);
  }

  .citation-detail__index {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.02rem;
    height: 1.02rem;
    border-radius: 50%;
    background: #f8fafc;
    color: #64748b;
    font-size: 0.62rem;
    font-weight: 780;
  }

  .citation-detail__body {
    min-width: 0;
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
      background: #f4f6fa;
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
      background: rgba(241, 245, 249, 0.74);
      color: #64748b;
      font-size: 0.62rem;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .citation-snippet {
    color: #334155;
    font-size: 0.74rem;
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
