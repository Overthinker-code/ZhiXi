<script setup lang="ts">
  import { computed, ref } from 'vue';
  import type { ChatToolPayload, ReasoningLevel, ResourceRequestPayload, TutorMode } from '@/api/ai-chat';
  import { DEFAULT_RESOURCE_TYPES, TUTOR_ACTIONS, type TutorPanel } from './tutorActions';

  const props = defineProps<{
    loading?: boolean;
    mode: TutorMode;
    tools: ChatToolPayload;
    reasoningLevel: ReasoningLevel;
    chips: string[];
    resourceRequest: ResourceRequestPayload;
  }>();

  const emit = defineEmits<{
    (e: 'send', payload: { text: string; files: File[] }): void;
    (e: 'stop'): void;
    (e: 'action', actionId: string): void;
    (e: 'toggle-web'): void;
    (e: 'set-reasoning', level: ReasoningLevel): void;
    (e: 'set-mode', mode: TutorMode): void;
    (e: 'open-panel', panel: TutorPanel): void;
    (e: 'update-resource-types', types: string[]): void;
  }>();

  const input = ref('');
  const files = ref<File[]>([]);
  const composing = ref(false);
  const fileInput = ref<HTMLInputElement | null>(null);
  const commandOpen = ref(false);
  const resourceTypeOpen = ref(false);

  const canSend = computed(
    () => Boolean(input.value.trim() || files.value.length) && !props.loading
  );

  const modeText = computed(() => {
    const map: Record<TutorMode, string> = {
      tutor: '课程问答',
      homework_review: '作业批改',
      resource_generation: '资料生成',
      deep_research: '深度研究',
    };
    return map[props.mode];
  });

  const fileLabel = computed(() =>
    files.value.length ? `已选择 ${files.value.length} 个文件` : ''
  );

  const formatBytes = (size: number) => {
    if (!size) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1);
    const value = size / 1024 ** index;
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[index]}`;
  };

  const chooseFiles = () => {
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
    commandOpen.value = false;
    resourceTypeOpen.value = false;
  };

  const onKeydown = (event: KeyboardEvent) => {
    if (event.key !== 'Enter' || event.shiftKey || composing.value) return;
    event.preventDefault();
    send();
  };

  const toggleResourceType = (type: string) => {
    const set = new Set(props.resourceRequest.types);
    if (set.has(type)) set.delete(type);
    else set.add(type);
    emit('update-resource-types', Array.from(set));
  };

  defineExpose({
    openUpload: chooseFiles,
  });
</script>

<template>
  <section class="chat-composer" data-testid="tutor-composer">
    <div class="composer-status">
      <span>当前模式：{{ modeText }}</span>
      <span v-for="chip in chips" :key="chip">{{ chip }}</span>
      <span v-if="fileLabel">{{ fileLabel }}</span>
    </div>

    <div class="composer-box">
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
        placeholder="输入问题，上传资料，或用 @ 选择课程上下文"
        rows="2"
        @compositionstart="composing = true"
        @compositionend="composing = false"
        @keydown="onKeydown"
      />

      <div class="composer-toolbar">
        <div class="toolbar-left">
          <input
            ref="fileInput"
            hidden
            type="file"
            multiple
            accept="image/*,.pdf,.doc,.docx,.txt,.md,.markdown,.ppt,.pptx,.py,.js,.ts,.java,.cpp,.c,.sql"
            @change="onFileChange"
          />
          <button type="button" class="tool-pill icon-pill" @click="chooseFiles">+</button>
          <button type="button" class="tool-pill" @click="emit('open-panel', 'course_picker')">@ 课程上下文</button>
          <div class="command-wrap">
            <button type="button" class="tool-pill" @click="commandOpen = !commandOpen">/ 命令</button>
            <div v-if="commandOpen" class="command-menu">
              <button
                v-for="action in TUTOR_ACTIONS.filter((item) => ['summarize_chapter', 'explain_problem', 'generate_outline', 'review_weak_points'].includes(item.id))"
                :key="action.id"
                type="button"
                @click="emit('action', action.id)"
              >
                <strong>{{ action.label }}</strong>
                <span>{{ action.description }}</span>
              </button>
            </div>
          </div>
        </div>

        <div class="toolbar-center">
          <button
            type="button"
            :class="['tool-pill', { active: tools.webSearch }]"
            data-testid="tool-web-search"
            @click="emit('toggle-web')"
          >
            联网搜索
          </button>
          <select
            class="tool-select"
            :value="reasoningLevel"
            data-testid="tool-reasoning"
            @change="emit('set-reasoning', ($event.target as HTMLSelectElement).value as ReasoningLevel)"
          >
            <option value="fast">深度思考：快速</option>
            <option value="balanced">深度思考：均衡</option>
            <option value="deep">深度思考：深度</option>
          </select>
          <button
            type="button"
            :class="['tool-pill', { active: mode === 'homework_review' }]"
            data-testid="mode-homework"
            @click="emit('action', 'homework_review')"
          >
            作业批改
          </button>
          <div class="command-wrap">
            <button
              type="button"
              :class="['tool-pill', { active: mode === 'resource_generation' }]"
              data-testid="mode-resource"
              @click="emit('action', 'resource_generation'); resourceTypeOpen = !resourceTypeOpen"
            >
              资料生成
            </button>
            <div v-if="resourceTypeOpen" class="resource-menu">
              <label v-for="type in DEFAULT_RESOURCE_TYPES" :key="type">
                <input
                  type="checkbox"
                  :checked="resourceRequest.types.includes(type)"
                  @change="toggleResourceType(type)"
                />
                {{ type }}
              </label>
            </div>
          </div>
          <button
            type="button"
            :class="['tool-pill', { active: mode === 'deep_research' }]"
            data-testid="mode-deep-research"
            @click="emit('action', 'deep_research')"
          >
            深度研究
          </button>
        </div>

        <div class="toolbar-right">
          <span class="model-chip">MiMo 2.5</span>
          <button
            v-if="loading"
            type="button"
            class="send-btn stop"
            data-testid="stop-generation"
            @click="emit('stop')"
          >
            停止
          </button>
          <button
            v-else
            type="button"
            class="send-btn"
            :disabled="!canSend"
            data-testid="send-message"
            @click="send"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped lang="scss">
  .chat-composer {
    width: min(880px, calc(100% - 48px));
    margin: 0 auto;
  }

  .composer-status {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;

    span {
      height: 28px;
      padding: 0 10px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 999px;
      color: #475467;
      background: #fff;
      font-size: 12px;
      line-height: 27px;
    }
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

  textarea {
    display: block;
    width: 100%;
    min-height: 72px;
    max-height: 240px;
    padding: 18px 20px 8px;
    border: 0;
    outline: none;
    resize: vertical;
    color: #101828;
    background: transparent;
    font: inherit;
    line-height: 1.6;

    &::placeholder {
      color: #98a2b3;
    }
  }

  .composer-files {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 12px 16px 0;

    button {
      display: grid;
      gap: 2px;
      max-width: 220px;
      padding: 8px 10px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 12px;
      background: #f7f9ff;
      text-align: left;
      cursor: pointer;
    }

    span {
      overflow: hidden;
      color: #344054;
      font-size: 13px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    small {
      color: #667085;
      font-size: 12px;
    }
  }

  .composer-toolbar {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 10px;
    align-items: center;
    padding: 8px 10px 10px;
  }

  .toolbar-left,
  .toolbar-center,
  .toolbar-right {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }

  .toolbar-center {
    justify-content: center;
  }

  .tool-pill,
  .tool-select,
  .model-chip {
    height: 34px;
    padding: 0 12px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 999px;
    color: #475467;
    background: #f7f9ff;
    font-size: 13px;
  }

  button.tool-pill {
    cursor: pointer;
    transition: background 0.18s ease, color 0.18s ease, transform 0.12s ease;

    &:hover {
      color: #4f46e5;
    }

    &:active {
      transform: scale(0.98);
    }

    &.active {
      color: #fff;
      background: #4f46e5;
      border-color: #4f46e5;
    }
  }

  .icon-pill {
    width: 34px;
    padding: 0;
    font-size: 20px;
  }

  .command-wrap {
    position: relative;
  }

  .command-menu,
  .resource-menu {
    position: absolute;
    bottom: 42px;
    left: 0;
    z-index: 20;
    width: 280px;
    padding: 8px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 16px;
    background: #fff;
    box-shadow: 0 16px 50px rgba(15, 23, 42, 0.1);
  }

  .command-menu button {
    display: grid;
    gap: 4px;
    width: 100%;
    padding: 10px;
    border: 0;
    border-radius: 12px;
    background: transparent;
    text-align: left;
    cursor: pointer;

    &:hover {
      background: #f7f9ff;
    }

    strong {
      color: #101828;
      font-size: 13px;
    }

    span {
      color: #667085;
      font-size: 12px;
      line-height: 1.45;
    }
  }

  .resource-menu {
    display: grid;
    gap: 8px;

    label {
      display: flex;
      gap: 8px;
      color: #344054;
      font-size: 13px;
    }
  }

  .send-btn {
    height: 38px;
    min-width: 64px;
    border: 0;
    border-radius: 999px;
    color: #fff;
    background: #4f46e5;
    font-weight: 700;
    cursor: pointer;
    transition: transform 0.12s ease, filter 0.18s ease;

    &:hover {
      filter: brightness(1.04);
    }

    &:active {
      transform: scale(0.98);
    }

    &:disabled {
      cursor: not-allowed;
      opacity: 0.45;
    }

    &.stop {
      background: #344054;
    }
  }

  @media (max-width: 1280px) {
    .chat-composer {
      width: min(820px, calc(100% - 32px));
    }

    .composer-toolbar {
      grid-template-columns: 1fr;
    }

    .toolbar-center {
      justify-content: flex-start;
    }
  }
</style>
