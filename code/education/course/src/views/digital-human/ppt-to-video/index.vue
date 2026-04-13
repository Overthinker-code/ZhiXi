<template>
  <div class="container">
    <Breadcrumb :items="['menu.digitalHuman', 'menu.digitalHuman.pptToVideo']" />
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
                <p class="upload-hint">支持 .ppt .pptx .pdf，单文件不超过 20MB</p>
              </template>
              <template v-else>
                <div class="file-preview">
                  <icon-file :size="30" />
                  <div>
                    <div class="file-name">{{ selectedFile.name }}</div>
                    <div class="file-size">{{ formatFileSize(selectedFile.size) }}</div>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <div class="panel-card" v-if="selectedFile">
            <h3 class="panel-title">视频设置</h3>
            <a-form :model="formData" layout="vertical">
              <a-form-item label="选择数字人">
                <a-select v-model="formData.digitalHuman" placeholder="请选择数字人">
                  <a-option v-for="dh in digitalHumanList" :key="dh.id" :value="dh.id">
                    {{ dh.name }}
                  </a-option>
                </a-select>
              </a-form-item>
              <a-form-item label="配音音色">
                <a-select v-model="formData.voice" placeholder="请选择配音">
                  <a-option v-for="voice in voiceList" :key="voice.id" :value="voice.id">
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
                <template v-if="!studioResultReady">
                  <div class="canvas-waiting">
                    <icon-play-circle :size="32" />
                    <p>PPT 渲染画布</p>
                    <span>生成后将展示数字人成片封面</span>
                  </div>
                </template>
                <template v-else>
                  <img :src="studioCoverImage" class="studio-cover" alt="数字人封面" />
                  <button type="button" class="play-glass-btn">
                    <icon-play-arrow :size="26" />
                  </button>
                </template>
                <div v-if="isStudioRendering" class="laser-scan-line" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { reactive, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { Message } from '@arco-design/web-vue';
  import studioCover from '@/assets/digital-human/studio-cover.png';
  import {
    IconLeft,
    IconPlus,
    IconFile,
    IconPlayCircle,
    IconPlayArrow,
  } from '@arco-design/web-vue/es/icon';

  const router = useRouter();
  const fileInput = ref<HTMLInputElement>();
  const isDragOver = ref(false);
  const selectedFile = ref<File | null>(null);
  const isGenerating = ref(false);
  const isStudioRendering = ref(false);
  const studioResultReady = ref(false);
  const studioCoverImage = ref(studioCover);

  const formData = reactive({
    digitalHuman: '',
    voice: '',
  });

  const digitalHumanList = ref([
    { id: '1', name: '小明老师' },
    { id: '2', name: '小红老师' },
    { id: '3', name: '商务男士' },
    { id: '4', name: '职业女性' },
  ]);

  const voiceList = ref([
    { id: '1', name: '标准男声' },
    { id: '2', name: '标准女声' },
    { id: '3', name: '温柔女声' },
    { id: '4', name: '磁性男声' },
  ]);

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
    const files = target.files;
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
    Message.success('文件上传成功');
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const startGenerate = () => {
    if (!formData.digitalHuman || !formData.voice) {
      Message.warning('请先选择数字人和配音音色');
      return;
    }
    isGenerating.value = true;
    isStudioRendering.value = true;
    studioResultReady.value = false;
    setTimeout(() => {
      isGenerating.value = false;
      isStudioRendering.value = false;
      studioResultReady.value = true;
      Message.success('视频生成任务已提交，请在“我的数字人”中查看进度');
    }, 3000);
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
    padding: 20px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 8px 28px rgba(15, 23, 42, 0.08);
    margin-bottom: 14px;
  }
  .panel-title {
    font-size: 15px;
    margin: 0 0 12px;
    color: #0f172a;
  }
  .upload-area {
    border: 1px dashed rgba(99, 102, 241, 0.45);
    border-radius: 12px;
    padding: 26px 16px;
    text-align: center;
    cursor: pointer;
    background: #f8fafc;
    &.drag-over,
    &:hover {
      border-color: #6366f1;
      background: #eef2ff;
    }
  }
  .upload-icon {
    color: #6366f1;
  }
  .upload-text {
    margin: 8px 0 4px;
    color: #0f172a;
    font-size: 14px;
  }
  .upload-hint {
    margin: 0;
    color: #64748b;
    font-size: 12px;
  }
  .file-preview {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    color: #334155;
  }
  .file-name {
    font-size: 13px;
    font-weight: 600;
  }
  .file-size {
    font-size: 12px;
    color: #64748b;
  }
  .studio-preview-shell {
    width: 60%;
    min-width: 420px;
  }
  .studio-preview-bg {
    height: 100%;
    min-height: 600px;
    border-radius: 18px;
    background-color: #0f172a;
    background-image:
      linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
      linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
    background-size: 26px 26px, 26px 26px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    box-shadow: inset 0 0 40px rgba(15, 23, 42, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 22px;
  }
  .studio-preview-canvas {
    width: 100%;
    display: flex;
    justify-content: center;
  }
  .canvas-frame {
    width: min(100%, 760px);
    aspect-ratio: 16 / 9;
    border-radius: 16px;
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.95), rgba(2, 6, 23, 0.98));
    border: 1px solid rgba(59, 130, 246, 0.35);
    overflow: hidden;
    position: relative;
  }
  .canvas-waiting {
    height: 100%;
    color: #93c5fd;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    p {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
    }
    span {
      font-size: 12px;
      color: #94a3b8;
    }
  }
  .studio-cover {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .play-glass-btn {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 82px;
    height: 82px;
    border-radius: 50%;
    border: 1px solid rgba(255, 255, 255, 0.45);
    background: rgba(255, 255, 255, 0.2);
    color: #fff;
    backdrop-filter: blur(10px);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }
  .laser-scan-line {
    position: absolute;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #38bdf8, transparent);
    box-shadow: 0 0 18px rgba(56, 189, 248, 0.8);
    animation: studio-scan 1.2s linear infinite;
  }
  @keyframes studio-scan {
    0% {
      top: 0%;
    }
    100% {
      top: calc(100% - 2px);
    }
  }

  @media (max-width: @screen-lg) {
    .studio-workbench {
      flex-direction: column;
    }
    .studio-control-panel,
    .studio-preview-shell {
      width: 100%;
      min-width: 0;
    }
  }
</style>
