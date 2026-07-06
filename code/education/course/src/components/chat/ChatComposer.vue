<script setup lang="ts">
  import { computed, ref } from 'vue';
  import type { ChatToolPayload, ReasoningLevel, ResourceRequestPayload, TutorMode } from '@/api/ai-chat';
  import { DEFAULT_RESOURCE_TYPES, TUTOR_ACTIONS, type TutorPanel } from './tutorActions';

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

  const visibleActions = TUTOR_ACTIONS.filter((item) =>
    ['summarize_chapter', 'explain_problem', 'generate_outline', 'review_weak_points'].includes(item.id)
  );
  const resourceTypeLabels: Record<string, string> = {
    lecture_note: '讲义',
    mind_map: '思维导图',
    quiz: '练习题',
    reading: '拓展阅读',
    code_case: '代码案例',
    video_script: '视频脚本',
  };

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
        placeholder="问任何课程问题，或上传资料让我一起分析"
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
              <h4>资料与上下文</h4>
              <button type="button" @click="chooseFiles">
                <strong>上传附件</strong>
                <span>图片、PDF、文档、代码或作业</span>
              </button>
              <button type="button" @click="emit('open-panel', 'course_picker'); toolMenuOpen = false">
                <strong>指定课程</strong>
                <span>默认会自动判断，需要时手动覆盖</span>
              </button>
            </section>

            <section>
              <h4>能力</h4>
              <button
                type="button"
                data-testid="tool-web-search"
                :class="{ active: tools.webSearch }"
                @click="toggleWebSearch"
              >
                <strong>{{ tools.webSearch ? '联网搜索已开' : '联网搜索' }}</strong>
                <span>需要外部资料或时效信息时启用</span>
              </button>
              <button
                type="button"
                data-testid="mode-homework"
                :class="{ active: mode === 'homework_review' }"
                @click="pickAction('homework_review')"
              >
                <strong>作业批改</strong>
                <span>评分、错因、订正建议</span>
              </button>
              <button
                type="button"
                data-testid="mode-resource"
                :class="{ active: mode === 'resource_generation' }"
                @click="pickAction('resource_generation'); resourceTypeOpen = !resourceTypeOpen"
              >
                <strong>资料生成</strong>
                <span>讲义、练习、思维导图、代码案例</span>
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
                data-testid="mode-deep-research"
                :class="{ active: mode === 'deep_research' }"
                @click="pickAction('deep_research')"
              >
                <strong>深度研究</strong>
                <span>多轮检索、分析和报告生成</span>
              </button>
            </section>

            <section>
              <h4>快捷任务</h4>
              <button
                v-for="action in visibleActions"
                :key="action.id"
                type="button"
                @click="pickAction(action.id)"
              >
                <strong>{{ action.label }}</strong>
                <span>{{ action.description }}</span>
              </button>
            </section>
          </div>
        </div>

        <select
          class="reasoning-select"
          :value="reasoningLevel"
          data-testid="tool-reasoning"
          aria-label="思考强度"
          @change="emit('set-reasoning', ($event.target as HTMLSelectElement).value as ReasoningLevel)"
        >
          <option value="fast">快速</option>
          <option value="balanced">均衡</option>
          <option value="deep">深度</option>
        </select>

        <div class="toolbar-spacer" />

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
    width: min(880px, calc(100vw - 420px));
    margin: 0 auto;
  }

  .composer-box {
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 28px;
    background: #fff;
    box-shadow: 0 16px 50px rgba(15, 23, 42, 0.08);
    transition: border-color 0.18s ease, box-shadow 0.18s ease;

    &:focus-within {
      border-color: #6366f1;
      box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.12), 0 16px 50px rgba(15, 23, 42, 0.08);
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
    min-height: 74px;
    max-height: 240px;
    resize: vertical;
    padding: 20px 24px 8px;
    border: 0;
    outline: none;
    color: #101828;
    background: transparent;
    font-size: 16px;
    line-height: 1.6;

    &::placeholder {
      color: #98a2b3;
    }
  }

  .composer-toolbar {
    position: relative;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px 12px;
  }

  .tool-wrap {
    position: relative;
  }

  .icon-button,
  .send-button,
  .reasoning-select {
    height: 40px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 999px;
    color: #344054;
    background: #f8fafc;
    font-weight: 600;
    transition: transform 0.14s ease, border-color 0.16s ease, background 0.16s ease, color 0.16s ease;
  }

  .icon-button {
    width: 40px;
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

  .reasoning-select {
    min-width: 92px;
    padding: 0 32px 0 14px;
    appearance: auto;
    cursor: pointer;

    &:hover,
    &:focus {
      border-color: rgba(99, 102, 241, 0.35);
      color: #4f46e5;
      outline: none;
    }
  }

  .toolbar-spacer {
    flex: 1;
  }

  .send-button {
    min-width: 64px;
    padding: 0 18px;
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

  .tool-menu {
    position: absolute;
    left: 0;
    bottom: 50px;
    z-index: 30;
    width: 340px;
    max-height: min(620px, calc(100vh - 220px));
    overflow: auto;
    padding: 8px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 20px;
    background: #fff;
    box-shadow: 0 24px 72px rgba(15, 23, 42, 0.16);
    animation: menu-enter 0.16s ease both;

    section + section {
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid rgba(15, 23, 42, 0.06);
    }

    h4 {
      margin: 6px 10px 8px;
      color: #98a2b3;
      font-size: 12px;
      font-weight: 700;
    }

    button {
      display: block;
      width: 100%;
      padding: 11px 12px;
      border: 0;
      border-radius: 14px;
      background: transparent;
      text-align: left;
      cursor: pointer;

      &:hover,
      &.active {
        background: #f7f9ff;
      }

      &.active strong {
        color: #4f46e5;
      }
    }

    strong {
      display: block;
      color: #101828;
      font-size: 14px;
      font-weight: 700;
    }

    span {
      display: block;
      margin-top: 3px;
      color: #667085;
      font-size: 12px;
      line-height: 1.45;
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

  @media (max-width: 1280px) {
    .chat-composer {
      width: min(820px, calc(100vw - 360px));
    }

    .tool-menu {
      width: 320px;
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
    .reasoning-select,
    .composer-box {
      animation: none;
      transition: none;
    }
  }
</style>
