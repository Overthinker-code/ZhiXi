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
      const thread = await createChatThread();
      const newConversation = {
        id: thread.thread_id,
        title: thread.title,
        createdAt: Date.parse(thread.created_at) || Date.now(),
        lastMessageAt: Date.parse(thread.last_message_at || thread.updated_at) || Date.now(),
        course: thread.course || '',
        knowledgePoint: thread.knowledge_point || '',
        intent: thread.intent || '',
        status: thread.session_status || 'active',
      };
      conversations.value.unshift(newConversation);
      _messagesMap.value[newConversation.id] = [];
      attachDraftMount(newConversation.id);
      currentConversationId.value = newConversation.id;
    };

    /**
     * 进入「空白新会话」：不请求后端、不出现在历史列表，仅清空草稿区消息。
     */
    const enterDraftSession = () => {
      currentConversationId.value = '';
      _messagesMap.value[DRAFT_KEY] = [];
    };

    const loadConversations = async () => {
      try {
        const raw = await fetchChatThreads();
        const threads = Array.isArray(raw) ? raw : [];
        conversations.value = threads.map((thread) => ({
          id: thread.thread_id,
          title: thread.title,
          createdAt: Date.parse(thread.created_at) || Date.now(),
          lastMessageAt:
            Date.parse(thread.last_message_at || thread.updated_at) ||
            Date.parse(thread.created_at) ||
            Date.now(),
          course: thread.course || '',
          knowledgePoint: thread.knowledge_point || '',
          intent: thread.intent || '',
          status: thread.session_status || 'active',
        }));

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
      const storedMessage = {
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
        citation_hints: [],
        ...message,
      };
      _messagesMap.value[key].push(storedMessage);
      // Return the object through Vue's reactive container. Returning the raw
      // object makes later SSE mutations invisible to computed/template users.
      return _messagesMap.value[key][_messagesMap.value[key].length - 1];
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

    /**
     * @param {string} content
     * @param {string=} reasoning_content
     * @param {number=} completion_tokens
     * @param {number=} speed
     * @param {Array<any>=} thoughts
     * @param {boolean=} requiresConfirmation
     * @param {string=} pendingActionId
     * @param {Array<any>=} suggestions
     * @param {Array<any>=} citations
     * @param {string=} confidence
     * @param {string=} groundingMode
     * @param {Record<string, any>=} metrics
     * @param {Array<any>=} agentPhases
     * @param {Array<any>=} reasoningActions
     * @param {Array<any>=} citationHints
     */
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
      metrics = {},
      agentPhases = [],
      reasoningActions = undefined,
      citationHints = undefined
    ) => {
      const key = activeConvKey();
      const msgs = _messagesMap.value[key];
      if (msgs && msgs.length > 0) {
        const idx = msgs.length - 1;
        const prev = msgs[idx];
        msgs[idx] = {
          ...prev,
          content,
          reasoning_content,
          completion_tokens,
          speed,
          thoughts,
          agentPhases,
          requires_confirmation: requiresConfirmation,
          pending_action_id: pendingActionId,
          suggestions,
          citations,
          ...(citationHints !== undefined
            ? { citation_hints: citationHints }
            : {}),
          confidence,
          grounding_mode: groundingMode,
          metrics,
          ...(reasoningActions !== undefined
            ? { reasoningActions: [...reasoningActions] }
            : {}),
        };
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
        const previousTitle = conversation.title;
        conversation.title = newTitle;
        try {
          await updateChatThreadTitle(conversationId, newTitle);
        } catch (error) {
          conversation.title = previousTitle;
          throw error;
        }
      } else {
        await updateChatThreadTitle(conversationId, newTitle);
      }
    };

    const deleteConversation = async (conversationId) => {
      if (!String(conversationId).startsWith('local-')) {
        await deleteChatThread(conversationId);
      }
      const index = conversations.value.findIndex(
        (c) => c.id === conversationId
      );
      if (index !== -1) {
        conversations.value.splice(index, 1);
        delete _messagesMap.value[conversationId];
        delete _mountedFileMap.value[conversationId];
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
      const results = await Promise.allSettled(
        list.map((conversation) =>
          String(conversation.id).startsWith('local-')
            ? Promise.resolve()
            : deleteChatThread(conversation.id)
        )
      );
      const failed = [];

      results.forEach((result, index) => {
        const conversation = list[index];
        if (result.status === 'fulfilled') {
          delete _messagesMap.value[conversation.id];
          delete _mountedFileMap.value[conversation.id];
        } else {
          failed.push(conversation);
        }
      });

      conversations.value = failed;
      if (failed.length) {
        currentConversationId.value = failed[0].id;
        throw new Error(`${failed.length} 个会话未能删除，请检查后端后重试`);
      }

      _mountedFileMap.value = {};
      enterDraftSession();
    };

    return {
      conversations,
      currentConversationId,
      currentConversation,
      currentMessages,
      isLoading,
      _messagesMap,
      _mountedFileMap,
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
      pick: [
        'conversations',
        'currentConversationId',
        '_messagesMap',
        '_mountedFileMap',
      ],
    },
  }
);

export { useChatStore };
export default useChatStore;
