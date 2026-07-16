<template>
  <div class="empty-state" :class="{ 'empty-state--compact': compact }">
    <div class="empty-icon">
      <slot name="icon">
        <icon-empty :size="iconSize" />
      </slot>
    </div>
    <p class="empty-text">{{ text }}</p>
    <p v-if="description" class="empty-description">{{ description }}</p>
    <div v-if="actionText || $slots.action" class="empty-actions">
      <slot name="action">
        <a-button v-if="actionText" type="primary" @click="$emit('action')">
          {{ actionText }}
        </a-button>
      </slot>
    </div>
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
  compact: {
    type: Boolean,
    default: false,
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
  animation: zy-fade-up var(--zy-duration-normal, 280ms) var(--zy-ease-out, ease) both;
}

.empty-state--compact {
  min-height: 120px;
  padding: 24px 16px;
}

.empty-icon {
  color: var(--zy-color-brand, #6366f1);
  opacity: 0.4;
}

.empty-text {
  margin-top: 16px;
  color: var(--zy-color-text-primary, #0f172a);
  font-size: 14px;
  font-weight: 500;
}

.empty-description {
  margin-top: 8px;
  color: var(--zy-color-text-secondary, #64748b);
  font-size: 12px;
  max-width: 280px;
  text-align: center;
  line-height: 1.5;
}

.empty-actions {
  margin-top: 16px;
}
</style>
