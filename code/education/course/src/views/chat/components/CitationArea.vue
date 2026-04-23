<script setup lang="ts">
  const props = defineProps<{
    citations?: Array<{
      citation_id: number;
      source: string;
      snippet: string;
      reason?: string;
      relevance_score?: number;
    }>;
    confidence?: string;
    groundingMode?: string;
    metrics?: Record<string, any>;
  }>();

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
</script>

<template>
  <div
    v-if="
      (citations && citations.length > 0) ||
      confidence ||
      groundingMode ||
      metrics?.agent_hops
    "
    class="citation-area"
  >
    <div class="citation-meta">
      <span v-if="groundingMode" class="meta-pill">
        {{ groundingLabel(groundingMode) }}
      </span>
      <span v-if="confidence" class="meta-pill">
        {{ confidenceLabel(confidence) }}
      </span>
      <span v-if="metrics?.agent_hops" class="meta-pill meta-pill--soft">
        {{ metrics.agent_hops }} 跳协作
      </span>
      <span v-if="metrics?.ttft_ms" class="meta-pill meta-pill--soft">
        TTFT {{ metrics.ttft_ms }}ms
      </span>
    </div>

    <div v-if="citations && citations.length > 0" class="citation-list">
      <div v-for="item in citations" :key="`${item.citation_id}-${item.source}`" class="citation-card">
        <div class="citation-head">
          <span class="citation-source">{{ item.source || `引用 ${item.citation_id}` }}</span>
          <span v-if="item.relevance_score" class="citation-score">
            相关度 {{ Number(item.relevance_score).toFixed(2) }}
          </span>
        </div>
        <div class="citation-snippet">{{ item.snippet }}</div>
        <div v-if="item.reason" class="citation-reason">{{ item.reason }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
  .citation-area {
    margin: 0.55rem 0 0 0.5rem;
  }

  .citation-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-bottom: 0.45rem;
  }

  .meta-pill {
    display: inline-flex;
    align-items: center;
    padding: 0.24rem 0.56rem;
    border-radius: 999px;
    background: rgba(99, 102, 241, 0.1);
    color: #4338ca;
    font-size: 0.76rem;
    font-weight: 600;

    &--soft {
      background: rgba(15, 23, 42, 0.06);
      color: #475569;
    }
  }

  .citation-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .citation-card {
    padding: 0.7rem 0.8rem;
    border-radius: 12px;
    border: 1px solid rgba(99, 102, 241, 0.12);
    background: rgba(255, 255, 255, 0.86);
    box-shadow: 0 8px 22px rgba(99, 102, 241, 0.08);
  }

  .citation-head {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.3rem;
    font-size: 0.78rem;
  }

  .citation-source {
    font-weight: 700;
    color: #0f172a;
  }

  .citation-score {
    color: #64748b;
    white-space: nowrap;
  }

  .citation-snippet {
    color: #334155;
    font-size: 0.82rem;
    line-height: 1.55;
  }

  .citation-reason {
    margin-top: 0.35rem;
    color: #6366f1;
    font-size: 0.76rem;
  }
</style>
