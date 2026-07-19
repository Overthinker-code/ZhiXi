<script setup lang="ts">
  import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { Message, Modal } from '@arco-design/web-vue';
  import {
    fetchAIContextCourses,
    fetchCourseAgents,
    uploadAIAttachment,
    type AIChatStreamPayload,
    type AIContextCourse,
    type ChatAttachmentPayload,
    type ChatToolPayload,
    type CourseContextPayload,
    type CourseAgentContractSummary,
    type ReasoningLevel,
    type ResourceRequestPayload,
    type TutorMode,
  } from '@/api/ai-chat';
  import { fetchAgentTasks, type AgentTask } from '@/api/agent-workspace';
  import {
    fetchCurrentLearningTask,
    updateCurrentLearningTask,
    type CurrentLearningTask,
  } from '@/api/learning-task';
  import { fetchChatHistory, fetchLearningReport } from '@/api/rag';
  import { useChatStore } from '@/store/chat';
  import { getToken } from '@/utils/auth';
  import ChatComposer from './ChatComposer.vue';
  import CourseAgentSessionBar from './CourseAgentSessionBar.vue';
  import ChatMain from './ChatMain.vue';
  import ChatSidebar from './ChatSidebar.vue';
  import ContextDrawer from './ContextDrawer.vue';
  import {
    isAbortFailure,
    markTraceStopped,
    markTraceStopping,
  } from './chatInterruption';
  import { createChatStreamTarget } from './chatStreamTarget';
  import { mergeTraceItem } from './chatTraceState';
  import {
    buildPracticeFollowUp,
    type GeneratePracticeFollowUp,
  } from './postAnswerActions';
  import {
    buildConversationTitle,
    shouldGenerateConversationTitle,
  } from './conversationTitle';
  import {
    computeChatBottomInset,
    DEFAULT_CHAT_BOTTOM_INSET,
  } from './chatLayoutMetrics';
  import { useSelectionQueryMenu } from '@/composables/useSelectionQueryMenu';
  import SelectionAiAnswerPanel from '@/views/course/coursevideo/components/SelectionAiAnswerPanel.vue';
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
  const router = useRouter();
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
  const courseAgents = ref<CourseAgentContractSummary[]>([]);
  const learningReport = ref<Record<string, any> | null>(null);
  const currentLearningTask = ref<CurrentLearningTask | null>(null);
  const taskEditorOpen = ref(false);
  const taskSaving = ref(false);
  const taskDraft = ref({ title: '', goal: '', deadline: '' });
  const abortController = ref<AbortController | null>(null);
  const activeAssistantMessage = ref<Record<string, any> | null>(null);
  const lastPayload = ref<AIChatStreamPayload | null>(null);
  const lastDraft = ref<{ text: string; files: File[] } | null>(null);
  const mainScroller = ref<HTMLElement | null>(null);
  const composerDockRef = ref<HTMLElement | null>(null);
  const chatBottomInset = ref(DEFAULT_CHAT_BOTTOM_INSET);
  let composerResizeObserver: ResizeObserver | null = null;

  function chatSelectionContext() {
    const course = selectedCourse.value?.title ? `当前课程：${selectedCourse.value.title}` : '';
    const recentMessages = messages.value
      .slice(-8)
      .map((item: any) => `${item.role === 'assistant' ? 'AI' : '用户'}：${String(item.content || '')}`)
      .join('\n');
    return [course, recentMessages].filter(Boolean).join('\n\n');
  }

  const {
    promptTemplates: selectionPromptTemplates,
    showContextMenu: showSelectionContextMenu,
    contextMenuStyle: selectionContextMenuStyle,
    isLoadingResponse: isSelectionLoadingResponse,
    responseCitations: selectionResponseCitations,
    responseCitationHints: selectionResponseCitationHints,
    responseConfidence: selectionResponseConfidence,
    responseGroundingMode: selectionResponseGroundingMode,
    responseMetrics: selectionResponseMetrics,
    showAnswerPanel: showSelectionAnswerPanel,
    answerPanelBounds: selectionAnswerPanelBounds,
    answerPanelSession: selectionAnswerPanelSession,
    isTypingAnswer: isSelectionTypingAnswer,
    renderedResponse: selectionRenderedResponse,
    bridgeLine: selectionBridgeLine,
    handleTextSelection: handleSelectionTextSelection,
    sendAIQuery: sendSelectionAIQuery,
    clearAnswerPanel: clearSelectionAnswerPanel,
  } = useSelectionQueryMenu(chatSelectionContext);

  const conversations = computed(() => chatStore.conversations || []);
  const messages = computed(() => chatStore.currentMessages || []);
  const latestAssistant = computed(() =>
    [...messages.value].reverse().find((item: any) => item.role === 'assistant')
  );
  const latestCitations = computed(() => latestAssistant.value?.citations || []);
  const latestToolEvents = computed(() => latestAssistant.value?.toolEvents || []);
  const latestArtifacts = computed(() => latestAssistant.value?.artifacts || []);
  const latestPackage = computed(() => latestAssistant.value?.resourcePackage || null);
  const selectedCourse = computed(() =>
    courses.value.find((item) => item.courseId === courseContext.value.courseId)
  );
  const routeAgentKey = computed(() => routeText(route.query.agentKey));
  const activeCourseAgent = computed(() =>
    courseAgents.value.find((item) => item.key === routeAgentKey.value)
  );
  const generalStarterActions = computed(() => [
    selectedCourse.value
      ? `请梳理《${selectedCourse.value.title}》当前最值得复习的三个知识点`
      : '请先帮我明确今天最值得完成的一项学习任务',
    '请从一道基础诊断题开始，不要提前给出答案',
    '帮我制定一个 30 分钟、可以立即执行的学习计划',
  ]);
  const profileItems = computed(() => {
    const weak = Array.isArray(learningReport.value?.weak_points)
      ? learningReport.value?.weak_points.slice(0, 2).join(' / ')
      : '待更新';
    return [
      { label: '学习目标', value: learningReport.value?.current_goal || '课程理解与题目迁移' },
      { label: '认知风格', value: learningReport.value?.learning_style || '例题驱动' },
      { label: '薄弱点', value: weak || '待更新' },
      {
        label: '学习状态',
        value: ({ low: '状态稳定', medium: '持续观察', high: '需要关注' } as Record<string, string>)[
          String(learningReport.value?.risk_level || 'medium').toLowerCase()
        ] || '持续观察',
      },
    ];
  });
  const currentTaskDeadline = computed(() => {
    const value = currentLearningTask.value?.deadline;
    if (!value) return '未设置截止时间';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '已设置截止时间';
    return `截止 ${parsed.toLocaleString('zh-CN', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })}`;
  });

  function deadlineInputValue(value?: string | null) {
    if (!value) return '';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '';
    const local = new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60_000);
    return local.toISOString().slice(0, 16);
  }

  function openTaskEditor() {
    const task = currentLearningTask.value;
    if (!task) return;
    taskDraft.value = {
      title: task.title,
      goal: task.goal,
      deadline: deadlineInputValue(task.deadline),
    };
    taskEditorOpen.value = true;
  }

  async function loadCurrentLearningTask() {
    try {
      currentLearningTask.value = await fetchCurrentLearningTask();
    } catch (error) {
      console.error('[Tutor] failed to load current learning task', error);
    }
  }

  async function saveCurrentLearningTask() {
    const title = taskDraft.value.title.trim();
    const goal = taskDraft.value.goal.trim();
    if (!title || !goal) {
      Message.warning('请填写任务名称和学习目标');
      return;
    }
    taskSaving.value = true;
    try {
      await updateCurrentLearningTask({
        title,
        goal,
        deadline: taskDraft.value.deadline
          ? new Date(taskDraft.value.deadline).toISOString()
          : null,
      });
      await loadCurrentLearningTask();
      taskEditorOpen.value = false;
      Message.success('学习任务已更新');
    } catch (error) {
      Message.error(error instanceof Error ? error.message : '学习任务更新失败');
    } finally {
      taskSaving.value = false;
    }
  }

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

  async function handlePostAction(action: GeneratePracticeFollowUp) {
    if (chatStore.isLoading || action.type !== 'generate_practice') return;

    const previousState = {
      action: activeAction.value,
      mode: mode.value,
      tools: { ...tools.value },
      resourceRequest: {
        ...resourceRequest.value,
        types: [...resourceRequest.value.types],
      },
    };
    const followUp = buildPracticeFollowUp(action.sourcePrompt);
    patchFromAction(getTutorAction('resource_generation'));
    resourceRequest.value = {
      ...resourceRequest.value,
      types: ['quiz'],
      difficulty: 'normal',
      target: followUp.target,
    };

    try {
      await send({ text: followUp.message, files: [] });
    } finally {
      activeAction.value = previousState.action;
      mode.value = previousState.mode;
      tools.value = previousState.tools;
      resourceRequest.value = previousState.resourceRequest;
    }
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

  function applyResourcePackage(assistant: Record<string, any>, packageData: unknown) {
    if (!packageData || typeof packageData !== 'object') return;
    const resourcePackage = packageData as Record<string, any>;
    assistant.resourcePackage = resourcePackage;
    assistant.artifacts = Array.isArray(resourcePackage.artifacts)
      ? resourcePackage.artifacts
      : [];
    assistant.metrics = {
      ...(assistant.metrics || {}),
      resourcePackage,
    };
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
        traceVersion: '1.0',
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
    process.phases = mergeTraceItem(
      phases,
      { title: phase.title || '处理阶段', ...phase },
      'phase'
    );
    process.currentSummary = phase.summary || phase.text || process.currentSummary;
  }

  function upsertTool(process: Record<string, any>, tool: Record<string, any>) {
    const toolsList = Array.isArray(process.tools) ? process.tools : [];
    process.tools = mergeTraceItem(
      toolsList,
      { title: tool.title || '调用学习工具', category: 'tool', ...tool },
      'tool'
    );
    process.currentSummary = tool.summary || tool.text || process.currentSummary;
  }

  function agentTaskStatus(status: unknown) {
    if (status === 'completed') return 'done';
    if (status === 'failed') return 'error';
    if (status === 'waiting') return 'pending';
    return 'running';
  }

  function agentTaskCapability(task: Record<string, any>) {
    const identity = `${task.task_key || ''} ${task.agent_name || ''}`;
    if (/manim|animation/i.test(identity)) return '教学动画智能体';
    if (/image|illustration|picture|绘图|插图/i.test(identity)) return '教学插图智能体';
    return '';
  }

  function userFacingAgentText(value: unknown, capability: string) {
    const text = String(value || '').trim();
    if (!text) return text;
    const inferredCapability =
      capability ||
      (/manim|animation/i.test(text)
        ? '教学动画智能体'
        : /image|illustration|picture|绘图|插图/i.test(text)
          ? '教学插图智能体'
          : '');
    if (!inferredCapability) return text;
    if (/已路由到\s*/.test(text)) return `已选择${inferredCapability}`;
    return text.replace(
      /(?:qwen\s*)?(?:manim|animation|image(?:\s*generation)?|illustration|picture)(?:\s*(?:agent|智能体))?/gi,
      inferredCapability
    );
  }

  function agentTaskTitle(task: Record<string, any>) {
    const key = String(task.task_key || '');
    const name = String(task.agent_name || '');
    const fixedLabels: Record<string, string> = {
      profile: '学习画像智能体',
      knowledge: '课程证据智能体',
      planner: '任务规划智能体',
      evaluator: '结果校验智能体',
    };
    if (fixedLabels[key]) return fixedLabels[key];
    const capability = agentTaskCapability(task);
    if (capability) return capability;
    if (/Quiz/i.test(name)) return '练习生成智能体';
    if (/KnowledgeGraph/i.test(name)) return '知识图谱智能体';
    if (/Resource/i.test(name)) return '资源生成智能体';
    if (/Tutor/i.test(name)) return '课程辅导智能体';
    return name || '专项任务智能体';
  }

  function applyAgentTasks(
    assistant: Record<string, any>,
    tasks: Array<AgentTask | Record<string, any>>
  ) {
    if (!tasks.length) return;
    const process = ensureLiveProcess(assistant);
    tasks.forEach((task, index) => {
      const status = agentTaskStatus(task.status);
      const progress = Math.max(0, Math.min(100, Number(task.progress || 0)));
      const capability = agentTaskCapability(task);
      const message = userFacingAgentText(task.message, capability);
      const progressText = progress > 0 && progress < 100 ? ` · ${progress}%` : '';
      upsertTool(process, {
        stepId: `agent-task-${task.task_key || index}`,
        tool: `agent:${task.task_key || index}`,
        title: agentTaskTitle(task),
        category: task.task_key === 'knowledge' ? 'retrieval' : 'tool',
        sequence: 20 + index,
        status,
        text: `${message}${progressText}`,
        summary: `${message}${progressText}`,
        startedAt: task.created_time,
        finishedAt: ['done', 'error'].includes(status) ? task.updated_time : undefined,
        agentTask: true,
        progress,
      });
    });
    const running = tasks.find((task) => task.status === 'running');
    const failed = tasks.find((task) => task.status === 'failed');
    if (failed) {
      process.status = 'error';
      process.currentSummary = userFacingAgentText(
        failed.message || '部分任务未完成',
        agentTaskCapability(failed)
      );
    } else if (running) {
      process.status = 'running';
      process.currentSummary = userFacingAgentText(
        running.message || '正在执行学习任务',
        agentTaskCapability(running)
      );
    } else if (tasks.every((task) => task.status === 'completed')) {
      process.status = 'done';
      process.currentSummary = '多智能体任务已完成';
    }
  }

  function handleLiveProcessEvent(assistant: Record<string, any>, event: string, data: Record<string, any>) {
    const process = ensureLiveProcess(assistant);
    if (event === 'run_started') {
      const retainedAgentTools = Array.isArray(process.tools)
        ? process.tools.filter((item: Record<string, any>) => item.agentTask)
        : [];
      assistant.liveProcess = {
        runId: data.runId,
        traceVersion: data.traceVersion || '1.0',
        status: 'running',
        collapsed: false,
        currentSummary: data.title || '开始处理问题',
        phases: [],
        tools: retainedAgentTools,
        reasoningText: '',
        citations: [],
        safetyStatus: undefined,
        startedAt: data.startedAt || data.timestamp || Date.now(),
        logs: [],
      };
      return;
    }
    if (event === 'agent_tasks') {
      applyAgentTasks(
        assistant,
        Array.isArray(data.tasks) ? data.tasks : []
      );
      return;
    }
    if (event === 'agent_contract') {
      process.agentContract = data;
      process.currentSummary = `${data.label || '专用智能体'}已接管本轮任务`;
      appendLiveLog(
        process,
        `能力边界已锁定：${Array.isArray(data.outputs) ? data.outputs.join('、') : '按任务契约执行'}`,
        'done',
        '选择专用智能体'
      );
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
        stepId: data.stepId,
        id: data.phaseId,
        title: data.title,
        category: data.category,
        sequence: data.sequence,
        status: 'running',
        text: data.text || '',
        startedAt: data.startedAt || data.timestamp || Date.now(),
      });
    } else if (event === 'phase_delta' || event === 'phase_updated' || event === 'process_delta') {
      upsertPhase(process, {
        stepId: data.stepId,
        id: data.phaseId,
        status: 'running',
        title: data.title,
        category: data.category,
        sequence: data.sequence,
        text: data.summary || data.text || '',
        summary: data.summary,
      });
    } else if (event === 'phase_finished') {
      upsertPhase(process, {
        stepId: data.stepId,
        id: data.phaseId,
        title: data.title,
        category: data.category,
        sequence: data.sequence,
        status: data.status || 'done',
        summary: data.summary || '',
        finishedAt: data.finishedAt || data.timestamp || Date.now(),
        durationMs: data.durationMs,
      });
    } else if (event === 'tool_started') {
      upsertTool(process, {
        stepId: data.stepId,
        callId: data.callId,
        tool: data.tool,
        title: data.title,
        category: data.category,
        sequence: data.sequence,
        status: 'running',
        text: data.text || '',
        startedAt: data.startedAt || data.timestamp || Date.now(),
      });
    } else if (event === 'tool_delta') {
      upsertTool(process, {
        stepId: data.stepId,
        callId: data.callId,
        tool: data.tool,
        category: data.category,
        sequence: data.sequence,
        status: 'running',
        text: data.text || '',
      });
    } else if (event === 'tool_result') {
      upsertTool(process, {
        stepId: data.stepId,
        callId: data.callId,
        tool: data.tool,
        title: data.title,
        category: data.category,
        sequence: data.sequence,
        status: data.status || 'done',
        summary: data.summary || '',
        items: Array.isArray(data.items) ? data.items : [],
        finishedAt: data.finishedAt || data.timestamp || Date.now(),
        durationMs: data.durationMs,
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
      process.finishedAt = data.finishedAt || data.timestamp || Date.now();
      process.durationMs = data.durationMs;
      appendLiveLog(process, process.currentSummary, 'done', '完成处理');
    } else if (event === 'error') {
      process.status = 'error';
      process.currentSummary = data.message || '处理失败';
      process.finishedAt = Date.now();
      appendLiveLog(process, process.currentSummary, 'error', '处理失败');
    }
  }

  async function ensureSession() {
    if (chatStore.currentConversationId) return chatStore.currentConversationId;
    if (!getToken()) {
      throw new Error('请先登录后再使用 AI 对话');
    }
    await chatStore.createConversation();
    return chatStore.currentConversationId;
  }

  async function ensureConversationTitle(sessionId: string, prompt: string) {
    const conversation = (conversations.value as Array<Record<string, any>>).find(
      (item: Record<string, any>) => String(item.id) === String(sessionId)
    );
    if (!conversation || !shouldGenerateConversationTitle(conversation.title)) return;
    const title = buildConversationTitle(prompt);
    if (!shouldGenerateConversationTitle(title)) {
      try {
        await chatStore.updateConversationTitle(sessionId, title);
      } catch (error) {
        console.error('[Tutor] failed to persist conversation title', error);
      }
    }
  }

  async function repairDefaultConversationTitles() {
    const pending = (conversations.value as Array<Record<string, any>>).filter((item) =>
      shouldGenerateConversationTitle(item.title)
    );
    let cursor = 0;
    const repairNext = async () => {
      while (cursor < pending.length) {
        const conversation = pending[cursor];
        cursor += 1;
        const localPrompt = chatStore
          .getConversationMessages(conversation.id)
          .find((message: Record<string, any>) => message.role === 'user')?.content;
        try {
          const prompt = localPrompt || (await fetchChatHistory(conversation.id))[0]?.user_input;
          if (prompt) await ensureConversationTitle(conversation.id, String(prompt));
        } catch (error) {
          console.error('[Tutor] failed to repair conversation title', error);
        }
      }
    };
    await Promise.all(
      Array.from({ length: Math.min(3, pending.length) }, () => repairNext())
    );
  }

  async function uploadFiles(files: File[], sessionId: string): Promise<ChatAttachmentPayload[]> {
    const scopedCourseContext =
      routeAgentKey.value && courseContext.value.courseId
        ? {
            courseId: courseContext.value.courseId,
            chapterId: courseContext.value.chapterId,
            knowledgePointIds: [...courseContext.value.knowledgePointIds],
          }
        : undefined;
    return Promise.all(
      files.map(async (file) => {
        const res = await uploadAIAttachment(file, sessionId, scopedCourseContext);
        const lowerName = file.name.toLowerCase();
        const inferredType: ChatAttachmentPayload['type'] =
          file.type.startsWith('image/') || /\.(png|jpe?g|webp|gif|bmp)$/i.test(lowerName)
            ? 'image'
            : /\.(pptx?|ppsx?)$/i.test(lowerName)
              ? 'ppt'
              : /\.pdf$/i.test(lowerName)
                ? 'pdf'
                : /\.(docx?|txt|md|markdown)$/i.test(lowerName)
                  ? 'doc'
                  : /\.(py|js|ts|java|cpp|c|sql)$/i.test(lowerName)
                    ? 'code'
                    : res.type;
        return {
          fileId: String(res.fileId),
          type: inferredType,
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
    return String(data.message || data.content || '回答生成失败，请稍后重试');
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
      agentKey: routeAgentKey.value || undefined,
      // Keep the selected course as ownership/organization context even when
      // course RAG is disabled.  The RAG switch controls retrieval only; it
      // must not detach generated resources from the course the learner chose.
      courseContext: courseContext.value.courseId
        ? { ...courseContext.value, useCourseRag: autoCourseRag }
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
    let streamTarget: ReturnType<typeof createChatStreamTarget> | null = null;
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
      void ensureConversationTitle(sessionId, text);
      const assistantLocalId = `assistant-${sessionId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const assistantMessage = chatStore.addMessage({
        localId: assistantLocalId,
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
          traceVersion: '1.0',
        },
        artifacts: [],
        resourcePackage: null,
      }) as Record<string, any>;
      activeAssistantMessage.value = assistantMessage;
      streamTarget = createChatStreamTarget(sessionId, assistantMessage);
      await nextTick();
      mainScroller.value?.scrollTo({ top: mainScroller.value.scrollHeight, behavior: 'smooth' });
      abortController.value = new AbortController();
      let streamedAnswerChars = 0;
      await streamTutorChat(
        payload,
        ({ event, data }) => {
          if (!streamTarget?.accepts(event, data)) return;
          const assistant = streamTarget.message;
          if (event === 'session_created') return;
          if (event === 'learning_task_updated') {
            if (data.task && typeof data.task === 'object') {
              currentLearningTask.value = data.task as CurrentLearningTask;
            }
          } else if (
            [
              'run_started',
              'agent_tasks',
              'agent_contract',
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
              detail: `已找到 ${Array.isArray(data.items) ? data.items.length : 0} 个参考来源`,
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
            // Public execution summaries arrive through process_delta; private reasoning is ignored.
          } else if (event === 'answer_delta') {
            const safeText = sanitizeAssistantText(data.text || '', { preserveEdges: true });
            if (!safeText) return;
            const isFirstAnswerDelta = streamedAnswerChars === 0;
            streamedAnswerChars += safeText.length;
            const process = ensureLiveProcess(assistant);
            process.answerChars = streamedAnswerChars;
            if (isFirstAnswerDelta) process.answerStartedAt = Date.now();
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
            applyResourcePackage(assistant, data);
            appendToolEvent(assistant, {
              agent: 'resource_generator',
              label: `资源包已生成：${data.package_id || ''}`,
              status: 'done',
            });
            Message.success('资源生成成功');
          } else if (event === 'profile_update') {
            // Background profile refresh is real but not a completed user-facing tool step.
            assistant.metrics = {
              ...(assistant.metrics || {}),
              profileUpdateStatus: data.status || 'queued',
            };
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
            process.currentSummary = data.summary || '本轮回答已完成';
            process.finishedAt = Date.now();
            assistant.metrics = {
              ...(assistant.metrics || {}),
              ...(data.usage || {}),
            };
            applyResourcePackage(assistant, data.usage?.resourcePackage);
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
      const assistant = streamTarget?.message;
      const message = error instanceof Error ? error.message : '生成失败';
      if (assistant?.role === 'assistant') {
        if (isAbortFailure(error)) {
          assistant.content = assistant.content || '已停止生成。';
          assistant.interrupted = true;
          assistant.liveProcess = markTraceStopped(assistant.liveProcess);
        } else {
          assistant.content = assistant.content || message;
          assistant.errorCode = assistant.errorCode || 'STREAM_FAILED';
          const process = ensureLiveProcess(assistant);
          process.status = 'error';
          process.currentSummary = message;
          process.finishedAt = Date.now();
        }
        assistant.loading = false;
      } else {
        if (!isAbortFailure(error)) Message.error(message);
      }
    } finally {
      abortController.value = null;
      if (activeAssistantMessage.value === streamTarget?.message) {
        activeAssistantMessage.value = null;
      }
      chatStore.setIsLoading(false);
      const assistant = streamTarget?.message;
      if (assistant?.role === 'assistant') assistant.loading = false;
      chatStore.loadConversations().catch((error: unknown) => {
        console.error('[Tutor] failed to refresh conversation list', error);
      });
    }
  }

  function stop() {
    const controller = abortController.value;
    const assistant = activeAssistantMessage.value;
    if (!controller || controller.signal.aborted) return;
    if (assistant) {
      assistant.stopRequested = true;
      assistant.liveProcess = markTraceStopping(assistant.liveProcess);
    }
    controller.abort();
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
      try {
        const tasks = await fetchAgentTasks(threadId);
        const lastAssistant = [...next]
          .reverse()
          .find((message) => message.role === 'assistant');
        if (lastAssistant && tasks.length) {
          lastAssistant.liveProcess = {
            runId: tasks[0].run_id,
            status: 'idle',
            collapsed: true,
            currentSummary: '已恢复最近一次执行记录',
            phases: [],
            tools: [],
            citations: [],
            logs: [],
            traceVersion: '1.0',
          };
          applyAgentTasks(lastAssistant, tasks);
        }
      } catch (error) {
        console.error('[Tutor] failed to restore agent tasks', error);
      }
      chatStore.setConversationMessages(threadId, next);
      const conversation = (conversations.value as Array<Record<string, any>>).find(
        (item: Record<string, any>) => String(item.id) === String(threadId)
      );
      if (conversation && shouldGenerateConversationTitle(conversation.title) && records[0]?.user_input) {
        void ensureConversationTitle(threadId, String(records[0].user_input));
      }
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

  async function loadCourseAgentContract() {
    if (!routeAgentKey.value) return;
    try {
      const catalog = await fetchCourseAgents(routeText(route.query.courseId) || undefined);
      courseAgents.value = catalog.agents || [];
      const contract = courseAgents.value.find((item) => item.key === routeAgentKey.value);
      if (contract) mode.value = contract.mode;
    } catch {
      courseAgents.value = [];
    }
  }

  function backToCourseAgents() {
    const courseId = routeText(route.query.courseId);
    if (courseId) {
      router.push({ name: 'StudentCourseAgent', params: { courseId }, query: { task: routeAgentKey.value } });
      return;
    }
    router.back();
  }

  onMounted(async () => {
    document.addEventListener('keydown', handleDocumentKeydown);
    if (typeof ResizeObserver !== 'undefined') {
      composerResizeObserver = new ResizeObserver(([entry]) => {
        chatBottomInset.value = computeChatBottomInset(entry?.contentRect.height);
      });
      if (composerDockRef.value) composerResizeObserver.observe(composerDockRef.value);
    }
    await chatStore.loadConversations();
    chatStore.enterDraftSession();
    void repairDefaultConversationTitles();
    try {
      courses.value = await fetchAIContextCourses();
    } catch {
      courses.value = [];
    }
    applyRouteContext();
    await loadCourseAgentContract();
    try {
      learningReport.value = await fetchLearningReport(false);
    } catch {
      learningReport.value = null;
    }
    await loadCurrentLearningTask();
  });

  onUnmounted(() => {
    document.removeEventListener('keydown', handleDocumentKeydown);
    composerResizeObserver?.disconnect();
    composerResizeObserver = null;
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
      'tutor-chat-layout--course-agent': Boolean(activeCourseAgent),
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
      <CourseAgentSessionBar
        v-if="activeCourseAgent"
        :agent="activeCourseAgent"
        :course-title="selectedCourse?.title"
        @back="backToCourseAgents"
      />
      <section
        v-if="currentLearningTask"
        class="current-learning-task"
        aria-label="当前学习任务"
      >
        <div v-if="!taskEditorOpen" class="current-learning-task__summary">
          <div class="current-learning-task__copy">
            <span>当前任务</span>
            <strong>{{ currentLearningTask.title }}</strong>
            <p>{{ currentLearningTask.goal }}</p>
          </div>
          <div class="current-learning-task__status">
            <small>{{ currentTaskDeadline }} · {{ currentLearningTask.current_stage }}</small>
            <div
              class="current-learning-task__progress"
              role="progressbar"
              :aria-valuenow="currentLearningTask.progress"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-label="`任务进度 ${currentLearningTask.progress}%`"
            >
              <i :style="{ width: `${currentLearningTask.progress}%` }" />
            </div>
          </div>
          <button type="button" class="current-learning-task__edit" @click="openTaskEditor">
            编辑
          </button>
        </div>
        <form v-else class="current-learning-task__form" @submit.prevent="saveCurrentLearningTask">
          <label>
            <span>任务名称</span>
            <input v-model="taskDraft.title" maxlength="200" autocomplete="off" />
          </label>
          <label>
            <span>学习目标</span>
            <input v-model="taskDraft.goal" maxlength="500" autocomplete="off" />
          </label>
          <label>
            <span>截止时间</span>
            <input v-model="taskDraft.deadline" type="datetime-local" />
          </label>
          <div class="current-learning-task__form-actions">
            <button type="button" @click="taskEditorOpen = false">取消</button>
            <button type="submit" class="primary" :disabled="taskSaving">
              {{ taskSaving ? '正在保存…' : '保存' }}
            </button>
          </div>
        </form>
      </section>
      <div class="chat-main-actions">
        <button
          ref="contextButtonRef"
          type="button"
          aria-controls="tutor-context-drawer"
          :aria-expanded="drawerVisible"
          @click="openContextDrawer"
        >上下文</button>
      </div>
      <div
        ref="mainScroller"
        class="chat-main-scroll chat-selection-root"
        @mouseup="handleSelectionTextSelection('.chat-selection-root', $event)"
        @touchend="handleSelectionTextSelection('.chat-selection-root', $event)"
      >
        <ChatMain
          :messages="messages"
          :loading="chatStore.isLoading"
          :bottom-inset="chatBottomInset"
          :empty-title="activeCourseAgent ? `${activeCourseAgent.label}准备好了` : undefined"
          :empty-description="activeCourseAgent?.description"
          :starter-actions="activeCourseAgent?.starterActions || generalStarterActions"
          @retry="retry"
          @send-suggestion="send({ text: $event, files: [] })"
          @post-action="handlePostAction"
          @stop="stop"
          @send-starter="send({ text: $event, files: [] })"
        />
      </div>
      <Transition name="sel-menu">
        <div
          v-if="showSelectionContextMenu"
          :style="selectionContextMenuStyle"
          class="selection-context-menu"
          @mousedown.stop
          @pointerdown.stop
        >
          <div class="selection-context-menu__title">划词唤醒</div>
          <button
            v-for="template in selectionPromptTemplates"
            :key="template.key"
            type="button"
            class="selection-context-menu__item"
            @click="sendSelectionAIQuery(template.key)"
          >
            {{ template.label }}
          </button>
        </div>
      </Transition>
      <svg
        v-if="selectionBridgeLine.active"
        class="selection-bridge"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <line
          :x1="selectionBridgeLine.x1"
          :y1="selectionBridgeLine.y1"
          :x2="selectionBridgeLine.x2"
          :y2="selectionBridgeLine.y2"
          stroke="#2563eb"
          stroke-width="2.5"
          stroke-linecap="round"
          class="selection-bridge-line"
        />
      </svg>
      <SelectionAiAnswerPanel
        v-if="showSelectionAnswerPanel && selectionAnswerPanelBounds"
        :visible="showSelectionAnswerPanel"
        :session="selectionAnswerPanelSession"
        :initial-bounds="selectionAnswerPanelBounds"
        :html="selectionRenderedResponse"
        :loading="isSelectionLoadingResponse"
        :typing="isSelectionTypingAnswer"
        :citations="selectionResponseCitations"
        :citation-hints="selectionResponseCitationHints"
        :confidence="selectionResponseConfidence"
        :grounding-mode="selectionResponseGroundingMode"
        :metrics="selectionResponseMetrics"
        @close="clearSelectionAnswerPanel"
      />
      <div ref="composerDockRef" class="composer-dock">
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
    display: flex;
    flex-direction: column;
    background: #fff;
  }

  .chat-main-scroll {
    min-height: 0;
    flex: 1;
    overflow: hidden;
  }

  .chat-selection-root {
    ::selection {
      color: #172033;
      background: rgba(99, 102, 241, 0.18);
    }
  }

  .selection-context-menu {
    position: fixed;
    z-index: 10003;
    width: 172px;
    padding: 8px;
    border: 1px solid rgba(209, 216, 238, 0.96);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.97);
    box-shadow: 0 18px 42px rgba(22, 31, 60, 0.18);
    backdrop-filter: blur(16px);
  }

  .selection-context-menu__title {
    margin-bottom: 4px;
    padding: 6px 8px 8px;
    border-bottom: 1px solid #edf0fb;
    color: #172033;
    font-size: 12px;
    font-weight: 700;
  }

  .selection-context-menu__item {
    width: 100%;
    padding: 9px 8px;
    border: 0;
    border-radius: 8px;
    color: #43506a;
    background: transparent;
    font-size: 13px;
    text-align: left;
    cursor: pointer;

    &:hover {
      color: #2f63e6;
      background: #f0f4ff;
    }
  }

  .sel-menu-enter-active,
  .sel-menu-leave-active {
    transition: opacity 0.18s ease, transform 0.18s ease;
  }

  .sel-menu-enter-from,
  .sel-menu-leave-to {
    opacity: 0;
    transform: translateY(4px) scale(0.98);
  }

  .selection-bridge {
    position: fixed;
    z-index: 10002;
    inset: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
  }

  .selection-bridge-line {
    stroke-dasharray: 8 7;
    filter: drop-shadow(0 0 6px rgba(47, 123, 255, 0.55));
  }

  .current-learning-task {
    width: min(820px, calc(100% - 150px));
    flex: 0 0 auto;
    margin: 12px auto 0;
    padding: 12px 14px;
    border: 1px solid rgba(79, 70, 229, 0.12);
    border-radius: 16px;
    background: #fafaff;
  }

  .current-learning-task__summary {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(150px, 210px) auto;
    align-items: center;
    gap: 16px;
  }

  .current-learning-task__copy {
    min-width: 0;

    span {
      display: block;
      color: #6366f1;
      font-size: 11px;
      font-weight: 750;
    }

    strong,
    p {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      margin-top: 2px;
      color: #1d2939;
      font-size: 14px;
    }

    p {
      margin: 3px 0 0;
      color: #667085;
      font-size: 12px;
    }
  }

  .current-learning-task__status {
    min-width: 0;

    small {
      display: block;
      overflow: hidden;
      color: #667085;
      font-size: 11px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .current-learning-task__progress {
    height: 5px;
    margin-top: 7px;
    overflow: hidden;
    border-radius: 999px;
    background: #e9eaf8;

    i {
      display: block;
      min-width: 2px;
      height: 100%;
      border-radius: inherit;
      background: #6366f1;
    }
  }

  .current-learning-task__edit,
  .current-learning-task__form-actions button {
    height: 32px;
    padding: 0 12px;
    border: 1px solid rgba(15, 23, 42, 0.1);
    border-radius: 10px;
    color: #475467;
    background: #fff;
    cursor: pointer;
  }

  .current-learning-task__form {
    display: grid;
    grid-template-columns: minmax(150px, 0.8fr) minmax(220px, 1.3fr) minmax(180px, 0.8fr) auto;
    align-items: end;
    gap: 10px;

    label {
      min-width: 0;
    }

    label span {
      display: block;
      margin-bottom: 5px;
      color: #667085;
      font-size: 11px;
    }

    input {
      width: 100%;
      height: 34px;
      padding: 0 10px;
      border: 1px solid #dfe3eb;
      border-radius: 9px;
      outline: none;
      color: #344054;
      background: #fff;

      &:focus-visible {
        border-color: #818cf8;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.12);
      }
    }
  }

  .current-learning-task__form-actions {
    display: flex;
    gap: 7px;

    button.primary {
      border-color: #4f46e5;
      color: #fff;
      background: #4f46e5;
    }

    button:disabled {
      cursor: wait;
      opacity: 0.6;
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

  .tutor-chat-layout--course-agent .chat-main-actions {
    top: 92px;
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

    .current-learning-task__form {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr);
    }
  }

  @media (max-width: 860px) {
    .tutor-chat-layout :deep(.chat-sidebar) {
      display: none;
    }

    .current-learning-task {
      width: calc(100% - 128px);
      margin-left: 16px;
    }

    .current-learning-task__summary {
      grid-template-columns: minmax(0, 1fr) auto;
    }

    .current-learning-task__status {
      display: none;
    }

    .current-learning-task__form {
      grid-template-columns: 1fr;
    }
  }
</style>
