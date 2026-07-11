<script setup lang="ts">
  import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
  import { useRoute } from 'vue-router';
  import { Message, Modal } from '@arco-design/web-vue';
  import {
    fetchAIContextCourses,
    uploadAIAttachment,
    type AIChatStreamPayload,
    type AIContextCourse,
    type ChatAttachmentPayload,
    type ChatToolPayload,
    type CourseContextPayload,
    type ReasoningLevel,
    type ResourceRequestPayload,
    type TutorMode,
  } from '@/api/ai-chat';
  import { fetchChatHistory, fetchLearningReport } from '@/api/rag';
  import { useChatStore } from '@/store/chat';
  import { getToken } from '@/utils/auth';
  import ChatComposer from './ChatComposer.vue';
  import ChatMain from './ChatMain.vue';
  import ChatSidebar from './ChatSidebar.vue';
  import ContextDrawer from './ContextDrawer.vue';
  import sanitizeAssistantText from './sanitizeAssistantText';
  import streamTutorChat from './useTutorStream';
  import {
    CHAT_DEFAULT_RESOURCE_TYPES,
    getTutorAction,
    type TutorAction,
    type TutorPanel,
  } from './tutorActions';

  const chatStore = useChatStore();
  const route = useRoute();
  const sidebarCollapsed = ref(false);
  const drawerVisible = ref(false);
  const composerRef = ref<InstanceType<typeof ChatComposer> | null>(null);
  const contextButtonRef = ref<HTMLButtonElement | null>(null);
  const activeAction = ref<TutorAction>(getTutorAction('general_chat'));
  const mode = ref<TutorMode>('tutor');
  const tools = ref<ChatToolPayload>({
    webSearch: false,
    courseRag: false,
    deepResearch: false,
    homeworkReview: false,
    resourceGeneration: false,
    citationRequired: true,
  });
  const reasoningLevel = ref<ReasoningLevel>('balanced');
  const courseContext = ref<CourseContextPayload>({
    courseId: '',
    chapterId: '',
    knowledgePointIds: [],
    useCourseRag: false,
  });
  const resourceRequest = ref<ResourceRequestPayload>({
    types: [...CHAT_DEFAULT_RESOURCE_TYPES],
    difficulty: 'normal',
    target: '',
  });
  const courses = ref<AIContextCourse[]>([]);
  const learningReport = ref<Record<string, any> | null>(null);
  const abortController = ref<AbortController | null>(null);
  const lastPayload = ref<AIChatStreamPayload | null>(null);
  const lastDraft = ref<{ text: string; files: File[] } | null>(null);
  const mainScroller = ref<HTMLElement | null>(null);
  const showRawReasoningDebug =
    import.meta.env.DEV && String(import.meta.env.VITE_SHOW_RAW_REASONING || '').toLowerCase() === 'true';

  const conversations = computed(() => chatStore.conversations || []);
  const messages = computed(() => chatStore.currentMessages || []);
  const latestAssistant = computed(() =>
    [...messages.value].reverse().find((item: any) => item.role === 'assistant')
  );
  const latestCitations = computed(() => latestAssistant.value?.citations || []);
  const latestToolEvents = computed(() => latestAssistant.value?.toolEvents || []);
  const latestArtifacts = computed(() => latestAssistant.value?.artifacts || []);
  const latestPackage = computed(() => latestAssistant.value?.resourcePackage || null);
  const latestRawReasoningDebug = computed(() =>
    showRawReasoningDebug ? String(latestAssistant.value?.debugRawReasoning || '') : ''
  );
  const selectedCourse = computed(() =>
    courses.value.find((item) => item.courseId === courseContext.value.courseId)
  );
  const profileItems = computed(() => {
    const weak = Array.isArray(learningReport.value?.weak_points)
      ? learningReport.value?.weak_points.slice(0, 2).join(' / ')
      : '待更新';
    return [
      { label: '学习目标', value: learningReport.value?.current_goal || '课程理解与题目迁移' },
      { label: '认知风格', value: learningReport.value?.learning_style || '例题驱动' },
      { label: '薄弱点', value: weak || '待更新' },
      { label: '风险等级', value: learningReport.value?.risk_level || 'medium' },
    ];
  });

  function openPanel(panel: TutorPanel) {
    if (panel === 'upload') {
      composerRef.value?.openUpload();
    } else if (panel === 'course_picker') {
      openContextDrawer();
    }
  }

  function openContextDrawer() {
    drawerVisible.value = true;
  }

  function closeContextDrawer(restoreFocus = true) {
    if (!drawerVisible.value) return;
    drawerVisible.value = false;
    if (restoreFocus) nextTick(() => contextButtonRef.value?.focus());
  }

  function handleDocumentKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && drawerVisible.value) closeContextDrawer();
  }

  function patchFromAction(action: TutorAction) {
    activeAction.value = action;
    mode.value = action.mode;
    if (action.requestPatch.tools) {
      tools.value = { ...tools.value, ...action.requestPatch.tools };
    }
    if (action.requestPatch.reasoning) {
      reasoningLevel.value = action.requestPatch.reasoning.level || reasoningLevel.value;
    }
    if (action.requestPatch.courseContext) {
      courseContext.value = {
        ...courseContext.value,
        ...action.requestPatch.courseContext,
        knowledgePointIds:
          action.requestPatch.courseContext.knowledgePointIds ||
          courseContext.value.knowledgePointIds,
      };
    }
    if (action.requestPatch.resourceRequest) {
      resourceRequest.value = {
        ...resourceRequest.value,
        ...action.requestPatch.resourceRequest,
      };
    }
    if (action.openPanel === 'upload') openPanel('upload');
  }

  function shouldUseCourseContext(text: string) {
    if (courseContext.value.useCourseRag) return Boolean(courseContext.value.courseId);
    if (activeAction.value.id !== 'general_chat') return Boolean(courseContext.value.useCourseRag);
    if (!courseContext.value.courseId) return false;
    const normalized = text.toLowerCase();
    return /课程|章节|本章|本节|课件|讲义|数据库|关系模型|er\s*模型|sql|事务|索引|范式|数据结构|二叉树|算法/.test(
      normalized
    );
  }

  function shouldAutoDeepResearch(text: string) {
    if (activeAction.value.id !== 'general_chat') return false;
    return /研究一下|调研|综述|近期|最新|主流|趋势|论文|进展|方向|对比|全景|报告/i.test(text);
  }

  function handleAction(actionId: string) {
    patchFromAction(getTutorAction(actionId));
  }

  function clearAllConversations() {
    if (!conversations.value.length) return;
    Modal.confirm({
      title: '清空全部历史对话',
      content: '将永久删除当前账号下的全部会话记录，此操作不可撤销。',
      okText: '清空',
      cancelText: '取消',
      async onOk() {
        try {
          await chatStore.deleteAllConversations();
          Message.success('已清空全部历史');
        } catch (error) {
          Message.error(error instanceof Error ? error.message : '部分会话删除失败，请重试');
          throw error;
        }
      },
    });
  }

  async function deleteConversation(conversationId: string) {
    try {
      await chatStore.deleteConversation(conversationId);
    } catch (error) {
      Message.error(error instanceof Error ? error.message : '删除会话失败，请稍后重试');
    }
  }

  function validateContext(files: File[], text: string) {
    const required = activeAction.value.requiredContext || [];
    if (required.includes('attachment') && !files.length && !text.trim()) {
      openPanel('upload');
      Message.warning('请上传题目材料，或直接在输入框粘贴题目文本');
      return false;
    }
    return true;
  }

  function appendToolEvent(assistant: Record<string, any>, next: Record<string, any>) {
    const list = Array.isArray(assistant.toolEvents) ? assistant.toolEvents : [];
    const key = String(next.agent || next.source || next.label || '');
    const index = list.findIndex((item: Record<string, any>) =>
      String(item.agent || item.source || item.label || '') === key && key
    );
    if (index >= 0) {
      list[index] = { ...list[index], ...next };
    } else {
      list.push(next);
    }
    assistant.toolEvents = [...list];
  }

  function appendProcessEvent(assistant: Record<string, any>, next: Record<string, any>) {
    const list = Array.isArray(assistant.processEvents) ? assistant.processEvents : [];
    const stage = String(next.stage || '');
    const status = String(next.status || 'running');
    const normalized = {
      ...next,
      stage,
      status,
      timestamp: next.timestamp || new Date().toISOString(),
    };
    const index = list.findIndex(
      (item: Record<string, any>) =>
        String(item.stage || '') === stage &&
        String(item.status || '') === status &&
        String(item.title || '') === String(next.title || '') &&
        String(item.log || '') === String(next.log || '')
    );
    if (index >= 0) {
      list[index] = { ...list[index], ...normalized };
    } else {
      list.push(normalized);
    }
    assistant.processEvents = [...list].slice(-40);
  }

  function timeLabel(value = Date.now()) {
    return new Date(value).toLocaleTimeString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }

  function ensureLiveProcess(assistant: Record<string, any>) {
    if (!assistant.liveProcess) {
      assistant.liveProcess = {
        status: 'idle',
        collapsed: false,
        currentSummary: '',
        phases: [],
        tools: [],
        reasoningText: '',
        citations: [],
        safetyStatus: undefined,
        logs: [],
      };
    }
    return assistant.liveProcess as Record<string, any>;
  }

  function appendLiveLog(process: Record<string, any>, text: string, status = 'running', title = '处理过程') {
    const clean = String(text || '').trim();
    if (!clean) return;
    const logs = Array.isArray(process.logs) ? process.logs : [];
    const last = logs[logs.length - 1];
    if (last?.text === clean && last?.status === status) return;
    process.logs = [
      ...logs,
      {
        id: `${Date.now()}-${logs.length}-${clean.slice(0, 20)}`,
        title,
        text: clean,
        status,
        time: timeLabel(),
        timestamp: Date.now(),
      },
    ].slice(-80);
  }

  function upsertPhase(process: Record<string, any>, phase: Record<string, any>) {
    const phases = Array.isArray(process.phases) ? process.phases : [];
    const id = String(phase.id || phase.phaseId || 'phase');
    const index = phases.findIndex((item: Record<string, any>) => String(item.id) === id);
    const current = index >= 0 ? phases[index] : { id, title: phase.title || '处理阶段', status: 'pending', text: '' };
    const next = {
      ...current,
      ...phase,
      id,
      title: phase.title || current.title || '处理阶段',
      status: phase.status || current.status || 'running',
      text: [current.text, phase.text].filter(Boolean).join(current.text && phase.text ? '\n' : ''),
      summary: phase.summary || current.summary,
      startedAt: current.startedAt || phase.startedAt || Date.now(),
      finishedAt: phase.finishedAt || current.finishedAt,
    };
    if (index >= 0) phases[index] = next;
    else phases.push(next);
    process.phases = [...phases];
    process.currentSummary = phase.summary || phase.text || process.currentSummary;
  }

  function upsertTool(process: Record<string, any>, tool: Record<string, any>) {
    const toolsList = Array.isArray(process.tools) ? process.tools : [];
    const key = String(tool.tool || tool.id || 'tool');
    const index = toolsList.findIndex((item: Record<string, any>) => String(item.tool) === key);
    const current = index >= 0 ? toolsList[index] : { tool: key, title: tool.title || '工具调用', status: 'running', text: '' };
    const next = {
      ...current,
      ...tool,
      tool: key,
      title: tool.title || current.title || '工具调用',
      status: tool.status || current.status || 'running',
      text: [current.text, tool.text].filter(Boolean).join(current.text && tool.text ? '\n' : ''),
      resultSummary: tool.summary || tool.resultSummary || current.resultSummary,
      items: Array.isArray(tool.items) ? tool.items : current.items || [],
      startedAt: current.startedAt || tool.startedAt || Date.now(),
      finishedAt: tool.finishedAt || current.finishedAt,
    };
    if (index >= 0) toolsList[index] = next;
    else toolsList.push(next);
    process.tools = [...toolsList];
    process.currentSummary = tool.summary || tool.text || process.currentSummary;
  }

  function handleLiveProcessEvent(assistant: Record<string, any>, event: string, data: Record<string, any>) {
    const process = ensureLiveProcess(assistant);
    if (event === 'run_started') {
      assistant.liveProcess = {
        runId: data.runId,
        status: 'running',
        collapsed: false,
        currentSummary: data.title || '开始处理问题',
        phases: [],
        tools: [],
        reasoningText: '',
        citations: [],
        safetyStatus: undefined,
        startedAt: Date.now(),
        logs: [],
      };
      return;
    }
    if (event === 'error') {
      process.status = 'error';
    } else if (event === 'run_finished') {
      process.status = 'done';
    } else {
      process.status = process.status || 'running';
    }
    if (event === 'phase_started') {
      upsertPhase(process, {
        id: data.phaseId,
        title: data.title,
        status: 'running',
        text: data.text || '',
        startedAt: Date.now(),
      });
    } else if (event === 'phase_delta' || event === 'phase_updated' || event === 'process_delta') {
      upsertPhase(process, {
        id: data.phaseId,
        status: 'running',
        title: data.title,
        text: data.summary || data.text || '',
        summary: data.summary,
      });
    } else if (event === 'phase_finished') {
      upsertPhase(process, {
        id: data.phaseId,
        title: data.title,
        status: data.status || 'done',
        summary: data.summary || '',
        finishedAt: Date.now(),
      });
    } else if (event === 'tool_started') {
      upsertTool(process, {
        tool: data.tool,
        title: data.title,
        status: 'running',
        text: data.text || '',
        startedAt: Date.now(),
      });
    } else if (event === 'tool_delta') {
      upsertTool(process, {
        tool: data.tool,
        status: 'running',
        text: data.text || '',
      });
    } else if (event === 'tool_result') {
      upsertTool(process, {
        tool: data.tool,
        title: data.title,
        status: data.status || 'done',
        summary: data.summary || '',
        items: Array.isArray(data.items) ? data.items : [],
        finishedAt: Date.now(),
      });
    } else if (event === 'process_sanitized') {
      upsertPhase(process, {
        id: data.phaseId || 'verify_output',
        title: data.title || '校验输出',
        status: data.status || 'done',
        summary: data.summary || '已完成过程整理',
        finishedAt: Date.now(),
      });
      process.currentSummary = data.summary || process.currentSummary;
    } else if (event === 'citation') {
      process.citations = [...(process.citations || []), data];
      process.currentSummary = `已确认引用：${data.title || data.source || '课程证据'}`;
    } else if (event === 'safety_check') {
      process.safetyStatus = data.status || 'passed';
      appendLiveLog(process, data.message || '已完成引用和安全检查', data.status === 'blocked' ? 'error' : 'done', '校验输出');
    } else if (event === 'run_finished') {
      process.status = 'done';
      process.currentSummary = data.summary || '本轮处理完成';
      process.finishedAt = Date.now();
      appendLiveLog(process, process.currentSummary, 'done', '完成处理');
    } else if (event === 'error') {
      process.status = 'error';
      process.currentSummary = data.message || '处理失败';
      process.finishedAt = Date.now();
      appendLiveLog(process, process.currentSummary, 'error', '处理失败');
    }
  }

  function latestAssistantMutable() {
    return chatStore.getLastMessage() as Record<string, any> | null;
  }

  async function ensureSession() {
    if (chatStore.currentConversationId) return chatStore.currentConversationId;
    if (!getToken()) {
      throw new Error('请先登录后再使用 AI 对话');
    }
    await chatStore.createConversation();
    return chatStore.currentConversationId;
  }

  async function uploadFiles(files: File[], sessionId: string): Promise<ChatAttachmentPayload[]> {
    return Promise.all(
      files.map(async (file) => {
        const res = await uploadAIAttachment(file, sessionId);
        return {
          fileId: String(res.fileId),
          type: res.type,
          name: res.name || file.name,
        };
      })
    );
  }

  function citationSourceType(tool: unknown) {
    const key = String(tool || '');
    if (key.includes('web')) return 'web';
    if (key.includes('attachment')) return 'uploaded';
    return 'course';
  }

  function suggestionsFromEvent(data: Record<string, any>) {
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.suggestions)) return data.suggestions;
    if (Array.isArray(data.data)) return data.data;
    return [];
  }

  function streamErrorMessage(code: string, data: Record<string, any>) {
    if (code === 'RAG_EMPTY') {
      return '当前课程资料不足，可切换联网搜索或上传资料。';
    }
    return String(data.message || data.content || '后端生成失败');
  }

  function buildPayload(text: string, attachments: ChatAttachmentPayload[]): AIChatStreamPayload {
    const autoCourseRag = shouldUseCourseContext(text);
    const autoDeepResearch = shouldAutoDeepResearch(text);
    const requestMode: TutorMode = autoDeepResearch ? 'deep_research' : mode.value;
    const requestReasoningLevel: ReasoningLevel = autoDeepResearch ? 'deep' : reasoningLevel.value;
    return {
      sessionId: chatStore.currentConversationId || undefined,
      message: text,
      mode: requestMode,
      actionId: autoDeepResearch ? 'auto_deep_research' : activeAction.value.id,
      courseContext: autoCourseRag
        ? { ...courseContext.value, useCourseRag: true }
        : { courseId: '', chapterId: '', knowledgePointIds: [], useCourseRag: false },
      tools: {
        ...tools.value,
        webSearch: tools.value.webSearch || autoDeepResearch,
        deepResearch: tools.value.deepResearch || autoDeepResearch,
        courseRag: autoCourseRag,
        citationRequired: tools.value.citationRequired || autoCourseRag || Boolean(attachments.length),
      },
      reasoning: {
        level: requestReasoningLevel,
        showSummary: true,
        showProcess: true,
      },
      attachments,
      resourceRequest: { ...resourceRequest.value },
    };
  }

  async function send({ text, files }: { text: string; files: File[] }) {
    if (!validateContext(files, text)) return;
    lastDraft.value = { text, files };
    chatStore.setIsLoading(true);
    try {
      const sessionId = await ensureSession();
      const attachments = files.length ? await uploadFiles(files, sessionId) : [];
      const payload = buildPayload(text, attachments);
      lastPayload.value = payload;
      chatStore.addMessage({
        role: 'user',
        content: text || (files.length ? '请处理我上传的材料。' : ''),
        files: files.map((file) => ({ name: file.name, size: file.size, type: file.type })),
      });
      chatStore.addMessage({
        role: 'assistant',
        content: '',
        reasoning_content: '',
        loading: true,
        mode: payload.mode,
        actionId: payload.actionId,
        citations: [],
        toolEvents: [],
        processEvents: [],
        liveProcess: {
          status: 'idle',
          collapsed: false,
          currentSummary: '',
          phases: [],
          tools: [],
          reasoningText: '',
          citations: [],
          logs: [],
        },
        artifacts: [],
        resourcePackage: null,
      });
      await nextTick();
      mainScroller.value?.scrollTo({ top: mainScroller.value.scrollHeight, behavior: 'smooth' });
      abortController.value = new AbortController();
      let streamedAnswerChars = 0;
      await streamTutorChat(
        payload,
        ({ event, data }) => {
          const assistant = latestAssistantMutable();
          if (!assistant) return;
          if (event === 'session_created' && data.sessionId && data.sessionId !== chatStore.currentConversationId) {
            chatStore.currentConversationId = String(data.sessionId);
          } else if (
            [
              'run_started',
              'phase_started',
              'phase_delta',
              'phase_updated',
              'phase_finished',
              'process_delta',
              'process_sanitized',
              'tool_started',
              'tool_delta',
              'tool_result',
              'run_finished',
            ].includes(event)
          ) {
            handleLiveProcessEvent(assistant, event, data);
            if (event === 'tool_result' && Array.isArray(data.items) && data.items.length) {
              const sourceType = citationSourceType(data.tool);
              assistant.citations = [
                ...(assistant.citations || []),
                ...data.items.map((item: Record<string, any>, index: number) => ({
                  id: item.id || item.citation_id || `${data.tool || 'tool'}-${index + 1}`,
                  title: item.title || item.file_name || item.source || `${data.title || '证据'} ${index + 1}`,
                  sourceType,
                  snippet: item.snippet || item.chunk || item.content || item.text || item.summary || '',
                  ...item,
                })),
              ];
            }
          } else if (event === 'process_update') {
            appendProcessEvent(assistant, data);
          } else if (event === 'agent_started') {
            appendToolEvent(assistant, {
              agent: data.agent || 'agent',
              label: data.label || '正在处理',
              status: 'running',
            });
          } else if (event === 'agent_finished') {
            appendToolEvent(assistant, {
              agent: data.agent || 'agent',
              label: data.label || '已完成',
              status: 'done',
            });
          } else if (event === 'retrieval_started') {
            appendProcessEvent(assistant, {
              stage: 'retrieve',
              title: '检索依据',
              detail: data.label || '正在检索资料',
              status: 'running',
              log: data.label || '正在检索资料',
            });
            appendToolEvent(assistant, {
              agent: data.source || 'course_retriever',
              label: data.label || '正在检索资料',
              status: 'running',
            });
          } else if (event === 'retrieval_result') {
            appendProcessEvent(assistant, {
              stage: 'retrieve',
              title: '检索依据',
              detail: `已准备 ${Array.isArray(data.items) ? data.items.length : 0} 条引用证据`,
              status: 'done',
              log: `检索完成，返回 ${Array.isArray(data.items) ? data.items.length : 0} 条候选证据`,
              items: Array.isArray(data.items)
                ? data.items.map((item: Record<string, any>) => item.title || item.file_name || item.source || item.chunk || item.content).filter(Boolean).slice(0, 5)
                : [],
            });
            appendToolEvent(assistant, {
              agent: data.source || 'course_retriever',
              label: `已检索 ${Array.isArray(data.items) ? data.items.length : 0} 条资料`,
              status: 'done',
            });
            if (Array.isArray(data.items)) {
              assistant.citations = [...(assistant.citations || []), ...data.items];
            }
          } else if (event === 'reasoning_summary_delta' || event === 'reasoning_delta') {
            // Legacy compatibility only. Productized streams use process_delta.
          } else if (event === 'debug_raw_reasoning_delta') {
            if (showRawReasoningDebug) {
              assistant.debugRawReasoning = `${assistant.debugRawReasoning || ''}${data.text || ''}`;
            }
          } else if (event === 'answer_delta') {
            const safeText = sanitizeAssistantText(data.text || '', { preserveEdges: true });
            if (!safeText) return;
            streamedAnswerChars += safeText.length;
            const process = ensureLiveProcess(assistant);
            process.answerChars = streamedAnswerChars;
            assistant.content = `${assistant.content || ''}${safeText}`;
          } else if (event === 'citation') {
            handleLiveProcessEvent(assistant, event, data);
            assistant.citations = [...(assistant.citations || []), data];
          } else if (event === 'artifact_started') {
            appendToolEvent(assistant, {
              agent: 'resource_generator',
              label: data.label || '正在生成资源包',
              status: 'running',
            });
          } else if (event === 'artifact_finished') {
            assistant.resourcePackage = data;
            assistant.artifacts = data.artifacts || [];
            assistant.metrics = {
              ...(assistant.metrics || {}),
              resourcePackage: data,
            };
            appendToolEvent(assistant, {
              agent: 'resource_generator',
              label: `资源包已生成：${data.package_id || ''}`,
              status: 'done',
            });
            Message.success('资源生成成功');
          } else if (event === 'profile_update') {
            appendToolEvent(assistant, {
              agent: 'memory_update',
              label: '学习画像更新已排队',
              status: 'done',
            });
          } else if (event === 'safety_check') {
            handleLiveProcessEvent(assistant, event, data);
            appendToolEvent(assistant, {
              agent: 'safety_check',
              label: data.status === 'passed' ? '引用与安全校验通过' : '已完成安全校验',
              status: 'done',
            });
          } else if (event === 'suggestions') {
            assistant.suggestions = suggestionsFromEvent(data);
          } else if (event === 'done') {
            const process = ensureLiveProcess(assistant);
            process.status = 'done';
            process.currentSummary = '本轮回答已完成引用、安全和后续建议检查';
            process.finishedAt = Date.now();
            assistant.metrics = {
              ...(assistant.metrics || {}),
              ...(data.usage || {}),
            };
            if (Array.isArray(data.suggestions)) {
              assistant.suggestions = data.suggestions;
            }
            assistant.loading = false;
          } else if (event === 'error') {
            handleLiveProcessEvent(assistant, event, data);
            const code = String(data.code || '');
            const message = streamErrorMessage(code, data);
            if (code === 'RESOURCE_GENERATION_FAILED' && assistant.content) {
              appendProcessEvent(assistant, {
                stage: 'compose',
                title: '生成资源',
                detail: message,
                status: 'error',
                log: message,
              });
              appendToolEvent(assistant, {
                agent: 'resource_generator',
                label: message,
                status: 'error',
              });
            } else {
              appendProcessEvent(assistant, {
                stage: 'verify',
                title: '处理失败',
                detail: message,
                status: 'error',
                log: message,
              });
              assistant.content = message;
              assistant.errorCode = code;
            }
            assistant.loading = false;
            Message.error(message);
          }
        },
        abortController.value.signal
      );
    } catch (error) {
      const assistant = latestAssistantMutable();
      const message = error instanceof Error ? error.message : '生成失败';
      if (assistant?.role === 'assistant') {
        assistant.content = /aborted/i.test(message) ? '已停止生成。' : message;
        assistant.loading = false;
      } else {
        chatStore.addMessage({ role: 'error', content: message });
      }
    } finally {
      abortController.value = null;
      chatStore.setIsLoading(false);
      const last = latestAssistantMutable();
      if (last?.role === 'assistant') last.loading = false;
      chatStore.loadConversations().catch((error: unknown) => {
        console.error('[Tutor] failed to refresh conversation list', error);
      });
    }
  }

  function stop() {
    abortController.value?.abort();
  }

  async function retry() {
    if (lastDraft.value) {
      await send(lastDraft.value);
    } else if (lastPayload.value) {
      await send({ text: lastPayload.value.message, files: [] });
    }
  }

  async function loadHistory(threadId: string) {
    if (!threadId) return;
    try {
      const records = await fetchChatHistory(threadId);
      const next: Record<string, any>[] = [];
      records.forEach((record: any) => {
        next.push({
          role: 'user',
          content: record.user_input,
          localId: `u-${record.id}`,
        });
        next.push({
          role: 'assistant',
          content: sanitizeAssistantText(record.response),
          localId: `a-${record.id}`,
          loading: false,
          mode: 'tutor',
          citations: record.citations || [],
          suggestions: record.suggestions || record.metrics?.suggestions || [],
          metrics: record.metrics || {},
          toolEvents: [],
          processEvents: [],
          artifacts: record.metrics?.resourcePackage?.artifacts || [],
          resourcePackage: record.metrics?.resourcePackage || null,
        });
      });
      chatStore.setConversationMessages(threadId, next);
    } catch (error) {
      console.error('[Tutor] failed to load conversation history', error);
      Message.error('加载对话历史失败，请稍后重试');
    }
  }

  function updateCourse(courseId: string) {
    const course = courses.value.find((item) => item.courseId === courseId);
    courseContext.value = {
      ...courseContext.value,
      courseId,
      chapterId: course?.chapters?.[0]?.chapterId || '',
      knowledgePointIds: course?.chapters?.[0]?.knowledgePointIds || [],
    };
  }

  function updateChapter(chapterId: string) {
    const chapter = selectedCourse.value?.chapters.find((item) => item.chapterId === chapterId);
    courseContext.value = {
      ...courseContext.value,
      chapterId,
      knowledgePointIds: chapter?.knowledgePointIds || [],
    };
  }

  function routeText(value: unknown) {
    return Array.isArray(value) ? String(value[0] || '') : String(value || '');
  }

  function applyRouteContext() {
    const courseId = routeText(route.query.courseId);
    const chapterId = routeText(route.query.chapterId || route.query.sectionId);
    const prompt = routeText(route.query.prompt);
    if (courseId && courses.value.some((item) => item.courseId === courseId)) {
      updateCourse(courseId);
      if (chapterId) updateChapter(chapterId);
      courseContext.value.useCourseRag = true;
    }
    if (prompt) composerRef.value?.setDraft(prompt);
  }

  onMounted(async () => {
    document.addEventListener('keydown', handleDocumentKeydown);
    await chatStore.loadConversations();
    chatStore.enterDraftSession();
    try {
      courses.value = await fetchAIContextCourses();
    } catch {
      courses.value = [];
    }
    applyRouteContext();
    try {
      learningReport.value = await fetchLearningReport(false);
    } catch {
      learningReport.value = null;
    }
  });

  onUnmounted(() => {
    document.removeEventListener('keydown', handleDocumentKeydown);
  });

  watch(
    () => chatStore.currentConversationId,
    async (id) => {
      if (chatStore.isLoading) return;
      if (id) await loadHistory(id);
    }
  );
</script>

<template>
  <div
    class="tutor-chat-layout"
    :class="{
      'tutor-chat-layout--sidebar-collapsed': sidebarCollapsed,
      'tutor-chat-layout--empty': !messages.length,
    }"
  >
    <ChatSidebar
      :conversations="conversations"
      :current-id="chatStore.currentConversationId"
      :collapsed="sidebarCollapsed"
      @new-chat="chatStore.enterDraftSession()"
      @switch="chatStore.switchConversation"
      @delete="deleteConversation"
      @clear-all="clearAllConversations"
      @toggle="sidebarCollapsed = !sidebarCollapsed"
    />

    <section class="tutor-chat-layout__main">
      <div class="chat-main-actions">
        <button
          ref="contextButtonRef"
          type="button"
          aria-controls="tutor-context-drawer"
          :aria-expanded="drawerVisible"
          @click="openContextDrawer"
        >上下文</button>
      </div>
      <div ref="mainScroller" class="chat-main-scroll">
        <ChatMain
          :messages="messages"
          :loading="chatStore.isLoading"
          @retry="retry"
          @send-suggestion="send({ text: $event, files: [] })"
        />
        <details v-if="latestRawReasoningDebug" class="raw-reasoning-debug">
          <summary>Raw reasoning debug</summary>
          <pre>{{ latestRawReasoningDebug }}</pre>
        </details>
      </div>
      <div class="composer-dock">
        <ChatComposer
          ref="composerRef"
          :loading="chatStore.isLoading"
          :mode="mode"
          :tools="tools"
          :reasoning-level="reasoningLevel"
          :resource-request="resourceRequest"
          @send="send"
          @stop="stop"
          @action="handleAction"
          @toggle-web="tools.webSearch = !tools.webSearch"
          @set-reasoning="reasoningLevel = $event"
          @open-panel="openPanel"
          @update-resource-types="resourceRequest.types = $event"
        />
      </div>
    </section>

    <ContextDrawer
      :visible="drawerVisible"
      :courses="courses"
      :course-context="courseContext"
      :citations="latestCitations"
      :tool-events="latestToolEvents"
      :profile-items="profileItems"
      :artifacts="latestArtifacts"
      :resource-package="latestPackage"
      @close="closeContextDrawer"
      @update-course="updateCourse"
      @update-chapter="updateChapter"
      @toggle-rag="courseContext.useCourseRag = !courseContext.useCourseRag"
    />
  </div>
</template>

<style scoped lang="scss">
  .tutor-chat-layout {
    --tutor-sidebar-width: 280px;

    display: flex;
    height: calc(100vh - 64px);
    overflow: hidden;
    background: #fff;
  }

  .tutor-chat-layout--sidebar-collapsed {
    --tutor-sidebar-width: 56px;
  }

  .tutor-chat-layout__main {
    position: relative;
    flex: 1;
    min-width: 0;
    background: #fff;
  }

  .chat-main-scroll {
    height: 100%;
    overflow: hidden;
  }

  .raw-reasoning-debug {
    position: absolute;
    right: 28px;
    bottom: 124px;
    z-index: 12;
    width: min(460px, calc(100vw - 720px));
    border: 1px dashed rgba(240, 68, 56, 0.3);
    border-radius: 14px;
    background: rgba(255, 251, 250, 0.96);
    color: #7a271a;
    font-size: 12px;
    box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);

    summary {
      cursor: pointer;
      padding: 10px 12px;
      font-weight: 600;
    }

    pre {
      max-height: 240px;
      overflow: auto;
      margin: 0;
      padding: 0 12px 12px;
      white-space: pre-wrap;
      word-break: break-word;
    }
  }

  .chat-main-actions {
    position: absolute;
    top: 16px;
    right: 24px;
    z-index: 8;

    button {
      height: 36px;
      padding: 0 14px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 999px;
      color: #475467;
      background: rgba(255, 255, 255, 0.92);
      cursor: pointer;

      &:hover {
        color: #4f46e5;
        border-color: rgba(99, 102, 241, 0.35);
      }
    }
  }

  .composer-dock {
    position: absolute;
    right: 0;
    bottom: 22px;
    left: 0;
    z-index: 10;
    pointer-events: none;
    transition: transform 0.18s ease;

    :deep(.chat-composer) {
      pointer-events: auto;
    }
  }

  @media (max-width: 1100px) {
    .tutor-chat-layout {
      height: calc(100vh - 64px);
    }
  }
</style>
