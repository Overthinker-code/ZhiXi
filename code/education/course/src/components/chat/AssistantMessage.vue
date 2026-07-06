<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { renderMarkdown } from '@/utils/markdown';
  import ArtifactCards from './ArtifactCards.vue';
  import CitationList from './CitationList.vue';
  import ToolTrace from './ToolTrace.vue';

  const props = defineProps<{
    message: Record<string, any>;
    isLast?: boolean;
  }>();

  const reasoningOpen = ref(false);
  const rendered = computed(() => renderMarkdown(String(props.message.content || ''), {
    streaming: Boolean(props.message.loading),
  }));
  const reasoning = computed(() => String(props.message.reasoning_content || '').trim());
</script>

<template>
  <article class="assistant-message">
    <ToolTrace
      :events="message.toolEvents || message.agentPhases || []"
      :loading="Boolean(message.loading)"
    />

    <button
      v-if="reasoning || message.loading"
      type="button"
      class="reasoning-toggle"
      @click="reasoningOpen = !reasoningOpen"
    >
      {{ reasoningOpen ? '收起思考摘要' : '查看思考摘要' }}
      <span v-if="message.loading" class="streaming-dots"><i /><i /><i /></span>
    </button>
    <div v-if="reasoningOpen && (reasoning || message.loading)" class="reasoning-box" aria-live="polite">
      {{ reasoning || '正在整理思考过程...' }}
    </div>

    <div v-if="message.content" class="assistant-message__body markdown-body" v-html="rendered" />
    <div v-else-if="message.loading" class="assistant-message__loading">
      <span />
      <span />
      <span />
    </div>

    <CitationList :citations="message.citations || []" compact />
    <ArtifactCards
      :artifacts="message.artifacts || []"
      :package-id="message.resourcePackage?.package_id"
    />

    <footer v-if="!message.loading && message.content" class="assistant-message__actions">
      <button type="button">生成练习</button>
      <button type="button">加入笔记</button>
      <button type="button">同步图谱</button>
      <button type="button">继续追问</button>
    </footer>
  </article>
</template>

<style scoped lang="scss">
  .assistant-message {
    width: min(820px, 100%);
    margin: 0 auto 28px;
    color: #344054;
  }

  .assistant-message__body {
    color: #344054;
    font-size: 15px;
    line-height: 1.75;

    :deep(h1),
    :deep(h2),
    :deep(h3) {
      margin: 18px 0 8px;
      color: #101828;
      line-height: 1.35;
    }

    :deep(p) {
      margin: 8px 0;
    }

    :deep(table) {
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0;
      overflow: hidden;
      border-radius: 12px;
    }

    :deep(th),
    :deep(td) {
      padding: 9px 10px;
      border: 1px solid rgba(15, 23, 42, 0.08);
    }

    :deep(pre) {
      overflow: auto;
      border-radius: 14px;
    }
  }

  .assistant-message__loading {
    display: inline-flex;
    gap: 5px;
    padding: 12px 0;

    span {
      width: 7px;
      height: 7px;
      border-radius: 999px;
      background: #6366f1;
      animation: loading-dot 1s ease-in-out infinite;

      &:nth-child(2) {
        animation-delay: 0.14s;
      }

      &:nth-child(3) {
        animation-delay: 0.28s;
      }
    }
  }

  .reasoning-toggle {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin: 10px 0;
    padding: 0;
    border: 0;
    color: #4f46e5;
    background: transparent;
    font-size: 13px;
    cursor: pointer;
  }

  .streaming-dots {
    display: inline-flex;
    gap: 3px;

    i {
      width: 5px;
      height: 5px;
      border-radius: 999px;
      background: #a4a7ff;
      animation: reasoning-dot 1s ease-in-out infinite;

      &:nth-child(2) {
        animation-delay: 0.14s;
      }

      &:nth-child(3) {
        animation-delay: 0.28s;
      }
    }
  }

  .reasoning-box {
    margin-bottom: 12px;
    padding: 12px;
    border-left: 3px solid #6366f1;
    border-radius: 12px;
    background: #f7f9ff;
    color: #667085;
    font-size: 13px;
    line-height: 1.7;
    white-space: pre-wrap;
  }

  .assistant-message__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;

    button {
      height: 32px;
      padding: 0 12px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 999px;
      color: #475467;
      background: #fff;
      cursor: pointer;

      &:hover {
        color: #4f46e5;
        border-color: rgba(99, 102, 241, 0.35);
      }
    }
  }

  @keyframes loading-dot {
    0%, 100% {
      opacity: 0.35;
      transform: translateY(0);
    }
    50% {
      opacity: 1;
      transform: translateY(-3px);
    }
  }

  @keyframes reasoning-dot {
    0%, 100% {
      opacity: 0.35;
    }
    50% {
      opacity: 1;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .assistant-message__loading span,
    .streaming-dots i {
      animation: none;
    }
  }
</style>
