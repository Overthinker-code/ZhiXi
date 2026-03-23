import { computed } from 'vue';
import { useChatStore } from '@/store/chat';
import { useSettingStore } from '@/store/setting';
import { messageHandler } from '@/utils/messageHandler';
import {
  createAssistantChat,
  fetchAssistantSettings,
  fetchChatHistory,
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

      const response = await createAssistantChat(
        messageContent.text,
        currentThreadId.value,
        {
          systemPrompt: settingStore.settings.customSystemPrompt || '',
          ragK: settingStore.settings.ragK as 3 | 4 | 5,
          promptKey: settingStore.settings.promptKey,
          strictMode: settingStore.settings.strictMode,
        }
      );
      const { content, reasoning } = parseAssistantResponse(
        response.response || ''
      );
      chatStore.updateLastMessage(content, reasoning, 0, 0);
    } catch (error) {
      chatStore.updateLastMessage(
        'Sorry, something went wrong. Please try again later.'
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
  };
}
