<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { IconDown, IconRight } from '@arco-design/web-vue/es/icon';

  const props = defineProps<{
    content?: string;
    streaming?: boolean;
    defaultExpanded?: boolean;
  }>();

  const expanded = ref(Boolean(props.defaultExpanded));

  watch(
    () => props.streaming,
    (v) => {
      if (v) expanded.value = true;
    }
  );

  const displayText = computed(() => (props.content || '').trim());
  const hasContent = computed(() => displayText.value.length > 0);
</script>

<template>
  <div v-if="hasContent || streaming" class="rb">
    <button type="button" class="rb-toggle" @click="expanded = !expanded">
      <span class="rb-icon" :class="{ 'rb-icon--spin': streaming }" />
      <span class="rb-label">
        {{ streaming ? '思考中…' : '思考过程' }}
      </span>
      <component :is="expanded ? IconDown : IconRight" class="rb-chevron" />
    </button>
    <Transition name="rb-fold">
      <div v-show="expanded" class="rb-body">
        <pre class="rb-text">{{ displayText || '正在组织思路…' }}</pre>
      </div>
    </Transition>
  </div>
</template>

<style scoped lang="less">
  .rb {
    margin: 8px 0 10px;
    border: 1px solid var(--color-border-2, #e5e6eb);
    border-radius: 10px;
    background: var(--color-fill-1, #f7f8fa);
    overflow: hidden;
  }

  .rb-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 10px 12px;
    border: none;
    background: transparent;
    cursor: pointer;
    color: var(--color-text-2, #4e5969);
    font-size: 13px;
    text-align: left;
  }

  .rb-icon {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid var(--color-text-4, #c9cdd4);
    border-top-color: rgb(var(--primary-6, 22, 93, 255));
    flex-shrink: 0;

    &--spin {
      animation: rb-spin 0.8s linear infinite;
    }
  }

  .rb-label {
    flex: 1;
    font-weight: 500;
  }

  .rb-chevron {
    font-size: 12px;
    opacity: 0.55;
  }

  .rb-body {
    padding: 0 12px 12px;
  }

  .rb-text {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: inherit;
    font-size: 13px;
    line-height: 1.65;
    color: var(--color-text-3, #86909c);
    max-height: 280px;
    overflow-y: auto;
  }

  .rb-fold-enter-active,
  .rb-fold-leave-active {
    transition: opacity 0.2s ease, max-height 0.25s ease;
  }

  .rb-fold-enter-from,
  .rb-fold-leave-to {
    opacity: 0;
    max-height: 0;
  }

  @keyframes rb-spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
