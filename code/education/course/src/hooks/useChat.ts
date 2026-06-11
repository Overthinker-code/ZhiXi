import { computed } from 'vue';
import { Message } from '@arco-design/web-vue';
import { getToken } from '@/utils/auth';
import { useChatStore } from '@/store/chat';
import { useSettingStore } from '@/store/setting';
import { messageHandler } from '@/utils/messageHandler';
import { mergeAgentPhases } from '@/utils/agentDisplay';
import {
  appendThoughtToReasoning,
  phaseSummaryToNarrative,
} from '@/utils/thoughtToNarrative';
import { shouldAppendThoughtToReasoning } from '@/utils/streamReasoning';
import { normalizeSuggestionList } from '@/utils/llmDisplay';
import {
  createAssistantChat,
  createAssistantChatStream,
  fetchAssistantSettings,
  fetchChatHistory,
  askSelectionQuery,
  resumeChatAction,
  generateChatTitle,
  uploadThreadFile,
  type ReasoningActionItem,
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
  const analysisMatch = rawResponse.match(/<analysis>([\s\S]*?)<\/analysis>/i);
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
      .replace(/<\/?(think|analysis)>/gi, '')
      .trim();
    return {
      reasoning,
      content: afterThink,
    };
  }

  return { content: rawResponse.trim(), reasoning: '' };
}

function buildFallbackTitleFromFirstQuery(text: string) {
  const normalized = (text || '')
    .replace(/\s+/g, ' ')
    .replace(/[\r\n]+/g, ' ')
    .trim();
  if (!normalized) return '新对话';
  const cleaned = normalized
    .replace(/["'`.,!?;:(){}<>，。！？；：、“”‘’]/g, '')
    .replace(/\[/g, '')
    .replace(/\]/g, '');
  return (cleaned || normalized).slice(0, 10) || '新对话';
}

/** 首轮发送后：占位标题才走 LLM 命名，避免覆盖用户已改好的标题 */
function isGenericThreadTitle(title: string) {
  const t = (title || '').trim();
  if (!t) return true;
  if (t === '新对话') return true;
  if (/^新会话\d*$/i.test(t)) return true;
  if (/^(未命名|无标题)/.test(t)) return true;
  if (/^LLM\s*Chat$/i.test(t)) return true;
  return false;
}

function sanitizeStreamingContent(raw: string) {
  const { content } = parseAssistantResponse(raw || '');
  const cleaned = (content || raw || '')
    .replace(/<think>[\s\S]*?<\/think>/gi, '')
    .replace(/<analysis>[\s\S]*?<\/analysis>/gi, '')
    .replace(/<\/?(think|analysis)>/gi, '')
    .replace(/<\/?final>/gi, '')
    .trim();
  return cleaned;
}

function needsFreshWebSearch(text: string) {
  const normalized = String(text || '').toLowerCase();
  return /最新|最近|当前|今天|本周|本月|今年|新闻|政策|发布|价格|行情|比分|排名|天气|版本|官网|current|latest|today|news|price|weather|version/.test(
    normalized
  );
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(reader.error || new Error('图片读取失败'));
    reader.readAsDataURL(file);
  });
}

type ChatSendOptions = {
  useWebSearch?: boolean;
  deepThinking?: boolean;
  mode?: 'chat' | 'exercise_grading' | 'digital_human_explain';
  gradingMode?: boolean;
  digitalHumanExplain?: boolean;
  activeTools?: string[];
  toolMode?: 'chat' | 'exercise_grading' | 'image_tutoring' | 'digital_human_explain';
};

type ChatSendContent = {
  text: string;
  files?: any[];
  options?: ChatSendOptions;
};

function uniqueTools(tools: string[]) {
  return Array.from(new Set(tools.filter(Boolean)));
}

function inferToolMode(messageContent: ChatSendContent) {
  const text = messageContent.text || '';
  if (
    messageContent.options?.gradingMode ||
    messageContent.options?.mode === 'exercise_grading' ||
    messageContent.options?.toolMode === 'exercise_grading'
  ) {
    return 'exercise_grading' as const;
  }
  if (
    messageContent.options?.digitalHumanExplain ||
    messageContent.options?.mode === 'digital_human_explain' ||
    messageContent.options?.toolMode === 'digital_human_explain'
  ) {
    return 'digital_human_explain' as const;
  }
  if (/批改|评分|打分|订正|错因|我的答案|参考答案|掌握度/.test(text)) {
    return 'exercise_grading' as const;
  }
  if ((messageContent.files || []).some((f: any) => String(f?.type || '').startsWith('image'))) {
    return 'image_tutoring' as const;
  }
  return 'chat' as const;
}

function buildModePrompt(messageContent: ChatSendContent, toolMode: string) {
  const sections: string[] = [];
  const hasImages = (messageContent.files || []).some((f: any) =>
    String(f?.type || '').startsWith('image')
  );
  if (messageContent.options?.useWebSearch) {
    sections.push(
      '已开启联网搜索：涉及外部事实、时效信息或来源校验时可以使用 web_search；最终回答必须单独写出「联网搜索补充」，标注来源类型、可信度判断和与课程资料的关系。'
    );
  }
  if (messageContent.options?.deepThinking) {
    sections.push(
      '已开启深度思考：先拆解问题、核对约束和隐含条件，再给出结构化结论；只展示必要推理摘要，不暴露冗长内部过程。'
    );
  }
  if (toolMode === 'exercise_grading') {
    sections.push(
      '已开启批改模式：请按「结论与得分、得分点、问题定位、订正建议、同类题提醒、掌握度反馈」输出。若题干或标准答案缺失，先说明评分假设，再给出可执行反馈；避免只给泛泛鼓励。'
    );
  }
  if (messageContent.options?.digitalHumanExplain) {
    sections.push(
      '已开启数字人讲解：回答要适合直接转成教师数字人口播，包含开场、分点讲解、课堂提问和收束语；语言自然、节奏清晰。'
    );
  }
  if (hasImages) {
    sections.push(
      '学生上传了图片：请把图片识别内容作为输入证据，与学生文字和课程知识联合判断；不确定的视觉细节必须说明。'
    );
  }
  return sections.join('\n');
}

/**
 * Composable for managing AI chat interactions.
 * Extracts conversation logic from LegacyAssistantPanel into a reusable hook.
 */
export function useChat() {
  const chatStore = useChatStore();
  const settingStore = useSettingStore();
  let streamAbortController: AbortController | null = null;

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
      if (!history?.length) {
        const local = chatStore.getConversationMessages(targetThreadId);
        if (local.length > 0) {
          return;
        }
      }
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
            citations: item.citations || [],
            confidence: item.confidence || '',
            grounding_mode: item.grounding_mode || '',
            suggestions: normalizeSuggestionList(item.suggestions || []),
            metrics: item.metrics || {},
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
      if (typeof settings?.developer_panel_enabled === 'boolean') {
        settingStore.developerPanelEnabled = settings.developer_panel_enabled;
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
  async function sendMessage(messageContent: ChatSendContent) {
    if (chatStore.isLoading) return;
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

    const threadIdForTitle = currentThreadId.value;
    const userCountBeforeSend = (chatStore.currentMessages || []).filter(
      (m: any) => m.role === 'user'
    ).length;
    const existingTitle = (chatStore.currentConversation?.title || '').trim();
    const needTitleSync =
      userCountBeforeSend === 0 && isGenericThreadTitle(existingTitle);
    let mountedFile = chatStore.getMountedFile(threadIdForTitle);
    const imageFiles = (messageContent.files || []).filter((f: any) =>
      String(f?.type || '').startsWith('image')
    );
    const firstDoc = (messageContent.files || []).find((f: any) => {
      const raw = f?.raw;
      const name = String(f?.name || '').toLowerCase();
      if (!raw || !name) return false;
      if (String(f?.type || '').startsWith('image')) return false;
      return (
        name.endsWith('.pdf') ||
        name.endsWith('.doc') ||
        name.endsWith('.docx') ||
        name.endsWith('.txt') ||
        name.endsWith('.md') ||
        name.endsWith('.markdown') ||
        name.endsWith('.ppt') ||
        name.endsWith('.pptx') ||
        name.endsWith('.py') ||
        name.endsWith('.js') ||
        name.endsWith('.ts') ||
        name.endsWith('.java') ||
        name.endsWith('.cpp') ||
        name.endsWith('.c') ||
        name.endsWith('.sql')
      );
    });

    let roundSucceeded = false;

    try {
      if (firstDoc?.raw && threadIdForTitle) {
        try {
          const uploadRes = await uploadThreadFile(
            firstDoc.raw,
            threadIdForTitle
          );
          if (uploadRes?.file_id) {
            mountedFile = {
              file_id: String(uploadRes.file_id),
              file_name: String(uploadRes.file_name || firstDoc.name || ''),
            };
            chatStore.setMountedFile(threadIdForTitle, mountedFile);
          }
        } catch (uploadError: unknown) {
          const detail =
            uploadError instanceof Error && uploadError.message
              ? uploadError.message
              : '';
          Message.warning(
            detail.includes('404')
              ? '文档挂载失败：后端缺少 /api/v1/file/upload 接口（当前服务未更新到最新代码）。'
              : '文档挂载失败：本轮将按普通问答处理。请检查文件格式或后端日志。'
          );
        }
      }

      const imageBase64List = (
        await Promise.all(
          imageFiles
            .filter((file: any) => file?.raw)
            .slice(0, 3)
            .map((file: any) => fileToDataUrl(file.raw))
        )
      ).filter(Boolean);
      const visibleUserText =
        messageContent.text?.trim() ||
        (imageFiles.length
          ? '请解析我上传的图片，并结合课程内容回答。'
          : firstDoc
            ? `请结合我上传的文件《${firstDoc.name || '参考文件'}》回答。`
            : '');
      const toolMode = inferToolMode({
        ...messageContent,
        text: visibleUserText,
      });
      const modePrompt = buildModePrompt(messageContent, toolMode);
      const userTextForModel =
        toolMode === 'exercise_grading'
          ? `【练习批改模式】\n请对下面题目或答案进行批改，必须包含：评分/等级、关键得分点、错误证据、订正步骤、后续练习建议、掌握度反馈。\n\n${visibleUserText}`
          : toolMode === 'digital_human_explain'
              ? `【数字人讲解模式】\n请把下面内容组织成适合数字人教师讲解的视频口播稿，结构清晰、面向学生。\n\n${visibleUserText}`
              : imageBase64List.length
                ? `【图像与文本联合提问】\n学生上传了图片，并补充以下文字。请结合图片识别内容、文字信息和课程知识进行回答；如果图片细节不确定，请明确说明。\n\n${visibleUserText}`
                : visibleUserText;

      chatStore.addMessage(
        messageHandler.formatMessage(
          'user',
          visibleUserText,
          '',
          messageContent.files
        )
      );
      chatStore.addMessage(messageHandler.formatMessage('assistant', '', ''));

      if (needTitleSync && threadIdForTitle) {
        const fallbackTitle = buildFallbackTitleFromFirstQuery(
          messageContent.text
        );
        chatStore.patchConversationTitleLocal(threadIdForTitle, fallbackTitle);
      }

      chatStore.setIsLoading(true);
      const lastMessage = chatStore.getLastMessage();
      if (lastMessage) lastMessage.loading = true;

      const rawTemperature = Number(settingStore.settings.temperature);
      const optionTools = messageContent.options?.activeTools || [];
      const activeTools = uniqueTools([
        ...(settingStore.settings.activeTools || []),
        ...optionTools,
        messageContent.options?.useWebSearch ? 'web_search' : '',
        messageContent.options?.deepThinking ? 'deep_thinking' : '',
        messageContent.options?.digitalHumanExplain ? 'digital_human_explain' : '',
      ]);
      if (
        !messageContent.options?.useWebSearch &&
        settingStore.settings.promptKey === 'tutor' &&
        activeTools.includes('knowledge_base') &&
        activeTools.includes('web_search') &&
        !needsFreshWebSearch(visibleUserText)
      ) {
        const webSearchIndex = activeTools.indexOf('web_search');
        if (webSearchIndex >= 0) {
          activeTools.splice(webSearchIndex, 1);
        }
      }

      const commonOptions = {
        systemPrompt: [
          settingStore.settings.customSystemPrompt || '',
          modePrompt,
        ]
          .filter(Boolean)
          .join('\n\n'),
        ragK: settingStore.settings.ragK as 3 | 4 | 5,
        promptKey: settingStore.settings.promptKey,
        strictMode: settingStore.settings.strictMode,
        activeTools,
        maxTokens: Math.max(Number(settingStore.settings.maxTokens) || 0, 16384),
        temperature:
          settingStore.settings.promptKey === 'tutor'
            ? Math.min(
                Number.isFinite(rawTemperature) ? rawTemperature : 0.45,
                0.45
              )
            : settingStore.settings.temperature,
        topP: settingStore.settings.topP,
        topK: settingStore.settings.topK,
        forceAgent: settingStore.settings.forceAgent || undefined,
        forceCache: Boolean(settingStore.settings.forceCache),
        debugMode: Boolean(settingStore.settings.debugMode),
      };

      const shouldStream = Boolean(settingStore.settings.stream);
      if (shouldStream) {
        streamAbortController = new AbortController();
        const thoughts: string[] = [];
        let agentPhases: Array<{
          phase: string;
          agent: string;
          summary: string;
          status?: string;
        }> = [];
        let suggestions: string[] = [];
        let answer = '';
        let streamError = '';
        let requiresConfirmation = false;
        let pendingActionId = '';
        let citations: any[] = [];
        let confidence = '';
        let groundingMode = '';
        let metrics: Record<string, any> = {};

        let reasoningText = '';
        let reasoningActions: ReasoningActionItem[] = [];
        let streamFinished = false;
        let sawReasoningToken = false;

        const pushStreamUpdate = () => {
          const displayContent = sanitizeStreamingContent(answer);
          chatStore.updateLastMessage(
            displayContent,
            reasoningText,
            0,
            0,
            [...thoughts],
            requiresConfirmation,
            pendingActionId,
            suggestions,
            citations,
            confidence,
            groundingMode,
            metrics,
            streamFinished ? [...agentPhases] : []
          );
          const last = chatStore.getLastMessage();
          if (last) {
            last.reasoningActions = [...reasoningActions];
          }
        };

        await createAssistantChatStream(
          userTextForModel,
          currentThreadId.value,
          {
            ...commonOptions,
            currentFileId: mountedFile?.file_id || undefined,
            fileName: mountedFile?.file_name || undefined,
            imageBase64List,
            toolMode,
          },
          (event) => {
            if (event.type === 'reasoning_token') {
              sawReasoningToken = true;
              reasoningText += event.content || '';
              pushStreamUpdate();
            } else if (event.type === 'reasoning_action') {
              reasoningActions.push({
                action: event.action,
                title: event.title,
                detail: event.detail,
                items: Array.isArray(event.items) ? event.items : [],
              });
              pushStreamUpdate();
            } else if (event.type === 'phase') {
              agentPhases = mergeAgentPhases(agentPhases, {
                phase: String(event.phase || 'process'),
                agent: String(event.agent || 'supervisor'),
                summary: String(event.summary || ''),
                status: String(event.status || 'running'),
              });
              const narrative = phaseSummaryToNarrative(event);
              if (
                narrative &&
                shouldAppendThoughtToReasoning(
                  narrative,
                  event.phase,
                  sawReasoningToken
                )
              ) {
                reasoningText = appendThoughtToReasoning(
                  reasoningText,
                  narrative
                );
              }
              pushStreamUpdate();
            } else if (event.type === 'thought') {
              if (event.content) thoughts.push(event.content);
              if (
                shouldAppendThoughtToReasoning(
                  event.content || '',
                  event.stage,
                  sawReasoningToken
                )
              ) {
                reasoningText = appendThoughtToReasoning(
                  reasoningText,
                  event.content || '',
                  event.stage
                );
              }
              pushStreamUpdate();
            } else if (event.type === 'token') {
              answer += event.content || '';
              pushStreamUpdate();
            } else if (event.type === 'suggestions') {
              suggestions = normalizeSuggestionList(event.data || []);
            } else if (event.type === 'final') {
              streamFinished = true;
              answer = event.content || answer;
              requiresConfirmation = Boolean(event.requires_confirmation);
              pendingActionId = event.pending_action_id || '';
              citations = Array.isArray(event.citations) ? event.citations : [];
              confidence = String(event.confidence || '');
              groundingMode = String(event.grounding_mode || '');
              metrics = event.metrics || {};
              pushStreamUpdate();
            } else if (event.type === 'error') {
              streamError = event.content || 'Stream failed';
            }
          },
          streamAbortController.signal
        );
        if (streamError) {
          throw new Error(streamError);
        }
        roundSucceeded = true;
      } else {
        const response = await createAssistantChat(
          userTextForModel,
          currentThreadId.value,
          {
            ...commonOptions,
            currentFileId: mountedFile?.file_id || undefined,
            fileName: mountedFile?.file_name || undefined,
            imageBase64List,
            toolMode,
          }
        );
        const { content, reasoning } = parseAssistantResponse(
          response.response || ''
        );
        chatStore.updateLastMessage(
          content,
          reasoning,
          0,
          0,
          [],
          false,
          '',
          normalizeSuggestionList(response.suggestions || []),
          response.citations || [],
          response.confidence || '',
          response.grounding_mode || '',
          response.metrics || {}
        );
        roundSucceeded = true;
      }
    } catch (error: unknown) {
      const detail =
        error instanceof Error && error.message
          ? error.message.slice(0, 500)
          : '';
      const abortedByUser =
        error instanceof Error &&
        (error.name === 'AbortError' || /aborted/i.test(error.message));
      let errorText = '当前连接时空有点波动，请稍后再试哦~';
      if (abortedByUser) {
        errorText = '已中断本次回复。你可以继续提问，或点击重新生成。';
      } else if (detail) {
        errorText = `生成未成功：${detail}`;
      }
      chatStore.updateLastMessage(errorText);
    } finally {
      streamAbortController = null;
      chatStore.setIsLoading(false);
      const lastMessage = chatStore.getLastMessage();
      if (lastMessage) lastMessage.loading = false;

      /* 首轮对话完成后：根据「用户首问 + 助手首答」自动生成会话标题（不依赖列表里是否仍为「新对话」） */
      if (needTitleSync && roundSucceeded && threadIdForTitle) {
        const raw = chatStore.getLastMessage()?.content || '';
        const plain = parseAssistantResponse(raw).content || raw;
        const snippet = plain.slice(0, 2000);
        if (snippet && !snippet.startsWith('生成未成功')) {
          generateChatTitle(messageContent.text, snippet)
            .then((res) => {
              const title = (res?.title || '').trim();
              if (!title || title === '新对话') return undefined;
              return chatStore.updateConversationTitle(threadIdForTitle, title);
            })
            .then(() => chatStore.loadConversations())
            .catch(() => null);
        } else {
          void chatStore.loadConversations();
        }
      }
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
    chatStore.enterDraftSession();
  }

  async function sendSelectionQuery(params: {
    selectedText: string;
    surroundingContext: string;
    videoTime?: string;
    courseModule?: string;
  }) {
    const text = params.selectedText?.trim();
    if (!text) return;
    if (!currentThreadId.value) {
      if (!getToken()) {
        Message.error('请先登录后再使用 AI 对话');
        return;
      }
      try {
        await chatStore.createConversation();
      } catch {
        Message.error('无法创建对话，请稍后重试');
        return;
      }
    }
    if (!currentThreadId.value) return;
    chatStore.addMessage(
      messageHandler.formatMessage('user', `划词提问：${text}`)
    );
    chatStore.addMessage(messageHandler.formatMessage('assistant', '', ''));
    chatStore.setIsLoading(true);
    const lastMessage = chatStore.getLastMessage();
    if (lastMessage) lastMessage.loading = true;

    try {
      const mountedFile = chatStore.getMountedFile(currentThreadId.value);
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
          currentFileId: mountedFile?.file_id,
          fileName: mountedFile?.file_name,
          forceAgent: settingStore.settings.forceAgent || undefined,
          forceCache: Boolean(settingStore.settings.forceCache),
          debugMode: Boolean(settingStore.settings.debugMode),
        }
      );
      const { content, reasoning } = parseAssistantResponse(
        response.response || ''
      );
      chatStore.updateLastMessage(
        content,
        reasoning,
        0,
        0,
        [],
        false,
        '',
        normalizeSuggestionList(response.suggestions || []),
        response.citations || [],
        response.confidence || '',
        response.grounding_mode || '',
        response.metrics || {}
      );
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

  function stopGenerating() {
    if (!chatStore.isLoading || !streamAbortController) return;
    streamAbortController.abort();
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
    stopGenerating,
    sendSelectionQuery,
    confirmPendingAction,
  };
}
