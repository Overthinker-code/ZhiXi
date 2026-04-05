import { computed } from 'vue';
import { Message } from '@arco-design/web-vue';
import { getToken } from '@/utils/auth';
import { useChatStore } from '@/store/chat';
import { useSettingStore } from '@/store/setting';
import { messageHandler } from '@/utils/messageHandler';
import {
  createAssistantChat,
  createAssistantChatStream,
  fetchAssistantSettings,
  fetchChatHistory,
  askSelectionQuery,
  resumeChatAction,
} from '@/api/rag';

/**
 * Parse raw assistant response that may contain <think>/<analysis>/<final> XML tags.
 * Returns { content, reasoning } where reasoning is the thinking process.
 */
export function parseAssistantResponse(rawResponse: string) {
  if (!rawResponse) {
    return { content: '', reasoning: '' };
  }

  const thinkMatch = rawResponse.match(/<think>([\s\S]*?)<\/think>/i);
  const analysisMatch = rawResponse.match(
    /<analysis>([\s\S]*?)<\/analysis>/i
  );
  const finalMatch = rawResponse.match(/<final>([\s\S]*?)<\/final>/i);

  if (finalMatch) {
    return {
      reasoning: (thinkMatch?.[1] || analysisMatch?.[1] || '').trim(),
      content: finalMatch[1].trim(),
    };
  }

  if (thinkMatch || analysisMatch) {
    const reasoning = (thinkMatch?.[1] || analysisMatch?.[1] || '').trim();
    const afterThink = rawResponse
      .replace(/<think>[\s\S]*?<\/think>/i, '')
      .replace(/<analysis>[\s\S]*?<\/analysis>/i, '')
      .trim();
    return {
      reasoning,
      content: afterThink,
    };
  }

  return { content: rawResponse.trim(), reasoning: '' };
}

/**
 * Composable for managing AI chat interactions.
 * Extracts conversation logic from LegacyAssistantPanel into a reusable hook.
 */
export function useChat() {
  const chatStore = useChatStore();
  const settingStore = useSettingStore();

  const currentThreadId = computed(() => chatStore.currentConversationId);
  const currentMessages = computed(() => chatStore.currentMessages);
  const isLoading = computed(() => chatStore.isLoading);
  const currentTitle = computed(
    () => chatStore.currentConversation?.title || 'LLM Chat'
  );

  /**
   * Load chat history for a specific thread from the backend.
   */
  async function loadHistory(targetThreadId: string) {
    if (!targetThreadId) return;
    try {
      const history = await fetchChatHistory(targetThreadId);
      const ordered = [...history].reverse();
      const historyMessages: any[] = [];
      ordered.forEach((item: any) => {
        if (item.user_input) {
          historyMessages.push({
            ...messageHandler.formatMessage('user', item.user_input),
            timestamp: item.created_at,
          });
        }
        if (item.response) {
          const { content, reasoning } = parseAssistantResponse(item.response);
          historyMessages.push({
            ...messageHandler.formatMessage('assistant', content, reasoning),
            timestamp: item.created_at,
          });
        }
      });
      chatStore.setConversationMessages(targetThreadId, historyMessages);
    } catch (error) {
      // ignore load history errors
    }
  }

  /**
   * Load assistant runtime settings (model, prompt options, etc.) from backend.
   */
  async function loadAssistantSettings() {
    try {
      const settings = await fetchAssistantSettings();
      if (settings?.model) {
        settingStore.settings.modelDisplay = settings.model;
      }
      if (settings?.prompt_options?.length) {
        settingStore.promptOptions = settings.prompt_options;
      }
      if (settings?.tool_options?.length) {
        settingStore.toolOptions = settings.tool_options;
      }
      if (
        settings?.default_active_tools?.length &&
        !(settingStore.settings.activeTools || []).length
      ) {
        settingStore.settings.activeTools = settings.default_active_tools;
      }
      if (
        settings?.rag_k_default &&
        ![3, 4, 5].includes(settingStore.settings.ragK)
      ) {
        settingStore.settings.ragK = settings.rag_k_default;
      }
      if (typeof settingStore.settings.strictMode !== 'boolean') {
        settingStore.settings.strictMode = Boolean(
          settings?.strict_mode_default
        );
      }
      const hasSelectedPrompt = settingStore.promptOptions.some(
        (item: any) => item.key === settingStore.settings.promptKey
      );
      if (!hasSelectedPrompt) {
        settingStore.settings.promptKey =
          settings?.default_prompt_key ||
          settingStore.promptOptions[0]?.key ||
          'tutor';
      }
    } catch (error) {
      // keep local defaults
    }
  }

  /**
   * Send a user message and get an AI response.
   */
  async function sendMessage(messageContent: { text: string; files?: any[] }) {
    if (!currentThreadId.value) {
      if (!getToken()) {
        Message.error('请先登录后再使用 AI 对话');
        return;
      }
      try {
        await chatStore.createConversation();
      } catch (err: unknown) {
        const fromApi =
          err instanceof Error && err.message
            ? err.message
            : '无法创建对话，请检查网络与登录状态后刷新页面';
        Message.error(fromApi);
        return;
      }
    }
    if (!currentThreadId.value) {
      Message.error('当前没有会话 ID，请刷新页面或点击「新对话」');
      return;
    }
    try {
      chatStore.addMessage(
        messageHandler.formatMessage(
          'user',
          messageContent.text,
          '',
          messageContent.files
        )
      );
      chatStore.addMessage(messageHandler.formatMessage('assistant', '', ''));

      chatStore.setIsLoading(true);
      const lastMessage = chatStore.getLastMessage();
      if (lastMessage) lastMessage.loading = true;

      const commonOptions = {
        systemPrompt: settingStore.settings.customSystemPrompt || '',
        ragK: settingStore.settings.ragK as 3 | 4 | 5,
        promptKey: settingStore.settings.promptKey,
        strictMode: settingStore.settings.strictMode,
        activeTools: settingStore.settings.activeTools || [],
        maxTokens: settingStore.settings.maxTokens,
        temperature: settingStore.settings.temperature,
        topP: settingStore.settings.topP,
        topK: settingStore.settings.topK,
      };

      const shouldStream = Boolean(settingStore.settings.stream);
      if (shouldStream) {
        const thoughts: string[] = [];
        let answer = '';
        let streamError = '';
        let requiresConfirmation = false;
        let pendingActionId = '';
        await createAssistantChatStream(
          messageContent.text,
          currentThreadId.value,
          commonOptions,
          (event) => {
            if (event.type === 'thought') {
              if (event.content) thoughts.push(event.content);
              chatStore.updateLastMessage(
                answer,
                thoughts.join('\n\n'),
                0,
                0,
                [...thoughts],
                requiresConfirmation,
                pendingActionId
              );
            } else if (event.type === 'token') {
              answer += event.content || '';
              chatStore.updateLastMessage(
                answer,
                thoughts.join('\n\n'),
                0,
                0,
                [...thoughts],
                requiresConfirmation,
                pendingActionId
              );
            } else if (event.type === 'final') {
              answer = event.content || answer;
              requiresConfirmation = Boolean(event.requires_confirmation);
              pendingActionId = event.pending_action_id || '';
              chatStore.updateLastMessage(
                answer,
                thoughts.join('\n\n'),
                0,
                0,
                [...thoughts],
                requiresConfirmation,
                pendingActionId
              );
            } else if (event.type === 'error') {
              streamError = event.content || 'Stream failed';
            }
          }
        );
        if (streamError) {
          throw new Error(streamError);
        }
      } else {
        const response = await createAssistantChat(
          messageContent.text,
          currentThreadId.value,
          commonOptions
        );
        const { content, reasoning } = parseAssistantResponse(
          response.response || ''
        );
        chatStore.updateLastMessage(content, reasoning, 0, 0);
      }
    } catch (error: unknown) {
      const detail =
        error instanceof Error && error.message
          ? error.message.slice(0, 500)
          : '';
      chatStore.updateLastMessage(
        detail
          ? `生成未成功：${detail}`
          : '当前连接时空有点波动，请稍后再试哦~'
      );
    } finally {
      chatStore.setIsLoading(false);
      const lastMessage = chatStore.getLastMessage();
      if (lastMessage) lastMessage.loading = false;
    }
  }

  /**
   * Regenerate the last AI response by re-sending the previous user message.
   */
  async function regenerateLastMessage() {
    try {
      const msgs = chatStore.currentMessages;
      if (msgs.length < 2) return;
      const lastUserMessage = msgs[msgs.length - 2];
      msgs.splice(-2, 2);
      await sendMessage({
        text: lastUserMessage.content,
        files: lastUserMessage.files,
      });
    } catch (error) {
      // ignore
    }
  }

  /**
   * Create a new conversation and clear its messages.
   */
  async function createNewChat() {
    await chatStore.createConversation();
    chatStore.setCurrentConversationMessages([]);
  }

  async function sendSelectionQuery(params: {
    selectedText: string;
    surroundingContext: string;
    videoTime?: string;
    courseModule?: string;
  }) {
    const text = params.selectedText?.trim();
    if (!text) return;
    chatStore.addMessage(messageHandler.formatMessage('user', `划词提问：${text}`));
    chatStore.addMessage(messageHandler.formatMessage('assistant', '', ''));
    chatStore.setIsLoading(true);
    const lastMessage = chatStore.getLastMessage();
    if (lastMessage) lastMessage.loading = true;

    try {
      const response = await askSelectionQuery(
        text,
        params.surroundingContext,
        currentThreadId.value,
        {
          systemPrompt: settingStore.settings.customSystemPrompt || '',
          ragK: settingStore.settings.ragK as 3 | 4 | 5,
          promptKey: settingStore.settings.promptKey,
          strictMode: settingStore.settings.strictMode,
          activeTools: settingStore.settings.activeTools || [],
          maxTokens: settingStore.settings.maxTokens,
          temperature: settingStore.settings.temperature,
          topP: settingStore.settings.topP,
          topK: settingStore.settings.topK,
          selectedText: text,
          surroundingContext: params.surroundingContext,
          videoTime: params.videoTime,
          courseModule: params.courseModule,
        }
      );
      const { content, reasoning } = parseAssistantResponse(response.response || '');
      chatStore.updateLastMessage(content, reasoning, 0, 0);
    } catch (error) {
      chatStore.updateLastMessage(
        '当前提问人数较多，正在为您从缓存中检索，请稍后重试。'
      );
    } finally {
      chatStore.setIsLoading(false);
      const msg = chatStore.getLastMessage();
      if (msg) msg.loading = false;
    }
  }

  async function confirmPendingAction(pendingActionId: string, approve = true) {
    if (!pendingActionId) return null;
    try {
      return await resumeChatAction(pendingActionId, approve);
    } catch {
      return null;
    }
  }

  return {
    // State
    currentThreadId,
    currentMessages,
    isLoading,
    currentTitle,
    // Actions
    sendMessage,
    regenerateLastMessage,
    loadHistory,
    loadAssistantSettings,
    createNewChat,
    sendSelectionQuery,
    confirmPendingAction,
  };
}
