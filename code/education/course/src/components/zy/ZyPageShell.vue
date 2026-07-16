<script setup lang="ts">
  defineProps<{
    title: string;
    subtitle?: string;
    maxWidth?: string;
  }>();
</script>

<template>
  <div class="zy-page-shell" :style="{ '--zy-shell-max': maxWidth || '1280px' }">
    <header v-if="title" class="zy-page-shell__head zy-stagger-child">
      <div>
        <h1>{{ title }}</h1>
        <p v-if="subtitle">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.actions" class="zy-page-shell__actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="zy-page-shell__body">
      <slot />
    </div>
  </div>
</template>

<style scoped lang="less">
  .zy-page-shell {
    max-width: var(--zy-shell-max);
    margin: 0 auto;
    padding: 20px 24px 40px;
  }

  .zy-page-shell__head {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 16px;
    margin-bottom: 18px;

    h1 {
      margin: 0;
      font-size: var(--zy-text-xl, 24px);
      font-weight: 700;
      color: var(--zy-color-text-primary, #0f172a);
      letter-spacing: -0.02em;
      font-family: var(--zy-font-display);
    }

    p {
      margin: 8px 0 0;
      color: #475569;
      font-size: var(--zy-text-sm, 14px);
      line-height: 1.6;
    }
  }

  .zy-page-shell__actions {
    display: flex;
    gap: 10px;
    flex-shrink: 0;
  }

  .zy-page-shell__body {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
</style>
