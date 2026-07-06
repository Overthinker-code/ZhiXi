<script setup lang="ts">
  import { computed } from 'vue';
  import AssistantMessage from './AssistantMessage.vue';
  import { TUTOR_ACTIONS } from './tutorActions';

  const props = defineProps<{
    messages: Array<Record<string, any>>;
    loading?: boolean;
  }>();

  const emit = defineEmits<{
    (e: 'action', actionId: string): void;
    (e: 'retry'): void;
  }>();

  const primaryActions = computed(() =>
    TUTOR_ACTIONS.filter((item) =>
      ['course_qa', 'homework_review', 'resource_generation', 'deep_research'].includes(item.id)
    )
  );

  const isLastAssistant = (index: number) =>
    index === props.messages.length - 1 && props.messages[index]?.role === 'assistant';
</script>

<template>
  <main class="chat-main" data-testid="tutor-chat-main">
    <section v-if="!messages.length" class="chat-empty">
      <h1>今天想学习什么？</h1>
      <p>可以问课程问题、上传作业、生成资料，或基于课程上下文进行深度研究。</p>
      <div class="chat-empty__actions">
        <button
          v-for="action in primaryActions"
          :key="action.id"
          type="button"
          @click="emit('action', action.id)"
        >
          <strong>{{ action.label }}</strong>
          <span>{{ action.description }}</span>
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
    min-width: 0;
    height: 100%;
    overflow-y: auto;
    padding: 28px 28px 210px;
    background: #fff;
  }

  .chat-empty {
    width: min(880px, 100%);
    margin: clamp(96px, 26vh, 170px) auto 0;
    animation: enter 0.18s ease both;

    h1 {
      margin: 0;
      color: #101828;
      font-size: 34px;
      font-weight: 720;
      letter-spacing: 0;
    }

    p {
      max-width: 620px;
      margin: 12px 0 28px;
      color: #667085;
      font-size: 16px;
      line-height: 1.7;
    }
  }

  .chat-empty__actions {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;

    button {
      min-height: 112px;
      padding: 16px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 20px;
      background: #fff;
      text-align: left;
      cursor: pointer;
      transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;

      &:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.28);
        box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
      }

      strong {
        display: block;
        color: #101828;
        font-size: 15px;
      }

      span {
        display: block;
        margin-top: 8px;
        color: #667085;
        font-size: 13px;
        line-height: 1.55;
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

  @media (max-width: 1280px) {
    .chat-main {
      padding-inline: 20px;
    }

    .chat-empty__actions {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .chat-empty,
    .chat-thread {
      animation: none;
    }
  }
</style>
