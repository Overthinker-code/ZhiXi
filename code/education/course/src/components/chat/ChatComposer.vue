<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import type { ChatToolPayload, ReasoningLevel, ResourceRequestPayload, TutorMode } from '@/api/ai-chat';
  import { DEFAULT_RESOURCE_TYPES, type TutorPanel } from './tutorActions';

  const props = defineProps<{
    loading?: boolean;
    mode: TutorMode;
    tools: ChatToolPayload;
    reasoningLevel: ReasoningLevel;
    resourceRequest: ResourceRequestPayload;
  }>();

  const emit = defineEmits<{
    (e: 'send', payload: { text: string; files: File[] }): void;
    (e: 'stop'): void;
    (e: 'action', actionId: string): void;
    (e: 'toggle-web'): void;
    (e: 'set-reasoning', level: ReasoningLevel): void;
    (e: 'open-panel', panel: TutorPanel): void;
    (e: 'update-resource-types', types: string[]): void;
  }>();

  const input = ref('');
  const files = ref<File[]>([]);
  const composing = ref(false);
  const fileInput = ref<HTMLInputElement | null>(null);
  const toolMenuOpen = ref(false);
  const resourceTypeOpen = ref(false);
  const reasoningMenuOpen = ref(false);
  const selectedReasoningId = ref('balanced');

  const resourceTypeLabels: Record<string, string> = {
    lecture_note: '讲义',
    mind_map: '思维导图',
    quiz: '练习题',
    reading: '拓展阅读',
    code_case: '代码案例',
    video_script: '视频脚本',
  };
  const reasoningOptions: Array<{ id: string; label: string; level: ReasoningLevel }> = [
    { id: 'smart', label: '智能', level: 'balanced' },
    { id: 'fast', label: '极速', level: 'fast' },
    { id: 'balanced', label: '均衡', level: 'balanced' },
    { id: 'high', label: '高级', level: 'deep' },
    { id: 'ultra', label: '超高', level: 'deep' },
  ];

  const canSend = computed(
    () => Boolean(input.value.trim() || files.value.length) && !props.loading
  );
  const hasActiveTools = computed(
    () =>
      props.tools.webSearch ||
      props.tools.homeworkReview ||
      props.tools.resourceGeneration ||
      props.tools.deepResearch ||
      files.value.length > 0
  );
  const selectedReasoning = computed(
    () =>
      reasoningOptions.find((item) => item.id === selectedReasoningId.value) ||
      reasoningOptions[2]
  );

  const formatBytes = (size: number) => {
    if (!size) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1);
    const value = size / 1024 ** index;
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[index]}`;
  };

  const chooseFiles = () => {
    toolMenuOpen.value = false;
    resourceTypeOpen.value = false;
    fileInput.value?.click();
  };

  const onFileChange = (event: Event) => {
    const target = event.target as HTMLInputElement;
    const next = Array.from(target.files || []);
    files.value = [...files.value, ...next].slice(0, 4);
    target.value = '';
  };

  const removeFile = (index: number) => {
    files.value.splice(index, 1);
  };

  const send = () => {
    if (!canSend.value) return;
    emit('send', { text: input.value.trim(), files: [...files.value] });
    input.value = '';
    files.value = [];
    toolMenuOpen.value = false;
    resourceTypeOpen.value = false;
    reasoningMenuOpen.value = false;
  };

  const onKeydown = (event: KeyboardEvent) => {
    if (event.key !== 'Enter' || event.shiftKey || composing.value) return;
    event.preventDefault();
    send();
  };

  const pickAction = (actionId: string) => {
    emit('action', actionId);
    if (actionId !== 'resource_generation') {
      toolMenuOpen.value = false;
      resourceTypeOpen.value = false;
    }
  };

  const toggleResourceType = (type: string) => {
    const set = new Set(props.resourceRequest.types);
    if (set.has(type)) set.delete(type);
    else set.add(type);
    emit('update-resource-types', Array.from(set));
  };

  const toggleWebSearch = () => {
    emit('toggle-web');
  };

  const chooseReasoning = (id: string) => {
    const option = reasoningOptions.find((item) => item.id === id);
    if (!option) return;
    selectedReasoningId.value = option.id;
    reasoningMenuOpen.value = false;
    emit('set-reasoning', option.level);
  };

  watch(
    () => props.reasoningLevel,
    (level) => {
      const current = reasoningOptions.find((item) => item.id === selectedReasoningId.value);
      if (current?.level === level) return;
      selectedReasoningId.value =
        level === 'fast' ? 'fast' : level === 'deep' ? 'high' : 'balanced';
    },
    { immediate: true }
  );

  defineExpose({
    openUpload: chooseFiles,
  });
</script>

<template>
  <section class="chat-composer" data-testid="tutor-composer">
    <div class="composer-box" :class="{ 'has-tools': hasActiveTools }">
      <div v-if="files.length" class="composer-files">
        <button
          v-for="(file, index) in files"
          :key="`${file.name}-${index}`"
          type="button"
          @click="removeFile(index)"
        >
          <span>{{ file.name }}</span>
          <small>{{ formatBytes(file.size) }} · 移除</small>
        </button>
      </div>

      <textarea
        v-model="input"
        placeholder="有问题，尽管问"
        rows="2"
        @compositionstart="composing = true"
        @compositionend="composing = false"
        @keydown="onKeydown"
      />

      <div class="composer-toolbar">
        <input
          ref="fileInput"
          hidden
          type="file"
          multiple
          accept="image/*,.pdf,.doc,.docx,.txt,.md,.markdown,.ppt,.pptx,.py,.js,.ts,.java,.cpp,.c,.sql"
          @change="onFileChange"
        />

        <div class="tool-wrap">
          <button
            type="button"
            class="icon-button"
            :class="{ active: toolMenuOpen || hasActiveTools }"
            aria-label="打开工具"
            data-testid="tool-menu"
            @click="toolMenuOpen = !toolMenuOpen"
          >
            +
          </button>

          <div v-if="toolMenuOpen" class="tool-menu" @keydown.esc="toolMenuOpen = false">
            <section>
              <button type="button" class="tool-menu__item featured" @click="chooseFiles">
                <span class="menu-icon">+</span>
                <span class="menu-copy">
                  <strong>添加照片和文件</strong>
                  <em>从电脑上传</em>
                </span>
              </button>
              <button
                type="button"
                class="tool-menu__item"
                @click="emit('open-panel', 'course_picker'); toolMenuOpen = false"
              >
                <span class="menu-icon">@</span>
                <span class="menu-copy">
                  <strong>课程上下文</strong>
                  <em>需要时手动指定</em>
                </span>
              </button>
              <button
                type="button"
                class="tool-menu__item"
                data-testid="tool-web-search"
                :class="{ active: tools.webSearch }"
                @click="toggleWebSearch"
              >
                <span class="menu-icon">网</span>
                <span class="menu-copy">
                  <strong>{{ tools.webSearch ? '联网搜索已开' : '联网搜索' }}</strong>
                  <em>查找实时资料和信息</em>
                </span>
              </button>
              <button
                type="button"
                class="tool-menu__item"
                data-testid="mode-homework"
                :class="{ active: mode === 'homework_review' }"
                @click="pickAction('homework_review')"
              >
                <span class="menu-icon">批</span>
                <span class="menu-copy">
                  <strong>作业批改</strong>
                  <em>评分、错因和订正建议</em>
                </span>
              </button>
              <button
                type="button"
                class="tool-menu__item"
                data-testid="mode-resource"
                :class="{ active: mode === 'resource_generation' }"
                @click="pickAction('resource_generation'); resourceTypeOpen = !resourceTypeOpen"
              >
                <span class="menu-icon">资</span>
                <span class="menu-copy">
                  <strong>资料生成</strong>
                  <em>讲义、练习和思维导图</em>
                </span>
              </button>
              <div v-if="resourceTypeOpen" class="resource-types">
                <label v-for="type in DEFAULT_RESOURCE_TYPES" :key="type">
                  <input
                    type="checkbox"
                    :checked="resourceRequest.types.includes(type)"
                    @change="toggleResourceType(type)"
                  />
                  {{ resourceTypeLabels[type] || type }}
                </label>
              </div>
              <button
                type="button"
                class="tool-menu__item"
                data-testid="mode-deep-research"
                :class="{ active: mode === 'deep_research' }"
                @click="pickAction('deep_research')"
              >
                <span class="menu-icon">研</span>
                <span class="menu-copy">
                  <strong>深度研究</strong>
                  <em>多轮检索和报告生成</em>
                </span>
              </button>
            </section>
          </div>
        </div>

        <div class="toolbar-spacer" />

        <div class="reasoning-wrap">
          <button
            type="button"
            class="reasoning-button"
            data-testid="tool-reasoning"
            aria-label="思考强度"
            :aria-expanded="reasoningMenuOpen"
            @click="reasoningMenuOpen = !reasoningMenuOpen"
          >
            <span>{{ selectedReasoning.label }}</span>
            <i />
          </button>

          <div v-if="reasoningMenuOpen" class="reasoning-menu">
            <button
              v-for="option in reasoningOptions"
              :key="option.id"
              type="button"
              :class="{ active: selectedReasoningId === option.id }"
              @click="chooseReasoning(option.id)"
            >
              <span>
                <strong>{{ option.label }}</strong>
              </span>
              <b v-if="selectedReasoningId === option.id">✓</b>
            </button>
          </div>
        </div>

        <button
          v-if="loading"
          type="button"
          class="send-button stop"
          data-testid="stop-generation"
          @click="emit('stop')"
        >
          停止
        </button>
        <button
          v-else
          type="button"
          class="send-button"
          :disabled="!canSend"
          data-testid="send-message"
          @click="send"
        >
          发送
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped lang="scss">
  .chat-composer {
    width: min(780px, calc(100vw - 500px));
    margin: 0 auto;
  }

  .composer-box {
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 24px;
    background: #fff;
    box-shadow: 0 14px 42px rgba(15, 23, 42, 0.07);
    transition: border-color 0.18s ease, box-shadow 0.18s ease;

    &:focus-within {
      border-color: #6366f1;
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1), 0 14px 42px rgba(15, 23, 42, 0.07);
    }
  }

  .composer-files {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 12px 14px 0;

    button {
      max-width: 220px;
      padding: 8px 10px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 14px;
      background: #f7f9ff;
      color: #344054;
      text-align: left;
      cursor: pointer;

      span,
      small {
        display: block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      small {
        margin-top: 2px;
        color: #667085;
        font-size: 11px;
      }
    }
  }

  textarea {
    width: 100%;
    min-height: 54px;
    max-height: 240px;
    resize: vertical;
    padding: 15px 20px 4px;
    border: 0;
    outline: none;
    color: #101828;
    background: transparent;
    font-size: 15px;
    line-height: 1.6;

    &::placeholder {
      color: #98a2b3;
    }
  }

  .composer-toolbar {
    position: relative;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px 10px;
  }

  .tool-wrap,
  .reasoning-wrap {
    position: relative;
  }

  .icon-button,
  .send-button,
  .reasoning-button {
    height: 40px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 999px;
    color: #344054;
    background: #f8fafc;
    font-weight: 600;
    transition: transform 0.14s ease, border-color 0.16s ease, background 0.16s ease, color 0.16s ease;
  }

  .icon-button {
    width: 38px;
    height: 38px;
    padding: 0;
    font-size: 22px;
    line-height: 1;
    cursor: pointer;

    &.active {
      color: #4f46e5;
      border-color: rgba(99, 102, 241, 0.3);
      background: #eef2ff;
    }

    &:hover {
      border-color: rgba(99, 102, 241, 0.34);
      background: #eef2ff;
    }
  }

  .reasoning-button {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    min-width: 76px;
    height: 38px;
    padding: 0 12px 0 14px;
    border-color: transparent;
    color: #8a8f98;
    background: transparent;
    font-size: 15px;
    font-weight: 560;
    cursor: pointer;

    &:hover,
    &:focus,
    &[aria-expanded='true'] {
      border-color: rgba(99, 102, 241, 0.35);
      color: #667085;
      background: #f2f4f7;
      outline: none;
    }

    i {
      width: 7px;
      height: 7px;
      border-right: 2px solid currentColor;
      border-bottom: 2px solid currentColor;
      transform: translateY(-2px) rotate(45deg);
    }
  }

  .toolbar-spacer {
    flex: 1;
  }

  .send-button {
    min-width: 58px;
    height: 38px;
    padding: 0 16px;
    color: #fff;
    border-color: transparent;
    background: #4f46e5;
    cursor: pointer;

    &:hover:not(:disabled) {
      background: #6366f1;
    }

    &:active:not(:disabled) {
      transform: scale(0.98);
    }

    &:disabled {
      cursor: not-allowed;
      opacity: 0.45;
    }

    &.stop {
      color: #344054;
      border-color: rgba(15, 23, 42, 0.1);
      background: #f2f4f7;
    }
  }

  .tool-menu,
  .reasoning-menu {
    position: absolute;
    bottom: 50px;
    z-index: 30;
    max-height: min(620px, calc(100vh - 220px));
    overflow: auto;
    padding: 8px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.98);
    box-shadow: 0 20px 56px rgba(15, 23, 42, 0.16);
  }

  .tool-menu {
    left: 0;
    bottom: 150px;
    width: 320px;
    animation: menu-enter 0.16s ease both;

    section + section {
      margin-top: 6px;
      padding-top: 6px;
      border-top: 1px solid rgba(15, 23, 42, 0.06);
    }

    .tool-menu__item {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      min-height: 46px;
      padding: 8px 10px;
      border: 0;
      border-radius: 13px;
      background: transparent;
      text-align: left;
      cursor: pointer;

      &.featured {
        background: #f3f4f6;
      }

      &:hover {
        background: #f7f9ff;
      }

      &.active {
        background: #eef2ff;
      }

      &.active strong {
        color: #4f46e5;
      }

      &.compact {
        min-height: 42px;
      }
    }

    strong {
      display: block;
      color: #101828;
      font-size: 13.5px;
      font-weight: 680;
    }

    em {
      display: block;
      margin-top: 2px;
      color: #8a94a6;
      font-size: 12px;
      font-style: normal;
      line-height: 1.35;
    }
  }

  .menu-icon {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 9px;
    color: #4f46e5;
    background: #eef2ff;
    font-size: 12px;
    font-weight: 800;
  }

  .menu-copy {
    min-width: 0;
  }

  .reasoning-menu {
    right: 0;
    bottom: 48px;
    width: 190px;
    padding: 10px;
    border-radius: 18px;
    transform: none;
    animation: reasoning-enter 0.16s ease both;

    &::before {
      content: '思考强度';
      display: block;
      padding: 4px 12px 8px;
      color: #98a2b3;
      font-size: 13px;
      font-weight: 650;
    }

    button {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      width: 100%;
      min-height: 42px;
      padding: 7px 12px;
      border: 0;
      border-radius: 12px;
      color: #101828;
      background: transparent;
      text-align: left;
      cursor: pointer;

      &:hover,
      &.active {
        background: #f7f9ff;
      }
    }

    span {
      min-width: 0;
    }

    strong {
      display: block;
    }

    strong {
      font-size: 14px;
      font-weight: 680;
    }

    b {
      color: #667085;
      font-size: 18px;
      font-weight: 500;
    }
  }

  .resource-types {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
    padding: 2px 10px 8px;

    label {
      display: flex;
      align-items: center;
      gap: 6px;
      min-height: 30px;
      color: #475467;
      font-size: 12px;
    }
  }

  @keyframes menu-enter {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes reasoning-enter {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 1280px) {
    .chat-composer {
      width: min(720px, calc(100vw - 420px));
    }

    .tool-menu {
      width: 300px;
    }

    .reasoning-menu {
      right: 0;
      animation-name: menu-enter;
    }
  }

  @media (max-width: 860px) {
    .chat-composer {
      width: calc(100vw - 32px);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .tool-menu,
    .icon-button,
    .send-button,
    .reasoning-button,
    .composer-box {
      animation: none;
      transition: none;
    }
  }
</style>
