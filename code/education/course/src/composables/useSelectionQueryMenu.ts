import {
  ref,
  reactive,
  computed,
  onMounted,
  onUnmounted,
} from 'vue';
import { Message } from '@arco-design/web-vue';
import { renderMarkdown, stripMarkdownCodeToolbar } from '@/utils/markdown';
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

type ViewportRect = {
  top: number;
  left: number;
  right: number;
  bottom: number;
  width: number;
  height: number;
};

export type AnswerPanelBounds = {
  left: number;
  top: number;
  width: number;
  height: number;
};

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
  const localSelectionThreadId = ref(`selection-notes-${Date.now()}`);
  const lastSelectionViewportRect = ref<ViewportRect | null>(null);
  const answerPanelBounds = ref<AnswerPanelBounds | null>(null);
  const answerPanelSession = ref(0);
  const typewriterLen = ref(0);
  /** 划词菜单中心 → 答案面板的短暂引导线（视口坐标） */
  const bridgeLine = ref<{
    active: boolean;
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  }>({ active: false, x1: 0, y1: 0, x2: 0, y2: 0 });
  let twTimer: ReturnType<typeof setInterval> | null = null;
  let bridgeTimer: ReturnType<typeof setTimeout> | null = null;

  const sanitizeSelectionAnswer = (raw: string) =>
    (raw || '')
      .replace(/<think>[\s\S]*?<\/think>/gi, '')
      .replace(/<analysis>[\s\S]*?<\/analysis>/gi, '')
      .replace(/<\/?final>/gi, '')
      .trim();

  const currentThreadId = computed(() => chatStore.currentConversationId || '');

  const getThreadId = () =>
    currentThreadId.value || localSelectionThreadId.value;

  const showAnswerPanel = computed(
    () => isLoadingResponse.value || Boolean(aiResponse.value)
  );

  const isTypingAnswer = computed(
    () =>
      Boolean(aiResponse.value) && typewriterLen.value < aiResponse.value.length
  );

  function stopTypewriter() {
    if (twTimer) {
      clearInterval(twTimer);
      twTimer = null;
    }
  }

  function startTypewriter() {
    stopTypewriter();
    const full = aiResponse.value;
    if (!full) return;
    typewriterLen.value = 0;
    const len = full.length;
    const perTick = Math.max(2, Math.ceil(len / 100));
    twTimer = setInterval(() => {
      if (typewriterLen.value >= len) {
        stopTypewriter();
        typewriterLen.value = len;
        return;
      }
      typewriterLen.value = Math.min(len, typewriterLen.value + perTick);
    }, 22);
  }

  function closeMenu() {
    showContextMenu.value = false;
  }

  function triggerBridgeToPanel() {
    if (bridgeTimer) {
      clearTimeout(bridgeTimer);
      bridgeTimer = null;
    }
    const r = lastSelectionViewportRect.value;
    const b = answerPanelBounds.value;
    if (!r || !b) return;
    const x1 = (r.left + r.right) / 2;
    const y1 = (r.top + r.bottom) / 2;
    const x2 = b.left + 20;
    const y2 = b.top + 48;
    bridgeLine.value = { active: true, x1, y1, x2, y2 };
    bridgeTimer = setTimeout(() => {
      bridgeLine.value = { ...bridgeLine.value, active: false };
      bridgeTimer = null;
    }, 720);
  }

  function syncBoundsFromSelection() {
    const defaultH = 380;
    const panelW = Math.min(
      440,
      Math.max(300, Math.floor(window.innerWidth * 0.38))
    );
    const r = lastSelectionViewportRect.value;
    if (!r) {
      answerPanelBounds.value = {
        left: Math.max(12, window.innerWidth - panelW - 24),
        top: 100,
        width: panelW,
        height: defaultH,
      };
      return;
    }
    const margin = 12;
    const spaceRight = window.innerWidth - r.right - margin;
    let left: number;
    if (spaceRight >= panelW) {
      left = r.right + margin;
    } else {
      left = r.left - panelW - margin;
    }
    left = Math.max(
      margin,
      Math.min(left, window.innerWidth - panelW - margin)
    );
    let top = r.top;
    top = Math.max(60, Math.min(top, window.innerHeight - defaultH - 12));
    const maxH = Math.min(520, window.innerHeight - top - 12);
    const height = Math.min(defaultH, maxH);
    answerPanelBounds.value = { left, top, width: panelW, height };
  }

  function positionMenuNearSelection(range: Range) {
    const rect = range.getBoundingClientRect();
    if (!rect.width && !rect.height) return false;
    lastSelectionViewportRect.value = {
      top: rect.top,
      left: rect.left,
      right: rect.right,
      bottom: rect.bottom,
      width: rect.width,
      height: rect.height,
    };
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

  function resolveSelectionContainer(
    range: Range,
    containerSelector: string
  ): HTMLElement | null {
    const node = range.commonAncestorContainer;
    const base =
      node.nodeType === Node.ELEMENT_NODE
        ? (node as HTMLElement)
        : node.parentElement;
    return base?.closest(containerSelector) || null;
  }

  function buildSurroundingContextFromRange(
    containerEl: HTMLElement,
    range: Range,
    selected: string
  ) {
    try {
      const beforeRange = range.cloneRange();
      beforeRange.selectNodeContents(containerEl);
      beforeRange.setEnd(range.startContainer, range.startOffset);
      const fullText = containerEl.innerText || containerEl.textContent || '';
      const startIndex = beforeRange.toString().length;
      const endIndex = startIndex + selected.length;
      const contextStart = Math.max(0, startIndex - 120);
      const contextEnd = Math.min(fullText.length, endIndex + 120);
      return fullText.slice(contextStart, contextEnd) || selected;
    } catch {
      const fallback = getContextSource();
      const startIndex = fallback.indexOf(selected);
      if (startIndex < 0) return selected;
      const endIndex = startIndex + selected.length;
      return fallback.slice(Math.max(0, startIndex - 120), endIndex + 120);
    }
  }

  function handleTextSelection(containerSelector: string, _event?: Event) {
    requestAnimationFrame(() => {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed) {
        closeMenu();
        return;
      }
      let range: Range;
      try {
        range = selection.getRangeAt(0);
      } catch {
        closeMenu();
        return;
      }
      const raw = range.toString().trim();
      if (!raw) {
        closeMenu();
        return;
      }
      if (raw.length < 2 || raw.length > 400) {
        closeMenu();
        return;
      }
      const containerEl = resolveSelectionContainer(range, containerSelector);
      if (!containerEl) {
        closeMenu();
        return;
      }

      selectedText.value = raw;
      surroundingContext.value = buildSurroundingContextFromRange(
        containerEl,
        range,
        raw
      );
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

    stopTypewriter();
    typewriterLen.value = 0;
    aiResponse.value = '';
    answerPanelSession.value += 1;
    syncBoundsFromSelection();
    isLoadingResponse.value = true;
    closeMenu();
    triggerBridgeToPanel();

    try {
      if (!currentThreadId.value) {
        // 课堂内容页无主会话时，划词问答使用独立临时线程，避免历史串话导致答非所问
        localSelectionThreadId.value = `selection-notes-${Date.now()}`;
      }
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
          maxTokens: Math.max(Number(settingStore.settings.maxTokens) || 0, 8192),
          temperature: 0.5,
        }
      );
      if (response?.response) {
        const cleanAnswer = sanitizeSelectionAnswer(response.response);
        aiResponse.value = cleanAnswer;
        chatStore.addMessage(
          messageHandler.formatMessage('user', selectedText.value)
        );
        chatStore.addMessage(
          messageHandler.formatMessage('assistant', cleanAnswer || response.response)
        );
        startTypewriter();
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

  function clearAnswerPanel() {
    stopTypewriter();
    typewriterLen.value = 0;
    aiResponse.value = '';
    isLoadingResponse.value = false;
    lastSelectionViewportRect.value = null;
    answerPanelBounds.value = null;
    bridgeLine.value = { active: false, x1: 0, y1: 0, x2: 0, y2: 0 };
    if (bridgeTimer) {
      clearTimeout(bridgeTimer);
      bridgeTimer = null;
    }
  }

  function onDocMouseDown(e: MouseEvent) {
    const t = e.target as HTMLElement;
    if (t.closest('.notes-context-menu')) return;
    if (t.closest('.selection-ai-answer-panel')) return;
    if (t.closest('.selection-ai-resize-handle')) return;
    closeMenu();
  }

  onMounted(() => {
    document.addEventListener('mousedown', onDocMouseDown);
    document.addEventListener('scroll', closeMenu, true);
  });
  onUnmounted(() => {
    document.removeEventListener('mousedown', onDocMouseDown);
    document.removeEventListener('scroll', closeMenu, true);
    stopTypewriter();
    if (bridgeTimer) {
      clearTimeout(bridgeTimer);
      bridgeTimer = null;
    }
  });

  const renderedResponse = computed(() => {
    const full = aiResponse.value;
    if (!full) return '';
    const slice = full.slice(0, typewriterLen.value);
    if (!slice) return '';
    return stripMarkdownCodeToolbar(renderMarkdown(slice));
  });

  return {
    promptTemplates,
    showContextMenu,
    contextMenuStyle,
    selectedText,
    isLoadingResponse,
    aiResponse,
    showAnswerPanel,
    answerPanelBounds,
    answerPanelSession,
    isTypingAnswer,
    renderedResponse,
    bridgeLine,
    handleTextSelection,
    sendAIQuery,
    closeMenu,
    clearAnswerPanel,
  };
}
