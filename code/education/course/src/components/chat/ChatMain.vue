<script setup lang="ts">
  import { computed, nextTick, ref, watch } from 'vue';
  import AssistantMessage from './AssistantMessage.vue';
  import type { GeneratePracticeFollowUp } from './postAnswerActions';

  const props = defineProps<{
    messages: Array<Record<string, any>>;
    loading?: boolean;
    bottomInset?: number;
    emptyTitle?: string;
    emptyDescription?: string;
    starterActions?: string[];
  }>();

  const emit = defineEmits<{
    (e: 'retry'): void;
    (e: 'sendSuggestion', text: string): void;
    (e: 'postAction', action: GeneratePracticeFollowUp): void;
    (e: 'stop'): void;
    (e: 'sendStarter', text: string): void;
  }>();

  const isLastAssistant = (index: number) =>
    index === props.messages.length - 1 && props.messages[index]?.role === 'assistant';

  function sourcePromptFor(index: number) {
    for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
      const message = props.messages[cursor];
      if (message?.role === 'user') return String(message.content || '');
    }
    return '';
  }

  const mainRef = ref<HTMLElement | null>(null);
  const shouldStickToBottom = ref(true);
  const streamSignature = computed(() =>
    props.messages
      .map((message) => `${message.localId || message.id || message.role}:${String(message.content || '').length}:${message.loading ? 1 : 0}`)
      .join('|')
  );

  function onScroll() {
    const el = mainRef.value;
    if (!el) return;
    shouldStickToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 180;
  }

  function scrollToBottom(behavior: 'auto' | 'smooth' = 'auto') {
    const el = mainRef.value;
    if (!el || !shouldStickToBottom.value) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
  }

  watch(
    streamSignature,
    async () => {
      await nextTick();
      scrollToBottom('auto');
    },
    { flush: 'post' }
  );
</script>

<template>
  <main
    ref="mainRef"
    class="chat-main"
    data-testid="tutor-chat-main"
    :style="{ '--chat-bottom-inset': `${bottomInset || 210}px` }"
    @scroll="onScroll"
  >
    <section v-if="!messages.length" class="chat-empty">
      <span v-if="emptyDescription" class="chat-empty__eyebrow">专用智能体已就绪</span>
      <h1>{{ emptyTitle || '今天想学习什么？' }}</h1>
      <p v-if="emptyDescription">{{ emptyDescription }}</p>
      <div v-if="starterActions?.length" class="chat-empty__starters">
        <button
          v-for="starter in starterActions"
          :key="starter"
          type="button"
          @click="emit('sendStarter', starter)"
        >
          {{ starter }}
        </button>
      </div>
    </section>

    <section v-else class="chat-thread" aria-live="polite">
      <template v-for="(message, index) in messages" :key="message.localId || message.id || index">
        <div v-if="message.role === 'user'" class="user-message">
          <div>
            <p>{{ message.content }}</p>
            <span v-if="message.files?.length">已附加 {{ message.files.length }} 个文件</span>
          </div>
        </div>
        <AssistantMessage
          v-else-if="message.role === 'assistant'"
          :message="message"
          :is-last="isLastAssistant(index)"
          :source-prompt="sourcePromptFor(index)"
          @send-suggestion="emit('sendSuggestion', $event)"
          @post-action="emit('postAction', $event)"
          @retry="emit('retry')"
          @stop="emit('stop')"
        />
        <div v-else-if="message.role === 'error'" class="error-message">
          <strong>{{ message.content }}</strong>
          <button type="button" @click="emit('retry')">重试</button>
        </div>
      </template>
    </section>
  </main>
</template>

<style scoped lang="scss">
  .chat-main {
    position: relative;
    min-width: 0;
    height: 100%;
    overflow-y: auto;
    padding: 28px 28px var(--chat-bottom-inset, 210px);
    background: #fff;
  }

  .chat-empty {
    position: absolute;
    top: clamp(250px, 38%, 360px);
    left: 50%;
    z-index: 1;
    display: flex;
    width: min(760px, calc(100% - 48px));
    align-items: center;
    justify-content: center;
    flex-direction: column;
    text-align: center;
    transform: translate(-50%, -50%);
    animation: empty-enter 0.18s ease both;

    h1 {
      margin: 0;
      color: #101828;
      font-size: 34px;
      font-weight: 720;
      letter-spacing: 0;
    }

    > p {
      max-width: 620px;
      margin: 12px auto 0;
      color: #697386;
      font-size: 14px;
      line-height: 1.7;
    }
  }

  .chat-empty__eyebrow {
    display: inline-block;
    margin-bottom: 10px;
    color: #6558d9;
    font-size: 12px;
    font-weight: 750;
    letter-spacing: 0.04em;
  }

  .chat-empty__starters {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 9px;
    margin-top: 22px;

    button {
      padding: 10px 14px;
      border: 1px solid #e0e3ee;
      border-radius: 14px;
      color: #3f4960;
      background: #fff;
      box-shadow: 0 8px 20px rgba(45, 52, 88, 0.055);
      font-size: 13px;
      cursor: pointer;

      &:hover {
        border-color: #c9c6ff;
        color: #5146cc;
        background: #f8f7ff;
      }
    }
  }

  .chat-thread {
    display: grid;
    gap: 4px;
    width: min(920px, 100%);
    margin: 0 auto;
    animation: enter 0.18s ease both;
  }

  .user-message {
    display: flex;
    justify-content: flex-end;
    margin: 8px 0 24px;

    div {
      max-width: min(70%, 620px);
      padding: 13px 16px;
      border-radius: 20px 20px 4px 20px;
      background: #eef2ff;
      color: #1d2939;
    }

    p {
      margin: 0;
      white-space: pre-wrap;
      line-height: 1.65;
    }

    span {
      display: block;
      margin-top: 8px;
      color: #667085;
      font-size: 12px;
    }
  }

  .error-message {
    width: min(820px, 100%);
    margin: 0 auto 20px;
    padding: 14px;
    border: 1px solid rgba(240, 68, 56, 0.2);
    border-radius: 16px;
    background: #fff5f5;
    color: #b42318;

    button {
      margin-left: 12px;
      border: 0;
      color: #4f46e5;
      background: transparent;
      cursor: pointer;
    }
  }

  @keyframes enter {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes empty-enter {
    from {
      opacity: 0;
      transform: translate(-50%, calc(-50% + 8px));
    }
    to {
      opacity: 1;
      transform: translate(-50%, -50%);
    }
  }

  @media (max-width: 1280px) {
    .chat-main {
      padding-inline: 20px;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .chat-empty,
    .chat-thread {
      animation: none;
    }
  }
</style>
