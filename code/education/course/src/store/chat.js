import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import {
  createChatThread,
  deleteChatThread,
  fetchChatThreads,
  updateChatThreadTitle,
} from '@/api/rag';

/** 未落库会话：仅内存消息，进入智能助手页默认停留在此，首条发送时才创建后端线程 */
const DRAFT_KEY = '';

const useChatStore = defineStore(
  'llm-chat',
  () => {
    const conversations = ref([]);

    const currentConversationId = ref('');

    const isLoading = ref(false);

    const _messagesMap = ref({});
    const _mountedFileMap = ref({});

    const activeConvKey = () =>
      currentConversationId.value === '' ||
      currentConversationId.value == null
        ? DRAFT_KEY
        : currentConversationId.value;

    const currentConversation = computed(() => {
      const id = currentConversationId.value;
      if (id === '') {
        return {
          id: '',
          title: '新对话',
          createdAt: Date.now(),
          get messages() {
            return _messagesMap.value[DRAFT_KEY] || [];
          },
          set messages(val) {
            _messagesMap.value[DRAFT_KEY] = val;
          },
        };
      }
      const meta = conversations.value.find((conv) => conv.id === id);
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

    const currentMessages = computed(
      () => _messagesMap.value[activeConvKey()] || []
    );

    const createConversation = async () => {
      const attachDraftMount = (newId) => {
        const draftMount = _mountedFileMap.value[DRAFT_KEY];
        if (draftMount) {
          _mountedFileMap.value[newId] = draftMount;
          delete _mountedFileMap.value[DRAFT_KEY];
        }
      };
      try {
        const thread = await createChatThread();
        const newConversation = {
          id: thread.thread_id,
          title: thread.title,
          createdAt: Date.parse(thread.created_at) || Date.now(),
        };
        conversations.value.unshift(newConversation);
        _messagesMap.value[newConversation.id] = [];
        attachDraftMount(newConversation.id);
        currentConversationId.value = newConversation.id;
      } catch {
        const id = `local-${Date.now()}`;
        const newConversation = {
          id,
          title: '新对话',
          createdAt: Date.now(),
        };
        conversations.value.unshift(newConversation);
        _messagesMap.value[newConversation.id] = [];
        attachDraftMount(newConversation.id);
        currentConversationId.value = newConversation.id;
      }
    };

    /**
     * 进入「空白新会话」：不请求后端、不出现在历史列表，仅清空草稿区消息。
     */
    const enterDraftSession = () => {
      currentConversationId.value = '';
      _messagesMap.value[DRAFT_KEY] = [];
    };

    const loadConversations = async () => {
      const localConversations = conversations.value.slice();
      try {
        const raw = await fetchChatThreads();
        const threads = Array.isArray(raw) ? raw : [];
        conversations.value = threads.map((thread) => ({
          id: thread.thread_id,
          title: thread.title,
          createdAt: Date.parse(thread.created_at) || Date.now(),
        }));

        if (!conversations.value.length && localConversations.length) {
          await Promise.all(
            localConversations.map((conv) =>
              createChatThread(conv.title, conv.id).catch(() => null)
            )
          );
          const refreshed = await fetchChatThreads();
          const list = Array.isArray(refreshed) ? refreshed : [];
          conversations.value = list.map((thread) => ({
            id: thread.thread_id,
            title: thread.title,
            createdAt: Date.parse(thread.created_at) || Date.now(),
          }));
        }

        const cid = currentConversationId.value;
        if (cid === '') {
          return;
        }
        const exists = conversations.value.some((c) => c.id === cid);
        if (!exists) {
          if (conversations.value.length > 0) {
            currentConversationId.value = conversations.value[0].id;
          } else {
            currentConversationId.value = '';
            if (!_messagesMap.value[DRAFT_KEY]) {
              _messagesMap.value[DRAFT_KEY] = [];
            }
          }
        }
      } catch {
        if (!conversations.value.length) {
          currentConversationId.value = '';
          if (!_messagesMap.value[DRAFT_KEY]) {
            _messagesMap.value[DRAFT_KEY] = [];
          }
        }
      }
    };

    const switchConversation = (conversationId) => {
      currentConversationId.value = conversationId;
    };

    const addMessage = (message) => {
      const key = activeConvKey();
      if (!_messagesMap.value[key]) {
        _messagesMap.value[key] = [];
      }
      _messagesMap.value[key].push({
        id: Date.now(),
        timestamp: new Date().toISOString(),
        thoughts: [],
        requires_confirmation: false,
        pending_action_id: '',
        citations: [],
        confidence: '',
        grounding_mode: '',
        suggestions: [],
        metrics: {},
        ...message,
      });
    };

    const setConversationMessages = (conversationId, messages) => {
      _messagesMap.value[conversationId] = messages;
    };

    const setCurrentConversationMessages = (messages) => {
      const key = activeConvKey();
      _messagesMap.value[key] = messages;
    };

    const getConversationMessages = (conversationId) => {
      const id =
        conversationId === '' || conversationId == null
          ? DRAFT_KEY
          : conversationId;
      return _messagesMap.value[id] || [];
    };

    const setIsLoading = (value) => {
      isLoading.value = value;
    };

    const updateLastMessage = (
      content,
      reasoning_content,
      completion_tokens,
      speed,
      thoughts = [],
      requiresConfirmation = false,
      pendingActionId = '',
      suggestions = [],
      citations = [],
      confidence = '',
      groundingMode = '',
      metrics = {}
    ) => {
      const key = activeConvKey();
      const msgs = _messagesMap.value[key];
      if (msgs && msgs.length > 0) {
        const lastMessage = msgs[msgs.length - 1];
        lastMessage.content = content;
        lastMessage.reasoning_content = reasoning_content;
        lastMessage.completion_tokens = completion_tokens;
        lastMessage.speed = speed;
        lastMessage.thoughts = thoughts;
        lastMessage.requires_confirmation = requiresConfirmation;
        lastMessage.pending_action_id = pendingActionId;
        lastMessage.suggestions = suggestions;
        lastMessage.citations = citations;
        lastMessage.confidence = confidence;
        lastMessage.grounding_mode = groundingMode;
        lastMessage.metrics = metrics;
      }
    };

    const setMountedFile = (conversationId, fileMeta) => {
      if (conversationId === undefined || conversationId === null) return;
      const key = conversationId === '' ? DRAFT_KEY : conversationId;
      _mountedFileMap.value[key] = fileMeta;
    };

    const getMountedFile = (conversationId) => {
      if (conversationId === undefined || conversationId === null) return null;
      const key = conversationId === '' ? DRAFT_KEY : conversationId;
      return _mountedFileMap.value[key] || null;
    };

    const getLastMessage = () => {
      const key = activeConvKey();
      const msgs = _messagesMap.value[key];
      if (msgs && msgs.length > 0) {
        return msgs[msgs.length - 1];
      }
      return null;
    };

    const patchConversationTitleLocal = (conversationId, newTitle) => {
      const conversation = conversations.value.find(
        (c) => c.id === conversationId
      );
      if (conversation) {
        conversation.title = newTitle;
      }
    };

    const updateConversationTitle = async (conversationId, newTitle) => {
      const conversation = conversations.value.find(
        (c) => c.id === conversationId
      );
      if (conversation) {
        conversation.title = newTitle;
      }
      try {
        await updateChatThreadTitle(conversationId, newTitle);
      } catch (error) {
        // ignore title sync errors
      }
    };

    const deleteConversation = async (conversationId) => {
      try {
        await deleteChatThread(conversationId);
      } catch {
        /* 仍执行本地移除，避免列表无法操作 */
      }
      const index = conversations.value.findIndex(
        (c) => c.id === conversationId
      );
      if (index !== -1) {
        conversations.value.splice(index, 1);
        delete _messagesMap.value[conversationId];
      }
      if (conversationId === currentConversationId.value) {
        if (conversations.value.length > 0) {
          currentConversationId.value = conversations.value[0].id;
        } else {
          enterDraftSession();
        }
      }
    };

    const deleteAllConversations = async () => {
      const list = [...conversations.value];
      for (const c of list) {
        try {
          await deleteChatThread(c.id);
        } catch {
          /* */
        }
        delete _messagesMap.value[c.id];
      }
      conversations.value = [];
      _mountedFileMap.value = {};
      enterDraftSession();
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
      getConversationMessages,
      setIsLoading,
      updateLastMessage,
      getLastMessage,
      setMountedFile,
      getMountedFile,
      loadConversations,
      createConversation,
      enterDraftSession,
      switchConversation,
      patchConversationTitleLocal,
      updateConversationTitle,
      deleteConversation,
      deleteAllConversations,
    };
  },
  {
    persist: {
      pick: ['conversations', 'currentConversationId'],
    },
  }
);

export { useChatStore };
export default useChatStore;
