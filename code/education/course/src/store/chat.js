import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import {
  createChatThread,
  deleteChatThread,
  fetchChatThreads,
  updateChatThreadTitle,
} from '@/api/rag';

export const useChatStore = defineStore(
  'llm-chat',
  () => {
    // 所有对话列表（元信息：id, title, createdAt）
    const conversations = ref([]);

    // 当前选中的对话ID
    const currentConversationId = ref('');

    // 加载状态
    const isLoading = ref(false);

    // 当前对话的消息（仅内存，不持久化）
    const _messagesMap = ref({});

    // 获取当前对话
    const currentConversation = computed(() => {
      const meta = conversations.value.find(
        (conv) => conv.id === currentConversationId.value
      );
      if (!meta) return null;
      return {
        ...meta,
        get messages() {
          return _messagesMap.value[meta.id] || [];
        },
        set messages(val) {
          _messagesMap.value[meta.id] = val;
        },
      };
    });

    // 获取当前对话的消息
    const currentMessages = computed(
      () => _messagesMap.value[currentConversationId.value] || []
    );

    const loadConversations = async () => {
      const localConversations = conversations.value.slice();
      const localCurrentId = currentConversationId.value;
      try {
        const threads = await fetchChatThreads();
        conversations.value = threads.map((thread) => ({
          id: thread.thread_id,
          title: thread.title,
          createdAt: Date.parse(thread.created_at) || Date.now(),
        }));

        if (!conversations.value.length) {
          if (localConversations.length) {
            for (const conv of localConversations) {
              try {
                await createChatThread(conv.title, conv.id);
              } catch (error) {
                // ignore single thread sync errors
              }
            }
            const refreshed = await fetchChatThreads();
            conversations.value = refreshed.map((thread) => ({
              id: thread.thread_id,
              title: thread.title,
              createdAt: Date.parse(thread.created_at) || Date.now(),
            }));
          } else {
            await createConversation();
            return;
          }
        }

        const exists = conversations.value.find(
          (conv) => conv.id === currentConversationId.value
        );
        if (!exists) {
          currentConversationId.value = localCurrentId || conversations.value[0].id;
        }
      } catch (error) {
        if (!conversations.value.length) {
          await createConversation();
        }
      }
    };

    // 创建新对话
    const createConversation = async () => {
      const thread = await createChatThread();
      const newConversation = {
        id: thread.thread_id,
        title: thread.title,
        createdAt: Date.parse(thread.created_at) || Date.now(),
      };
      conversations.value.unshift(newConversation);
      _messagesMap.value[newConversation.id] = [];
      currentConversationId.value = newConversation.id;
    };

    // 切换对话
    const switchConversation = (conversationId) => {
      currentConversationId.value = conversationId;
    };

    // 添加消息到当前对话
    const addMessage = (message) => {
      const id = currentConversationId.value;
      if (!id) return;
      if (!_messagesMap.value[id]) {
        _messagesMap.value[id] = [];
      }
      _messagesMap.value[id].push({
        id: Date.now(),
        timestamp: new Date().toISOString(),
        ...message,
      });
    };

    const setConversationMessages = (conversationId, messages) => {
      _messagesMap.value[conversationId] = messages;
    };

    const setCurrentConversationMessages = (messages) => {
      const id = currentConversationId.value;
      if (id) {
        _messagesMap.value[id] = messages;
      }
    };

    const setIsLoading = (value) => {
      isLoading.value = value;
    };

    const updateLastMessage = (
      content,
      reasoning_content,
      completion_tokens,
      speed
    ) => {
      const msgs = _messagesMap.value[currentConversationId.value];
      if (msgs && msgs.length > 0) {
        const lastMessage = msgs[msgs.length - 1];
        lastMessage.content = content;
        lastMessage.reasoning_content = reasoning_content;
        lastMessage.completion_tokens = completion_tokens;
        lastMessage.speed = speed;
      }
    };

    const getLastMessage = () => {
      const msgs = _messagesMap.value[currentConversationId.value];
      if (msgs && msgs.length > 0) {
        return msgs[msgs.length - 1];
      }
      return null;
    };

    // 更新对话标题
    const updateConversationTitle = async (conversationId, newTitle) => {
      try {
        await updateChatThreadTitle(conversationId, newTitle);
      } catch (error) {
        return;
      }
      const conversation = conversations.value.find(
        (c) => c.id === conversationId
      );
      if (conversation) {
        conversation.title = newTitle;
      }
    };

    // 删除对话
    const deleteConversation = async (conversationId) => {
      try {
        await deleteChatThread(conversationId);
      } catch (error) {
        return;
      }
      const index = conversations.value.findIndex(
        (c) => c.id === conversationId
      );
      if (index !== -1) {
        conversations.value.splice(index, 1);
        delete _messagesMap.value[conversationId];

        // 如果删除后没有对话了，创建一个新对话
        if (conversations.value.length === 0) {
          await createConversation();
        }
        // 如果删除的是当前对话，切换到第一个对话
        else if (conversationId === currentConversationId.value) {
          currentConversationId.value = conversations.value[0].id;
        }
      }
    };

    return {
      conversations,
      currentConversationId,
      currentConversation,
      currentMessages,
      isLoading,
      addMessage,
      setConversationMessages,
      setCurrentConversationMessages,
      setIsLoading,
      updateLastMessage,
      getLastMessage,
      loadConversations,
      createConversation,
      switchConversation,
      updateConversationTitle,
      deleteConversation,
    };
  },
  {
    persist: {
      pick: ['conversations', 'currentConversationId'],
    },
  }
);
