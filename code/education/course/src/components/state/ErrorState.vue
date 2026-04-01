<template>
  <div class="error-state">
    <div class="error-icon">
      <slot name="icon">
        <icon-close-circle-fill :size="iconSize" style="color: #f53f3f" />
      </slot>
    </div>
    <p class="error-text">{{ text }}</p>
    <p v-if="description" class="error-description">{{ description }}</p>
    <a-space>
      <a-button v-if="retryText" type="primary" @click="$emit('retry')">
        {{ retryText }}
      </a-button>
      <a-button v-if="backText" @click="$emit('back')">
        {{ backText }}
      </a-button>
    </a-space>
  </div>
</template>

<script setup lang="ts">
defineProps({
  text: {
    type: String,
    default: '加载失败',
  },
  description: {
    type: String,
    default: '',
  },
  iconSize: {
    type: Number,
    default: 48,
  },
  retryText: {
    type: String,
    default: '重试',
  },
  backText: {
    type: String,
    default: '',
  },
});

defineEmits(['retry', 'back']);
</script>

<style scoped>
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  min-height: 200px;
}

.error-icon {
  color: #f53f3f;
}

.error-text {
  margin-top: 16px;
  color: #86909c;
  font-size: 14px;
}

.error-description {
  margin-top: 8px;
  margin-bottom: 16px;
  color: #c9cdd4;
  font-size: 12px;
}
</style>
