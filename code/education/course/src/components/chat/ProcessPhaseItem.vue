<script setup lang="ts">
  import { computed } from 'vue';
  import {
    Check,
    CircleAlert,
    FileSearch,
    ListTree,
    LoaderCircle,
    Route,
    ShieldCheck,
    Sparkles,
    Square,
    Wrench,
  } from 'lucide-vue-next';

  const props = defineProps<{
    title: string;
    text: string;
    status?: 'pending' | 'running' | 'done' | 'error' | string;
    active?: boolean;
    category?: string;
    durationMs?: number;
    itemCount?: number;
  }>();

  const icon = computed(() => {
    if (props.status === 'error') return CircleAlert;
    if (['cancelled', 'stopped'].includes(String(props.status))) return Square;
    if (props.status === 'running' || props.active) return LoaderCircle;
    if (props.category === 'retrieval') return FileSearch;
    if (props.category === 'tool') return Wrench;
    if (props.category === 'safety') return ShieldCheck;
    if (props.category === 'route') return Route;
    if (props.category === 'plan') return ListTree;
    if (props.category === 'model' || props.category === 'output') return Sparkles;
    return Check;
  });

  const duration = computed(() => {
    const value = Number(props.durationMs || 0);
    if (!value) return '';
    if (value < 1000) return `${Math.round(value)}ms`;
    return `${(value / 1000).toFixed(value < 10000 ? 1 : 0)}s`;
  });
</script>

<template>
  <article class="trace-step" :class="[`is-${status || 'pending'}`, { 'is-active': active }]">
    <span class="trace-step__icon">
      <component :is="icon" :size="15" :stroke-width="2" />
    </span>
    <div class="trace-step__content">
      <div class="trace-step__heading">
        <strong>{{ title }}</strong>
        <span v-if="status === 'running'" class="trace-step__state">进行中</span>
        <span v-else-if="status === 'error'" class="trace-step__state">未完成</span>
        <span v-else-if="status === 'cancelled' || status === 'stopped'" class="trace-step__state">已停止</span>
        <span v-if="itemCount" class="trace-step__meta">{{ itemCount }} 项</span>
        <time v-if="duration">{{ duration }}</time>
      </div>
      <p v-if="text">{{ text }}</p>
    </div>
  </article>
</template>

<style scoped lang="scss">
  .trace-step {
    position: relative;
    display: grid;
    grid-template-columns: 28px minmax(0, 1fr);
    gap: 10px;
    padding: 8px 0;
    color: #667085;

    &:not(:last-child)::after {
      position: absolute;
      top: 36px;
      bottom: -8px;
      left: 13px;
      width: 1px;
      background: #e4e7ec;
      content: '';
    }
  }

  .trace-step__icon {
    position: relative;
    z-index: 1;
    display: inline-flex;
    width: 28px;
    height: 28px;
    align-items: center;
    justify-content: center;
    border: 1px solid #e4e7ec;
    border-radius: 9px;
    background: #fff;
    color: #667085;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
  }

  .trace-step__content {
    min-width: 0;
    padding-top: 3px;
  }

  .trace-step__heading {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 7px;

    strong {
      overflow: hidden;
      color: #344054;
      font-size: 13px;
      font-weight: 650;
      line-height: 1.4;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    time,
    .trace-step__meta {
      color: #98a2b3;
      font-size: 11px;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }

    time {
      margin-left: auto;
    }
  }

  .trace-step__state {
    flex: 0 0 auto;
    padding: 1px 6px;
    border-radius: 999px;
    background: #eef2ff;
    color: #4f46e5;
    font-size: 10px;
    line-height: 17px;
  }

  p {
    margin: 3px 0 0;
    overflow: hidden;
    color: #667085;
    font-size: 12px;
    line-height: 1.55;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .is-running .trace-step__icon,
  .is-active .trace-step__icon {
    border-color: rgba(79, 70, 229, 0.2);
    background: #f5f6ff;
    color: #4f46e5;

    :deep(svg) {
      animation: trace-spin 1.4s linear infinite;
    }
  }

  .is-error .trace-step__icon {
    border-color: rgba(217, 45, 32, 0.18);
    background: #fff6f5;
    color: #d92d20;
  }

  .is-cancelled .trace-step__icon,
  .is-stopped .trace-step__icon {
    border-color: #e4e7ec;
    background: #f2f4f7;
    color: #667085;
  }

  .is-cancelled .trace-step__state,
  .is-stopped .trace-step__state {
    background: #e9eaed;
    color: #667085;
  }

  .is-error .trace-step__state {
    background: #fff1f0;
    color: #b42318;
  }

  @keyframes trace-spin {
    to { transform: rotate(360deg); }
  }

  @media (prefers-reduced-motion: reduce) {
    .trace-step__icon :deep(svg) { animation: none !important; }
  }
</style>
