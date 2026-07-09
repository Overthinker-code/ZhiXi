<script setup lang="ts">
  import { computed } from 'vue';
  import { renderMarkdown } from '@/utils/markdown';
  import ArtifactCards from './ArtifactCards.vue';
  import CitationList from './CitationList.vue';
  import LiveProcessPanel from './LiveProcessPanel.vue';

  const props = defineProps<{
    message: Record<string, any>;
    isLast?: boolean;
  }>();

  const emit = defineEmits<{
    (e: 'send-suggestion', text: string): void;
    (e: 'retry'): void;
  }>();

  const rendered = computed(() =>
    renderMarkdown(String(props.message.content || ''), {
      streaming: Boolean(props.message.loading),
    })
  );
  const suggestions = computed(() =>
    (Array.isArray(props.message.suggestions) ? props.message.suggestions : [])
      .map((item: unknown) => String(item || '').trim())
      .filter(Boolean)
      .slice(0, 3)
  );
</script>

<template>
  <article class="assistant-message" :class="{ 'is-streaming': message.loading }">
    <LiveProcessPanel :state="message.liveProcess" :loading="message.loading" />

    <div
      v-if="message.content"
      class="assistant-message__body markdown-body"
      :class="{ 'is-streaming': message.loading }"
      v-html="rendered"
    />
    <div v-else-if="message.loading" class="assistant-message__answer-waiting">
      <span />
      <p>正在组织回答…</p>
    </div>

    <CitationList :citations="message.citations || []" compact />
    <ArtifactCards
      :artifacts="message.artifacts || []"
      :package-id="message.resourcePackage?.package_id"
    />

    <section v-if="!message.loading && message.errorCode" class="assistant-message__error-actions">
      <button type="button" @click="emit('retry')">重试</button>
    </section>

    <section v-else-if="!message.loading && suggestions.length" class="follow-up-capsules">
      <button
        v-for="item in suggestions"
        :key="item"
        type="button"
        @click="emit('send-suggestion', item)"
      >
        {{ item }}
      </button>
    </section>

    <footer v-if="!message.loading && message.content && !message.errorCode" class="assistant-message__actions">
      <button type="button">生成练习</button>
      <button type="button">加入笔记</button>
      <button type="button">同步图谱</button>
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
    animation: answer-reveal 0.2s ease both;

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

    :deep(ul),
    :deep(ol) {
      padding-left: 1.45em;
      margin: 9px 0;
    }

    :deep(li) {
      margin: 4px 0;
    }

    :deep(table) {
      width: 100%;
      margin: 12px 0;
      overflow: hidden;
      border-collapse: collapse;
      border-radius: 12px;
    }

    :deep(th),
    :deep(td) {
      padding: 9px 10px;
      border: 1px solid rgba(15, 23, 42, 0.08);
    }

    :deep(code:not(pre code)) {
      padding: 2px 6px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 6px;
      background: #f6f8fb;
      color: #344054;
      font-size: 0.92em;
    }

    :deep(.code-block),
    :deep(.markdown-it-code-block),
    :deep(pre:not(.code-block)),
    :deep(pre.hljs:not(.code-block)) {
      margin: 14px 0;
      overflow: hidden;
      border: 1px solid rgba(15, 23, 42, 0.1);
      border-radius: 14px;
      background: #ffffff !important;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
    }

    :deep(pre.code-block.hljs) {
      position: relative;
      padding: 0;
      background: #ffffff !important;
      color: #344054 !important;
      text-shadow: none !important;
      white-space: normal;
    }

    :deep(pre.code-block.hljs::before) {
      display: flex;
      min-height: 34px;
      align-items: center;
      padding: 0 44px 0 12px;
      border-bottom: 1px solid rgba(15, 23, 42, 0.08);
      background: #f8fafc;
      color: #667085;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      content: attr(data-lang);
    }

    :deep(.code-block > code) {
      display: block;
      padding: 14px 16px;
      overflow-x: auto;
      background: transparent !important;
      color: #344054 !important;
      font-size: 13px;
      line-height: 1.65;
      white-space: pre;
    }

    :deep(.code-header) {
      display: flex;
      min-height: 34px;
      align-items: center;
      justify-content: space-between;
      padding: 0 12px;
      border-bottom: 1px solid rgba(15, 23, 42, 0.08);
      background: #f8fafc;
      color: #667085;
      font-size: 12px;
    }

    :deep(.code-lang) {
      color: #667085;
      font-weight: 700;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }

    :deep(.code-actions) {
      display: inline-flex;
      gap: 4px;
    }

    :deep(.code-action-btn) {
      display: inline-flex;
      width: 24px;
      height: 24px;
      align-items: center;
      justify-content: center;
      border: 0;
      border-radius: 7px;
      background: transparent;
      cursor: pointer;

      &:hover {
        background: #eef2ff;
      }

      img {
        width: 14px;
        height: 14px;
        opacity: 0.72;
      }
    }

    :deep(.code-action-btn--floating) {
      position: absolute;
      top: 5px;
      right: 8px;
      z-index: 1;
    }

    :deep(pre:not(.code-block)),
    :deep(pre.hljs:not(.code-block)) {
      padding: 14px 16px;
      color: #344054 !important;
      font-size: 13px;
      line-height: 1.65;
      text-shadow: none !important;
    }

    :deep(pre code),
    :deep(pre.hljs code),
    :deep(.hljs),
    :deep(.hljs-subst) {
      background: transparent !important;
      color: #344054 !important;
      text-shadow: none !important;
    }

    :deep(.hljs-keyword),
    :deep(.hljs-selector-tag),
    :deep(.hljs-title.function_),
    :deep(.hljs-built_in),
    :deep(.hljs-type),
    :deep(.hljs-name),
    :deep(.hljs-operator) {
      color: #4f46e5 !important;
    }

    :deep(.hljs-string),
    :deep(.hljs-attr),
    :deep(.hljs-symbol),
    :deep(.hljs-regexp),
    :deep(.hljs-link) {
      color: #087443 !important;
    }

    :deep(.hljs-number),
    :deep(.hljs-literal),
    :deep(.hljs-variable),
    :deep(.hljs-template-variable) {
      color: #b54708 !important;
    }

    :deep(.hljs-comment),
    :deep(.hljs-quote) {
      color: #98a2b3 !important;
    }

    :deep(.hljs-title),
    :deep(.hljs-section),
    :deep(.hljs-selector-id),
    :deep(.hljs-selector-class) {
      color: #175cd3 !important;
    }

    :deep(.hljs-meta),
    :deep(.hljs-doctag),
    :deep(.hljs-addition),
    :deep(.hljs-deletion) {
      color: #475467 !important;
      background: transparent !important;
    }
  }

  .assistant-message__answer-waiting {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    min-height: 36px;
    color: #667085;
    animation: answer-reveal 0.2s ease both;

    span {
      position: relative;
      width: 82px;
      height: 8px;
      overflow: hidden;
      border-radius: 999px;
      background: #eef2ff;

      &::after {
        position: absolute;
        inset: 0;
        background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.28), transparent);
        content: '';
        animation: shimmer 1.05s linear infinite;
      }
    }

    p {
      margin: 0;
      font-size: 13px;
    }
  }

  .follow-up-capsules {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;

    button {
      max-width: 100%;
      min-height: 34px;
      padding: 0 13px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 999px;
      color: #344054;
      background: #f8fafc;
      cursor: pointer;
      font-size: 13px;
      line-height: 1.3;
      transition:
        border-color 0.16s ease,
        color 0.16s ease,
        background 0.16s ease,
        transform 0.16s ease;

      &:hover {
        border-color: rgba(99, 102, 241, 0.28);
        color: #4f46e5;
        background: #eef2ff;
        transform: translateY(-1px);
      }
    }
  }

  .assistant-message__error-actions {
    display: flex;
    margin-top: 12px;

    button {
      min-height: 34px;
      padding: 0 14px;
      border: 1px solid rgba(240, 68, 56, 0.18);
      border-radius: 999px;
      color: #b42318;
      background: #fff7f7;
      cursor: pointer;
      font-size: 13px;
      font-weight: 700;
      transition:
        border-color 0.16s ease,
        background 0.16s ease,
        transform 0.16s ease;

      &:hover {
        border-color: rgba(240, 68, 56, 0.32);
        background: #fff1f1;
        transform: translateY(-1px);
      }
    }
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

  @keyframes answer-reveal {
    from {
      opacity: 0;
      filter: blur(6px);
      transform: translateY(8px);
    }

    to {
      opacity: 1;
      filter: blur(0);
      transform: translateY(0);
    }
  }

  @keyframes shimmer {
    from {
      transform: translateX(-100%);
    }

    to {
      transform: translateX(100%);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .assistant-message__body,
    .assistant-message__answer-waiting,
    .assistant-message__answer-waiting span::after {
      animation: none !important;
      filter: none;
    }
  }
</style>
