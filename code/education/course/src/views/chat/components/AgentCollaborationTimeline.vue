<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { AGENT_LABELS } from '@/utils/agentDisplay';
  import { renderMarkdown, stripMarkdownCodeToolbar } from '@/utils/markdown';

  export type AgentPhase = {
    phase: string;
    agent: string;
    summary: string;
    status?: string;
  };

  const props = defineProps<{
    phases?: AgentPhase[];
    thoughts?: string[];
    streaming?: boolean;
    metrics?: Record<string, unknown>;
  }>();

  const expanded = ref(false);

  const PHASE_LABELS: Record<string, string> = {
    understand: '理解意图',
    retrieve: '检索证据',
    research: '联网补充',
    analyze: '学情分析',
    quiz: '测验出题',
    code: '代码辅导',
    execute: '工具执行',
    perceive: '视觉理解',
    plan: '策略规划',
    process: '协作处理',
    finalize: '汇总答复',
  };

  const normalizedPhases = computed<AgentPhase[]>(() => {
    if (props.phases?.length) {
      return props.phases;
    }
    const seen = new Set<string>();
    const out: AgentPhase[] = [];
    for (const raw of props.thoughts || []) {
      const m = String(raw).match(/^【([^】]+)】([\s\S]*)$/);
      const tag = m?.[1]?.trim() || '协作';
      const summary = (m?.[2] || raw).trim().slice(0, 120);
      const key = `${tag}:${summary.slice(0, 40)}`;
      if (seen.has(key)) continue;
      seen.add(key);
      let phase = 'process';
      let agent = 'supervisor';
      if (/检索|RAG|知识|文档/.test(tag)) {
        phase = 'retrieve';
        agent = 'retrieval_agent';
      } else if (/联网|web/i.test(tag)) {
        phase = 'research';
        agent = 'web_research_agent';
      } else if (/汇总|审查|安全/.test(tag)) {
        phase = 'finalize';
        agent = 'safety_review_agent';
      } else if (/主管|流水线|策略/.test(tag)) {
        phase = 'understand';
        agent = 'supervisor';
      }
      out.push({ phase, agent, summary: summary || tag, status: 'done' });
    }
    return out.slice(-6);
  });

  const agentCount = computed(() => {
    return new Set(normalizedPhases.value.map((p) => p.agent)).size;
  });

  const roundCount = computed(() => {
    const hops = props.metrics?.agent_hops;
    if (typeof hops === 'number' && hops > 0) return hops;
    return Math.max(1, normalizedPhases.value.length);
  });

  const capsuleText = computed(() => {
    if (props.streaming) return '多智能体协作中…';
    return `协作 ${roundCount.value} 轮 · 涉及 ${agentCount.value} 个智能体`;
  });

  function agentLabel(key: string) {
    return AGENT_LABELS[key] || key;
  }

  function phaseLabel(key: string) {
    return PHASE_LABELS[key] || key;
  }

  function renderSummary(value: string) {
    return stripMarkdownCodeToolbar(renderMarkdown(value || ''));
  }
</script>

<template>
  <div v-if="normalizedPhases.length || streaming" class="act">
    <button type="button" class="act-capsule" @click="expanded = !expanded">
      <span class="act-dot" :class="{ 'act-dot--live': streaming }" />
      <span>{{ capsuleText }}</span>
      <span class="act-hint">{{ expanded ? '收起' : '展开' }}</span>
    </button>

    <Transition name="act-slide">
      <div v-show="expanded" class="act-timeline">
        <div
          v-for="(item, idx) in normalizedPhases"
          :key="`${item.phase}-${idx}`"
          class="act-item"
        >
          <div class="act-rail">
            <span class="act-node" />
            <span v-if="idx < normalizedPhases.length - 1" class="act-line" />
          </div>
          <div class="act-content">
            <div class="act-meta">
              <span class="act-phase">{{ phaseLabel(item.phase) }}</span>
              <span class="act-agent">{{ agentLabel(item.agent) }}</span>
            </div>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div class="act-summary" v-html="renderSummary(item.summary)" />
          </div>
        </div>
        <p v-if="streaming" class="act-streaming">正在等待下一阶段…</p>
      </div>
    </Transition>
  </div>
</template>

<style scoped lang="less">
  .act {
    margin: 6px 0 10px;
  }

  .act-capsule {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border-radius: 999px;
    border: 1px solid var(--color-border-2, #e5e6eb);
    background: var(--color-bg-2, #fff);
    color: var(--color-text-2, #4e5969);
    font-size: 12px;
    cursor: pointer;
    transition: border-color 0.2s, box-shadow 0.2s;

    &:hover {
      border-color: rgb(var(--primary-6, 22, 93, 255));
      box-shadow: 0 2px 8px rgba(22, 93, 255, 0.08);
    }
  }

  .act-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--color-text-4, #c9cdd4);

    &--live {
      background: rgb(var(--primary-6, 22, 93, 255));
      animation: act-pulse 1.2s ease-in-out infinite;
    }
  }

  .act-hint {
    opacity: 0.55;
    margin-left: 4px;
  }

  .act-timeline {
    margin-top: 10px;
    padding: 12px 14px;
    border-radius: 10px;
    border: 1px solid var(--color-border-2, #e5e6eb);
    background: var(--color-fill-1, #f7f8fa);
  }

  .act-summary :deep(p) {
    margin: 0;
  }

  .act-item {
    display: flex;
    gap: 10px;
  }

  .act-rail {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 12px;
    flex-shrink: 0;
  }

  .act-node {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: rgb(var(--primary-6, 22, 93, 255));
    margin-top: 5px;
  }

  .act-line {
    flex: 1;
    width: 2px;
    min-height: 20px;
    background: var(--color-border-2, #e5e6eb);
    margin: 4px 0;
  }

  .act-content {
    flex: 1;
    padding-bottom: 12px;
  }

  .act-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  }

  .act-phase {
    font-size: 12px;
    font-weight: 600;
    color: var(--color-text-1, #1d2129);
  }

  .act-agent {
    font-size: 11px;
    color: rgb(var(--primary-6, 22, 93, 255));
    background: rgba(var(--primary-6, 22, 93, 255), 0.08);
    padding: 1px 6px;
    border-radius: 4px;
  }

  .act-summary {
    margin: 0;
    font-size: 12px;
    line-height: 1.55;
    color: var(--color-text-3, #86909c);
  }

  .act-streaming {
    margin: 4px 0 0 22px;
    font-size: 12px;
    color: var(--color-text-4, #c9cdd4);
  }

  .act-slide-enter-active,
  .act-slide-leave-active {
    transition: opacity 0.2s ease, transform 0.2s ease;
  }

  .act-slide-enter-from,
  .act-slide-leave-to {
    opacity: 0;
    transform: translateY(-4px);
  }

  @keyframes act-pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.35;
    }
  }
</style>
