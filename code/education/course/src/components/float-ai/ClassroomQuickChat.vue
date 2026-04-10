<template>
  <div class="classroom-ai">
    <div class="ai-head">
      <div class="title-row">
        <span class="name">小知</span>
        <span class="course">当前课程：数据库原理</span>
      </div>
    </div>
    <div ref="messagePanel" class="message-panel">
      <div class="assistant-card">
        <div class="intro">
          Hi，我是小知，在数据库原理课程学习中，我可以为你提供以下帮助：
          <br />
          1. 回答数据库学习中的知识点问题
          <br />
          2. 讲解练习/测验里不会的题目和易错点
        </div>
      </div>
      <div v-for="item in messages" :key="item.id" class="bubble-row">
        <div :class="item.role === 'user' ? 'bubble user' : 'bubble assistant'">
          <template v-if="item.role === 'assistant'">
            <div
              v-if="item.reasoning || item.loading"
              class="reasoning-toggle"
              @click="item.showReasoning = !item.showReasoning"
            >
              <span>{{ item.loading ? '正在思考中…' : '深度思考' }}</span>
              <span class="arrow">{{ item.showReasoning ? '▴' : '▾' }}</span>
            </div>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div
              v-if="item.showReasoning && (item.reasoning || item.loading)"
              class="reasoning-content markdown-body"
              v-html="
                renderMarkdown(
                  item.reasoning ||
                    '我先拆分你的问题，再整理成更容易吸收的讲解。'
                )
              "
            />
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div class="markdown-body" v-html="renderMarkdown(item.content)" />
          </template>
          <template v-else>
            {{ item.content }}
          </template>
        </div>
      </div>
    </div>
    <div class="suggestions" v-if="suggestions.length">
      <button
        v-for="s in suggestions"
        :key="s"
        class="suggestion-pill"
        @click="handleSuggestion(s)"
      >
        {{ s }}
      </button>
    </div>
    <div class="input-wrap">
      <a-textarea
        v-model="inputValue"
        :max-length="400"
        :auto-size="{ minRows: 2, maxRows: 5 }"
        placeholder="你可以向我提问"
        @keydown.enter.exact.prevent="handleSend"
      />
      <div class="actions">
        <a-button @click="handleClear">清空会话</a-button>
        <a-button v-if="loading" status="danger" @click="handleStop"
          >暂停回答</a-button
        >
        <a-button type="primary" :loading="loading" @click="handleSend">
          发送
        </a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { createAssistantChatStream } from '@/api/rag';
  import { Message } from '@arco-design/web-vue';
  import { nextTick, ref } from 'vue';
  import { renderMarkdown } from '@/utils/markdown';
  import humanizeAgentReasoning from '@/utils/humanizeAgentReasoning';

  interface ChatItem {
    id: number;
    role: 'user' | 'assistant';
    content: string;
    reasoning: string;
    loading?: boolean;
    showReasoning?: boolean;
  }

  const DEFAULT_SYSTEM_PROMPT =
    '你是数据库原理课的课堂助教，请以教师口吻清晰讲解知识点，优先给出能直接用于考试与刷题的要点。';

  const inputValue = ref('');
  const loading = ref(false);
  const messages = ref<ChatItem[]>([]);
  const suggestions = ref<string[]>([]);
  const messagePanel = ref<HTMLElement | null>(null);
  const localThreadId = ref(`monitor-db-${Date.now()}`);
  let abortController: AbortController | null = null;

  const scrollToBottom = async () => {
    await nextTick();
    if (!messagePanel.value) return;
    messagePanel.value.scrollTop = messagePanel.value.scrollHeight;
  };

  const addAssistantPlaceholder = () => {
    messages.value.push({
      id: Date.now() + Math.floor(Math.random() * 1000),
      role: 'assistant',
      content: '',
      reasoning: '',
      loading: true,
      showReasoning: true,
    });
  };

  const getLastAssistant = () => {
    const last = messages.value[messages.value.length - 1];
    return last && last.role === 'assistant' ? last : null;
  };

  const handleSend = async () => {
    const text = inputValue.value.trim();
    if (!text || loading.value) return;
    inputValue.value = '';
    messages.value.push({
      id: Date.now(),
      role: 'user',
      content: text,
      reasoning: '',
    });
    addAssistantPlaceholder();
    await scrollToBottom();

    loading.value = true;
    abortController = new AbortController();
    let streamError = '';
    let answer = '';
    const thoughts: string[] = [];

    try {
      await createAssistantChatStream(
        text,
        localThreadId.value,
        {
          systemPrompt: DEFAULT_SYSTEM_PROMPT,
          promptKey: 'tutor',
          ragK: 4,
          strictMode: false,
        },
        (event) => {
          const msg = getLastAssistant();
          if (!msg) return;
          if (event.type === 'token') {
            answer += event.content || '';
            msg.content = answer;
          } else if (event.type === 'thought') {
            if (event.content) thoughts.push(event.content);
            msg.reasoning = humanizeAgentReasoning(thoughts.join('\n\n'));
          } else if (event.type === 'suggestions') {
            suggestions.value = Array.isArray(event.data)
              ? event.data.slice(0, 3)
              : [];
          } else if (event.type === 'final') {
            msg.content = (event.content || answer || '').trim();
          } else if (event.type === 'error') {
            streamError = event.content || '生成失败';
          }
          scrollToBottom();
        },
        abortController.signal
      );
      if (streamError) throw new Error(streamError);
    } catch (error: any) {
      const msg = getLastAssistant();
      if (!msg) return;
      if (error?.name === 'AbortError') {
        msg.content = msg.content || '已暂停本次回答。你可以继续提问。';
      } else {
        msg.content = `查询失败：${error?.message || '请稍后重试'}`;
        Message.error('查询失败，请稍后重试');
      }
    } finally {
      const msg = getLastAssistant();
      if (msg) msg.loading = false;
      loading.value = false;
      abortController = null;
      scrollToBottom();
    }
  };

  const handleStop = () => {
    if (!abortController) return;
    abortController.abort();
  };

  const handleSuggestion = (text: string) => {
    inputValue.value = text;
    handleSend();
  };

  const handleClear = () => {
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
    messages.value = [];
    suggestions.value = [];
    loading.value = false;
    localThreadId.value = `monitor-db-${Date.now()}`;
  };
</script>

<style scoped lang="less">
  .classroom-ai {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: linear-gradient(180deg, #e9fbf4 0%, #e4f7ef 100%);
    border-radius: 20px;
    overflow: hidden;
  }
  .ai-head {
    padding: 14px 16px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
    .title-row {
      display: flex;
      align-items: center;
      gap: 12px;
      .name {
        font-size: 26px;
        font-weight: 800;
        color: #1c3a34;
      }
      .course {
        color: #35534b;
        font-size: 15px;
        font-weight: 500;
      }
    }
  }
  .message-panel {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
  }
  .assistant-card {
    background: #fff;
    border-radius: 14px;
    padding: 12px 14px;
    margin-bottom: 12px;
    box-shadow: 0 4px 14px rgba(17, 47, 40, 0.08);
    .intro {
      font-size: 14px;
      line-height: 1.8;
      color: #1f2d2a;
    }
  }
  .bubble-row {
    display: flex;
    margin-bottom: 10px;
  }
  .bubble {
    max-width: 92%;
    border-radius: 14px;
    padding: 10px 12px;
    white-space: pre-wrap;
    line-height: 1.65;
    font-size: 14px;
    box-shadow: 0 4px 10px rgba(15, 23, 42, 0.06);
    &.user {
      margin-left: auto;
      background: #e6f0ff;
      color: #24406b;
    }
    &.assistant {
      background: #fff;
      color: #1f2d2a;
    }
  }
  .reasoning-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: 1px solid rgba(25, 103, 210, 0.2);
    border-radius: 999px;
    padding: 3px 9px;
    font-size: 12px;
    color: #1a57af;
    margin-bottom: 8px;
    cursor: pointer;
    .arrow {
      font-size: 11px;
    }
  }
  .reasoning-content {
    margin-bottom: 8px;
    padding: 8px 10px;
    border-left: 3px solid #bcd3f8;
    background: #f7fbff;
    border-radius: 0 8px 8px 0;
    color: #556987;
    font-size: 13px;
  }
  .suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    padding: 0 16px 10px;
    .suggestion-pill {
      border: 1px solid #c9d4f0;
      border-radius: 999px;
      font-size: 12px;
      padding: 5px 10px;
      background: #f4f7ff;
      color: #3a4f7a;
      cursor: pointer;
    }
  }
  .input-wrap {
    padding: 12px 14px 14px;
    background: rgba(255, 255, 255, 0.5);
    border-top: 1px solid rgba(255, 255, 255, 0.8);
    .actions {
      margin-top: 9px;
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }
  }
</style>
