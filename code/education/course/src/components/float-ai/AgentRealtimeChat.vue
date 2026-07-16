<template>
  <div class="agent-live-chat" @dragover.prevent @drop.prevent="handleDrop">
    <section class="agent-identity">
      <span class="agent-avatar"><icon-robot /></span>
      <div>
        <div class="identity-line">
          <strong>{{ agentLabel }}</strong>
          <span>专用智能体</span>
        </div>
        <p>{{ description }}</p>
      </div>
    </section>

    <div class="scope-strip">
      <span>当前课程</span>
      <strong>{{ courseTitle }}</strong>
      <small v-if="chapterLabel">{{ chapterLabel }}</small>
    </div>

    <p class="sr-only" role="status" aria-live="polite">{{ liveAnnouncement }}</p>
    <main ref="messagePanel" class="message-panel" role="log" aria-live="off">
      <section v-if="!messages.length" class="empty-state">
        <span class="empty-mark"><icon-robot /></span>
        <strong>直接在这里完成任务</strong>
        <p>回答、课程检索和工具执行都会保留在当前页面，不再跳转到 AI 伴学。</p>
        <div class="starter-list">
          <button
            v-for="action in starterActions"
            :key="action"
            type="button"
            @click="send(action)"
          >
            {{ action }}
          </button>
        </div>
      </section>

      <article
        v-for="message in messages"
        :key="message.id"
        :class="['message-row', `is-${message.role}`]"
      >
        <div v-if="message.role === 'assistant'" class="assistant-label">
          <span><icon-robot /></span>
          {{ agentLabel }}
        </div>
        <div class="message-bubble">
          <section v-if="message.role === 'assistant' && message.process.length" class="live-process">
            <button
              type="button"
              class="process-summary"
              :aria-expanded="message.processOpen"
              @click="message.processOpen = !message.processOpen"
            >
              <span :class="['process-dot', { running: message.loading }]" />
              <strong>{{ message.loading ? message.currentStage || '正在执行' : '执行过程' }}</strong>
              <small>{{ message.processOpen ? '收起' : '展开' }}</small>
            </button>
            <ol v-if="message.processOpen">
              <li v-for="(step, index) in message.process" :key="`${message.id}-${index}`">
                <span :class="`is-${step.status}`">
                  {{ step.status === 'running' ? '·' : step.status === 'cancelled' ? '—' : step.status === 'error' ? '!' : '✓' }}
                </span>
                <div>
                  <strong>{{ step.title }}</strong>
                  <p v-if="step.detail">{{ step.detail }}</p>
                </div>
              </li>
            </ol>
          </section>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div
            v-if="message.content"
            class="markdown-body"
            v-html="renderAnswer(message.content, Boolean(message.loading))"
          />
          <div v-else-if="message.loading" class="answer-pending">
            <i /><i /><i />
            <span>正在准备回答</span>
          </div>
          <div v-if="message.interrupted" class="interrupted-note">
            已停止接收本轮回答，停止前的内容已保留。
            <button type="button" @click="continueAnswer">继续完成</button>
          </div>
          <div v-if="message.suggestions.length && !message.loading" class="answer-actions">
            <button
              v-for="item in message.suggestions"
              :key="item"
              type="button"
              @click="send(item)"
            >
              {{ item }}
            </button>
          </div>
        </div>
      </article>
    </main>

    <section v-if="files.length" class="attachment-list">
      <span v-for="(file, index) in files" :key="`${file.name}-${index}`">
        {{ file.name }}
        <button type="button" aria-label="移除附件" @click="files.splice(index, 1)">×</button>
      </span>
    </section>

    <footer class="composer">
      <textarea
        v-model="draft"
        rows="1"
        :aria-label="`向${agentLabel}描述任务`"
        :placeholder="`向${agentLabel}描述你的任务…`"
        @keydown.enter.exact.prevent="send()"
      />
      <div class="composer-actions">
        <label class="attach-button">
          <input
            type="file"
            aria-label="添加任务附件"
            multiple
            accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md,image/*"
            @change="handleFileChange"
          />
          <span aria-hidden="true">＋ 附件</span>
        </label>
        <span class="context-status" role="status" aria-live="polite">
          {{ stopping ? '正在停止当前任务' : '课程上下文已绑定' }}
        </span>
        <button v-if="loading" type="button" class="stop-button" :disabled="stopping" @click="stop">
          <span /> {{ stopping ? '正在停止' : '停止' }}
        </button>
        <button
          v-else
          type="button"
          class="send-button"
          :disabled="!canSend"
          @click="send()"
        >
          发送
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
  import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { IconRobot } from '@arco-design/web-vue/es/icon';
  import {
    streamAIChat,
    uploadAIAttachment,
    type ChatAttachmentPayload,
    type CourseAgentContractSummary,
  } from '@/api/ai-chat';
  import { createChatThread } from '@/api/rag';
  import { renderMarkdown, stripMarkdownCodeToolbar } from '@/utils/markdown';
  import sanitizeAssistantText from '@/components/chat/sanitizeAssistantText';
  import {
    AGENT_CONTINUE_PROMPT,
    agentProcessStatusFromPhase,
    isAgentStreamTokenCurrent,
    markAgentMessageInterrupted,
    type AgentStreamToken,
    type AgentProcessStep,
    type AgentWindowMessage,
  } from './agentRealtimeState';

  const props = defineProps<{
    sessionToken: string;
    agent: CourseAgentContractSummary;
    courseId: string;
    courseTitle: string;
    chapterId?: string;
    chapterLabel?: string;
    knowledgePointIds?: string[];
    initialPrompt?: string;
  }>();

  const draft = ref(props.initialPrompt || '');
  const files = ref<File[]>([]);
  const messages = ref<AgentWindowMessage[]>([]);
  const loading = ref(false);
  const messagePanel = ref<HTMLElement | null>(null);
  const sessionId = ref('');
  const lastUserMessage = ref('');
  const stopping = ref(false);
  const liveAnnouncement = ref('');
  let activeAssistant: AgentWindowMessage | null = null;
  let controller: AbortController | null = null;
  let activeRequestId = 0;

  const agentLabel = computed(() => props.agent.label || '课程智能体');
  const description = computed(() => props.agent.description || '结合当前课程完成学习任务。');
  const starterActions = computed(() => (props.agent.starterActions || []).slice(0, 4));
  const canSend = computed(() => !loading.value && Boolean(draft.value.trim() || files.value.length));

  function renderAnswer(content: string, streaming: boolean) {
    return stripMarkdownCodeToolbar(renderMarkdown(content, { streaming }));
  }

  async function scrollToBottom() {
    await nextTick();
    const panel = messagePanel.value;
    if (panel) panel.scrollTop = panel.scrollHeight;
  }

  function beginRequest(): AgentStreamToken {
    activeRequestId += 1;
    return { sessionToken: props.sessionToken, requestId: activeRequestId };
  }

  function isCurrentRequest(token: AgentStreamToken) {
    return isAgentStreamTokenCurrent(props.sessionToken, activeRequestId, token);
  }

  async function ensureSession(token: AgentStreamToken) {
    if (sessionId.value) return sessionId.value;
    const thread = await createChatThread(`${agentLabel.value} · ${props.courseTitle}`);
    if (!isCurrentRequest(token)) return '';
    sessionId.value = String(thread.thread_id);
    return sessionId.value;
  }

  function upsertProcess(message: AgentWindowMessage, step: AgentProcessStep) {
    const index = message.process.findIndex((item) => item.key === step.key);
    if (index >= 0) message.process[index] = { ...message.process[index], ...step };
    else message.process.push(step);
    message.currentStage = step.title;
    if (liveAnnouncement.value !== step.title) liveAnnouncement.value = step.title;
  }

  const phaseTitleMap: Record<string, string> = {
    understand: '理解任务',
    understand_problem: '理解任务',
    plan: '选择能力',
    select_capability: '选择能力',
    prepare_context: '绑定课程上下文',
    retrieve_knowledge: '检索课程资料',
    compose: '生成内容',
    generate_answer: '生成内容',
    verify_output: '校验输出',
    update_learning_profile: '更新学习记录',
    suggest_next_step: '整理下一步',
  };

  function phaseTitle(key: string, data: Record<string, any>, fallback: string) {
    return String(data.title || data.label || phaseTitleMap[key] || fallback);
  }

  function eventSuggestions(data: Record<string, any>) {
    const raw = data.items || data.suggestions || data.data || [];
    return Array.isArray(raw)
      ? raw.map((item) => String(typeof item === 'string' ? item : item?.label || item?.title || '')).filter(Boolean).slice(0, 4)
      : [];
  }

  function handleEvent(message: AgentWindowMessage, event: string, data: Record<string, any>) {
    if (event === 'answer_delta') {
      message.content += sanitizeAssistantText(String(data.text || ''), { preserveEdges: true });
    } else if (event === 'phase_started' || event === 'phase_updated' || event === 'phase_delta') {
      const key = String(data.phaseId || data.id || data.stage || 'thinking');
      upsertProcess(message, {
        key,
        title: phaseTitle(key, data, String(data.stage || '分析任务')),
        detail: String(data.summary || data.detail || data.text || ''),
        status: 'running',
      });
    } else if (event === 'phase_finished') {
      const key = String(data.phaseId || data.id || data.stage || 'thinking');
      upsertProcess(message, {
        key,
        title: phaseTitle(key, data, String(data.stage || '完成阶段')),
        detail: String(data.summary || data.detail || ''),
        status: agentProcessStatusFromPhase(data.status),
      });
    } else if (event === 'tool_started') {
      const key = `tool-${String(data.tool || data.name || data.id || 'tool')}`;
      upsertProcess(message, {
        key,
        title: String(data.label || data.title || '调用课程工具'),
        detail: String(data.summary || data.detail || ''),
        status: 'running',
      });
    } else if (event === 'tool_result') {
      const key = `tool-${String(data.tool || data.name || data.id || 'tool')}`;
      upsertProcess(message, {
        key,
        title: String(data.label || data.title || '课程工具已完成'),
        detail: String(data.summary || data.detail || (Array.isArray(data.items) ? `返回 ${data.items.length} 条结果` : '')),
        status: 'done',
      });
    } else if (event === 'agent_contract') {
      upsertProcess(message, {
        key: 'contract',
        title: `${agentLabel.value} 已确认任务`,
        detail: '已根据当前课程和任务要求准备处理',
        status: 'done',
      });
    } else if (event === 'artifact_finished') {
      upsertProcess(message, {
        key: 'artifact',
        title: '学习资源已生成',
        detail: String(data.label || '可以预览或下载完整内容'),
        status: 'done',
      });
    } else if (event === 'suggestions') {
      message.suggestions = eventSuggestions(data);
    } else if (event === 'run_finished' || event === 'done') {
      message.process.forEach((step) => {
        if (step.status === 'running') step.status = 'done';
      });
      message.currentStage = String(data.summary || '本轮任务已完成');
      liveAnnouncement.value = message.currentStage;
      message.suggestions = eventSuggestions(data).length ? eventSuggestions(data) : message.suggestions;
    } else if (event === 'error') {
      upsertProcess(message, {
        key: 'error',
        title: '执行失败',
        detail: String(data.message || data.content || '请稍后重试'),
        status: 'error',
      });
      message.content ||= String(data.message || data.content || '执行失败，请稍后重试。');
    }
    void scrollToBottom();
  }

  async function uploadFiles(
    threadId: string,
    signal: AbortSignal
  ): Promise<ChatAttachmentPayload[]> {
    return Promise.all(
      files.value.map(async (file) => {
        const response = await uploadAIAttachment(
          file,
          threadId,
          {
            courseId: props.courseId,
            chapterId: props.chapterId,
            knowledgePointIds: props.knowledgePointIds || [],
          },
          signal
        );
        return { fileId: String(response.fileId), type: response.type, name: response.name || file.name };
      })
    );
  }

  async function send(text = '') {
    const content = String(text || draft.value).trim();
    if (loading.value || (!content && !files.value.length)) return;
    lastUserMessage.value = content || '请处理我上传的材料。';
    const assistant: AgentWindowMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      loading: true,
      interrupted: false,
      currentStage: '正在启动',
      processOpen: true,
      process: [],
      suggestions: [],
    };
    messages.value.push({
      id: `user-${Date.now()}`,
      role: 'user',
      content: lastUserMessage.value,
      loading: false,
      interrupted: false,
      currentStage: '',
      processOpen: false,
      process: [],
      suggestions: [],
    });
    messages.value.push(assistant);
    activeAssistant = assistant;
    stopping.value = false;
    draft.value = '';
    loading.value = true;
    const requestToken = beginRequest();
    const requestController = new AbortController();
    controller = requestController;
    void scrollToBottom();
    try {
      const threadId = await ensureSession(requestToken);
      if (!threadId || !isCurrentRequest(requestToken)) return;
      const attachments = files.value.length
        ? await uploadFiles(threadId, requestController.signal)
        : [];
      if (!isCurrentRequest(requestToken)) return;
      files.value = [];
      await streamAIChat(
        {
          sessionId: threadId,
          message: lastUserMessage.value,
          mode: props.agent.mode || 'tutor',
          agentKey: props.agent.key,
          courseContext: {
            courseId: props.courseId,
            chapterId: props.chapterId,
            knowledgePointIds: props.knowledgePointIds || [],
            useCourseRag: true,
          },
          tools: {
            webSearch: props.agent.capabilities?.includes('web_search') || false,
            courseRag: true,
            deepResearch: props.agent.mode === 'deep_research',
            homeworkReview: props.agent.mode === 'homework_review',
            resourceGeneration: props.agent.mode === 'resource_generation',
            citationRequired: true,
          },
          reasoning: { level: 'balanced', showSummary: true, showProcess: true },
          attachments,
          resourceRequest: {
            types: ['lecture_note', 'mind_map', 'quiz'],
            difficulty: 'normal',
            target: content,
          },
        },
        ({ event, data }) => {
          if (isCurrentRequest(requestToken)) handleEvent(assistant, event, data);
        },
        requestController.signal
      );
    } catch (error) {
      if (!isCurrentRequest(requestToken)) return;
      if (error instanceof Error && error.name === 'AbortError') {
        markAgentMessageInterrupted(assistant);
      } else {
        const detail = error instanceof Error ? error.message : '请稍后重试';
        assistant.content ||= `执行失败：${detail}`;
        Message.error(detail);
      }
    } finally {
      if (!isCurrentRequest(requestToken)) return;
      assistant.loading = false;
      loading.value = false;
      activeAssistant = null;
      stopping.value = false;
      if (controller === requestController) controller = null;
      void scrollToBottom();
    }
  }

  function stop() {
    if (!controller || stopping.value) return;
    stopping.value = true;
    if (activeAssistant) {
      markAgentMessageInterrupted(activeAssistant);
      upsertProcess(activeAssistant, {
        key: 'cancelled',
        title: '已停止接收本轮回答',
        detail: '已中断当前页面的流式显示，停止前的内容仍保留在窗口中',
        status: 'cancelled',
      });
    }
    const activeController = controller;
    activeRequestId += 1;
    controller = null;
    activeAssistant = null;
    loading.value = false;
    stopping.value = false;
    activeController.abort();
  }

  function discardActiveStream() {
    activeRequestId += 1;
    const activeController = controller;
    controller = null;
    activeAssistant = null;
    loading.value = false;
    stopping.value = false;
    activeController?.abort();
  }

  function continueAnswer() {
    send(AGENT_CONTINUE_PROMPT);
  }

  function addFiles(incoming: File[]) {
    const next = incoming.filter((file) => file.size <= 20 * 1024 * 1024).slice(0, 5 - files.value.length);
    if (next.length !== incoming.length) Message.warning('单个附件不超过 20MB，每轮最多 5 个');
    files.value.push(...next);
  }

  function handleFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    addFiles(Array.from(input.files || []));
    input.value = '';
  }

  function handleDrop(event: DragEvent) {
    addFiles(Array.from(event.dataTransfer?.files || []));
  }

  watch(
    () => [props.sessionToken, props.agent.key, props.courseId],
    () => {
      discardActiveStream();
      messages.value = [];
      files.value = [];
      sessionId.value = '';
      draft.value = props.initialPrompt || '';
    }
  );

  onUnmounted(discardActiveStream);

  defineExpose({ handleDrop });
</script>

<style scoped lang="less">
  .agent-live-chat {
    height: 100%;
    min-height: 0;
    display: flex;
    flex-direction: column;
    color: #172033;
    background:
      radial-gradient(circle at 12% 0%, rgba(55, 119, 246, 0.1), transparent 27%),
      #f8fbff;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  .agent-identity {
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr);
    gap: 11px;
    align-items: center;
    padding: 14px 16px 10px;

    p {
      display: -webkit-box;
      margin: 4px 0 0;
      overflow: hidden;
      color: #6b768a;
      font-size: 12px;
      line-height: 1.45;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }
  }

  .agent-avatar,
  .empty-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 14px;
    color: #fff;
    background: linear-gradient(145deg, #3777f6, #5258dc);
    box-shadow: 0 9px 20px rgba(55, 119, 246, 0.2);
  }

  .agent-avatar {
    width: 42px;
    height: 42px;
    font-size: 20px;
  }

  .identity-line {
    display: flex;
    align-items: center;
    gap: 8px;

    strong { font-size: 15px; }
    span {
      padding: 3px 7px;
      border-radius: 999px;
      color: #2f68df;
      background: #eaf2ff;
      font-size: 10px;
      font-weight: 800;
    }
  }

  .scope-strip {
    display: flex;
    align-items: center;
    gap: 7px;
    margin: 0 14px 10px;
    padding: 8px 10px;
    border: 1px solid #deebfb;
    border-radius: 11px;
    color: #61708a;
    background: rgba(255, 255, 255, 0.82);
    font-size: 11px;

    strong { color: #284a7e; }
    small { margin-left: auto; color: #8390a5; }
  }

  .message-panel {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 10px 14px 18px;
    scroll-behavior: smooth;
  }

  .empty-state {
    min-height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 24px 12px;
    text-align: center;

    > strong { margin-top: 13px; font-size: 17px; }
    > p { max-width: 330px; margin: 7px 0 16px; color: #748096; font-size: 12px; line-height: 1.6; }
  }

  .empty-mark { width: 50px; height: 50px; font-size: 23px; }

  .starter-list {
    width: 100%;
    display: grid;
    gap: 8px;

    button {
      padding: 10px 12px;
      border: 1px solid #dce7f6;
      border-radius: 12px;
      color: #315181;
      background: #fff;
      font-size: 12px;
      text-align: left;
      cursor: pointer;
      &:hover { border-color: #a9c7fb; background: #f3f8ff; }
    }
  }

  .message-row { margin-bottom: 16px; }
  .message-row.is-user { display: flex; justify-content: flex-end; }
  .message-row.is-user .message-bubble { max-width: 84%; color: #18335f; background: #eaf2ff; }

  .assistant-label {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
    color: #56647b;
    font-size: 11px;
    font-weight: 700;
    span { color: #3777f6; }
  }

  .message-bubble {
    padding: 11px 13px;
    border: 1px solid #e1e8f2;
    border-radius: 15px;
    background: #fff;
    box-shadow: 0 7px 19px rgba(37, 51, 91, 0.045);
  }

  .live-process {
    margin-bottom: 10px;
    border: 1px solid #e4eaf3;
    border-radius: 11px;
    background: #f8fafc;
  }

  .process-summary {
    width: 100%;
    min-height: 38px;
    display: grid;
    grid-template-columns: 8px minmax(0, 1fr) auto;
    gap: 8px;
    align-items: center;
    padding: 7px 10px;
    border: 0;
    color: #4f5d72;
    background: transparent;
    text-align: left;
    cursor: pointer;
    strong { overflow: hidden; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
    small { color: #8c97a8; font-size: 10px; }
  }

  .process-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #49a878;
    &.running { background: #3777f6; animation: pulse 1.1s ease-in-out infinite; }
  }

  .live-process ol { margin: 0; padding: 0 10px 8px; list-style: none; }
  .live-process li {
    display: grid;
    grid-template-columns: 18px minmax(0, 1fr);
    gap: 7px;
    padding: 6px 0;
    border-top: 1px solid #edf1f6;
    > span { color: #49a878; font-size: 11px; }
    > span.is-running { color: #3777f6; }
    > span.is-cancelled { color: #8b96a8; }
    > span.is-error { color: #d14c4c; }
    strong { display: block; color: #435168; font-size: 11px; }
    p { margin: 2px 0 0; color: #7b8799; font-size: 10px; line-height: 1.4; }
  }

  .markdown-body {
    color: #26354c;
    font-size: 13px;
    line-height: 1.72;
    :deep(p:first-child) { margin-top: 0; }
    :deep(p:last-child) { margin-bottom: 0; }
    :deep(pre) { max-width: 100%; overflow: auto; border-radius: 10px; }
  }

  .answer-pending { display: flex; align-items: center; gap: 4px; color: #78859a; font-size: 12px; }
  .answer-pending i { width: 5px; height: 5px; border-radius: 50%; background: #6a94ea; animation: blink 1s infinite; }
  .answer-pending i:nth-child(2) { animation-delay: .15s; }
  .answer-pending i:nth-child(3) { animation-delay: .3s; margin-right: 5px; }

  .interrupted-note {
    margin-top: 9px;
    padding-top: 9px;
    border-top: 1px solid #edf1f6;
    color: #7b8799;
    font-size: 11px;
    button { margin-left: 5px; border: 0; color: #2f68df; background: transparent; font-weight: 800; cursor: pointer; }
  }

  .answer-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
  .answer-actions button {
    padding: 5px 8px;
    border: 1px solid #d8e4f4;
    border-radius: 8px;
    color: #3a5f91;
    background: #f8fbff;
    font-size: 10px;
    cursor: pointer;
  }

  .attachment-list { display: flex; gap: 6px; overflow-x: auto; padding: 7px 14px 0; }
  .attachment-list span {
    max-width: 180px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 8px;
    border: 1px solid #dce6f3;
    border-radius: 9px;
    overflow: hidden;
    color: #53637b;
    background: #fff;
    font-size: 10px;
    text-overflow: ellipsis;
    white-space: nowrap;
    button { border: 0; color: #8995a6; background: transparent; cursor: pointer; }
  }

  .composer {
    margin: 10px 12px 12px;
    padding: 10px;
    border: 1px solid #dfe6f1;
    border-radius: 15px;
    background: #fff;
    box-shadow: 0 12px 28px rgba(39, 54, 88, 0.09);
    transition: border-color 160ms ease, box-shadow 160ms ease;

    &:focus-within {
      border-color: #94a3b8;
      box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.07), 0 12px 28px rgba(39, 54, 88, 0.09);
    }

    textarea {
      width: 100%;
      min-height: 38px;
      max-height: 108px;
      resize: vertical;
      border: 0;
      outline: 0 !important;
      box-shadow: none !important;
      color: #24324a;
      background: transparent;
      font: inherit;
      font-size: 13px;
    }
  }

  .composer-actions { display: flex; align-items: center; gap: 8px; }
  .attach-button { position: relative; }
  .attach-button input {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    margin: 0;
    opacity: 0;
    outline: none !important;
    cursor: pointer;
  }
  .attach-button:focus-within span {
    outline: 2px solid rgba(51, 65, 85, 0.5);
    outline-offset: 2px;
  }
  .attach-button span,
  .send-button,
  .stop-button {
    min-height: 30px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0 10px;
    border-radius: 9px;
    font-size: 11px;
    font-weight: 800;
    cursor: pointer;
  }
  .attach-button span { border: 1px solid #dce5f1; color: #53637b; background: #f8fafc; }
  .context-status { flex: 1; color: #8792a4; font-size: 10px; }
  .send-button { border: 0; color: #fff; background: #3777f6; }
  .send-button:disabled { opacity: .45; cursor: not-allowed; }
  .stop-button { gap: 6px; border: 1px solid #f0caca; color: #b53d3d; background: #fff7f7; }
  .stop-button span { width: 7px; height: 7px; border-radius: 2px; background: currentColor; }

  @keyframes pulse { 50% { opacity: .35; transform: scale(.82); } }
  @keyframes blink { 50% { opacity: .25; transform: translateY(-2px); } }

  @media (max-width: 520px) {
    .scope-strip small,
    .context-status { display: none; }
    .composer { margin: 8px; }
  }

  @media (prefers-reduced-motion: reduce) {
    .process-dot.running,
    .answer-pending i { animation: none; }
  }
</style>
