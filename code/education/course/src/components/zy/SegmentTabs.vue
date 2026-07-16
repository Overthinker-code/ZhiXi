<template>
  <div class="segment-tabs">
    <div class="segment-tabs__list" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        role="tab"
        class="segment-tabs__item"
        :class="{ 'segment-tabs__item--active': modelValue === tab.value }"
        :aria-selected="modelValue === tab.value"
        @click="$emit('update:modelValue', tab.value)"
      >
        {{ tab.label }}
      </button>
      <span
        class="segment-tabs__indicator"
        :style="indicatorStyle"
      />
    </div>
    <div class="segment-tabs__panel">
      <slot :active="modelValue" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue';

  export interface SegmentTab {
    label: string;
    value: string;
  }

  const props = defineProps<{
    tabs: SegmentTab[];
    modelValue: string;
  }>();

  defineEmits<{
    'update:modelValue': [value: string];
  }>();

  const activeIndex = computed(() =>
    Math.max(
      0,
      props.tabs.findIndex((t) => t.value === props.modelValue)
    )
  );

  const indicatorStyle = computed(() => {
    const count = props.tabs.length || 1;
    const width = 100 / count;
    return {
      width: `${width}%`,
      transform: `translateX(${activeIndex.value * 100}%)`,
    };
  });
</script>

<style scoped lang="less">
  .segment-tabs__list {
    position: relative;
    display: flex;
    background: #f1f5f9;
    border-radius: 10px;
    padding: 4px;
    margin-bottom: 16px;
  }

  .segment-tabs__item {
    flex: 1;
    position: relative;
    z-index: 1;
    padding: 8px 12px;
    border: none;
    background: transparent;
    font-size: 13px;
    font-weight: 500;
    color: #64748b;
    cursor: pointer;
    border-radius: 8px;
    transition: color var(--zy-duration-fast, 150ms) ease;
  }

  .segment-tabs__item--active {
    color: var(--zy-color-brand, #6366f1);
    font-weight: 600;
  }

  .segment-tabs__indicator {
    position: absolute;
    top: 4px;
    left: 4px;
    height: calc(100% - 8px);
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08);
    transition: transform var(--zy-duration-normal, 280ms) var(--zy-ease-out, ease);
    pointer-events: none;
  }

  .segment-tabs__panel {
    min-height: 120px;
  }
</style>
