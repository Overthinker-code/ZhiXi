<script setup>
  import '@/assets/styles/main.scss';
  import { useChatStore } from '@/store/chat';
  import { streamInterventionEvents } from '@/api/rag';
  import { useChat } from '@/hooks/useChat';
  import 'animate.css';
  import { computed, nextTick, onActivated, onMounted, onUnmounted, ref, watch } from 'vue';
  import { onBeforeRouteLeave, useRoute } from 'vue-router';

  import ChatInput from './components/ChatInput.vue';
  import ChatMessage from './components/ChatMessage.vue';
  import DialogEdit from './components/DialogEdit.vue';
  import PopupMenu from './components/PopupMenu.vue';
  import SettingsPanel from './components/SettingsPanel.vue';
  import DeveloperPanel from './components/DeveloperPanel.vue';
  import { useSettingStore } from '@/store/setting';

  const chatStore = useChatStore();
  const settingStore = useSettingStore();
  const route = useRoute();
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
  /* 不包含 thoughts：避免多智能体流式事件频繁触发整页滚到底，用户可停留在上方阅读 */
  const messageStreamSignature = computed(() => {
    const last = currentMessages.value[currentMessages.value.length - 1];
    return [
      currentMessages.value.length,
      last?.id || '',
      (last?.content || '').length,
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

  /** 离开智能助手路由后再进入（含 keep-alive 激活）时，打开空白草稿且不新建后端线程 */
  const refreshDraftOnNextActivate = ref(false);

  onBeforeRouteLeave(() => {
    refreshDraftOnNextActivate.value = true;
  });

  onMounted(async () => {
    await loadAssistantSettings();
    await chatStore.loadConversations();
    chatStore.enterDraftSession();
    await nextTick();
    scrollToBottom();
  });

  onActivated(async () => {
    await chatStore.loadConversations();
    if (refreshDraftOnNextActivate.value) {
      chatStore.enterDraftSession();
      refreshDraftOnNextActivate.value = false;
    }
    await nextTick();
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
  const developerPanelVisible = ref(false);

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
        x: rect.left,
        y: rect.bottom + 8,
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

  const handleDeveloperShortcut = (event) => {
    if (!settingStore.developerPanelEnabled) return;
    if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'd') {
      event.preventDefault();
      developerPanelVisible.value = !developerPanelVisible.value;
    }
  };

  onMounted(() => {
    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('scroll', hideSelectionMenu, true);
    document.addEventListener('click', handleDocumentClick);
    document.addEventListener('keydown', handleDeveloperShortcut);
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
    document.removeEventListener('keydown', handleDeveloperShortcut);
  });

  const initialPrompt = computed(() => String(route.query.prompt || ''));

  const quickChips = [
    '总结本章',
    '讲解这道题',
    '生成提纲',
    '复习薄弱点',
  ];
</script>

<template>
  <div class="chat-container">
    <div class="chat-header">
      <div class="header-left">
        <PopupMenu ref="popupMenu" />
        <a-button class="new-chat-btn" type="primary" size="small" @click="handleNewChat">
          <template #icon><icon-plus /></template>
          新对话
        </a-button>
        <div class="conversation-tab">
          <span class="tab-dot" />
          <h1 class="chat-title">{{ currentTitle || '当前对话' }}</h1>
          <button
            v-if="chatStore.currentConversationId"
            type="button"
            class="edit-btn"
            @click="
              dialogEdit.openDialog(chatStore.currentConversationId, 'edit')
            "
          >
            <icon-edit />
          </button>
        </div>
      </div>

      <div class="header-right">
        <a-tooltip content="设置" position="top">
          <a-button class="settings-btn" type="text" shape="circle" @click="settingDrawer.openDrawer()">
            <icon-settings />
          </a-button>
        </a-tooltip>
      </div>
    </div>

    <div
      class="messages-container"
      ref="messagesContainer"
      @scroll="syncAutoStickStatus"
    >
      <TransitionGroup name="msg-slide" tag="div" class="messages-list">
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
      </TransitionGroup>
      <div v-if="currentMessages.length === 0" class="empty-state">
        <div class="empty-bubble" aria-hidden="true">
          <icon-message />
        </div>
        <h2>开始对话吧</h2>
        <p>选择快捷指令，或直接输入你的学习问题</p>
        <div class="quick-chips">
          <button
            v-for="chip in quickChips"
            :key="chip"
            type="button"
            class="quick-chip"
            @click="handleSuggestion(chip)"
          >
            {{ chip }}
          </button>
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
      <div class="input-shell">
        <chat-input
          :loading="isLoading"
          :initial-text="initialPrompt"
          @send="handleSend"
          @stop="handleStop"
        />
      </div>
    </div>

    <SettingsPanel ref="settingDrawer" />
    <DialogEdit ref="dialogEdit" />
    <DeveloperPanel
      :visible="developerPanelVisible"
      @update:visible="(value) => (developerPanelVisible = value)"
    />
  </div>
</template>

<style lang="less" scoped>
  .chat-container {
    position: relative;
    height: calc(100vh - 153px);
    min-height: 620px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    font-family: var(--zy-font-display);
    background: #fafbff;
  }

  .chat-header {
    position: relative;
    z-index: 2;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 22px;
    background: #fff;
    border-bottom: 1px solid rgba(99, 102, 241, 0.08);

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }

    .new-chat-btn {
      border-radius: var(--zy-radius-pill);
      font-weight: 700;
      box-shadow: 0 6px 16px rgba(99, 102, 241, 0.28);
    }

    .conversation-tab {
      min-width: 0;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border-radius: var(--zy-radius-pill);
      background: var(--zy-bg-tag);
      border: 1px solid rgba(99, 102, 241, 0.12);

      .tab-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--zy-color-brand);
        flex-shrink: 0;
      }

      .chat-title {
        margin: 0;
        font-size: var(--zy-text-sm);
        font-weight: 650;
        color: var(--zy-color-text-primary);
        line-height: 1.35;
        max-width: 280px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .edit-btn {
        opacity: 0.5;
        width: 20px;
        height: 20px;
        padding: 0;
        border: none;
        background: none;
        cursor: pointer;
        color: var(--zy-color-text-secondary);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        transition: opacity var(--zy-duration-fast) ease;

        &:hover {
          opacity: 1;
          color: var(--zy-color-brand);
        }
      }
    }

    .settings-btn {
      color: var(--zy-color-text-secondary);
      font-size: 18px;

      &:hover {
        color: var(--zy-color-brand);
        background: var(--zy-bg-tag);
      }
    }
  }

  .messages-container {
    position: relative;
    z-index: 1;
    flex: 1;
    overflow-y: auto;
    width: min(100%, 1080px);
    margin: 0 auto;
    padding: 24px 28px 16px;

    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-thumb {
      border-radius: var(--zy-radius-pill);
      background: rgba(99, 102, 241, 0.28);
    }
  }

  .messages-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .msg-slide-enter-active {
    transition: all var(--zy-duration-normal) var(--zy-ease-spring);
  }

  .msg-slide-enter-from {
    opacity: 0;
    transform: translateY(12px);
  }

  .msg-slide-move {
    transition: transform var(--zy-duration-normal) ease;
  }

  .empty-state {
    min-height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
    text-align: center;

    .empty-bubble {
      width: 88px;
      height: 88px;
      border-radius: 28px 28px 28px 8px;
      background: linear-gradient(135deg, #eef2ff, #c7d2fe);
      color: var(--zy-color-brand);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 40px;
      margin-bottom: 20px;
      box-shadow: 0 16px 36px rgba(99, 102, 241, 0.2);
    }

    h2 {
      margin: 0 0 8px;
      color: var(--zy-color-text-primary);
      font-size: 22px;
      font-weight: 800;
    }

    p {
      margin: 0 0 20px;
      color: var(--zy-color-text-secondary);
      font-size: var(--zy-text-sm);
    }
  }

  .quick-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: center;
    max-width: 520px;
  }

  .quick-chip {
    padding: 8px 16px;
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: var(--zy-radius-pill);
    background: #fff;
    color: var(--zy-color-brand-hover);
    font-size: var(--zy-text-sm);
    font-weight: 600;
    cursor: pointer;
    transition:
      background var(--zy-duration-fast) ease,
      box-shadow var(--zy-duration-fast) ease;

    &:hover {
      background: var(--zy-bg-tag);
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.12);
    }
  }

  .chat-input-container {
    position: relative;
    z-index: 2;
    width: min(100%, 1080px);
    margin: 0 auto;
    padding: 12px 28px 18px;
    background: transparent;
  }

  .input-shell {
    border-radius: 20px;
    background: #fff;
    border: 1px solid rgba(99, 102, 241, 0.12);
    box-shadow: 0 12px 32px rgba(15, 23, 42, 0.06);
    padding: 4px;
  }

  .selection-menu {
    position: fixed;
    z-index: 1200;
    display: inline-flex;
    gap: 6px;
    padding: 6px;
    border-radius: var(--zy-radius-sm);
    border: 1px solid rgba(99, 102, 241, 0.14);
    background: rgba(255, 255, 255, 0.98);
    box-shadow: var(--zy-shadow-card);

    .menu-btn {
      border: none;
      border-radius: 6px;
      padding: 4px 10px;
      background: var(--zy-bg-tag);
      color: var(--zy-color-text-primary);
      font-size: var(--zy-text-xs);
      cursor: pointer;

      &:hover {
        background: rgba(99, 102, 241, 0.18);
        color: var(--zy-color-brand);
      }
    }
  }

  @media (max-width: 960px) {
    .chat-container {
      height: calc(100vh - 210px);
      min-height: 460px;
    }

    .chat-header {
      padding: 10px 12px;
    }

    .messages-container,
    .chat-input-container {
      width: 100%;
      padding-left: 12px;
      padding-right: 12px;
    }
  }
</style>
