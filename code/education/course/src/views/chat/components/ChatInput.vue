<script setup>
  import { Close, Document, Plus, Picture, UploadFilled } from '@element-plus/icons-vue';
  import { computed, ref, watch } from 'vue';
  import { ElMessage } from 'element-plus';

  const inputValue = ref('');
  const fileList = ref([]);
  const menuOpen = ref(false);
  const dragActive = ref(false);
  const webSearchEnabled = ref(false);
  const deepThinkEnabled = ref(false);
  const activeMode = ref('chat');
  const fileInputRef = ref(null);
  const imageInputRef = ref(null);
  const codeInputRef = ref(null);

  const props = defineProps({
    loading: {
      type: Boolean,
      default: false,
    },
    initialText: {
      type: String,
      default: '',
    },
  });

  const emit = defineEmits(['send', 'stop']);

  const acceptedDocumentTypes = [
    '.pdf',
    '.doc',
    '.docx',
    '.txt',
    '.md',
    '.markdown',
    '.ppt',
    '.pptx',
  ];
  const acceptedCodeTypes = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.sql'];
  const acceptedExtensions = [...acceptedDocumentTypes, ...acceptedCodeTypes];

  const canSend = computed(
    () => (inputValue.value.trim() || fileList.value.length > 0) && !props.loading
  );

  const isImageFile = (file) => file.type?.startsWith('image/');
  const fileExt = (name = '') => {
    const dot = name.lastIndexOf('.');
    return dot >= 0 ? name.slice(dot).toLowerCase() : '';
  };
  const isDocumentFile = (file) => acceptedDocumentTypes.includes(fileExt(file.name));
  const isCodeFile = (file) => acceptedCodeTypes.includes(fileExt(file.name));

  const formatBytes = (size) => {
    if (!size) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1);
    const value = size / 1024 ** index;
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[index]}`;
  };

  const triggerFileInput = (kind) => {
    menuOpen.value = false;
    if (kind === 'image') imageInputRef.value?.click();
    else if (kind === 'code') codeInputRef.value?.click();
    else fileInputRef.value?.click();
  };

  const normalizeFile = (file) => ({
    name: file.name,
    url: URL.createObjectURL(file),
    type: isImageFile(file) ? 'image' : isCodeFile(file) ? 'code' : 'file',
    size: file.size,
    raw: file,
  });

  const addFiles = (files) => {
    const currentImages = fileList.value.filter((item) => item.type === 'image').length;
    const currentDocs = fileList.value.filter((item) => item.type !== 'image').length;
    let nextImages = currentImages;
    let nextDocs = currentDocs;
    const accepted = [];
    Array.from(files || []).forEach((file) => {
      if (isImageFile(file)) {
        if (nextImages >= 3) {
          ElMessage.warning('图片最多同时上传 3 张');
          return;
        }
        nextImages += 1;
        accepted.push(file);
        return;
      }
      if (!isDocumentFile(file) && !isCodeFile(file)) {
        ElMessage.warning(`暂不支持 ${file.name} 的文件类型`);
        return;
      }
      if (nextDocs >= 1) {
        ElMessage.warning('本轮对话先挂载 1 个主文档或代码文件');
        return;
      }
      nextDocs += 1;
      accepted.push(file);
    });
    fileList.value.push(...accepted.map(normalizeFile));
  };

  const handleNativeFileChange = (event) => {
    addFiles(event.target.files);
    event.target.value = '';
  };

  const handleDrop = (event) => {
    event.preventDefault();
    dragActive.value = false;
    addFiles(event.dataTransfer?.files || []);
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    dragActive.value = true;
  };

  const handleDragLeave = (event) => {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      dragActive.value = false;
    }
  };

  const handleFileRemove = (file) => {
    const index = fileList.value.findIndex((item) => item.url === file.url);
    if (index !== -1) {
      URL.revokeObjectURL(fileList.value[index].url);
      fileList.value.splice(index, 1);
    }
  };

  const handleSend = () => {
    if (!canSend.value) return;
    const text = inputValue.value.trim();
    const selectedTools = [];
    if (webSearchEnabled.value) selectedTools.push('web_search');
    if (deepThinkEnabled.value) selectedTools.push('deep_thinking');
    if (activeMode.value === 'digital_human_explain') {
      selectedTools.push('digital_human_explain');
    }

    emit('send', {
      text,
      files: fileList.value,
      options: {
        useWebSearch: webSearchEnabled.value,
        deepThinking: deepThinkEnabled.value,
        mode: activeMode.value,
        gradingMode: activeMode.value === 'exercise_grading',
        digitalHumanExplain: activeMode.value === 'digital_human_explain',
        activeTools: selectedTools,
        toolMode: activeMode.value === 'chat' ? undefined : activeMode.value,
      },
    });

    inputValue.value = '';
    fileList.value = [];
    activeMode.value = 'chat';
    menuOpen.value = false;
  };

  const handleNewline = (event) => {
    event.preventDefault();
    inputValue.value += '\n';
  };

  watch(
    () => props.initialText,
    (value) => {
      const text = String(value || '').trim();
      if (!text) return;
      if (inputValue.value.trim() || fileList.value.length > 0) return;
      inputValue.value = text;
    },
    { immediate: true }
  );
</script>

<template>
  <div
    class="chat-input-wrapper"
    :class="{ 'is-dragging': dragActive }"
    @drop="handleDrop"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
  >
    <div v-if="dragActive" class="drag-layer">
      <el-icon><UploadFilled /></el-icon>
      <span>释放以上传到本轮对话</span>
    </div>

    <input
      ref="fileInputRef"
      hidden
      type="file"
      :accept="acceptedDocumentTypes.join(',')"
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
    <input
      ref="codeInputRef"
      hidden
      type="file"
      :accept="acceptedCodeTypes.join(',')"
      @change="handleNativeFileChange"
    />

    <div v-if="fileList.length > 0" class="preview-area">
      <div v-for="file in fileList" :key="file.url" class="preview-item">
        <div v-if="file.type === 'image'" class="image-preview">
          <img :src="file.url" :alt="file.name" />
          <span class="status-badge">发送后联合识别</span>
          <div class="remove-btn" @click="handleFileRemove(file)">
            <el-icon><Close /></el-icon>
          </div>
        </div>
        <div v-else class="file-preview">
          <el-icon><Document /></el-icon>
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ formatBytes(file.size) }}</span>
          <span v-if="file.type === 'code'" class="status-badge">代码上下文</span>
          <span v-else class="status-badge">发送后挂载</span>
          <div class="remove-btn" @click="handleFileRemove(file)">
            <el-icon><Close /></el-icon>
          </div>
        </div>
      </div>
    </div>

    <el-input
      v-model="inputValue"
      type="textarea"
      :autosize="{ minRows: 1, maxRows: 6 }"
      placeholder="输入消息，Enter 发送，Shift + Enter 换行；也可以拖入图片或文档"
      resize="none"
      @keydown.enter.exact.prevent="handleSend"
      @keydown.enter.shift="handleNewline"
    />

    <div class="button-group">
      <div class="add-menu-wrap">
        <button
          class="action-btn add-btn"
          type="button"
          aria-label="添加素材"
          @click="menuOpen = !menuOpen"
        >
          <el-icon><Plus /></el-icon>
        </button>
        <div v-if="menuOpen" class="add-menu">
          <button type="button" @click="triggerFileInput('file')">
            <el-icon><Document /></el-icon>
            <span>上传文件</span>
          </button>
          <button type="button" @click="triggerFileInput('image')">
            <el-icon><Picture /></el-icon>
            <span>上传图片</span>
          </button>
          <button type="button" @click="triggerFileInput('code')">
            <span class="code-icon">〈〉</span>
            <span>导入代码</span>
          </button>
        </div>
      </div>

      <div class="divider"></div>
      <button
        :class="['tool-btn', { active: webSearchEnabled }]"
        type="button"
        @click="webSearchEnabled = !webSearchEnabled"
      >
        联网搜索
      </button>
      <button
        :class="['tool-btn', { active: deepThinkEnabled }]"
        type="button"
        @click="deepThinkEnabled = !deepThinkEnabled"
      >
        深度思考
      </button>

      <div class="mode-control" aria-label="回答模式">
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
        <button
          :class="{ active: activeMode === 'digital_human_explain' }"
          type="button"
          @click="activeMode = 'digital_human_explain'"
        >
          数字人
        </button>
      </div>

      <button class="action-btn send-btn" :disabled="!canSend" @click="handleSend">
        <img src="@/assets/photo/发送.png" alt="send" />
      </button>
      <button v-if="props.loading" class="action-btn stop-btn" @click="emit('stop')">
        停止
      </button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
  .chat-input-wrapper {
    --input-border: rgba(99, 102, 241, 0.18);
    --input-bg: rgba(255, 255, 255, 0.96);
    --input-action-bg: rgba(245, 243, 255, 0.9);
    --input-action-hover: rgba(99, 102, 241, 0.1);
    --input-send-start: #6366f1;
    --input-send-end: #4f46e5;
    position: relative;
    padding: 0.75rem;
    border-radius: 18px;
    border: 1px solid var(--input-border);
    background: var(--input-bg);
    backdrop-filter: blur(8px);
    box-shadow: 0 14px 24px rgba(15, 23, 42, 0.11);
    transition: box-shadow 0.2s ease, border-color 0.2s ease;

    &.is-dragging {
      border-color: rgba(99, 102, 241, 0.45);
      box-shadow: 0 18px 34px rgba(99, 102, 241, 0.16);
    }

    &:focus-within {
      border-color: rgba(99, 102, 241, 0.34);
      box-shadow: 0 16px 30px rgba(15, 23, 42, 0.14);
    }

    .drag-layer {
      position: absolute;
      inset: 6px;
      z-index: 6;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      border: 1px dashed rgba(99, 102, 241, 0.55);
      border-radius: 14px;
      background: rgba(248, 247, 255, 0.94);
      color: #4f46e5;
      font-size: 0.92rem;
      font-weight: 700;
      pointer-events: none;
    }

    .preview-area {
      margin-bottom: 0.55rem;
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .preview-item {
      position: relative;
      border-radius: 10px;
      overflow: hidden;
      border: 1px solid rgba(15, 23, 42, 0.08);
      background: #fff;
    }

    .image-preview {
      width: 88px;
      height: 88px;
      position: relative;

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
    }

    .file-preview {
      min-height: 44px;
      padding: 0 0.55rem;
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      background: #f8fbff;
    }

    .file-name {
      max-width: 150px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #1a2f4d;
      font-size: 0.83rem;
    }

    .file-size {
      color: #6a7f9e;
      font-size: 0.74rem;
    }

    .status-badge {
      border-radius: 999px;
      padding: 0.12rem 0.38rem;
      background: rgba(99, 102, 241, 0.1);
      color: #4f46e5;
      font-size: 0.68rem;
      font-weight: 700;
      white-space: nowrap;
    }

    .image-preview .status-badge {
      position: absolute;
      left: 5px;
      bottom: 5px;
      background: rgba(15, 23, 42, 0.68);
      color: #fff;
    }

    .remove-btn {
      position: absolute;
      top: 4px;
      right: 4px;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: rgba(15, 23, 42, 0.58);
      color: #fff;
      cursor: pointer;
      transition: background 0.2s ease;

      &:hover {
        background: rgba(15, 23, 42, 0.8);
      }
    }

    :deep(.el-textarea__inner) {
      border: none;
      box-shadow: none;
      border-radius: 12px;
      padding: 0.7rem 0.8rem;
      background: #fbfaff;
      color: #132743;
      font-size: 0.95rem;
      line-height: 1.55;

      &::placeholder {
        color: #7c8ea8;
      }
    }

    .button-group {
      margin-top: 0.55rem;
      margin-left: auto;
      width: fit-content;
      padding: 0.3rem 0.45rem;
      border-radius: 999px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      background: var(--input-action-bg);
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    .add-menu-wrap {
      position: relative;
    }

    .add-menu {
      position: absolute;
      left: 0;
      bottom: calc(100% + 10px);
      z-index: 10;
      width: 172px;
      padding: 0.45rem;
      border-radius: 12px;
      border: 1px solid #dbe5f2;
      background: #fff;
      box-shadow: 0 14px 28px rgba(15, 23, 42, 0.16);

      button {
        width: 100%;
        height: 36px;
        border: none;
        border-radius: 8px;
        background: transparent;
        color: #243a55;
        display: flex;
        align-items: center;
        gap: 0.55rem;
        padding: 0 0.55rem;
        cursor: pointer;
        font-size: 0.86rem;
        font-weight: 650;
        text-align: left;

        &:hover {
          background: #f1f6ff;
        }
      }
    }

    .code-icon {
      font-size: 0.8rem;
      font-weight: 900;
    }

    .divider {
      width: 1px;
      height: 1rem;
      background: linear-gradient(
        180deg,
        transparent,
        rgba(90, 107, 132, 0.38),
        transparent
      );
    }

    .action-btn,
    .tool-btn,
    .mode-control button {
      height: 1.8rem;
      border: none;
      border-radius: 999px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
      white-space: nowrap;
    }

    .action-btn {
      width: 1.8rem;
      background: transparent;

      img {
        width: 1rem;
        height: 1rem;
      }

      &:hover {
        background: var(--input-action-hover);
      }

      &.send-btn {
        width: 2rem;
        height: 2rem;
        background: linear-gradient(
          135deg,
          var(--input-send-start),
          var(--input-send-end)
        );
        box-shadow: 0 8px 16px rgba(99, 102, 241, 0.26);

        img {
          width: 1.15rem;
          height: 1.15rem;
        }

        &:disabled {
          opacity: 0.55;
          cursor: not-allowed;
          box-shadow: none;
        }
      }

      &.stop-btn {
        width: auto;
        min-width: 2.5rem;
        padding: 0 0.65rem;
        background: #fff4f2;
        color: #c73e1d;
        border: 1px solid rgba(199, 62, 29, 0.25);
        font-size: 0.74rem;
        font-weight: 700;
      }
    }

    .tool-btn {
      padding: 0 0.7rem;
      background: transparent;
      color: #38516f;
      font-size: 0.78rem;
      font-weight: 700;

      &:hover,
      &.active {
        background: rgba(99, 102, 241, 0.1);
        color: #4f46e5;
      }
    }

    .mode-control {
      display: inline-flex;
      align-items: center;
      gap: 2px;
      padding: 2px;
      border-radius: 999px;
      background: rgba(99, 102, 241, 0.08);

      button {
        padding: 0 0.58rem;
        background: transparent;
        color: #53657e;
        font-size: 0.76rem;
        font-weight: 750;

        &.active {
          background: #fff;
          color: #4f46e5;
          box-shadow: 0 2px 7px rgba(99, 102, 241, 0.14);
        }
      }
    }
  }

  @media (max-width: 760px) {
    .chat-input-wrapper {
      padding: 0.65rem;
      border-radius: 14px;

      .button-group {
        width: 100%;
        flex-wrap: wrap;
        justify-content: flex-end;
      }
    }
  }
</style>
