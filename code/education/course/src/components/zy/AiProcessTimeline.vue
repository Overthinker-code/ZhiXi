<template>
  <div class="ai-timeline" :class="{ 'ai-timeline--compact': compact }">
    <div
      v-for="(step, index) in steps"
      :key="step.key || index"
      class="ai-timeline__item"
      :class="`ai-timeline__item--${step.status || 'idle'}`"
    >
      <div class="ai-timeline__track">
        <div
          class="ai-timeline__dot"
          :class="{ 'zy-node-pulse': step.status === 'running' }"
        >
          <icon-check v-if="step.status === 'done'" />
          <icon-close v-else-if="step.status === 'error'" />
          <span v-else-if="step.status === 'running'" class="ai-timeline__spinner" />
          <span v-else class="ai-timeline__idle-num">{{ index + 1 }}</span>
        </div>
        <div
          v-if="index < steps.length - 1"
          class="ai-timeline__line"
          :class="{ 'ai-timeline__line--active': step.status === 'done' }"
        />
      </div>
      <div class="ai-timeline__content">
        <div class="ai-timeline__label">{{ step.label }}</div>
        <div v-if="step.message" class="ai-timeline__message">{{ step.message }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  export type TimelineStepStatus = 'idle' | 'running' | 'done' | 'error';

  export interface TimelineStep {
    key?: string;
    label: string;
    message?: string;
    status?: TimelineStepStatus;
  }

  withDefaults(
    defineProps<{
      steps: TimelineStep[];
      compact?: boolean;
    }>(),
    {
      compact: false,
    }
  );
</script>

<style scoped lang="less">
  .ai-timeline {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .ai-timeline__item {
    display: flex;
    gap: 12px;
    min-height: 52px;
  }

  .ai-timeline--compact .ai-timeline__item {
    min-height: 40px;
  }

  .ai-timeline__track {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 28px;
    flex-shrink: 0;
  }

  .ai-timeline__dot {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    background: #f1f5f9;
    color: #94a3b8;
    border: 2px solid #e2e8f0;
    transition: all var(--zy-duration-normal, 280ms) var(--zy-ease-out, ease);
  }

  .ai-timeline__item--running .ai-timeline__dot {
    background: #eef2ff;
    border-color: var(--zy-color-brand, #6366f1);
    color: var(--zy-color-brand, #6366f1);
  }

  .ai-timeline__item--done .ai-timeline__dot {
    background: var(--zy-color-brand, #6366f1);
    border-color: var(--zy-color-brand, #6366f1);
    color: #fff;
  }

  .ai-timeline__item--error .ai-timeline__dot {
    background: #fef2f2;
    border-color: #ef4444;
    color: #ef4444;
  }

  .ai-timeline__line {
    flex: 1;
    width: 2px;
    min-height: 16px;
    background: #e2e8f0;
    transition: background var(--zy-duration-normal, 280ms) ease;
  }

  .ai-timeline__line--active {
    background: var(--zy-color-brand, #6366f1);
  }

  .ai-timeline__content {
    flex: 1;
    padding-bottom: 12px;
  }

  .ai-timeline__label {
    font-size: 14px;
    font-weight: 600;
    color: var(--zy-color-text-primary, #0f172a);
    line-height: 28px;
  }

  .ai-timeline__item--idle .ai-timeline__label {
    color: #94a3b8;
  }

  .ai-timeline__message {
    font-size: 12px;
    color: var(--zy-color-text-secondary, #64748b);
    line-height: 1.5;
    font-family: 'JetBrains Mono', 'SF Mono', monospace;
  }

  .ai-timeline__spinner {
    width: 12px;
    height: 12px;
    border: 2px solid rgba(99, 102, 241, 0.25);
    border-top-color: var(--zy-color-brand, #6366f1);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .ai-timeline__idle-num {
    font-size: 11px;
  }
</style>
