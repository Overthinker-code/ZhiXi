<template>
  <TransitionGroup
    name="result-reveal"
    tag="div"
    class="result-reveal"
    :class="{ 'result-reveal--grid': grid }"
  >
    <slot />
  </TransitionGroup>
</template>

<script setup lang="ts">
  withDefaults(
    defineProps<{
      grid?: boolean;
    }>(),
    {
      grid: false,
    }
  );
</script>

<style scoped lang="less">
  .result-reveal {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .result-reveal--grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 12px;
  }

  .result-reveal :deep(> *) {
    transition: all var(--zy-duration-normal, 280ms) var(--zy-ease-out, ease);
  }

  .result-reveal-enter-active {
    transition: all var(--zy-duration-slow, 480ms) var(--zy-ease-spring, ease);
  }

  .result-reveal-enter-from {
    opacity: 0;
    transform: translateY(16px);
  }

  .result-reveal-move {
    transition: transform var(--zy-duration-normal, 280ms) ease;
  }
</style>
