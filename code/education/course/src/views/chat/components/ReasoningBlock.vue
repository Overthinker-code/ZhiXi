<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { IconDown, IconRight } from '@arco-design/web-vue/es/icon';
  import type { ReasoningActionItem } from '@/api/rag';
  import { renderMarkdown } from '@/utils/markdown';

  const props = defineProps<{
    content?: string;
    actions?: ReasoningActionItem[];
    streaming?: boolean;
    defaultExpanded?: boolean;
  }>();

  const expanded = ref(Boolean(props.defaultExpanded ?? true));

  const displayText = computed(() => (props.content || '').trim());

  const actionCards = computed(() =>
    (props.actions || []).filter((a) => a && (a.title || a.detail))
  );

  watch(
    () => props.streaming,
    (v) => {
      if (v) expanded.value = true;
    },
    { immediate: true }
  );

  const visibleText = computed(() => {
    if (!displayText.value) {
      return props.streaming ? '正在组织思路…' : '';
    }
    return displayText.value;
  });

  const visibleHtml = computed(() =>
    renderMarkdown(visibleText.value, { streaming: Boolean(props.streaming) })
  );

  const renderActionText = (value?: string) =>
    renderMarkdown(value || '', { streaming: Boolean(props.streaming) });

  const hasContent = computed(
    () =>
      displayText.value.length > 0 ||
      actionCards.value.length > 0 ||
      Boolean(props.streaming)
  );
</script>

<template>
  <div v-if="hasContent" class="rb">
    <button type="button" class="rb-toggle" @click="expanded = !expanded">
      <span class="rb-icon" :class="{ 'rb-icon--pulse': streaming }" />
      <span class="rb-label">
        {{ streaming ? '深度思考' : '已完成思考' }}
      </span>
      <span v-if="streaming" class="rb-live">思考中</span>
      <component :is="expanded ? IconDown : IconRight" class="rb-chevron" />
    </button>
    <Transition name="rb-fold">
      <div v-show="expanded" class="rb-body">
        <div v-if="actionCards.length" class="rb-actions">
          <div v-for="(card, idx) in actionCards" :key="idx" class="rb-action-card">
            <div class="rb-action-title">{{ card.title || card.action }}</div>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div
              v-if="card.detail"
              class="rb-action-detail"
              v-html="renderActionText(card.detail)"
            />
            <ul v-if="card.items?.length" class="rb-action-items">
              <!-- eslint-disable-next-line vue/no-v-html -->
              <li
                v-for="(item, i) in card.items"
                :key="i"
                v-html="renderActionText(item)"
              />
            </ul>
          </div>
        </div>
        <div v-if="visibleText" class="rb-text">
          <div class="rb-markdown" v-html="visibleHtml" />
          <span v-if="streaming" class="rb-caret" aria-hidden="true" />
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped lang="less">
  .rb {
    margin: 8px 0 14px;
    border-radius: 12px;
    background: #f8fafc;
    border: 1px solid #dce3ec;
    border-left: 3px solid #6574f7;
    overflow: hidden;
  }

  .rb-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 11px 14px;
    border: none;
    background: transparent;
    cursor: pointer;
    color: #64748b;
    font-size: 13px;
    text-align: left;
  }

  .rb-icon {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #94a3b8;
    flex-shrink: 0;

    &--pulse {
      background: #6366f1;
      box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.45);
      animation: rb-pulse 1.4s ease-out infinite;
    }
  }

  .rb-label {
    flex: 1;
    font-weight: 600;
    color: #475569;
  }

  .rb-live {
    font-size: 11px;
    color: #6366f1;
    background: rgba(99, 102, 241, 0.1);
    padding: 2px 8px;
    border-radius: 999px;
  }

  .rb-chevron {
    font-size: 12px;
    opacity: 0.5;
  }

  .rb-body {
    padding: 0 16px 15px;
    border-top: 1px solid rgba(148, 163, 184, 0.2);
  }

  .rb-actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 12px;
  }

  .rb-action-card {
    padding: 8px 10px;
    border-radius: 8px;
    background: rgba(99, 102, 241, 0.06);
    border: 1px solid rgba(99, 102, 241, 0.15);
  }

  .rb-action-title {
    font-size: 12px;
    font-weight: 600;
    color: #4f46e5;
  }

  .rb-action-detail {
    margin-top: 4px;
    font-size: 12px;
    color: #64748b;
    line-height: 1.5;
  }

  .rb-action-items {
    margin: 6px 0 0;
    padding-left: 18px;
    font-size: 11.5px;
    color: #64748b;
  }

  .rb-action-detail :deep(p),
  .rb-action-items :deep(p) {
    margin: 0;
  }

  .rb-text {
    margin: 12px 0 0;
    word-break: break-word;
    font-family: inherit;
    font-size: 14px;
    line-height: 1.82;
    color: #59677b;
    max-height: 320px;
    overflow-y: auto;
  }

  .rb-markdown {
    display: inline;

    :deep(p) {
      display: inline;
      margin: 0;
    }

    :deep(.katex-display) {
      display: block;
      margin: 10px 0;
      overflow-x: auto;
      overflow-y: hidden;
    }

    :deep(.katex) {
      font-size: 1.02em;
    }
  }

  .rb-caret {
    display: inline-block;
    width: 2px;
    height: 1em;
    margin-left: 2px;
    vertical-align: text-bottom;
    background: #6366f1;
    animation: rb-blink 0.9s step-end infinite;
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

  @keyframes rb-pulse {
    0% {
      box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.45);
    }
    70% {
      box-shadow: 0 0 0 8px rgba(99, 102, 241, 0);
    }
    100% {
      box-shadow: 0 0 0 0 rgba(99, 102, 241, 0);
    }
  }

  @keyframes rb-blink {
    50% {
      opacity: 0;
    }
  }
</style>
