<template>
  <div class="classroom-ai">
    <div class="ai-head">
      <div class="title-row">
        <span class="name">小慕</span>
        <span class="course">当前课程：程序设计基础（C&C++）</span>
      </div>
      <div class="banner">免费模式可试用20次，开通认证学习服务享无限次问答</div>
    </div>

    <div ref="messagePanel" class="message-panel">
      <div class="assistant-card">
        <div class="intro">
          Hi，我是小慕，在课程学习中，我可以为你提供以下帮助：
          <br />
          1. 回答课程学习中的任何知识问题
          <br />
          2. 为你讲解测验/作业/考试不懂的题目
        </div>
      </div>

      <div v-for="item in messages" :key="item.id" class="bubble-row">
        <div :class="item.role === 'user' ? 'bubble user' : 'bubble assistant'">
          {{ item.content }}
        </div>
      </div>

      <div v-if="loading" class="bubble-row">
        <div class="bubble assistant">内容生成中...</div>
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
        :auto-size="{ minRows: 2, maxRows: 4 }"
        placeholder="你可以向我提问"
        @keydown.enter.exact.prevent="handleSend"
      />
      <div class="actions">
        <a-button @click="handleClear">清空会话</a-button>
        <a-button type="primary" :loading="loading" @click="handleSend">
          发送
        </a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { createAssistantChat } from '@/api/rag';
  import { Message } from '@arco-design/web-vue';
  import { nextTick, ref } from 'vue';

  interface ChatItem {
    id: number;
    role: 'user' | 'assistant';
    content: string;
  }

  const DEFAULT_SYSTEM_PROMPT =
    '你是数据库课程的课堂助教，请围绕数据库基础、SQL、事务与并发控制做简洁清晰的讲解。回答后给出便于继续学习的一句话建议。';

  const inputValue = ref('');
  const loading = ref(false);
  const messages = ref<ChatItem[]>([]);
  const suggestions = ref<string[]>([]);
  const messagePanel = ref<HTMLElement | null>(null);
  const localThreadId = ref(`monitor-db-${Date.now()}`);

  const parseResponse = (raw: string) => {
    const final = raw.match(/<final>([\s\S]*?)<\/final>/i);
    const text = final ? final[1].trim() : raw.trim();
    return text;
  };

  const splitSuggestions = (text: string) => {
    const m = text.match(/\[SUGGESTIONS\]([\s\S]*)/i);
    if (!m) return { body: text, sug: [] as string[] };
    const body = text.slice(0, m.index).trim();
    const sug = m[1]
      .split('\n')
      .map((line) => line.replace(/^\s*[-\d.:：、)]*\s*/, '').trim())
      .filter(Boolean)
      .slice(0, 3);
    return { body, sug };
  };

  const scrollToBottom = async () => {
    await nextTick();
    if (!messagePanel.value) return;
    messagePanel.value.scrollTop = messagePanel.value.scrollHeight;
  };

  const appendMessage = (role: 'user' | 'assistant', content: string) => {
    messages.value.push({
      id: Date.now() + Math.floor(Math.random() * 1000),
      role,
      content,
    });
  };

  const handleSend = async () => {
    const text = inputValue.value.trim();
    if (!text || loading.value) return;
    inputValue.value = '';
    appendMessage('user', text);
    await scrollToBottom();

    loading.value = true;
    try {
      const res = await createAssistantChat(text, localThreadId.value, {
        systemPrompt: DEFAULT_SYSTEM_PROMPT,
        promptKey: 'tutor',
        ragK: 4,
        strictMode: false,
      });
      const parsed = parseResponse(res?.response || '');
      const { body, sug } = splitSuggestions(parsed);
      appendMessage(
        'assistant',
        body || '我整理了一下你的问题，可以继续追问我。'
      );
      suggestions.value = sug;
    } catch (error) {
      Message.error('查询失败，请稍后重试');
      appendMessage('assistant', '抱歉，刚刚网络有波动，请再发一次问题。');
    } finally {
      loading.value = false;
      await scrollToBottom();
    }
  };

  const handleSuggestion = (text: string) => {
    inputValue.value = text;
    handleSend();
  };

  const handleClear = () => {
    messages.value = [];
    suggestions.value = [];
    localThreadId.value = `monitor-db-${Date.now()}`;
  };
</script>

<style scoped lang="less">
  .classroom-ai {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: #dff6ee;
    border-radius: 16px;
    overflow: hidden;
  }
  .ai-head {
    padding: 14px 14px 8px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
    .title-row {
      display: flex;
      align-items: center;
      gap: 10px;
      .name {
        font-size: 28px;
        font-weight: 700;
      }
      .course {
        color: #3f4f4a;
        font-size: 14px;
      }
    }
    .banner {
      margin-top: 8px;
      font-size: 12px;
      color: #3f6760;
      background: rgba(255, 255, 255, 0.5);
      border-radius: 12px;
      padding: 6px 10px;
      text-align: center;
    }
  }
  .message-panel {
    flex: 1;
    overflow-y: auto;
    padding: 14px;
  }
  .assistant-card {
    background: #fff;
    border-radius: 14px;
    padding: 12px;
    margin-bottom: 10px;
    .intro {
      font-size: 14px;
      line-height: 1.8;
      color: #1f2d2a;
    }
  }
  .bubble-row {
    display: flex;
    margin-bottom: 8px;
  }
  .bubble {
    max-width: 90%;
    border-radius: 12px;
    padding: 8px 10px;
    white-space: pre-wrap;
    line-height: 1.6;
    font-size: 13px;
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
  .suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 0 14px 8px;
    .suggestion-pill {
      border: 1px solid #c9d4f0;
      border-radius: 999px;
      font-size: 12px;
      padding: 4px 9px;
      background: #f4f7ff;
      color: #3a4f7a;
      cursor: pointer;
    }
  }
  .input-wrap {
    padding: 10px 12px 12px;
    background: rgba(255, 255, 255, 0.35);
    .actions {
      margin-top: 8px;
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }
  }
</style>
