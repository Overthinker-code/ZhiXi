<template>
  <div class="empty-state">
    <div class="empty-icon">
      <slot name="icon">
        <icon-empty :size="iconSize" />
      </slot>
    </div>
    <p class="empty-text">{{ text }}</p>
    <p v-if="description" class="empty-description">{{ description }}</p>
    <a-button v-if="actionText" type="primary" @click="$emit('action')">
      {{ actionText }}
    </a-button>
  </div>
</template>

<script setup lang="ts">
defineProps({
  text: {
    type: String,
    default: '暂无数据',
  },
  description: {
    type: String,
    default: '',
  },
  iconSize: {
    type: Number,
    default: 48,
  },
  actionText: {
    type: String,
    default: '',
  },
});

defineEmits(['action']);
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  min-height: 200px;
}

.empty-icon {
  color: #c9cdd4;
}

.empty-text {
  margin-top: 16px;
  color: #86909c;
  font-size: 14px;
}

.empty-description {
  margin-top: 8px;
  color: #c9cdd4;
  font-size: 12px;
}
</style>
