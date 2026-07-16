<template>
  <div class="zy-empty-guide">
    <div class="zy-empty-guide__icon">
      <slot name="icon">
        <icon-empty :size="56" />
      </slot>
    </div>
    <h4 v-if="title" class="zy-empty-guide__title">{{ title }}</h4>
    <p v-if="description" class="zy-empty-guide__desc">{{ description }}</p>
    <div class="zy-empty-guide__actions">
      <a-button v-if="primaryText" type="primary" @click="$emit('primary')">
        {{ primaryText }}
      </a-button>
      <a-button
        v-if="secondaryText"
        type="outline"
        @click="$emit('secondary')"
      >
        {{ secondaryText }}
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
  defineProps<{
    title?: string;
    description?: string;
    primaryText?: string;
    secondaryText?: string;
  }>();

  defineEmits<{
    primary: [];
    secondary: [];
  }>();
</script>

<style scoped lang="less">
  .zy-empty-guide {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 48px 24px;
    text-align: center;
    min-height: 200px;
  }

  .zy-empty-guide__icon {
    color: var(--zy-color-brand, #6366f1);
    opacity: 0.55;
    margin-bottom: 16px;
  }

  .zy-empty-guide__title {
    margin: 0 0 8px;
    font-size: 16px;
    font-weight: 600;
    color: var(--zy-color-text-primary, #0f172a);
  }

  .zy-empty-guide__desc {
    margin: 0 0 20px;
    max-width: 320px;
    font-size: 13px;
    line-height: 1.6;
    color: var(--zy-color-text-secondary, #64748b);
  }

  .zy-empty-guide__actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    justify-content: center;
  }
</style>
