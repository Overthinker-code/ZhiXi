import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
import { Message } from '@arco-design/web-vue';
import { renderMarkdown } from '@/utils/markdown';
import { useChatStore } from '@/store/chat';
import { askSelectionQuery } from '@/api/rag';
import { useSettingStore } from '@/store/setting';
import { messageHandler } from '@/utils/messageHandler';

const promptTemplates = [
  {
    key: 'explain',
    label: '📖 解释概念',
    prompt: (selected: string) =>
      `请用简白易懂的方式解释以下数据库概念：\n"${selected}"\n\n要求：先给定义，再举实例，最后说明实际应用。`,
  },
  {
    key: 'example',
    label: '💡 举个例子',
    prompt: (selected: string) =>
      `关于"${selected}"这个概念，请给出：\n1. 一个具体的现实生活中的例子\n2. 对应的数据库表结构示例\n3. 相关的SQL语句`,
  },
  {
    key: 'summarize',
    label: '📝 总结要点',
    prompt: (selected: string) =>
      `请总结以下代码段或内容的核心要点：\n"${selected}"\n\n要求：用3-5条关键点概括，每条简洁清晰`,
  },
  {
    key: 'deepdive',
    label: '🔍 深入讲解',
    prompt: (selected: string) =>
      `请对"${selected}"进行深入讲解，包括：\n1. 原理和机制\n2. 常见的做法或最佳实践\n3. 可能的陷阱和注意事项`,
  },
];

/** 划词菜单：fixed 定位须使用 getBoundingClientRect 的视口坐标，勿加 scrollX/scrollY */
export function useSelectionQueryMenu(getContextSource: () => string) {
  const chatStore = useChatStore();
  const settingStore = useSettingStore();
  const showContextMenu = ref(false);
  const contextMenuStyle = reactive({
    position: 'fixed' as const,
    top: '0px',
    left: '0px',
  });
  const selectedText = ref('');
  const surroundingContext = ref('');
  const isLoadingResponse = ref(false);
  const aiResponse = ref('');
  const currentThreadId = computed(
    () => chatStore.currentConversationId || 'selection-notes-thread'
  );

  const getThreadId = () => currentThreadId.value;

  function closeMenu() {
    showContextMenu.value = false;
  }

  function positionMenuNearSelection(range: Range) {
    const rect = range.getBoundingClientRect();
    if (!rect.width && !rect.height) return false;
    const pad = 8;
    const menuW = 280;
    const menuH = 200;
    let left = rect.left;
    let top = rect.bottom + 6;
    if (left + menuW > window.innerWidth - pad) {
      left = window.innerWidth - menuW - pad;
    }
    if (left < pad) left = pad;
    if (top + menuH > window.innerHeight - pad) {
      top = Math.max(pad, rect.top - menuH - 6);
    }
    contextMenuStyle.left = `${left}px`;
    contextMenuStyle.top = `${top}px`;
    return true;
  }

  function handleTextSelection(containerSelector: string, _event?: Event) {
    requestAnimationFrame(() => {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed) {
        closeMenu();
        return;
      }
      const raw = selection.toString().trim();
      if (!raw) {
        closeMenu();
        return;
      }
      const anchor = selection.anchorNode;
      const el =
        anchor?.nodeType === Node.TEXT_NODE
          ? (anchor.parentElement as HTMLElement | null)
          : (anchor as HTMLElement | null);
      if (!el?.closest(containerSelector)) {
        closeMenu();
        return;
      }

      selectedText.value = raw;
      const fullText = getContextSource();
      const startIndex = fullText.indexOf(raw);
      if (startIndex >= 0) {
        const endIndex = startIndex + raw.length;
        const contextStart = Math.max(0, startIndex - 100);
        const contextEnd = Math.min(fullText.length, endIndex + 100);
        surroundingContext.value = fullText.substring(contextStart, contextEnd);
      } else {
        surroundingContext.value = raw;
      }

      let range: Range;
      try {
        range = selection.getRangeAt(0);
      } catch {
        closeMenu();
        return;
      }
      if (!positionMenuNearSelection(range)) {
        closeMenu();
        return;
      }
      showContextMenu.value = true;
    });
  }

  async function sendAIQuery(promptKey: string) {
    if (!selectedText.value) {
      Message.info('请先选中文本');
      return;
    }
    const template = promptTemplates.find((t) => t.key === promptKey);
    if (!template) return;

    isLoadingResponse.value = true;
    aiResponse.value = '';
    closeMenu();

    try {
      const response = await askSelectionQuery(
        selectedText.value,
        surroundingContext.value,
        getThreadId(),
        {
          systemPrompt: template.prompt(selectedText.value),
          ragK: settingStore.settings.ragK as 3 | 4 | 5,
          promptKey: 'custom',
          strictMode: settingStore.settings.strictMode,
          activeTools: settingStore.settings.activeTools || [],
          maxTokens: 2000,
          temperature: 0.7,
        }
      );
      if (response?.response) {
        aiResponse.value = response.response;
        chatStore.addMessage(
          messageHandler.formatMessage('user', selectedText.value)
        );
        chatStore.addMessage(
          messageHandler.formatMessage('assistant', response.response)
        );
      } else {
        Message.error('AI 响应为空');
      }
    } catch (error) {
      Message.error(
        `查询失败: ${error instanceof Error ? error.message : String(error)}`
      );
    } finally {
      isLoadingResponse.value = false;
    }
  }

  function onDocMouseDown(e: MouseEvent) {
    const t = e.target as HTMLElement;
    if (t.closest('.notes-context-menu')) return;
    closeMenu();
  }

  onMounted(() => {
    document.addEventListener('mousedown', onDocMouseDown);
    document.addEventListener('scroll', closeMenu, true);
  });
  onUnmounted(() => {
    document.removeEventListener('mousedown', onDocMouseDown);
    document.removeEventListener('scroll', closeMenu, true);
  });

  return {
    promptTemplates,
    showContextMenu,
    contextMenuStyle,
    selectedText,
    isLoadingResponse,
    aiResponse,
    renderedResponse: computed(() =>
      aiResponse.value ? renderMarkdown(aiResponse.value) : ''
    ),
    handleTextSelection,
    sendAIQuery,
    closeMenu,
  };
}

