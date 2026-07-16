<template>
  <div class="agent-stage">
    <div class="agent-stage__nodes">
      <div
        v-for="(node, index) in nodes"
        :key="node.key"
        class="agent-stage__node"
        :class="[
          `agent-stage__node--${node.status || 'idle'}`,
          { 'zy-node-pulse': node.status === 'running' },
        ]"
      >
        <div class="agent-stage__node-icon">
          <icon-check v-if="node.status === 'done'" />
          <icon-close v-else-if="node.status === 'error'" />
          <span v-else-if="node.status === 'running'" class="agent-stage__spinner" />
          <span v-else>{{ index + 1 }}</span>
        </div>
        <div class="agent-stage__node-label">{{ node.label }}</div>
        <div v-if="node.sub" class="agent-stage__node-sub">{{ node.sub }}</div>
      </div>
    </div>
    <svg
      v-if="nodes.length > 1"
      class="agent-stage__connectors"
      :viewBox="`0 0 ${connectorWidth} 40`"
      preserveAspectRatio="none"
    >
      <line
        v-for="(seg, i) in connectorSegments"
        :key="i"
        :x1="seg.x1"
        y1="20"
        :x2="seg.x2"
        y2="20"
        :class="['agent-stage__line', { 'agent-stage__line--active': seg.active }]"
      />
    </svg>
    <div v-if="currentMessage" class="agent-stage__message">
      {{ currentMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue';

  export type AgentNodeStatus = 'idle' | 'running' | 'done' | 'error';

  export interface AgentStageNode {
    key: string;
    label: string;
    sub?: string;
    status?: AgentNodeStatus;
    message?: string;
  }

  const props = defineProps<{
    nodes: AgentStageNode[];
  }>();

  const connectorWidth = computed(() => Math.max(200, props.nodes.length * 120));

  const connectorSegments = computed(() => {
    const n = props.nodes.length;
    if (n < 2) return [];
    const segW = connectorWidth.value / n;
    return Array.from({ length: n - 1 }, (_, i) => ({
      x1: segW * (i + 0.75),
      x2: segW * (i + 1.25),
      active: props.nodes[i]?.status === 'done',
    }));
  });

  const currentMessage = computed(() => {
    const running = props.nodes.find((n) => n.status === 'running');
    if (running?.message) return running.message;
    const lastDone = [...props.nodes].reverse().find((n) => n.status === 'done');
    return lastDone?.message || '';
  });
</script>

<style scoped lang="less">
  .agent-stage {
    position: relative;
    padding: 16px 0;
  }

  .agent-stage__nodes {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    position: relative;
    z-index: 1;
  }

  .agent-stage__node {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    min-width: 0;
  }

  .agent-stage__node-icon {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 600;
    background: #f1f5f9;
    color: #94a3b8;
    border: 2px solid #e2e8f0;
    margin-bottom: 8px;
    transition: all var(--zy-duration-normal, 280ms) ease;
  }

  .agent-stage__node--running .agent-stage__node-icon {
    background: #eef2ff;
    border-color: #6366f1;
    color: #6366f1;
  }

  .agent-stage__node--done .agent-stage__node-icon {
    background: #6366f1;
    border-color: #6366f1;
    color: #fff;
  }

  .agent-stage__node--error .agent-stage__node-icon {
    background: #fef2f2;
    border-color: #ef4444;
    color: #ef4444;
  }

  .agent-stage__node-label {
    font-size: 12px;
    font-weight: 600;
    color: #0f172a;
    line-height: 1.3;
  }

  .agent-stage__node--idle .agent-stage__node-label {
    color: #94a3b8;
  }

  .agent-stage__node-sub {
    font-size: 10px;
    color: #64748b;
    margin-top: 2px;
  }

  .agent-stage__connectors {
    position: absolute;
    top: 34px;
    left: 0;
    width: 100%;
    height: 40px;
    z-index: 0;
    pointer-events: none;
  }

  .agent-stage__line {
    stroke: #e2e8f0;
    stroke-width: 2;
    transition: stroke var(--zy-duration-normal, 280ms) ease;
  }

  .agent-stage__line--active {
    stroke: #6366f1;
  }

  .agent-stage__message {
    margin-top: 12px;
    padding: 8px 12px;
    background: #f8fafc;
    border-radius: 8px;
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
    color: #64748b;
    text-align: center;
  }

  .agent-stage__spinner {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(99, 102, 241, 0.25);
    border-top-color: #6366f1;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
