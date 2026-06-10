<template>
  <div class="zy-page-enter">
    <slot />
  </div>
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue';

  const props = withDefaults(
    defineProps<{
      stagger?: boolean;
      baseDelay?: number;
    }>(),
    {
      stagger: true,
      baseDelay: 0,
    }
  );

  const ready = ref(false);

  onMounted(() => {
    requestAnimationFrame(() => {
      ready.value = true;
    });
  });

  defineExpose({ ready });
</script>

<style scoped lang="less">
  .zy-page-enter :deep(> .zy-stagger-child) {
    opacity: 0;
    transform: translateY(16px);
    animation: zy-fade-up var(--zy-duration-slow, 480ms) var(--zy-ease-out, ease)
      both;
  }

  .zy-page-enter :deep(> .zy-stagger-child:nth-child(1)) {
    animation-delay: calc(var(--zy-stagger-step, 80ms) * 0);
  }
  .zy-page-enter :deep(> .zy-stagger-child:nth-child(2)) {
    animation-delay: calc(var(--zy-stagger-step, 80ms) * 1);
  }
  .zy-page-enter :deep(> .zy-stagger-child:nth-child(3)) {
    animation-delay: calc(var(--zy-stagger-step, 80ms) * 2);
  }
  .zy-page-enter :deep(> .zy-stagger-child:nth-child(4)) {
    animation-delay: calc(var(--zy-stagger-step, 80ms) * 3);
  }
  .zy-page-enter :deep(> .zy-stagger-child:nth-child(5)) {
    animation-delay: calc(var(--zy-stagger-step, 80ms) * 4);
  }
  .zy-page-enter :deep(> .zy-stagger-child:nth-child(6)) {
    animation-delay: calc(var(--zy-stagger-step, 80ms) * 5);
  }
  .zy-page-enter :deep(> .zy-stagger-child:nth-child(7)) {
    animation-delay: calc(var(--zy-stagger-step, 80ms) * 6);
  }
  .zy-page-enter :deep(> .zy-stagger-child:nth-child(8)) {
    animation-delay: calc(var(--zy-stagger-step, 80ms) * 7);
  }
</style>
