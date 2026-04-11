<script setup>
  import '@/assets/styles/main.scss';
  import { useChatStore } from '@/store/chat';
  import { streamInterventionEvents } from '@/api/rag';
  import { useChat } from '@/hooks/useChat';
  import { Plus } from '@element-plus/icons-vue';
  import 'animate.css';
  import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

  import ChatInput from './components/ChatInput.vue';
  import ChatMessage from './components/ChatMessage.vue';
  import DialogEdit from './components/DialogEdit.vue';
  import PopupMenu from './components/PopupMenu.vue';
  import SettingsPanel from './components/SettingsPanel.vue';

  const chatStore = useChatStore();
  const {
    currentMessages,
    isLoading,
    currentThreadId,
    currentTitle,
    sendMessage,
    regenerateLastMessage,
    loadHistory,
    loadAssistantSettings,
    createNewChat,
    stopGenerating,
    sendSelectionQuery,
    confirmPendingAction,
  } = useChat();

  const messagesContainer = ref(null);
  const autoStickToBottom = ref(true);
  const messageStreamSignature = computed(() => {
    const last = currentMessages.value[currentMessages.value.length - 1];
    return [
      currentMessages.value.length,
      last?.id || '',
      (last?.content || '').length,
      (last?.thoughts || []).length,
      Boolean(last?.loading),
    ].join(':');
  });
  const syncAutoStickStatus = () => {
    const el = messagesContainer.value;
    if (!el) return;
    const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    autoStickToBottom.value = distanceToBottom < 80;
  };
  const scrollToBottom = () => {
    nextTick(() => {
      const el = messagesContainer.value;
      if (!el) return;
      el.scrollTop = el.scrollHeight;
    });
  };
  watch(messageStreamSignature, () => {
    if (autoStickToBottom.value) {
      scrollToBottom();
    }
  });

  onMounted(async () => {
    await Promise.all([chatStore.loadConversations(), loadAssistantSettings()]);
    await createNewChat();
    scrollToBottom();
  });

  watch(
    () => currentThreadId.value,
    async (newThreadId) => {
      if (!newThreadId) return;
      await loadHistory(newThreadId);
    },
    { immediate: true }
  );

  const handleSend = async (messageContent) => {
    await sendMessage(messageContent);
  };
  const handleStop = () => {
    stopGenerating();
  };

  const handleSuggestion = async (text) => {
    if (!text) return;
    await sendMessage({ text, files: [] });
  };

  const handleRegenerate = async () => {
    await regenerateLastMessage();
  };

  const handleResumeAction = async ({ pendingActionId, approve }) => {
    const result = await confirmPendingAction(pendingActionId, approve);
    const text = result?.message || (approve ? '计划已确认。' : '已取消计划。');
    chatStore.addMessage({
      role: 'assistant',
      content: text,
      reasoning_content: '',
      thoughts: ['🧑‍💼 HITL 已完成人工确认。'],
    });
  };

  const settingDrawer = ref(null);
  const popupMenu = ref(null);

  const handleNewChat = async () => {
    await createNewChat();
  };

  const dialogEdit = ref(null);
  const selectionMenu = ref({
    visible: false,
    text: '',
    x: 0,
    y: 0,
    context: '',
  });

  const hideSelectionMenu = () => {
    selectionMenu.value.visible = false;
  };

  const handleMouseUp = () => {
    const selection = window.getSelection();
    const selectedText = selection?.toString()?.trim() || '';
    if (
      !selection ||
      !selectedText ||
      selectedText.length < 2 ||
      selectedText.length > 200
    ) {
      hideSelectionMenu();
      return;
    }
    try {
      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      if (!rect.width && !rect.height) {
        hideSelectionMenu();
        return;
      }
      const full = selection.anchorNode?.textContent || '';
      const anchorOffset = selection.anchorOffset || 0;
      const start = Math.max(0, anchorOffset - 120);
      const end = Math.min(
        full.length,
        anchorOffset + selectedText.length + 120
      );
      selectionMenu.value = {
        visible: true,
        text: selectedText,
        x: rect.left + window.scrollX,
        y: rect.bottom + window.scrollY + 8,
        context: full.slice(start, end),
      };
    } catch {
      hideSelectionMenu();
    }
  };

  const askWithSelection = async (mode) => {
    const selectedText = selectionMenu.value.text;
    if (!selectedText) return;
    const prefixMap = {
      explain: '请解释这个概念并给一个简单例子：',
      example: '请基于当前上下文给一个更贴近课堂的例子：',
      bug: '请从代码排错角度解释这个概念的常见问题：',
    };
    await sendSelectionQuery({
      selectedText: `${prefixMap[mode] || ''}${selectedText}`,
      surroundingContext: selectionMenu.value.context,
      videoTime: '01:10',
      courseModule: '并发控制',
    });
    hideSelectionMenu();
    window.getSelection()?.removeAllRanges();
  };

  const handleDocumentClick = (e) => {
    const { target } = e;
    if (!(target instanceof HTMLElement)) return;
    if (!target.closest('.selection-menu')) hideSelectionMenu();
  };

  onMounted(() => {
    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('scroll', hideSelectionMenu, true);
    document.addEventListener('click', handleDocumentClick);
    streamInterventionEvents((event) => {
      if (event.type !== 'intervention') return;
      chatStore.addMessage({
        role: 'assistant',
        content: event.content,
        reasoning_content: '',
        thoughts: ['📢 Intervention_Agent 主动介入提醒。'],
      });
    }).catch(() => {
      // keep silent in demo mode
    });
  });

  onUnmounted(() => {
    document.removeEventListener('mouseup', handleMouseUp);
    document.removeEventListener('scroll', hideSelectionMenu, true);
    document.removeEventListener('click', handleDocumentClick);
  });
</script>

<template>
  <div class="chat-container">
    <div class="chat-header">
      <div class="header-left">
        <PopupMenu ref="popupMenu" />
        <el-button class="new-chat-btn" :icon="Plus" @click="handleNewChat">
          新对话
        </el-button>
        <div class="divider"></div>
        <div class="title-wrapper">
          <h1 class="chat-title">{{ currentTitle }}</h1>
          <button
            class="edit-btn"
            @click="
              dialogEdit.openDialog(chatStore.currentConversationId, 'edit')
            "
          >
            <img src="@/assets/photo/编辑.png" alt="edit" />
          </button>
        </div>
      </div>

      <div class="header-right">
        <el-tooltip content="设置" placement="top">
          <button class="action-btn" @click="settingDrawer.openDrawer()">
            <img src="@/assets/photo/设置.png" alt="settings" />
          </button>
        </el-tooltip>
      </div>
    </div>

    <div
      class="messages-container"
      ref="messagesContainer"
      @scroll="syncAutoStickStatus"
    >
      <template v-if="currentMessages.length > 0">
        <chat-message
          v-for="(message, index) in currentMessages"
          :key="message.id"
          :message="message"
          :is-last-assistant-message="
            index === currentMessages.length - 1 && message.role === 'assistant'
          "
          @regenerate="handleRegenerate"
          @resume-action="handleResumeAction"
          @suggestion="handleSuggestion"
        />
      </template>
      <div v-else class="empty-state">
        <div class="empty-content">
          <img src="@/assets/photo/对话.png" alt="chat" class="empty-icon" />
          <h2>开始对话吧</h2>
          <p>有什么想和我聊的吗？</p>
        </div>
      </div>
    </div>

    <div
      v-if="selectionMenu.visible"
      class="selection-menu"
      :style="{ left: `${selectionMenu.x}px`, top: `${selectionMenu.y}px` }"
    >
      <button class="menu-btn" @click="askWithSelection('explain')">
        解释
      </button>
      <button class="menu-btn" @click="askWithSelection('example')">
        举例
      </button>
      <button class="menu-btn" @click="askWithSelection('bug')">找Bug</button>
    </div>

    <div class="chat-input-container">
      <chat-input :loading="isLoading" @send="handleSend" @stop="handleStop" />
    </div>

    <SettingsPanel ref="settingDrawer" />
    <DialogEdit ref="dialogEdit" />
  </div>
</template>

<style lang="scss" scoped>
  .chat-container {
    --assistant-primary: #1967d2;
    --assistant-primary-dark: #0f4ca8;
    --assistant-accent: #ff9f43;
    --assistant-border: #d8e4f3;
    --assistant-surface: rgba(255, 255, 255, 0.76);
    --assistant-text-main: #11243d;
    --assistant-text-sub: #5a6b84;
    position: relative;
    height: calc(100vh - 140px);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    font-family: 'Noto Sans SC', 'IBM Plex Sans', 'SF Pro Display',
      'PingFang SC', sans-serif;
  }

  .chat-header {
    position: relative;
    z-index: 2;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.9rem 1.1rem;
    background: var(--assistant-surface);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(216, 228, 243, 0.9);

    .header-left {
      display: flex;
      align-items: center;
      gap: 0.85rem;
      min-width: 0;

      .new-chat-btn {
        height: 2rem;
        padding: 0 0.8rem;
        border-radius: 999px;
        border: 1px solid rgba(25, 103, 210, 0.25);
        background: linear-gradient(
          135deg,
          rgba(25, 103, 210, 0.14),
          rgba(25, 103, 210, 0.05)
        );
        color: var(--assistant-primary-dark);
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        transition: all 0.2s ease;

        &:hover {
          color: #fff;
          border-color: var(--assistant-primary);
          background: linear-gradient(
            135deg,
            var(--assistant-primary),
            var(--assistant-primary-dark)
          );
          box-shadow: 0 8px 16px rgba(25, 103, 210, 0.25);
        }

        :deep(.el-icon) {
          margin-right: 4px;
          font-size: 0.9rem;
        }
      }

      .divider {
        width: 1px;
        height: 1.5rem;
        background: linear-gradient(
          180deg,
          transparent,
          rgba(90, 107, 132, 0.35),
          transparent
        );
      }

      .title-wrapper {
        min-width: 0;
        display: flex;
        align-items: center;
        gap: 0.45rem;

        .chat-title {
          margin: 0;
          font-size: 1.02rem;
          font-weight: 650;
          color: var(--assistant-text-main);
          letter-spacing: 0.015em;
          line-height: 1.3;
          white-space: normal;
        }

        .edit-btn {
          opacity: 0;
          width: 1rem;
          height: 1rem;
          padding: 0;
          border: none;
          background: none;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          transition: opacity 0.2s ease;

          img {
            width: 100%;
            height: 100%;
          }
        }

        &:hover .edit-btn {
          opacity: 0.8;
        }
      }
    }

    .header-right {
      .action-btn {
        width: 2.1rem;
        height: 2.1rem;
        padding: 0;
        border: 1px solid rgba(17, 36, 61, 0.08);
        background: rgba(255, 255, 255, 0.9);
        border-radius: 10px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;

        img {
          width: 1.2rem;
          height: 1.2rem;
        }

        &:hover {
          border-color: rgba(25, 103, 210, 0.25);
          box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
          transform: translateY(-1px);
        }
      }
    }
  }

  .messages-container {
    position: relative;
    z-index: 1;
    flex: 1;
    overflow-y: auto;
    width: min(100%, 940px);
    margin: 0 auto;
    padding: 1.2rem 1.1rem 1.5rem;

    &::-webkit-scrollbar {
      width: 8px;
    }

    &::-webkit-scrollbar-thumb {
      border-radius: 999px;
      background: linear-gradient(180deg, #c9d7ea, #aebfd8);
      border: 2px solid transparent;
      background-clip: padding-box;
    }

    &::-webkit-scrollbar-track {
      background: transparent;
    }
  }

  .empty-state {
    min-height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2.4rem 1rem;

    .empty-content {
      width: min(100%, 460px);
      text-align: center;
      background: rgba(255, 255, 255, 0.78);
      border: 1px solid rgba(216, 228, 243, 0.95);
      border-radius: 18px;
      padding: 2rem 1.2rem;
      box-shadow: 0 14px 30px rgba(15, 23, 42, 0.07);
      animation: float-in 0.35s ease;

      .empty-icon {
        width: 60px;
        height: 60px;
        opacity: 0.72;
        margin-bottom: 1rem;
      }

      h2 {
        margin: 0 0 0.4rem;
        color: var(--assistant-text-main);
        font-size: 1.24rem;
        font-weight: 700;
      }

      p {
        margin: 0;
        color: var(--assistant-text-sub);
        font-size: 0.94rem;
      }
    }
  }

  .chat-input-container {
    position: relative;
    z-index: 2;
    width: min(100%, 940px);
    margin: 0 auto;
    padding: 0 1.1rem 1.1rem;
  }

  .selection-menu {
    position: fixed;
    z-index: 1200;
    display: inline-flex;
    gap: 6px;
    padding: 6px;
    border-radius: 10px;
    border: 1px solid rgba(17, 36, 61, 0.12);
    background: rgba(255, 255, 255, 0.96);
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14);

    .menu-btn {
      border: none;
      border-radius: 8px;
      padding: 4px 8px;
      background: #edf4ff;
      color: #11458e;
      font-size: 12px;
      cursor: pointer;

      &:hover {
        background: #d9e9ff;
      }
    }
  }

  @keyframes float-in {
    from {
      transform: translateY(10px);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  @media (max-width: 960px) {
    .chat-container {
      height: calc(100vh - 140px);
    }

    .chat-header {
      padding: 0.8rem 0.85rem;

      .header-left {
        gap: 0.6rem;

        .new-chat-btn {
          padding: 0 0.65rem;
        }

        .title-wrapper .chat-title {
          font-size: 0.94rem;
        }
      }
    }

    .messages-container {
      padding: 0.9rem 0.75rem 1.1rem;
    }

    .chat-input-container {
      padding: 0 0.75rem 0.8rem;
    }
  }
</style>
