<script setup lang="ts">
  import { computed, ref } from 'vue';

  const props = defineProps<{
    events: Array<Record<string, any>>;
    loading?: boolean;
  }>();

  const expanded = ref(false);
  const internalAgents = new Set(['intent_classifier', 'course_context']);
  const INTERNAL_LABEL_RE =
    /(intent_classifier|course_context|deep_research|首条系统消息|系统消息|数据库系统原理|第\s*\d+\s*章|ER\s*模型)/i;
  const stageLabelMap: Record<string, string> = {
    course_retriever: '检索课程资料',
    course: '检索课程资料',
    web_search: '联网搜索',
    web: '联网搜索',
    resource_planner: '规划资源',
    resource_generator: '生成资源包',
    safety_check: '校验引用',
    memory_update: '更新学习画像',
    attachment_parser: '解析附件',
  };
  const normalizeAgent = (item: Record<string, any>) =>
    String(item.agent || item.source || '').trim();
  const visibleEvents = computed(() =>
    props.events.filter((item) => !internalAgents.has(normalizeAgent(item)))
  );
  const friendlyLabel = (item: Record<string, any>, index = 0) => {
    const key = normalizeAgent(item);
    if (key === 'deep_research') return '深度研究';
    if (stageLabelMap[key]) return stageLabelMap[key];
    const label = String(item.label || item.summary || item.message || '').trim();
    if (INTERNAL_LABEL_RE.test(label)) {
      if (/检索|知识库|资料/.test(label)) return '检索资料';
      if (/研究|deep_research/i.test(label)) return '深度研究';
      return `处理步骤 ${index + 1}`;
    }
    if (/检索/.test(label)) return '检索资料';
    if (/联网|搜索/.test(label)) return '联网搜索';
    if (/研究|报告/.test(label)) return '深度研究';
    if (/资源/.test(label)) return '生成资源';
    if (/画像/.test(label)) return '更新学习画像';
    if (/安全|校验|引用/.test(label)) return '校验引用';
    return `处理步骤 ${index + 1}`;
  };
  const running = computed(() =>
    visibleEvents.value.find((item) => item.status === 'running')
  );
  const summaryText = computed(() => {
    if (running.value) return `正在${friendlyLabel(running.value)}`;
    return visibleEvents.value.length ? '已整理好回答依据' : '正在分析问题';
  });
  const statusLabel = (status: string | undefined) => {
    if (status === 'running') return '进行中';
    if (status === 'error') return '处理失败';
    return '已完成';
  };
</script>

<template>
  <section v-if="visibleEvents.length || loading" class="tool-trace">
    <button type="button" class="tool-trace__summary" @click="expanded = !expanded">
      <span :class="['tool-dot', { 'is-running': loading || running }]" />
      <span>{{ summaryText }}</span>
      <strong>{{ expanded ? '收起' : '查看过程' }}</strong>
    </button>
    <ol v-if="expanded" class="tool-trace__steps">
      <li v-for="(item, index) in visibleEvents" :key="`${normalizeAgent(item) || index}-${index}`">
        <span :class="['step-state', item.status || 'done']" />
        <div>
          <strong>{{ friendlyLabel(item, index) }}</strong>
          <p>{{ statusLabel(item.status) }}</p>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped lang="scss">
  .tool-trace {
    margin-top: 12px;
  }

  .tool-trace__summary {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    height: 32px;
    padding: 0 12px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 999px;
    background: #fff;
    color: #667085;
    cursor: pointer;

    strong {
      color: #4f46e5;
      font-weight: 700;
    }
  }

  .tool-dot,
  .step-state {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #12b76a;
  }

  .tool-dot.is-running,
  .step-state.running {
    background: #6366f1;
    animation: pulse 1.1s ease-in-out infinite;
  }

  .step-state.error {
    background: #f04438;
  }

  .tool-trace__steps {
    display: grid;
    gap: 10px;
    margin: 10px 0 0;
    padding: 12px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 14px;
    background: #f8faff;
    list-style: none;

    li {
      display: grid;
      grid-template-columns: 10px 1fr;
      gap: 10px;
      align-items: start;
    }

    strong {
      color: #344054;
      font-size: 13px;
    }

    p {
      margin: 2px 0 0;
      color: #667085;
      font-size: 13px;
      line-height: 1.5;
    }
  }

  @keyframes pulse {
    0%, 100% {
      box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.25);
    }
    50% {
      box-shadow: 0 0 0 5px rgba(99, 102, 241, 0);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .tool-dot.is-running,
    .step-state.running {
      animation: none;
    }
  }
</style>
