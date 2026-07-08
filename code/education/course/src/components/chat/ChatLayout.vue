<script setup lang="ts">
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { Message, Modal } from '@arco-design/web-vue';
  import {
    fetchAIContextCourses,
    streamAIChat,
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
  import { isPipelineThought } from '@/utils/streamReasoning';
  import ChatComposer from './ChatComposer.vue';
  import ChatMain from './ChatMain.vue';
  import ChatSidebar from './ChatSidebar.vue';
  import ContextDrawer from './ContextDrawer.vue';
  import {
    CHAT_DEFAULT_RESOURCE_TYPES,
    getTutorAction,
    type TutorAction,
    type TutorPanel,
  } from './tutorActions';

  const chatStore = useChatStore();
  const sidebarCollapsed = ref(false);
  const drawerVisible = ref(false);
  const composerRef = ref<InstanceType<typeof ChatComposer> | null>(null);
  const activeAction = ref<TutorAction>(getTutorAction('general_chat'));
  const mode = ref<TutorMode>('tutor');
  const tools = ref<ChatToolPayload>({
    webSearch: false,
    deepResearch: false,
    homeworkReview: false,
    resourceGeneration: false,
    citationRequired: true,
  });
  const reasoningLevel = ref<ReasoningLevel>('balanced');
  const courseContext = ref<CourseContextPayload>({
    courseId: 'c1111111-1111-4111-9111-111111111101',
    chapterId: 'ch3',
    knowledgePointIds: ['er-model'],
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
    if (activeAction.value.id !== 'general_chat') return Boolean(courseContext.value.useCourseRag);
    const normalized = text.toLowerCase();
    return /课程|章节|本章|本节|课件|讲义|数据库|关系模型|er\s*模型|sql|事务|索引|范式|数据结构|二叉树|算法/.test(
      normalized
    );
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
        await chatStore.deleteAllConversations();
        Message.success('已清空全部历史');
      },
    });
  }

  function openPanel(panel: TutorPanel) {
    if (panel === 'upload') {
      composerRef.value?.openUpload();
    } else if (panel === 'course_picker') {
      drawerVisible.value = true;
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

  function hasProcessStage(assistant: Record<string, any>, stage: string, status?: string) {
    const list = Array.isArray(assistant.processEvents) ? assistant.processEvents : [];
    return list.some((item: Record<string, any>) =>
      String(item.stage || '') === stage && (!status || String(item.status || '') === status)
    );
  }

  const INTERNAL_REASONING_LINE_RE =
    /^(intent_classifier|course_context|deep_research|tutor|homework_review|resource_generation|course_retriever|safety_check|memory_update|数据库系统原理|第\s*\d+\s*章.*|.*ER\s*模型.*)$/i;
  const INTERNAL_REASONING_TEXT_RE =
    /(首条系统消息|已根据当前问题检索知识库|上下文注入协作线程|协作线程|系统消息|course_context|intent_classifier|deep_research|数据库系统原理\s*$)/i;

  function normalizeReasoningLine(line: string) {
    const text = line
      .replace(/^【[^】]+】\s*/, '')
      .replace(/\s*\([^)]*(?:系统消息|agent|context|classifier)[^)]*\)\s*/gi, '')
      .trim();
    if (!text) return '';
    if (INTERNAL_REASONING_LINE_RE.test(text)) return '';
    if (INTERNAL_REASONING_TEXT_RE.test(text)) return '';
    return text;
  }

  function appendReasoningDelta(assistant: Record<string, any>, data: Record<string, any>) {
    const raw = String(data.text || '');
    if (!raw) return;
    const stage = String(data.stage || data.agent || '').trim();
    const visible = raw
      .split(/\r?\n/)
      .map((line) => {
        const text = line.trim();
        if (!text) return '';
        if (isPipelineThought(text, stage)) return '';
        if (/^(intent_classifier|course_context|deep_research)$/i.test(text)) return '';
        if (/^(agent|router|planner|worker|tool)_[a-z0-9_]+$/i.test(text)) return '';
        return normalizeReasoningLine(text);
      })
      .filter(Boolean)
      .join('\n');
    if (!visible.trim()) return;
    assistant.reasoning_content = `${assistant.reasoning_content || ''}${visible}\n`;
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
    const attachments: ChatAttachmentPayload[] = [];
    for (const file of files) {
      const res = await uploadAIAttachment(file, sessionId);
      attachments.push({
        fileId: String(res.fileId),
        type: res.type,
        name: res.name || file.name,
      });
    }
    return attachments;
  }

  function buildPayload(text: string, attachments: ChatAttachmentPayload[]): AIChatStreamPayload {
    const autoCourseRag = shouldUseCourseContext(text);
    return {
      sessionId: chatStore.currentConversationId || undefined,
      message: text,
      mode: mode.value,
      actionId: activeAction.value.id,
      courseContext: { ...courseContext.value, useCourseRag: autoCourseRag },
      tools: {
        ...tools.value,
        citationRequired: tools.value.citationRequired || autoCourseRag || Boolean(attachments.length),
      },
      reasoning: {
        level: reasoningLevel.value,
        showSummary: true,
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
        artifacts: [],
        resourcePackage: null,
      });
      await nextTick();
      mainScroller.value?.scrollTo({ top: mainScroller.value.scrollHeight, behavior: 'smooth' });
      abortController.value = new AbortController();
      let streamedAnswerChars = 0;
      let lastProcessCharMark = 0;
      await streamAIChat(
        payload,
        ({ event, data }) => {
          const assistant = latestAssistantMutable();
          if (!assistant) return;
          if (event === 'session_created' && data.sessionId && data.sessionId !== chatStore.currentConversationId) {
            chatStore.currentConversationId = String(data.sessionId);
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
          } else if (event === 'reasoning_summary_delta') {
            appendReasoningDelta(assistant, data);
          } else if (event === 'answer_delta') {
            streamedAnswerChars += String(data.text || '').length;
            if (!hasProcessStage(assistant, 'compose', 'running')) {
              appendProcessEvent(assistant, {
                stage: 'compose',
                title: '组织回答',
                detail: '模型正在流式生成正文',
                status: 'running',
                log: '开始接收 answer_delta',
              });
            }
            if (streamedAnswerChars - lastProcessCharMark >= 420) {
              lastProcessCharMark = streamedAnswerChars;
              appendProcessEvent(assistant, {
                stage: 'compose',
                title: '组织回答',
                detail: '模型正在持续输出正文',
                status: 'running',
                log: `已接收约 ${streamedAnswerChars} 个字符，继续流式生成`,
              });
            }
            assistant.content = `${assistant.content || ''}${data.text || ''}`;
          } else if (event === 'citation') {
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
            appendToolEvent(assistant, {
              agent: 'safety_check',
              label: data.status === 'passed' ? '引用与安全校验通过' : '已完成安全校验',
              status: 'done',
            });
          } else if (event === 'suggestions') {
            assistant.suggestions = Array.isArray(data.items)
              ? data.items
              : Array.isArray(data.suggestions)
                ? data.suggestions
                : Array.isArray(data.data)
                  ? data.data
                  : [];
          } else if (event === 'done') {
            appendProcessEvent(assistant, {
              stage: 'compose',
              title: '组织回答',
              detail: '正文回答已生成完成',
              status: 'done',
              log: '回答流已结束',
            });
            appendProcessEvent(assistant, {
              stage: 'verify',
              title: '校验输出',
              detail: '本轮回答已完成引用、安全和后续建议检查',
              status: 'done',
              log: '处理完成',
            });
            assistant.metrics = {
              ...(assistant.metrics || {}),
              ...(data.usage || {}),
            };
            if (Array.isArray(data.suggestions)) {
              assistant.suggestions = data.suggestions;
            }
            assistant.loading = false;
          } else if (event === 'error') {
            const code = String(data.code || '');
            const message =
              code === 'RAG_EMPTY'
                ? '当前课程资料不足，可切换联网搜索或上传资料。'
                : String(data.message || data.content || '后端生成失败');
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
      void chatStore.loadConversations();
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
          content: record.response,
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
    } catch {
      chatStore.setConversationMessages(threadId, []);
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

  onMounted(async () => {
    await chatStore.loadConversations();
    chatStore.enterDraftSession();
    try {
      courses.value = await fetchAIContextCourses();
    } catch {
      courses.value = [];
    }
    try {
      learningReport.value = await fetchLearningReport(false);
    } catch {
      learningReport.value = null;
    }
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
      @delete="chatStore.deleteConversation"
      @clear-all="clearAllConversations"
      @toggle="sidebarCollapsed = !sidebarCollapsed"
    />

    <section class="tutor-chat-layout__main">
      <div class="chat-main-actions">
        <button type="button" @click="drawerVisible = true">上下文</button>
      </div>
      <div ref="mainScroller" class="chat-main-scroll">
      <ChatMain
        :messages="messages"
        :loading="chatStore.isLoading"
        @retry="retry"
        @send-suggestion="send({ text: $event, files: [] })"
      />
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
      @close="drawerVisible = false"
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
