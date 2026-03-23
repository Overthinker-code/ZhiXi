<script setup lang="ts">
  import { ref, computed, watch } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import {
    uploadReferenceFileWithPreview,
    commitReferenceFile,
    cancelReferenceFile,
    type StreamPreviewEvent,
  } from '@/api/rag';

  interface Props {
    visible: boolean;
    isAdmin?: boolean;
  }

  interface Emits {
    (e: 'update:visible', value: boolean): void;
    (e: 'success'): void;
  }

  const props = defineProps<Props>();
  const emit = defineEmits<Emits>();

  const selectedFile = ref<File | null>(null);
  const uploadScope = ref<'system' | 'personal'>('personal');
  const isUploading = ref(false);
  const currentStage = ref<string>('');
  const stages = ref<Record<string, { status: string; message: string }>>({
    saving: { status: 'pending', message: '保存临时文件' },
    parsed: { status: 'pending', message: '文档解析' },
    splitting: { status: 'pending', message: '文档切分' },
    ready: { status: 'pending', message: '等待确认' },
    committing: { status: 'pending', message: '写入向量库' },
    completed: { status: 'completed', message: '完成' },
  });

  const textPreview = ref('');
  const chunksTotal = ref(0);
  const chunksPreview = ref<
    Array<{ chunk_id: number; text_preview: string; length: number }>
  >([]);
  const fileId = ref<string>('');
  const fileSize = ref(0);
  const createdAt = ref('');

  const canUpload = computed(() => !!selectedFile.value && !isUploading.value);
  const isPreviewReady = computed(() => currentStage.value === 'ready');

  watch(
    () => props.visible,
    (visible) => {
      if (!visible) return;
      uploadScope.value = props.isAdmin ? 'system' : 'personal';
    },
    { immediate: true }
  );

  const formatBytes = (bytes: number) => {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(
      Math.floor(Math.log(bytes) / Math.log(1024)),
      units.length - 1
    );
    const value = bytes / 1024 ** index;
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[index]}`;
  };

  const onFileChange = (e: Event) => {
    const input = e.target as HTMLInputElement;
    selectedFile.value = input.files?.[0] || null;
  };

  const handleClose = () => {
    isUploading.value = false;
    currentStage.value = '';
    selectedFile.value = null;
    uploadScope.value = props.isAdmin ? 'system' : 'personal';
    textPreview.value = '';
    chunksTotal.value = 0;
    chunksPreview.value = [];
    fileId.value = '';
    fileSize.value = 0;
    createdAt.value = '';
    Object.keys(stages.value).forEach((key) => {
      stages.value[key].status = 'pending';
    });
    emit('update:visible', false);
  };

  const handleUpload = async () => {
    if (!selectedFile.value) {
      Message.warning('请选择文件');
      return;
    }

    isUploading.value = true;
    currentStage.value = 'saving';

    // Reset stages
    Object.keys(stages.value).forEach((key) => {
      stages.value[key] = {
        status: 'pending',
        message: stages.value[key].message,
      };
    });

    try {
      await uploadReferenceFileWithPreview(
        selectedFile.value,
        (event: StreamPreviewEvent) => {
          currentStage.value = event.stage;

          // Update stage status
          if (event.stage === 'saved') {
            stages.value.saving.status = 'success';
            fileId.value = event.file_id || '';
            fileSize.value = event.file_size || 0;
            createdAt.value = event.created_at || '';
          } else if (event.stage === 'parsed') {
            stages.value.parsed.status = 'success';
            textPreview.value = event.text_preview || '';
          } else if (event.stage === 'ready') {
            stages.value.splitting.status = 'success';
            stages.value.ready.status = 'pending';
            chunksTotal.value = event.chunks_total || 0;
            chunksPreview.value = event.chunks_preview || [];
          } else if (event.stage === 'error') {
            throw new Error(event.message || 'Upload error');
        }
        },
        800,
        5,
        300,
        uploadScope.value
      );
    } catch (error: any) {
      Message.error(error?.message || 'Upload failed');
      isUploading.value = false;
    }
  };

  const handleConfirm = async () => {
    if (!fileId.value) return;

    stages.value.ready.status = 'loading';
    stages.value.committing.status = 'loading';

    try {
      await commitReferenceFile(fileId.value);
      stages.value.committing.status = 'success';
      stages.value.completed.status = 'success';

      Message.success('Upload completed successfully');
      handleClose();
      emit('success');
    } catch (error: any) {
      Message.error(error?.message || 'Commit failed');
      stages.value.committing.status = 'error';
    }
  };

  const handleOkClick = async () => {
    if (isPreviewReady.value) {
      await handleConfirm();
      return false;
    }
    if (canUpload.value) {
      await handleUpload();
      return false;
    }
    return false;
  };

  const handleCancel = async () => {
    if (!fileId.value) {
      handleClose();
      return;
    }

    try {
      await cancelReferenceFile(fileId.value);
      Message.success('Upload cancelled');
      handleClose();
    } catch (error: any) {
      Message.error(error?.message || 'Cancel failed');
    }
  };
</script>

<template>
  <a-modal
    :visible="visible"
    title="上传参考文件"
    width="600px"
    @update:visible="handleClose"
    :ok-button-props="{ disabled: !isPreviewReady && !canUpload }"
    :ok-text="isPreviewReady ? '确认上传' : '开始上传'"
    :cancel-button-props="{ disabled: !isPreviewReady && isUploading }"
    :cancel-text="isPreviewReady ? '取消' : '关闭'"
    :on-before-ok="handleOkClick"
    @cancel="handleCancel"
    :mask-closable="false"
    :closable="false"
  >
    <div class="upload-container">
      <!-- File Selection -->
      <div v-if="!isUploading && !isPreviewReady" class="file-selection">
        <div v-if="props.isAdmin" class="scope-selection">
          <span class="scope-label">上传范围：</span>
          <a-radio-group v-model="uploadScope" type="button" size="small">
            <a-radio value="system">系统资料</a-radio>
            <a-radio value="personal">个人资料</a-radio>
          </a-radio-group>
        </div>
        <div class="file-input-wrapper">
          <input
            type="file"
            accept=".doc,.docx,.pdf,.ppt,.pptx,.md,.markdown"
            @change="onFileChange"
            class="file-input"
          />
          <span class="file-name">{{
            selectedFile?.name ||
            '选择文件 (.doc, .docx, .pdf, .ppt, .pptx, .md, .markdown)'
          }}</span>
        </div>
      </div>

      <!-- Processing Stages -->
      <div v-if="isUploading || isPreviewReady" class="processing-stages">
        <div
          v-for="(stage, stageKey) in stages"
          :key="stageKey"
          class="stage-item"
          :class="stage.status"
        >
          <div class="stage-header">
            <div class="stage-icon">
              <span v-if="stage.status === 'loading'" class="loading-spinner">
                ⟳
              </span>
              <span v-else-if="stage.status === 'success'" class="success-icon">
                ✓
              </span>
              <span v-else-if="stage.status === 'error'" class="error-icon">
                ✕
              </span>
              <span v-else class="pending-circle" />
            </div>
            <span class="stage-message">{{ stage.message }}</span>
          </div>
        </div>
      </div>

      <!-- Text Preview -->
      <div v-if="textPreview && isPreviewReady" class="preview-section">
        <div class="preview-title">文本预览 (前 800 字符)</div>
        <div class="text-preview">
          {{ textPreview }}
          <span v-if="textPreview.length >= 800">...</span>
        </div>
      </div>

      <!-- Chunks Preview -->
      <div
        v-if="chunksPreview.length > 0 && isPreviewReady"
        class="chunks-section"
      >
        <div class="chunks-info">
          共 <strong>{{ chunksTotal }}</strong> 个分片，显示前
          <strong>{{ chunksPreview.length }}</strong> 个
        </div>
        <div class="chunks-list">
          <div
            v-for="chunk in chunksPreview"
            :key="chunk.chunk_id"
            class="chunk-item"
          >
            <div class="chunk-header">
              <span class="chunk-id">分片 #{{ chunk.chunk_id }}</span>
              <span class="chunk-length">{{ chunk.length }} 字符</span>
            </div>
            <div class="chunk-content">
              {{ chunk.text_preview }}
              <span v-if="chunk.text_preview.length >= 300">...</span>
            </div>
          </div>
        </div>
      </div>

      <!-- File Info -->
      <div v-if="isPreviewReady" class="file-info">
        <div class="info-item">
          <span class="label">文件大小:</span>
          <span class="value">{{ formatBytes(fileSize) }}</span>
        </div>
        <div class="info-item">
          <span class="label">创建时间:</span>
          <span class="value">{{ new Date(createdAt).toLocaleString() }}</span>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<style scoped lang="scss">
  .upload-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .file-selection {
    padding: 20px;
    background: #f5f5f5;
    border-radius: 4px;

    .scope-selection {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;

      .scope-label {
        color: #595959;
        font-size: 14px;
      }
    }

    .file-input-wrapper {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      border: 2px dashed #d9d9d9;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.3s;

      &:hover {
        border-color: #595959;
        background: #f0f0f0;
      }

      .file-input {
        position: absolute;
        width: 100%;
        height: 100%;
        opacity: 0;
        cursor: pointer;
      }

      .file-name {
        cursor: pointer;
        color: #595959;
        font-size: 14px;
      }
    }
  }

  .processing-stages {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .stage-item {
      display: flex;
      align-items: center;
      padding: 12px;
      border-radius: 4px;
      background: #f5f5f5;
      transition: all 0.3s;

      &.success {
        background: #f6ffed;
        border-left: 4px solid #52c41a;
      }

      &.loading {
        background: #e6f7ff;
        border-left: 4px solid #1890ff;
      }

      &.error {
        background: #fff1f0;
        border-left: 4px solid #ff4d4f;
      }

      .stage-header {
        display: flex;
        align-items: center;
        gap: 12px;
        width: 100%;

        .stage-icon {
          flex-shrink: 0;
          width: 24px;
          height: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;

          .pending-circle {
            width: 8px;
            height: 8px;
            background: #d9d9d9;
            border-radius: 50%;
          }

          .loading-spinner {
            font-size: 14px;
            color: #1890ff;
            animation: spin 1s linear infinite;
          }

          .success-icon {
            font-size: 14px;
            color: #52c41a;
          }

          .error-icon {
            font-size: 14px;
            color: #ff4d4f;
          }
        }

        .stage-message {
          font-size: 14px;
          color: #262626;
        }
      }
    }
  }

  .preview-section {
    padding: 12px;
    background: #fafafa;
    border-radius: 4px;

    .preview-title {
      font-size: 14px;
      font-weight: 500;
      margin-bottom: 8px;
      color: #262626;
    }

    .text-preview {
      font-size: 12px;
      color: #595959;
      line-height: 1.5;
      max-height: 120px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-wrap: break-word;
      padding: 8px;
      background: #fff;
      border-radius: 2px;
    }
  }

  .chunks-section {
    .chunks-info {
      font-size: 13px;
      color: #595959;
      margin-bottom: 12px;
    }

    .chunks-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 250px;
      overflow-y: auto;

      .chunk-item {
        padding: 10px;
        background: #fafafa;
        border-left: 3px solid #1890ff;
        border-radius: 2px;

        .chunk-header {
          display: flex;
          justify-content: space-between;
          font-size: 12px;
          font-weight: 500;
          color: #262626;
          margin-bottom: 6px;

          .chunk-id {
            color: #1890ff;
          }

          .chunk-length {
            color: #8c8c8c;
          }
        }

        .chunk-content {
          font-size: 12px;
          color: #595959;
          line-height: 1.4;
          max-height: 60px;
          overflow: hidden;
          text-overflow: ellipsis;
          display: -webkit-box;
          -webkit-line-clamp: 3;
          line-clamp: 3;
          -webkit-box-orient: vertical;
        }
      }
    }
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  .file-info {
    padding: 12px;
    background: #f5f5f5;
    border-radius: 4px;
    font-size: 13px;

    .info-item {
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;

      .label {
        color: #8c8c8c;
        font-weight: 500;
      }

      .value {
        color: #262626;
      }
    }
  }
</style>
