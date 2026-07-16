<template>
  <div class="loading-state">
    <template v-if="skeleton">
      <ZySkeleton :rows="skeletonRows" block />
    </template>
    <template v-else>
      <a-spin :size="size" :tip="tip">
        <template v-if="$slots.icon" #icon>
          <slot name="icon" />
        </template>
      </a-spin>
      <div v-if="showDots" class="zy-thinking-dots" aria-hidden="true">
        <span /><span /><span />
      </div>
    </template>
    <p v-if="text" class="loading-text">{{ text }}</p>
  </div>
</template>

<script setup lang="ts">
import ZySkeleton from '../zy/ZySkeleton.vue';

defineProps({
  text: {
    type: String,
    default: '',
  },
  tip: {
    type: String,
    default: '',
  },
  size: {
    type: Number,
    default: 32,
  },
  skeleton: {
    type: Boolean,
    default: false,
  },
  skeletonRows: {
    type: Number,
    default: 4,
  },
  showDots: {
    type: Boolean,
    default: false,
  },
});
</script>

<style scoped>
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  min-height: 200px;
  width: 100%;
}

.loading-text {
  margin-top: 16px;
  color: var(--zy-color-text-secondary, #64748b);
  font-size: 14px;
}

.zy-thinking-dots {
  margin-top: 12px;
}
</style>
