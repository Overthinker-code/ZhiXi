<script setup lang="ts">
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { Message } from '@arco-design/web-vue';
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
  import ChatComposer from './ChatComposer.vue';
  import ChatMain from './ChatMain.vue';
  import ChatSidebar from './ChatSidebar.vue';
  import ContextDrawer from './ContextDrawer.vue';
  import {
    DEFAULT_RESOURCE_TYPES,
    getTutorAction,
    type TutorAction,
    type TutorPanel,
  } from './tutorActions';

  const chatStore = useChatStore();
  const sidebarCollapsed = ref(false);
  const drawerVisible = ref(false);
  const activePanel = ref<TutorPanel | null>(null);
  const composerRef = ref<InstanceType<typeof ChatComposer> | null>(null);
  const activeAction = ref<TutorAction>(getTutorAction('course_qa'));
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
    useCourseRag: true,
  });
  const resourceRequest = ref<ResourceRequestPayload>({
    types: [...DEFAULT_RESOURCE_TYPES],
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
  const selectedChapter = computed(() =>
    selectedCourse.value?.chapters.find((item) => item.chapterId === courseContext.value.chapterId)
  );
  const chips = computed(() => {
    const out: string[] = [];
    if (selectedCourse.value) out.push(selectedCourse.value.title);
    if (selectedChapter.value) out.push(selectedChapter.value.title);
    if (courseContext.value.useCourseRag) out.push('课程 RAG 开启');
    if (tools.value.webSearch) out.push('联网搜索开启');
    out.push(`深度思考：${reasoningLevel.value === 'deep' ? '深度' : reasoningLevel.value === 'fast' ? '快速' : '均衡'}`);
    return out;
  });
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
    if (action.openPanel) openPanel(action.openPanel);
  }

  function handleAction(actionId: string) {
    patchFromAction(getTutorAction(actionId));
  }

  function openPanel(panel: TutorPanel) {
    activePanel.value = panel;
    if (panel === 'upload') {
      composerRef.value?.openUpload();
    } else {
      drawerVisible.value = true;
    }
  }

  function validateContext(files: File[]) {
    const required = activeAction.value.requiredContext || [];
    if (required.includes('course') && !courseContext.value.courseId) {
      openPanel('course_picker');
      Message.warning('请先选择课程上下文');
      return false;
    }
    if (required.includes('chapter') && !courseContext.value.chapterId) {
      openPanel('course_picker');
      Message.warning('请先选择章节');
      return false;
    }
    if (required.includes('attachment') && !files.length) {
      openPanel('upload');
      Message.warning('请先上传题目、答案或作业截图');
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
    return {
      sessionId: chatStore.currentConversationId || undefined,
      message: text,
      mode: mode.value,
      actionId: activeAction.value.id,
      courseContext: { ...courseContext.value },
      tools: { ...tools.value },
      reasoning: {
        level: reasoningLevel.value,
        showSummary: true,
      },
      attachments,
      resourceRequest: { ...resourceRequest.value },
    };
  }

  async function send({ text, files }: { text: string; files: File[] }) {
    if (!validateContext(files)) return;
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
        artifacts: [],
        resourcePackage: null,
      });
      await nextTick();
      mainScroller.value?.scrollTo({ top: mainScroller.value.scrollHeight, behavior: 'smooth' });
      abortController.value = new AbortController();
      await streamAIChat(
        payload,
        ({ event, data }) => {
          const assistant = latestAssistantMutable();
          if (!assistant) return;
          if (event === 'session_created' && data.sessionId && data.sessionId !== chatStore.currentConversationId) {
            chatStore.currentConversationId = String(data.sessionId);
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
            appendToolEvent(assistant, {
              agent: data.source || 'course_retriever',
              label: data.label || '正在检索资料',
              status: 'running',
            });
          } else if (event === 'retrieval_result') {
            appendToolEvent(assistant, {
              agent: data.source || 'course_retriever',
              label: `已检索 ${Array.isArray(data.items) ? data.items.length : 0} 条资料`,
              status: 'done',
            });
            if (Array.isArray(data.items)) {
              assistant.citations = [...(assistant.citations || []), ...data.items];
            }
          } else if (event === 'reasoning_summary_delta') {
            assistant.reasoning_content = `${assistant.reasoning_content || ''}${data.text || ''}`;
          } else if (event === 'answer_delta') {
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
          } else if (event === 'done') {
            assistant.metrics = data.usage || assistant.metrics || {};
            assistant.loading = false;
          } else if (event === 'error') {
            const code = String(data.code || '');
            const message =
              code === 'RAG_EMPTY'
                ? '当前课程资料不足，可切换联网搜索或上传资料。'
                : String(data.message || data.content || '后端生成失败');
            if (code === 'RESOURCE_GENERATION_FAILED' && assistant.content) {
              appendToolEvent(assistant, {
                agent: 'resource_generator',
                label: message,
                status: 'error',
              });
            } else {
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
          metrics: record.metrics || {},
          toolEvents: [],
          artifacts: [],
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
  <div class="tutor-chat-layout">
    <ChatSidebar
      :conversations="conversations"
      :current-id="chatStore.currentConversationId"
      :collapsed="sidebarCollapsed"
      @new-chat="chatStore.enterDraftSession()"
      @switch="chatStore.switchConversation"
      @delete="chatStore.deleteConversation"
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
          @action="handleAction"
          @retry="retry"
        />
      </div>
      <div class="composer-dock">
        <ChatComposer
          ref="composerRef"
          :loading="chatStore.isLoading"
          :mode="mode"
          :tools="tools"
          :reasoning-level="reasoningLevel"
          :chips="chips"
          :resource-request="resourceRequest"
          @send="send"
          @stop="stop"
          @action="handleAction"
          @toggle-web="tools.webSearch = !tools.webSearch"
          @set-reasoning="reasoningLevel = $event"
          @set-mode="mode = $event"
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
    display: flex;
    height: calc(100vh - 64px);
    overflow: hidden;
    background: #fff;
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
