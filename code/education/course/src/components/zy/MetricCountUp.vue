<template>
  <span class="metric-count-up">{{ displayValue }}</span>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { useTransition, TransitionPresets } from '@vueuse/core';

  const props = withDefaults(
    defineProps<{
      value: number;
      duration?: number;
      suffix?: string;
      decimals?: number;
    }>(),
    {
      duration: 800,
      suffix: '',
      decimals: 0,
    }
  );

  const source = ref(0);

  watch(
    () => props.value,
    (v) => {
      source.value = v;
    },
    { immediate: true }
  );

  const output = useTransition(source, {
    duration: props.duration,
    transition: TransitionPresets.easeOutCubic,
  });

  const displayValue = computed(() => {
    const n = output.value;
    const formatted =
      props.decimals > 0 ? n.toFixed(props.decimals) : Math.round(n).toString();
    return `${formatted}${props.suffix}`;
  });
</script>

<style scoped>
  .metric-count-up {
    font-variant-numeric: tabular-nums;
  }
</style>
