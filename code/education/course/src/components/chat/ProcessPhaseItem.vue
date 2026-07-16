<script setup lang="ts">
  defineProps<{
    title: string;
    text: string;
    status?: 'pending' | 'running' | 'done' | 'error' | string;
    active?: boolean;
  }>();
</script>

<template>
  <article class="process-phase-item" :class="[`is-${status || 'pending'}`, { 'is-active': active }]">
    <span class="process-phase-item__node">
      <i v-if="status === 'done'">✓</i>
    </span>
    <div>
      <strong>{{ title }}</strong>
      <p>{{ text }}</p>
    </div>
  </article>
</template>

<style scoped lang="scss">
  .process-phase-item {
    position: relative;
    display: grid;
    grid-template-columns: 18px 1fr;
    gap: 9px;
    padding: 6px 0 12px;
    color: #667085;
    animation: process-reveal 0.2s ease both;

    &::before {
      position: absolute;
      top: 24px;
      bottom: -2px;
      left: 6px;
      width: 1px;
      background: linear-gradient(180deg, rgba(99, 102, 241, 0.18), rgba(99, 102, 241, 0.04));
      content: '';
    }

    &:last-child::before {
      display: none;
    }

    strong {
      display: inline-flex;
      margin-bottom: 3px;
      color: #475467;
      font-size: 13px;
      font-weight: 720;
      line-height: 1.35;
    }

    p {
      margin: 0;
      color: #667085;
      font-size: 13px;
      line-height: 1.62;
      white-space: pre-wrap;
    }
  }

  .process-phase-item.is-active strong,
  .process-phase-item.is-running strong {
    color: #4f46e5;
  }

  .process-phase-item__node {
    position: relative;
    z-index: 1;
    display: inline-flex;
    width: 13px;
    height: 13px;
    align-items: center;
    justify-content: center;
    margin-top: 3px;
    border: 2px solid #fff;
    border-radius: 999px;
    background: #d0d5dd;
    box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.08);

    i {
      color: #fff;
      font-size: 8px;
      font-style: normal;
      line-height: 1;
    }
  }

  .is-running .process-phase-item__node,
  .is-active .process-phase-item__node {
    background: #6366f1;
    box-shadow: 0 0 0 5px rgba(99, 102, 241, 0.09);
    animation: process-pulse 1.35s ease-in-out infinite;
  }

  .is-done .process-phase-item__node {
    background: #667085;
    box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.08);
    animation: none;
  }

  .is-error .process-phase-item__node {
    background: #f04438;
    box-shadow: 0 0 0 5px rgba(240, 68, 56, 0.1);
  }

  @keyframes process-reveal {
    from {
      opacity: 0;
      filter: blur(6px);
      transform: translateY(8px);
    }

    to {
      opacity: 1;
      filter: blur(0);
      transform: translateY(0);
    }
  }

  @keyframes process-pulse {
    0%, 100% {
      opacity: 0.72;
      transform: scale(0.94);
    }

    50% {
      opacity: 1;
      transform: scale(1);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .process-phase-item,
    .process-phase-item__node {
      animation: none !important;
      filter: none;
    }
  }
</style>
