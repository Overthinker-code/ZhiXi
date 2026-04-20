<template>
  <div class="container">
    <Breadcrumb
      :items="['menu.digitalHuman', 'menu.digitalHuman.pptToVideo']"
    />
    <div class="content">
      <div class="header">
        <div class="back-btn" @click="goBack">
          <icon-left />
          <span>返回</span>
        </div>
        <h1 class="title">PPT Studio 创作台</h1>
        <p class="subtitle">上传 PPT/PDF，快速生成高质量数字人讲解视频</p>
      </div>

      <div class="studio-workbench">
        <div class="studio-control-panel">
          <div class="panel-card">
            <h3 class="panel-title">上传课件</h3>
            <div
              class="upload-area"
              :class="{ 'drag-over': isDragOver, 'has-file': selectedFile }"
              @click="triggerUpload"
              @dragover.prevent="handleDragOver"
              @dragleave="handleDragLeave"
              @drop.prevent="handleDrop"
            >
              <input
                ref="fileInput"
                type="file"
                accept=".ppt,.pptx,.pdf"
                style="display: none"
                @change="handleFileChange"
              />
              <template v-if="!selectedFile">
                <div class="upload-icon">
                  <icon-plus :size="36" />
                </div>
                <p class="upload-text">点击或拖拽文件到此处上传</p>
                <p class="upload-hint"
                  >支持 .ppt .pptx .pdf，单文件不超过 20MB</p
                >
              </template>
              <template v-else>
                <div class="file-preview">
                  <icon-file :size="30" />
                  <div>
                    <div class="file-name">{{ selectedFile.name }}</div>
                    <div class="file-size">{{
                      formatFileSize(selectedFile.size)
                    }}</div>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <div class="panel-card" v-if="selectedFile">
            <h3 class="panel-title">视频设置</h3>
            <a-form :model="formData" layout="vertical">
              <a-form-item label="选择数字人">
                <a-select
                  v-model="formData.digitalHuman"
                  placeholder="请选择数字人"
                >
                  <a-option
                    v-for="dh in digitalHumanList"
                    :key="dh.id"
                    :value="dh.id"
                  >
                    {{ dh.name }}
                  </a-option>
                </a-select>
              </a-form-item>
              <a-form-item label="配音音色">
                <a-select v-model="formData.voice" placeholder="请选择配音">
                  <a-option
                    v-for="voice in voiceList"
                    :key="voice.id"
                    :value="voice.id"
                  >
                    {{ voice.name }}
                  </a-option>
                </a-select>
              </a-form-item>
            </a-form>
            <a-button
              type="primary"
              size="large"
              long
              :loading="isGenerating"
              @click="startGenerate"
            >
              <template #icon><icon-play-circle /></template>
              生成视频
            </a-button>
          </div>
        </div>

        <div class="studio-preview-shell">
          <div class="studio-preview-bg">
            <div class="studio-preview-canvas">
              <div class="canvas-frame">
                <template v-if="videoUrl && jobStatus.status === 'success'">
                  <video :src="videoUrl" class="studio-cover" controls />
                </template>
                <template
                  v-else-if="jobStatus.status === 'processing' || activeTaskId"
                >
                  <div class="canvas-progress">
                    <div class="canvas-progress-title">{{ jobMessage }}</div>
                    <div class="canvas-progress-value">{{ jobProgress }}%</div>
                    <a-progress
                      :percent="jobProgress"
                      :show-text="false"
                      :animation="true"
                    />
                    <div class="canvas-progress-sub">
                      任务 ID：{{ activeTaskId || '等待创建' }}
                    </div>
                  </div>
                </template>
                <template v-else>
                  <div class="canvas-waiting">
                    <icon-play-circle :size="32" />
                    <p>PPT 渲染画布</p>
                    <span>生成后将展示数字人成片封面</span>
                  </div>
                </template>
                <div v-if="isStudioRendering" class="laser-scan-line" />
              </div>
            </div>
          </div>
          <div class="status-card">
            <div class="status-card__row">
              <span>当前状态</span>
              <strong>{{ statusBadge }}</strong>
            </div>
            <div class="status-card__row">
              <span>任务消息</span>
              <strong>{{ jobMessage }}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { reactive, ref, computed } from 'vue';
  import { useRouter } from 'vue-router';
  import { Message } from '@arco-design/web-vue';
  import {
    IconLeft,
    IconPlus,
    IconFile,
    IconPlayCircle,
  } from '@arco-design/web-vue/es/icon';
  import { createPptToVideoJob } from '@/api/digital-human';
  import useDigitalHumanJob from '@/composables/useDigitalHumanJob';
  import { resolveMediaUrl } from '@/utils/mediaUrl';

  const router = useRouter();
  const fileInput = ref<HTMLInputElement>();
  const isDragOver = ref(false);
  const selectedFile = ref<File | null>(null);
  const isGenerating = ref(false);
  const isStudioRendering = ref(false);
  const videoUrl = ref('');
  const {
    activeTaskId,
    status: jobStatus,
    startPolling,
  } = useDigitalHumanJob();

  const formData = reactive({
    digitalHuman: '',
    voice: '',
  });

  const digitalHumanList = ref([
    { id: 'teacher-default', name: '默认教师形象' },
    { id: 'teacher-warm', name: '温和女教师' },
    { id: 'teacher-business', name: '商务讲师' },
  ]);

  const voiceList = ref([
    { id: 'zh-CN-YunxiNeural', name: '知性男声 Yunxi' },
    { id: 'zh-CN-XiaoxiaoNeural', name: '温和女声 Xiaoxiao' },
    { id: 'zh-CN-YunjianNeural', name: '沉稳女声 Yunjian' },
  ]);

  const jobProgress = computed(() => Number(jobStatus.value.progress || 0));
  const jobMessage = computed(() => jobStatus.value.message || '等待任务开始');
  const statusBadge = computed(() => {
    if (jobStatus.value.status === 'success') return '渲染完成';
    if (jobStatus.value.status === 'failed') return '渲染失败';
    if (jobStatus.value.status === 'processing') {
      return `${jobStatus.value.message} (${jobProgress.value}%)`;
    }
    if (activeTaskId.value) {
      return `渲染排队中 (${jobProgress.value}%)`;
    }
    return '等待上传';
  });

  const goBack = () => {
    router.back();
  };

  const triggerUpload = () => fileInput.value?.click();
  const handleDragOver = () => {
    isDragOver.value = true;
  };
  const handleDragLeave = () => {
    isDragOver.value = false;
  };
  const handleDrop = (e: DragEvent) => {
    isDragOver.value = false;
    const files = e.dataTransfer?.files;
    if (files?.length) validateAndSetFile(files[0]);
  };
  const handleFileChange = (e: Event) => {
    const target = e.target as HTMLInputElement;
    const { files } = target;
    if (files?.length) validateAndSetFile(files[0]);
  };

  const validateAndSetFile = (file: File) => {
    const validTypes = ['.ppt', '.pptx', '.pdf'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validTypes.includes(ext)) {
      Message.error('仅支持 ppt、pptx、pdf 格式文件');
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      Message.error('文件大小不能超过 20MB');
      return;
    }
    selectedFile.value = file;
    videoUrl.value = '';
    Message.success('文件上传成功');
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const startGenerate = async () => {
    if (!selectedFile.value) {
      Message.warning('请先上传课件');
      return;
    }
    if (!formData.digitalHuman || !formData.voice) {
      Message.warning('请先选择数字人和配音音色');
      return;
    }
    isGenerating.value = true;
    isStudioRendering.value = true;
    videoUrl.value = '';
    try {
      const job = await createPptToVideoJob({
        file: selectedFile.value,
        title: selectedFile.value.name,
        voice_id: formData.voice,
        digital_human_id: formData.digitalHuman,
      });
      const finalStatus = await startPolling(job.task_id);
      if (finalStatus.status === 'success' && finalStatus.video_url) {
        videoUrl.value = resolveMediaUrl(finalStatus.video_url);
        Message.success('PPT 数字人视频渲染完成');
      } else if (finalStatus.status === 'failed') {
        Message.error(finalStatus.message || 'PPT 数字人渲染失败');
      }
    } catch (error: any) {
      Message.error(error?.message || '提交 PPT 数字人任务失败');
    } finally {
      isGenerating.value = false;
      isStudioRendering.value = false;
    }
  };
</script>

<script lang="ts">
  export default {
    name: 'PptToVideo',
  };
</script>

<style scoped lang="less">
  .container {
    padding: 0 20px 20px;
  }
  .content {
    max-width: 1280px;
    margin: 0 auto;
  }
  .header {
    text-align: center;
    padding: 20px 0 30px;
    position: relative;
    .back-btn {
      position: absolute;
      left: 0;
      top: 20px;
      display: flex;
      align-items: center;
      gap: 4px;
      color: var(--color-text-3);
      cursor: pointer;
    }
    .title {
      font-size: 26px;
      font-weight: 600;
      color: var(--color-text-1);
      margin-bottom: 8px;
    }
    .subtitle {
      font-size: 14px;
      color: var(--color-text-3);
    }
  }
  .studio-workbench {
    display: flex;
    gap: 24px;
  }
  .studio-control-panel {
    width: 40%;
    min-width: 380px;
  }
  .panel-card {
    background: #fff;
    border-radius: 14px;
    padding: 24px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    margin-bottom: 20px;
  }
  .panel-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--color-text-1);
    margin-bottom: 16px;
  }
  .upload-area {
    border: 2px dashed var(--color-border-2);
    border-radius: 12px;
    padding: 40px 20px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    &.drag-over {
      border-color: rgb(var(--primary-6));
      background: rgb(var(--primary-1));
    }
    &.has-file {
      border-style: solid;
      border-color: rgb(var(--success-6));
    }
  }
  .upload-icon {
    color: rgb(var(--primary-6));
    margin-bottom: 12px;
  }
  .upload-text {
    font-size: 16px;
    color: var(--color-text-1);
    margin-bottom: 8px;
  }
  .upload-hint {
    font-size: 13px;
    color: var(--color-text-3);
  }
  .file-preview {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
  }
  .file-name {
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text-1);
  }
  .file-size {
    font-size: 12px;
    color: var(--color-text-3);
  }
  .studio-preview-shell {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .studio-preview-bg {
    flex: 1;
    background: radial-gradient(
        circle at 20% 20%,
        rgba(59, 130, 246, 0.18),
        transparent 35%
      ),
      linear-gradient(180deg, #0f172a 0%, #111827 100%);
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 20px 45px rgba(15, 23, 42, 0.22);
  }
  .studio-preview-canvas {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .canvas-frame {
    width: 100%;
    height: 100%;
    min-height: 420px;
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    background: rgba(15, 23, 42, 0.6);
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .canvas-waiting {
    text-align: center;
    color: #cbd5e1;
    p {
      margin: 12px 0 8px;
      font-size: 18px;
      font-weight: 600;
    }
    span {
      font-size: 14px;
      color: #94a3b8;
    }
  }
  .canvas-progress {
    width: min(420px, 72%);
    display: grid;
    gap: 16px;
    padding: 24px;
    border-radius: 16px;
    background: rgba(15, 23, 42, 0.72);
    border: 1px solid rgba(56, 189, 248, 0.24);
    color: #e2e8f0;
  }
  .canvas-progress-title {
    font-size: 20px;
    font-weight: 600;
  }
  .canvas-progress-value {
    font-size: 48px;
    font-weight: 700;
    color: #38bdf8;
  }
  .canvas-progress-sub {
    font-size: 12px;
    color: #94a3b8;
    word-break: break-all;
  }
  .laser-scan-line {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #38bdf8, transparent);
    box-shadow: 0 0 18px rgba(56, 189, 248, 0.9);
    animation: laser-scan 1.4s linear infinite;
  }
  .studio-cover {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .status-card {
    display: grid;
    gap: 10px;
    padding: 16px 18px;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.9);
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  }
  .status-card__row {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    color: #334155;
    strong {
      color: #0f172a;
      text-align: right;
    }
  }
  @keyframes laser-scan {
    0% {
      top: 0;
    }
    100% {
      top: calc(100% - 2px);
    }
  }
  @media (max-width: @screen-lg) {
    .studio-workbench {
      flex-direction: column;
    }
    .studio-control-panel {
      width: 100%;
      min-width: 0;
    }
  }
</style>
