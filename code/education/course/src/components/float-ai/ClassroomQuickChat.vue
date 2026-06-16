<template>
  <div
    class="classroom-ai"
    :class="{ 'is-dragging': dragActive }"
  >
    <div v-if="dragActive" class="panel-drag-layer">
      释放文件，添加到小智对话
    </div>
    <header class="mobile-topbar">
      <button type="button" class="back-btn" aria-label="返回">
        <icon-left />
      </button>
      <h1>课堂 AI 助理</h1>
      <span class="topbar-spacer" />
    </header>

    <div class="course-card">
      <span class="course-badge">当前课程</span>
      <strong>{{ currentCourse?.title || '课程学习' }}</strong>
      <span class="course-meta">{{ currentLessonLabel }}</span>
    </div>

    <div ref="messagePanel" class="message-panel" @scroll="handlePanelScroll">
      <div class="assistant-card">
        <div class="xiaozhi-head">
          <div class="xiaozhi-avatar">智</div>
          <div>
            <strong>小智</strong>
            <span>课堂 AI 助教</span>
          </div>
        </div>
        <p class="intro-lead">
          Hi，我是小智！在{{ currentCourse?.shortTitle || '当前课程' }}中，我可以帮你：
        </p>
        <ul class="feature-list">
          <li><icon-book /> 讲解知识点与考试要点</li>
          <li><icon-edit /> 批改练习与测验作答</li>
          <li><icon-image /> 解析图片题目与 ER 图</li>
          <li><icon-bulb /> 生成复习提纲与易错提醒</li>
        </ul>
      </div>
      <div v-for="item in messages" :key="item.id" class="bubble-row">
        <div :class="item.role === 'user' ? 'bubble user' : 'bubble assistant'">
          <template v-if="item.role === 'assistant'">
            <div
              v-if="item.reasoning || item.loading"
              class="reasoning-toggle"
              @click="item.showReasoning = !item.showReasoning"
            >
              <span>{{ item.loading ? '正在思考中…' : '深度思考' }}</span>
              <span class="arrow">{{ item.showReasoning ? '▴' : '▾' }}</span>
            </div>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div
              v-if="item.showReasoning && (item.reasoning || item.loading)"
              class="reasoning-content markdown-body"
              v-html="
                renderSafeMarkdown(
                  displayAssistantReasoning(item),
                  Boolean(item.loading)
                )
              "
            />
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div
              class="markdown-body"
              v-html="
                renderSafeMarkdown(
                  displayAssistantContent(item),
                  Boolean(item.loading)
                )
              "
            />
          </template>
          <template v-else>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div class="markdown-body" v-html="renderSafeMarkdown(item.content)" />
          </template>
        </div>
      </div>
    </div>
    <div class="suggestions">
      <button
        v-for="s in defaultChips"
        :key="s"
        class="suggestion-pill"
        @click="handleSuggestion(s)"
      >
        {{ s }}
      </button>
      <button
        v-for="s in suggestions"
        :key="`dyn-${s}`"
        class="suggestion-pill suggestion-pill--dynamic"
        @click="handleSuggestion(s)"
      >
        {{ s }}
      </button>
    </div>
    <div
      class="input-wrap"
    >
      <input
        ref="fileInputRef"
        hidden
        type="file"
        accept=".pdf,.doc,.docx,.txt,.md,.markdown,.ppt,.pptx"
        @change="handleNativeFileChange"
      />
      <input
        ref="imageInputRef"
        hidden
        type="file"
        accept="image/*"
        multiple
        @change="handleNativeFileChange"
      />
      <div v-if="fileList.length" class="quick-file-row">
        <div
          v-for="file in fileList"
          :key="file.url"
          :class="['quick-file-card', `is-${file.type}`]"
        >
          <img v-if="file.type === 'image'" :src="file.url" :alt="file.name" />
          <span v-else class="file-icon">文</span>
          <span class="file-name">{{ file.name }}</span>
          <span class="file-status">{{
            file.type === 'image' ? '发送后联合识别' : '发送后挂载'
          }}</span>
          <button type="button" @click="handleFileRemove(file)">×</button>
        </div>
      </div>
      <a-textarea
        v-model="inputValue"
        :max-length="400"
        :auto-size="{ minRows: 1, maxRows: 5 }"
        placeholder="你可以向我提问，也可以拖入图片或文档"
        @keydown.enter.exact.prevent="handleSend"
      />
      <div class="actions">
        <div class="quick-add-wrap">
          <button class="quick-add-btn" type="button" @click="menuOpen = !menuOpen">
            +
          </button>
          <div v-if="menuOpen" class="quick-add-menu">
            <button type="button" @click="triggerFileInput('file')">上传文件</button>
            <button type="button" @click="triggerFileInput('image')">上传图片</button>
          </div>
        </div>
        <button
          :class="['quick-toggle', { active: webSearchEnabled }]"
          type="button"
          @click="webSearchEnabled = !webSearchEnabled"
        >
          联网搜索
        </button>
        <button
          :class="['quick-toggle', { active: deepThinkEnabled }]"
          type="button"
          @click="deepThinkEnabled = !deepThinkEnabled"
        >
          深度思考
        </button>
        <div class="quick-mode">
          <button
            :class="{ active: activeMode === 'chat' }"
            type="button"
            @click="activeMode = 'chat'"
          >
            普通
          </button>
          <button
            :class="{ active: activeMode === 'exercise_grading' }"
            type="button"
            @click="activeMode = 'exercise_grading'"
          >
            批改
          </button>
        </div>
        <a-button @click="handleClear">清空</a-button>
        <a-button v-if="loading" status="danger" @click="handleStop"
          >暂停回答</a-button
        >
        <a-button
          type="primary"
          :disabled="!canSend"
          :loading="loading"
          @click="handleSend"
        >
          发送
        </a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { createAssistantChatStream, uploadThreadFile } from '@/api/rag';
  import { Message } from '@arco-design/web-vue';
  import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
  import { useRoute } from 'vue-router';
  import { renderMarkdown, stripMarkdownCodeToolbar } from '@/utils/markdown';
  import humanizeAgentReasoning from '@/utils/humanizeAgentReasoning';
  import { appendThoughtToReasoning } from '@/utils/thoughtToNarrative';
  import { shouldAppendThoughtToReasoning } from '@/utils/streamReasoning';
  import { normalizeSuggestionList } from '@/utils/llmDisplay';
  import { getClassroomCourse } from '@/data/classroomCourses';

  interface ChatItem {
    id: number;
    role: 'user' | 'assistant';
    content: string;
    reasoning: string;
    loading?: boolean;
    showReasoning?: boolean;
  }

  const route = useRoute();
  const currentCourse = computed(() =>
    getClassroomCourse(
      typeof route.params.courseId === 'string'
        ? route.params.courseId
        : typeof route.query.courseId === 'string'
          ? route.query.courseId
          : null
    )
  );
  const currentLesson = computed(() => {
    const lessons =
      currentCourse.value?.chapters.flatMap((chapter) => chapter.lessons) || [];
    const lessonId =
      typeof route.query.lessonId === 'string' ? route.query.lessonId : '';
    return (
      lessons.find((lesson) => lesson.id === lessonId) ||
      lessons.find((lesson) => lesson.status === 'pending') ||
      lessons[0]
    );
  });
  const currentLessonLabel = computed(
    () => currentLesson.value?.label || '课程知识答疑与练习辅导'
  );
  const defaultSystemPrompt = computed(() => {
    const title = currentCourse.value?.title || '当前课程';
    const lesson = currentLesson.value?.label || '当前学习内容';
    return `你是《${title}》的课堂助教，当前课节为“${lesson}”。请以教师口吻清晰讲解，优先使用本课程知识与资料，不得混入其他课程内容。`;
  });
  const defaultChips = computed(() => {
    const points = currentCourse.value?.concepts.flatMap((item) => item.points) || [];
    return [
      points[0] ? `解释${points[0]}` : '讲解当前知识点',
      '讲解这道题',
      '总结本章要点',
      '复习薄弱知识点',
    ];
  });

  const inputValue = ref('');
  const loading = ref(false);
  const messages = ref<ChatItem[]>([]);
  const fileList = ref<any[]>([]);
  const suggestions = ref<string[]>([]);
  const messagePanel = ref<HTMLElement | null>(null);
  const autoStickToBottom = ref(true);
  const localThreadId = ref(
    `course-${currentCourse.value?.id || 'general'}-${Date.now()}`
  );
  const menuOpen = ref(false);
  const dragActive = ref(false);
  const webSearchEnabled = ref(false);
  const deepThinkEnabled = ref(false);
  const activeMode = ref<'chat' | 'exercise_grading'>('chat');
  const fileInputRef = ref<HTMLInputElement | null>(null);
  const imageInputRef = ref<HTMLInputElement | null>(null);
  let abortController: AbortController | null = null;
  const streamAssistId = ref<number | null>(null);
  const streamContentLen = ref(0);
  const streamReasonLen = ref(0);
  let streamChaseTimer: ReturnType<typeof setInterval> | null = null;

  watch(
    () => currentCourse.value?.id || '',
    (nextId, previousId) => {
      if (!previousId || nextId === previousId) return;
      abortController?.abort();
      loading.value = false;
      messages.value = [];
      suggestions.value = [];
      fileList.value.forEach((file) => URL.revokeObjectURL(file.url));
      fileList.value = [];
      localThreadId.value = `course-${nextId || 'general'}-${Date.now()}`;
    }
  );

  const renderSafeMarkdown = (content: string, streaming = false) =>
    stripMarkdownCodeToolbar(renderMarkdown(content || '', { streaming }));
  const canSend = computed(
    () => (inputValue.value.trim() || fileList.value.length > 0) && !loading.value
  );

  const isImageFile = (file: File) => file.type?.startsWith('image/');
  const isDocFile = (file: File) =>
    /\.(pdf|docx?|txt|md|markdown|pptx?)$/i.test(file.name || '');
  const fileToDataUrl = (file: File) =>
    new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(reader.error || new Error('图片读取失败'));
      reader.readAsDataURL(file);
    });

  const addFiles = (files: FileList | File[]) => {
    let imageCount = fileList.value.filter((item) => item.type === 'image').length;
    let docCount = fileList.value.filter((item) => item.type !== 'image').length;
    Array.from(files || []).forEach((file) => {
      if (isImageFile(file)) {
        if (imageCount >= 3) {
          Message.warning('图片最多同时上传 3 张');
          return;
        }
        imageCount += 1;
      } else if (isDocFile(file)) {
        if (docCount >= 1) {
          Message.warning('小智本轮先挂载 1 个主文档');
          return;
        }
        docCount += 1;
      } else {
        Message.warning(`暂不支持 ${file.name} 的文件类型`);
        return;
      }
      fileList.value.push({
        name: file.name,
        url: URL.createObjectURL(file),
        type: isImageFile(file) ? 'image' : 'file',
        size: file.size,
        raw: file,
      });
    });
  };

  const triggerFileInput = (kind: 'file' | 'image') => {
    menuOpen.value = false;
    if (kind === 'image') imageInputRef.value?.click();
    else fileInputRef.value?.click();
  };

  const handleNativeFileChange = (event: Event) => {
    const target = event.target as HTMLInputElement;
    addFiles(target.files || []);
    target.value = '';
  };

  const handleDrop = (event: DragEvent) => {
    event.preventDefault();
    dragActive.value = false;
    addFiles(event.dataTransfer?.files || []);
  };

  const handleDragOver = (event: DragEvent) => {
    event.preventDefault();
    dragActive.value = true;
  };

  const handleDragLeave = (event: DragEvent) => {
    const current = event.currentTarget as HTMLElement;
    if (!current.contains(event.relatedTarget as Node | null)) {
      dragActive.value = false;
    }
  };

  defineExpose({
    handleDrop,
    handleDragOver,
    handleDragLeave,
  });

  const handleFileRemove = (file: any) => {
    const index = fileList.value.findIndex((item) => item.url === file.url);
    if (index >= 0) {
      URL.revokeObjectURL(fileList.value[index].url);
      fileList.value.splice(index, 1);
    }
  };

  const sanitizeStreamingContent = (raw: string) =>
    (raw || '')
      .replace(/<think>[\s\S]*?<\/think>/gi, '')
      .replace(/<analysis>[\s\S]*?<\/analysis>/gi, '')
      .replace(/<\/?final>/gi, '')
      .trim();

  const displayAssistantContent = (item: ChatItem) => {
    if (item.role !== 'assistant') return item.content;
    if (item.loading && item.id === streamAssistId.value) {
      return (item.content || '').slice(0, streamContentLen.value);
    }
    return item.content;
  };

  const displayAssistantReasoning = (item: ChatItem) => {
    if (item.role !== 'assistant') return item.reasoning || '';
    if (item.loading && item.id === streamAssistId.value) {
      return (item.reasoning || '').slice(0, streamReasonLen.value);
    }
    return item.reasoning || '';
  };

  const getLastAssistant = () => {
    const last = messages.value[messages.value.length - 1];
    return last && last.role === 'assistant' ? last : null;
  };

  watch(
    () => {
      const last = messages.value[messages.value.length - 1];
      const isAssist =
        last && last.role === 'assistant' && last.loading === true;
      return [
        loading.value,
        isAssist ? last.id : 0,
        isAssist ? last.content : '',
        isAssist ? last.reasoning : '',
      ] as const;
    },
    () => {
      const last = messages.value[messages.value.length - 1];
      const active =
        last &&
        last.role === 'assistant' &&
        last.loading &&
        last.id === streamAssistId.value;
      if (!loading.value || !active) {
        const m = getLastAssistant();
        streamContentLen.value = (m?.content || '').length;
        streamReasonLen.value = (m?.reasoning || '').length;
        if (streamChaseTimer) {
          clearInterval(streamChaseTimer);
          streamChaseTimer = null;
        }
        return;
      }
      if (streamContentLen.value > (last.content || '').length) {
        streamContentLen.value = 0;
      }
      if (streamReasonLen.value > (last.reasoning || '').length) {
        streamReasonLen.value = 0;
      }
      if (!streamChaseTimer) {
        streamChaseTimer = setInterval(() => {
          const m = messages.value[messages.value.length - 1];
          if (!m || m.role !== 'assistant' || !m.loading) return;
          const tc = (m.content || '').length;
          if (streamContentLen.value < tc) {
            const behind = tc - streamContentLen.value;
            const step = Math.max(1, Math.min(28, Math.ceil(behind / 4)));
            streamContentLen.value = Math.min(tc, streamContentLen.value + step);
          }
          const tr = (m.reasoning || '').length;
          if (streamReasonLen.value < tr) {
            const behind = tr - streamReasonLen.value;
            const step = Math.max(1, Math.min(36, Math.ceil(behind / 4)));
            streamReasonLen.value = Math.min(tr, streamReasonLen.value + step);
          }
        }, 28);
      }
    },
    { immediate: true }
  );

  onUnmounted(() => {
    if (streamChaseTimer) {
      clearInterval(streamChaseTimer);
      streamChaseTimer = null;
    }
  });

  const scrollToBottom = async (force = false) => {
    if (!force && !autoStickToBottom.value) return;
    await nextTick();
    if (!messagePanel.value) return;
    messagePanel.value.scrollTop = messagePanel.value.scrollHeight;
  };
  const handlePanelScroll = () => {
    const el = messagePanel.value;
    if (!el) return;
    const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    autoStickToBottom.value = distanceToBottom < 80;
  };

  const addAssistantPlaceholder = () => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    streamAssistId.value = id;
    streamContentLen.value = 0;
    streamReasonLen.value = 0;
    messages.value.push({
      id,
      role: 'assistant',
      content: '',
      reasoning: '',
      loading: true,
      showReasoning: true,
    });
  };

  const buildModePrompt = (hasImages: boolean, fileName = '') => {
    const prompts: string[] = [];
    if (webSearchEnabled.value) {
      prompts.push(
        '已开启联网搜索：如需外部事实或时效校验，请使用联网搜索，并在回答中说明来源类型和可信度。'
      );
    }
    if (deepThinkEnabled.value) {
      prompts.push('已开启深度思考：先拆解问题，再给出简洁、可执行的学习建议。');
    }
    if (activeMode.value === 'exercise_grading') {
      prompts.push(
        '已开启批改模式：请像老师一样先肯定有效部分，再指出错误证据、订正步骤和后续练习。'
      );
    }
    if (hasImages) {
      prompts.push('学生上传了图片，请结合图片内容和文本一起回答；不确定的图片细节要明确说明。');
    }
    if (fileName) {
      prompts.push(`学生挂载了参考文件《${fileName}》，回答时优先结合该文件。`);
    }
    return [defaultSystemPrompt.value, ...prompts].join('\n');
  };

  const buildUserText = (text: string, hasImages: boolean) => {
    if (activeMode.value === 'exercise_grading') {
      return `【练习批改模式】\n请批改下面题目或答案，给出评分/等级、得分点、错因、订正建议和掌握度反馈。\n\n${text}`;
    }
    if (hasImages) {
      return `【图像与文本联合提问】\n学生上传了图片，并补充以下文字。请结合图片识别内容、文字信息和课程知识进行回答。\n\n${text || '请解析图片并给出学习建议。'}`;
    }
    return text;
  };

  const handleSend = async () => {
    const text = inputValue.value.trim();
    if (!canSend.value) return;
    const sendingFiles = [...fileList.value];
    const imageFiles = sendingFiles.filter((item) => item.type === 'image' && item.raw);
    const docFile = sendingFiles.find((item) => item.type !== 'image' && item.raw);
    let mountedFile:
      | {
          file_id: string;
          file_name: string;
        }
      | undefined;
    if (docFile?.raw) {
      try {
        const uploadRes = await uploadThreadFile(
          docFile.raw,
          localThreadId.value
        );
        if (!uploadRes?.file_id) {
          throw new Error('文档未返回有效文件 ID');
        }
        mountedFile = {
          file_id: String(uploadRes.file_id),
          file_name: String(uploadRes.file_name || docFile.name || ''),
        };
      } catch (error: any) {
        Message.error(`文档挂载失败，本轮未发送：${error?.message || '请稍后重试'}`);
        return;
      }
    }
    messages.value.push({
      id: Date.now(),
      role: 'user',
      content:
        text ||
        (imageFiles.length ? '请解析我上传的图片。' : `请结合文件《${docFile?.name || ''}》回答。`),
      reasoning: '',
    });
    addAssistantPlaceholder();
    autoStickToBottom.value = true;
    await scrollToBottom(true);

    loading.value = true;
    abortController = new AbortController();
    let streamError = '';
    let answer = '';
    const thoughts: string[] = [];
    let sawReasoningToken = false;

    try {
      const imageBase64List = (
        await Promise.all(
          imageFiles
            .slice(0, 3)
            .map((file) => fileToDataUrl(file.raw as File))
        )
      ).filter(Boolean);
      const hasImages = imageBase64List.length > 0;
      const activeTools = [
        'knowledge_base',
        webSearchEnabled.value ? 'web_search' : '',
        deepThinkEnabled.value ? 'deep_thinking' : '',
      ].filter(Boolean);
      const toolMode =
        activeMode.value === 'exercise_grading'
          ? 'exercise_grading'
          : hasImages
            ? 'image_tutoring'
            : 'chat';

      await createAssistantChatStream(
        buildUserText(text, hasImages),
        localThreadId.value,
        {
          systemPrompt: buildModePrompt(hasImages, mountedFile?.file_name || ''),
          promptKey: 'tutor',
          ragK: 4,
          strictMode: false,
          activeTools,
          maxTokens: 32768,
          temperature: 0.4,
          topP: 0.85,
          topK: 50,
          currentFileId: mountedFile?.file_id,
          fileName: mountedFile?.file_name,
          imageBase64List,
          toolMode,
          reasoningEnabled: deepThinkEnabled.value,
        },
        (event) => {
          const msg = getLastAssistant();
          if (!msg) return;
          if (event.type === 'token') {
            answer += event.content || '';
            msg.content = sanitizeStreamingContent(answer);
          } else if (event.type === 'reasoning_token') {
            sawReasoningToken = true;
            msg.reasoning = (msg.reasoning || '') + (event.content || '');
          } else if (event.type === 'thought') {
            if (event.content) thoughts.push(event.content);
            if (
              shouldAppendThoughtToReasoning(
                event.content || '',
                event.stage,
                sawReasoningToken
              )
            ) {
              msg.reasoning = appendThoughtToReasoning(
                msg.reasoning || '',
                event.content || '',
                event.stage
              );
            }
          } else if (event.type === 'suggestions') {
            suggestions.value = normalizeSuggestionList(event.data || []);
          } else if (event.type === 'final') {
            msg.content = sanitizeStreamingContent(event.content || answer || '');
          } else if (event.type === 'error') {
            streamError = event.content || '生成失败';
          }
          void scrollToBottom();
        },
        abortController.signal
      );
      if (streamError) throw new Error(streamError);
      inputValue.value = '';
      fileList.value.forEach((file) => URL.revokeObjectURL(file.url));
      fileList.value = [];
      menuOpen.value = false;
    } catch (error: any) {
      const msg = getLastAssistant();
      if (!msg) return;
      if (error?.name === 'AbortError') {
        msg.content = msg.content || '已暂停本次回答。你可以继续提问。';
      } else {
        msg.content = `查询失败：${error?.message || '请稍后重试'}`;
        Message.error('查询失败，请稍后重试');
      }
    } finally {
      const msg = getLastAssistant();
      if (msg) msg.loading = false;
      loading.value = false;
      abortController = null;
      void scrollToBottom();
    }
  };

  const handleStop = () => {
    if (!abortController) return;
    abortController.abort();
  };

  const handleSuggestion = (text: string) => {
    inputValue.value = text;
    handleSend();
  };

  const handleClear = () => {
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
    messages.value = [];
    fileList.value.forEach((file) => URL.revokeObjectURL(file.url));
    fileList.value = [];
    suggestions.value = [];
    loading.value = false;
    activeMode.value = 'chat';
    menuOpen.value = false;
    autoStickToBottom.value = true;
    streamAssistId.value = null;
    streamContentLen.value = 0;
    streamReasonLen.value = 0;
    if (streamChaseTimer) {
      clearInterval(streamChaseTimer);
      streamChaseTimer = null;
    }
    localThreadId.value = `monitor-db-${Date.now()}`;
  };
</script>

<style scoped lang="less">
  .classroom-ai {
    position: relative;
    height: 100%;
    display: flex;
    flex-direction: column;
    background: linear-gradient(180deg, #f5f3ff 0%, #eef2ff 40%, #f8fafc 100%);
    border-radius: 20px;
    overflow: hidden;

    &.is-dragging {
      outline: 2px solid rgba(79, 70, 229, 0.35);
      outline-offset: -2px;
    }
  }

  .panel-drag-layer {
    position: absolute;
    inset: 8px;
    z-index: 40;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px dashed rgba(79, 70, 229, 0.55);
    border-radius: 16px;
    background: rgba(248, 250, 255, 0.94);
    color: #4338ca;
    font-size: 14px;
    font-weight: 800;
    pointer-events: none;
    backdrop-filter: blur(6px);
  }

  .mobile-topbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 14px;
    background: rgba(255, 255, 255, 0.92);
    border-bottom: 1px solid rgba(99, 102, 241, 0.08);

    h1 {
      flex: 1;
      margin: 0;
      text-align: center;
      font-size: 16px;
      font-weight: 800;
      color: #312e81;
    }
  }

  .back-btn {
    width: 32px;
    height: 32px;
    border: none;
    border-radius: 50%;
    background: var(--zy-bg-tag, #eef2ff);
    color: var(--zy-color-brand, #6366f1);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 16px;
  }

  .topbar-spacer {
    width: 32px;
    flex-shrink: 0;
  }

  .course-card {
    margin: 10px 12px 0;
    padding: 12px 14px;
    border-radius: 14px;
    background: #fff;
    border: 1px solid rgba(99, 102, 241, 0.12);
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.08);

    strong {
      display: block;
      margin: 4px 0 2px;
      font-size: 16px;
      color: #1e293b;
    }
  }

  .course-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    background: rgba(99, 102, 241, 0.1);
    color: #6366f1;
    font-size: 11px;
    font-weight: 700;
  }

  .course-meta {
    font-size: 12px;
    color: #64748b;
  }

  .message-panel {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 10px 12px;
  }

  .assistant-card {
    background: #fff;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 8px;
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.12);
    border: 1px solid rgba(99, 102, 241, 0.08);
  }

  .xiaozhi-head {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;

    strong {
      display: block;
      font-size: 18px;
      color: #312e81;
    }

    span {
      font-size: 12px;
      color: #64748b;
    }
  }

  .xiaozhi-avatar {
    width: 44px;
    height: 44px;
    border-radius: 14px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 800;
    box-shadow: 0 6px 16px rgba(99, 102, 241, 0.3);
  }

  .intro-lead {
    margin: 0 0 10px;
    font-size: 14px;
    line-height: 1.5;
    color: #334155;
  }

  .feature-list {
    margin: 0;
    padding: 0;
    list-style: none;

    li {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 7px 0;
      font-size: 13px;
      color: #475569;
      border-bottom: 1px solid #f1f5f9;

      &:last-child {
        border-bottom: none;
      }

      svg {
        color: #6366f1;
        flex-shrink: 0;
      }
    }
  }
  .bubble-row {
    display: flex;
    margin-bottom: 6px;
  }
  .bubble {
    max-width: 92%;
    border-radius: 14px;
    padding: 8px 10px;
    white-space: pre-wrap;
    line-height: 1.42;
    font-size: 14px;
    box-shadow: 0 4px 10px rgba(15, 23, 42, 0.06);
    &.user {
      margin-left: auto;
      background: #e6f0ff;
      color: #24406b;
    }
    &.assistant {
      background: #fff;
      color: #1e293b;
    }
  }
  .reasoning-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: 1px solid rgba(25, 103, 210, 0.2);
    border-radius: 999px;
    padding: 3px 9px;
    font-size: 12px;
    color: #1a57af;
    margin-bottom: 8px;
    cursor: pointer;
    .arrow {
      font-size: 11px;
    }
  }
  .reasoning-content {
    margin-bottom: 6px;
    padding: 6px 9px;
    border-left: 3px solid #bcd3f8;
    background: #f7fbff;
    border-radius: 0 8px 8px 0;
    color: #556987;
    font-size: 13px;
    line-height: 1.4;
  }
  .suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    padding: 0 12px 8px;

    .suggestion-pill {
      border: 1px solid rgba(99, 102, 241, 0.2);
      border-radius: 999px;
      font-size: 12px;
      padding: 6px 12px;
      background: #fff;
      color: #4f46e5;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s ease;

      &:hover {
        background: #eef2ff;
      }

      &--dynamic {
        border-style: dashed;
        color: #64748b;
      }
    }
  }

  .input-wrap {
    position: relative;
    margin: 0 10px 10px;
    padding: 10px 12px;
    background: #fff;
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    flex-shrink: 0;

    &.is-dragging {
      background: rgba(239, 246, 255, 0.92);
    }

    .drag-layer {
      position: absolute;
      inset: 6px;
      z-index: 8;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px dashed rgba(37, 99, 235, 0.55);
      border-radius: 12px;
      background: rgba(248, 251, 255, 0.94);
      color: #1d5fd0;
      font-size: 13px;
      font-weight: 800;
      pointer-events: none;
    }

    .quick-file-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 7px;
    }

    .quick-file-card {
      min-height: 34px;
      max-width: 100%;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 7px;
      border: 1px solid #dbe5f2;
      border-radius: 10px;
      background: #fff;

      img {
        width: 28px;
        height: 28px;
        border-radius: 7px;
        object-fit: cover;
      }

      .file-icon {
        width: 24px;
        height: 24px;
        border-radius: 7px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: #edf4ff;
        color: #1d5fd0;
        font-size: 12px;
        font-weight: 800;
      }

      .file-name {
        max-width: 110px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        color: #243a55;
        font-size: 12px;
        font-weight: 650;
      }

      .file-status {
        color: #1d5fd0;
        font-size: 11px;
        font-weight: 700;
      }

      button {
        border: none;
        background: transparent;
        color: #64748b;
        cursor: pointer;
        font-size: 16px;
        line-height: 1;
      }
    }

    .actions {
      margin-top: 9px;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 6px;
      flex-wrap: wrap;
    }

    .quick-add-wrap {
      position: relative;
      margin-right: auto;
    }

    .quick-add-btn,
    .quick-toggle,
    .quick-mode button {
      height: 28px;
      border: none;
      border-radius: 999px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 750;
      white-space: nowrap;
    }

    .quick-add-btn {
      width: 28px;
      background: #e8eef7;
      color: #24406b;
      font-size: 18px;
      line-height: 1;
    }

    .quick-add-menu {
      position: absolute;
      left: 0;
      bottom: calc(100% + 8px);
      z-index: 12;
      width: 124px;
      padding: 6px;
      border: 1px solid #dbe5f2;
      border-radius: 12px;
      background: #fff;
      box-shadow: 0 12px 24px rgba(15, 23, 42, 0.14);

      button {
        width: 100%;
        height: 32px;
        border: none;
        border-radius: 8px;
        background: transparent;
        color: #243a55;
        text-align: left;
        padding: 0 8px;
        cursor: pointer;
        font-size: 12px;
        font-weight: 700;

        &:hover {
          background: #f1f6ff;
        }
      }
    }

    .quick-toggle {
      padding: 0 9px;
      background: #eef4ff;
      color: #38516f;

      &.active {
        background: #dcecff;
        color: #155fc0;
      }
    }

    .quick-mode {
      display: inline-flex;
      padding: 2px;
      border-radius: 999px;
      background: #e8eef7;

      button {
        padding: 0 9px;
        background: transparent;
        color: #53657e;

        &.active {
          background: #fff;
          color: #155fc0;
          box-shadow: 0 2px 6px rgba(15, 23, 42, 0.1);
        }
      }
    }
  }

  :deep(.markdown-body .code-block) {
    margin: 4px 0;
    border: 1px solid #d6e2f1;
    border-radius: 10px;
    overflow: hidden;
  }

  :deep(.markdown-body .code-header) {
    display: flex;
    align-items: center;
    min-height: 32px;
    padding: 0 10px;
    background: #eff5ff;
    border-bottom: 1px solid #d6e2f1;
  }

  :deep(.markdown-body .code-header img) {
    width: 14px;
    height: 14px;
  }

  :deep(.markdown-body pre.hljs) {
    margin: 0;
    padding: 8px 10px;
    overflow-x: auto;
  }

  :deep(.markdown-body) {
    line-height: 1.32;
  }

  :deep(.markdown-body h1),
  :deep(.markdown-body h2),
  :deep(.markdown-body h3),
  :deep(.markdown-body h4),
  :deep(.markdown-body h5),
  :deep(.markdown-body h6) {
    margin: 0.26em 0 0.12em;
    line-height: 1.2;
  }

  :deep(.markdown-body p) {
    margin: 0 0 0.16em;
    line-height: 1.32;
  }

  :deep(.markdown-body p:last-child) {
    margin-bottom: 0;
  }

  :deep(.markdown-body h1 + p),
  :deep(.markdown-body h2 + p),
  :deep(.markdown-body h3 + p),
  :deep(.markdown-body h4 + p),
  :deep(.markdown-body h5 + p),
  :deep(.markdown-body h6 + p) {
    margin-top: 0;
  }

  :deep(.markdown-body ul),
  :deep(.markdown-body ol) {
    margin: 0.12em 0;
    padding-left: 1em;
  }

  :deep(.markdown-body ul ul),
  :deep(.markdown-body ul ol),
  :deep(.markdown-body ol ul),
  :deep(.markdown-body ol ol) {
    margin: 0.06em 0;
  }

  :deep(.markdown-body li) {
    margin: 0.04em 0;
    line-height: 1.28;
  }
</style>
