<template>
  <div class="loading-state">
    <a-spin :size="size" :tip="tip">
      <template v-if="$slots.icon" #icon>
        <slot name="icon" />
      </template>
    </a-spin>
    <p v-if="text" class="loading-text">{{ text }}</p>
  </div>
</template>

<script setup lang="ts">
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
}

.loading-text {
  margin-top: 16px;
  color: #86909c;
  font-size: 14px;
}
</style>
