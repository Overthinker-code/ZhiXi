<template>
  <div class="zy-skeleton-wrap" :class="{ 'zy-skeleton-wrap--block': block }">
    <div
      v-for="n in rows"
      :key="n"
      class="zy-skeleton zy-bar"
      :style="{ width: barWidth(n), height: `${height}px` }"
    />
  </div>
</template>

<script setup lang="ts">
  const props = withDefaults(
    defineProps<{
      rows?: number;
      height?: number;
      block?: boolean;
    }>(),
    {
      rows: 3,
      height: 14,
      block: false,
    }
  );

  function barWidth(index: number): string {
    if (index === props.rows) return '60%';
    if (index === 1) return '100%';
    return `${85 - (index % 3) * 12}%`;
  }
</script>

<style scoped lang="less">
  .zy-skeleton-wrap {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 4px 0;
  }

  .zy-skeleton-wrap--block {
    min-height: 120px;
    justify-content: center;
  }

  .zy-bar {
    border-radius: 8px;
    background: linear-gradient(90deg, #eef2ff 25%, #c7d2fe 50%, #eef2ff 75%);
    background-size: 200% 100%;
    animation: zy-shimmer 1.5s infinite;
  }
</style>
