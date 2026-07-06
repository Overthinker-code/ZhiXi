<script setup lang="ts">
  import { computed, ref } from 'vue';

  const props = defineProps<{
    events: Array<Record<string, any>>;
    loading?: boolean;
  }>();

  const expanded = ref(false);
  const doneCount = computed(
    () => props.events.filter((item) => item.status === 'done').length
  );
  const running = computed(() =>
    props.events.find((item) => item.status === 'running')
  );
</script>

<template>
  <section v-if="events.length || loading" class="tool-trace">
    <button type="button" class="tool-trace__summary" @click="expanded = !expanded">
      <span :class="['tool-dot', { 'is-running': loading || running }]" />
      <span>
        {{
          running
            ? running.label
            : `已完成 ${doneCount || events.length} 个步骤`
        }}
      </span>
      <strong>{{ expanded ? '收起' : '查看过程' }}</strong>
    </button>
    <ol v-if="expanded" class="tool-trace__steps">
      <li v-for="(item, index) in events" :key="`${item.agent || item.label}-${index}`">
        <span :class="['step-state', item.status || 'done']" />
        <div>
          <strong>{{ item.agent || item.source || `步骤 ${index + 1}` }}</strong>
          <p>{{ item.label || item.summary || item.message || '已完成' }}</p>
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
