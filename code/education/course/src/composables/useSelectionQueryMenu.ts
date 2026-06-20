import {
  ref,
  reactive,
  computed,
  onMounted,
  onUnmounted,
} from 'vue';
import { Message } from '@arco-design/web-vue';
import { renderMarkdown, stripMarkdownCodeToolbar } from '@/utils/markdown';
import {
  askSelectionQuery,
  normalizeCitationItems,
  type ChatMetrics,
  type CitationItem,
} from '@/api/rag';
import { useSettingStore } from '@/store/setting';

const promptTemplates = [
  {
    key: 'explain',
    label: '解释概念',
    prompt: (selected: string, context: string) =>
      `请结合当前课程内容解释被选中的知识点：\n"${selected}"\n\n课堂上下文：\n${context || '暂无额外上下文'}\n\n要求：先给定义，再说明适用条件，最后给一个贴合本课程的例子。`,
  },
  {
    key: 'example',
    label: '举个例子',
    prompt: (selected: string, context: string) =>
      `关于"${selected}"，请基于当前课程举例说明。\n\n课堂上下文：\n${context || '暂无额外上下文'}\n\n请输出：\n1. 一个具体场景\n2. 这个场景中哪些条件对应被选知识点\n3. 学生最容易混淆的地方`,
  },
  {
    key: 'summarize',
    label: '总结要点',
    prompt: (selected: string, context: string) =>
      `请总结以下课堂内容的核心要点：\n"${selected}"\n\n课堂上下文：\n${context || '暂无额外上下文'}\n\n要求：用 3-5 条关键点概括，并指出它和当前课程其它知识点的关系。`,
  },
  {
    key: 'deepdive',
    label: '深入讲解',
    prompt: (selected: string, context: string) =>
      `请对"${selected}"进行课程内深入讲解。\n\n课堂上下文：\n${context || '暂无额外上下文'}\n\n请包括：\n1. 原理和机制\n2. 与前后知识点的关系\n3. 常见误区和检查题\n4. 一个可继续追问的问题`,
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
// AI辅助生成：Trae IDE, 2026-04-22
export function useSelectionQueryMenu(getContextSource: () => string) {
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
  const responseCitations = ref<CitationItem[]>([]);
  const responseCitationHints = ref<CitationItem[]>([]);
  const responseConfidence = ref('');
  const responseGroundingMode = ref('');
  const responseMetrics = ref<ChatMetrics | undefined>();
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
  let activeController: AbortController | null = null;
  let requestSeq = 0;
  let disposed = false;

  const sanitizeSelectionAnswer = (raw: string) =>
    (raw || '')
      .replace(/<think>[\s\S]*?<\/think>/gi, '')
      .replace(/<analysis>[\s\S]*?<\/analysis>/gi, '')
      .replace(/<hr\s*\/?>/gi, '\n')
      .replace(/<\/?final>/gi, '')
      .split(/\r?\n/)
      .filter((line) => {
        const trimmed = line.trim();
        if (!trimmed) return true;
        if (/^([-*_=])\1{2,}$/.test(trimmed)) return false;
        if (/^[＿_—─━―－﹘﹣]{3,}$/.test(trimmed)) return false;
        if (/^(?:\|\s*:?-{3,}:?\s*)+\|?$/.test(trimmed)) return false;
        return true;
      })
      .join('\n')
      .replace(/(?:^|\s)(?:[-*_=\u2014\u2015\u2500\u2501\uFF3F]){3,}(?=\s|$)/g, ' ')
      .replace(/\|\s*:?-{3,}:?\s*(?=\|)/g, '| ')
      .replace(/\n{3,}/g, '\n\n')
      .trim();

  function resetEvidence() {
    responseCitations.value = [];
    responseCitationHints.value = [];
    responseConfidence.value = '';
    responseGroundingMode.value = '';
    responseMetrics.value = undefined;
  }

  function buildSelectionFallbackHint(templateLabel: string): CitationItem[] {
    const context =
      surroundingContext.value || getContextSource() || selectedText.value;
    const snippet = context
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 180);
    return [
      {
        citation_id: 1,
        source: '课堂划词上下文',
        file_name: '课堂划词上下文',
        context_scope: 'route_context',
        locator: templateLabel,
        snippet:
          snippet ||
          '本次回答仅基于当前划词和页面上下文，未找到可定位的课程原文片段。',
        reason: '仅用于提示本次回答的页面入口和划词范围，不代表可核验原文。',
      },
    ];
  }

  const showAnswerPanel = computed(
    () => isLoadingResponse.value || Boolean(aiResponse.value)
  );

  function createSelectionThreadId() {
    return `sel-${Date.now().toString(36)}-${Math.random()
      .toString(36)
      .slice(2, 8)}`;
  }

  function cancelActiveRequest() {
    if (activeController) {
      activeController.abort();
      activeController = null;
    }
  }

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

  function applyMenuPosition(
    rect: Pick<ViewportRect, 'top' | 'left' | 'right' | 'bottom' | 'height'>
  ) {
    const pad = 8;
    const menuW = 280;
    const menuH = 200;
    const maxTop = Math.max(pad, window.innerHeight - menuH - pad);
    const anchorIsVisible =
      rect.bottom >= pad && rect.top <= window.innerHeight - pad;
    const anchorTop = anchorIsVisible
      ? rect.top
      : Math.min(Math.max(rect.top, pad), maxTop);
    const anchorBottom = anchorIsVisible
      ? rect.bottom
      : Math.min(
          anchorTop + Math.max(16, Math.min(rect.height || 18, 32)),
          window.innerHeight - pad
        );
    let left = rect.left;
    let top = anchorBottom + 6;
    if (left + menuW > window.innerWidth - pad) {
      left = window.innerWidth - menuW - pad;
    }
    if (left < pad) left = pad;
    if (top + menuH > window.innerHeight - pad) {
      top = anchorTop - menuH - 6;
    }
    top = Math.max(pad, Math.min(top, maxTop));
    contextMenuStyle.left = `${left}px`;
    contextMenuStyle.top = `${top}px`;
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
    applyMenuPosition(rect);
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

  function positionMenuNearRect(rect: ViewportRect) {
    applyMenuPosition(rect);
  }

  function openMenuForText(
    text: string,
    rectLike: DOMRect | ViewportRect,
    context?: string
  ) {
    const raw = text.trim();
    if (raw.length < 2 || raw.length > 400) {
      closeMenu();
      return;
    }
    const rect = {
      top: rectLike.top,
      left: rectLike.left,
      right: rectLike.right,
      bottom: rectLike.bottom,
      width: rectLike.width,
      height: rectLike.height,
    };
    selectedText.value = raw;
    surroundingContext.value = context?.trim() || getContextSource();
    lastSelectionViewportRect.value = rect;
    positionMenuNearRect(rect);
    showContextMenu.value = true;
  }

  function handleTextSelection(containerSelector: string, event?: Event) {
    const target = event?.target as HTMLElement | null;
    if (target?.closest('.node-hotspot')) return;

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

    cancelActiveRequest();
    const seq = requestSeq + 1;
    requestSeq = seq;
    const controller = new AbortController();
    activeController = controller;

    stopTypewriter();
    typewriterLen.value = 0;
    aiResponse.value = '';
    resetEvidence();
    answerPanelSession.value += 1;
    syncBoundsFromSelection();
    isLoadingResponse.value = true;
    closeMenu();
    triggerBridgeToPanel();

    try {
      // 课堂内容页划词问答不复用 AI 对话线程，避免晚返回的结果串到智能伴学页面。
      localSelectionThreadId.value = createSelectionThreadId();
      const response = await askSelectionQuery(
        selectedText.value,
        surroundingContext.value,
        localSelectionThreadId.value,
        {
          systemPrompt: template.prompt(
            selectedText.value,
            surroundingContext.value || getContextSource()
          ),
          ragK: settingStore.settings.ragK as 3 | 4 | 5,
          promptKey: 'custom',
          strictMode: settingStore.settings.strictMode,
          activeTools: settingStore.settings.activeTools || [],
          maxTokens: Math.max(Number(settingStore.settings.maxTokens) || 0, 8192),
          temperature: 0.5,
          signal: controller.signal,
        }
      );
      if (disposed || seq !== requestSeq || controller.signal.aborted) return;
      if (response?.response) {
        const cleanAnswer = sanitizeSelectionAnswer(response.response);
        const citations = normalizeCitationItems(response.citations);
        const citationHints = normalizeCitationItems(response.citation_hints);
        responseCitations.value = citations;
        responseCitationHints.value =
          citations.length || citationHints.length
            ? citationHints
            : buildSelectionFallbackHint(template.label);
        responseConfidence.value = String(
          response.confidence || (citations.length ? 'medium' : 'low')
        );
        responseGroundingMode.value = String(
          response.grounding_mode || (citations.length ? 'rag' : 'general')
        );
        responseMetrics.value = response.metrics;
        aiResponse.value = cleanAnswer;
        startTypewriter();
      } else {
        Message.error('AI 响应为空');
      }
    } catch (error) {
      if (
        disposed ||
        seq !== requestSeq ||
        controller.signal.aborted ||
        (error instanceof Error && error.name === 'CanceledError')
      ) {
        return;
      }
      Message.error(
        `查询失败: ${error instanceof Error ? error.message : String(error)}`
      );
    } finally {
      if (seq === requestSeq) {
        isLoadingResponse.value = false;
        activeController = null;
      }
    }
  }

  function clearAnswerPanel() {
    requestSeq += 1;
    cancelActiveRequest();
    stopTypewriter();
    typewriterLen.value = 0;
    aiResponse.value = '';
    resetEvidence();
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
    if (t.closest('.selection-context-menu')) return;
    if (t.closest('.selection-ai-answer-panel')) return;
    if (t.closest('.selection-ai-resize-handle')) return;
    closeMenu();
  }

  onMounted(() => {
    disposed = false;
    document.addEventListener('mousedown', onDocMouseDown);
    document.addEventListener('scroll', closeMenu, true);
  });
  onUnmounted(() => {
    disposed = true;
    document.removeEventListener('mousedown', onDocMouseDown);
    document.removeEventListener('scroll', closeMenu, true);
    cancelActiveRequest();
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
    return stripMarkdownCodeToolbar(
      renderMarkdown(slice, { streaming: isLoadingResponse.value })
    );
  });

  return {
    promptTemplates,
    showContextMenu,
    contextMenuStyle,
    selectedText,
    isLoadingResponse,
    aiResponse,
    responseCitations,
    responseCitationHints,
    responseConfidence,
    responseGroundingMode,
    responseMetrics,
    showAnswerPanel,
    answerPanelBounds,
    answerPanelSession,
    isTypingAnswer,
    renderedResponse,
    bridgeLine,
    handleTextSelection,
    openMenuForText,
    sendAIQuery,
    closeMenu,
    clearAnswerPanel,
  };
}
