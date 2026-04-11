<template>
  <div class="container">
    <Breadcrumb :items="['menu.digitalHuman', 'menu.digitalHuman.pptToVideo']" />
    <div class="content">
      <!-- 头部 -->
      <div class="header">
        <div class="back-btn" @click="goBack">
          <icon-left />
          <span>返回</span>
        </div>
        <h1 class="title">
          <icon-star-fill class="star-icon" />
          从PPT开始创作
          <icon-star-fill class="star-icon" />
        </h1>
        <p class="subtitle">上传PPT或PDF作为视频素材进行创作</p>
      </div>

      <!-- 上传区域 -->
      <div class="upload-section">
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
              <icon-plus :size="40" />
            </div>
            <p class="upload-text">点击或拖拽文件到此处上传</p>
            <p class="upload-hint">
              <span>1.仅支持ppt、pptx、pdf</span>
              <span class="divider">|</span>
              <span>2.限制20MB以内</span>
            </p>
          </template>
          
          <template v-else>
            <div class="file-preview">
              <div class="file-icon">
                <icon-file :size="48" />
              </div>
              <div class="file-info">
                <p class="file-name">{{ selectedFile.name }}</p>
                <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
              </div>
              <div class="file-actions">
                <a-button type="text" status="danger" @click.stop="removeFile">
                  <template #icon><icon-delete /></template>
                </a-button>
              </div>
            </div>
          </template>
        </div>

        <!-- 模板推荐 -->
        <div class="template-section">
          <div class="template-header">
            <div class="template-tags">
              <a-tag
                v-for="(tag, index) in templateTags"
                :key="index"
                color="arcoblue"
                class="template-tag"
                @click="selectTemplate(tag)"
              >
                <template #icon><icon-file-ppt /></template>
                {{ tag.name }}
              </a-tag>
            </div>
            <a-button type="text" @click="refreshTemplates">
              <template #icon><icon-refresh /></template>
              换一换
            </a-button>
          </div>
        </div>
      </div>

      <!-- 设置区域 -->
      <div class="settings-section" v-if="selectedFile">
        <h3 class="section-title">视频设置</h3>
        <a-form :model="formData" layout="vertical">
          <a-row :gutter="24">
            <a-col :span="12">
              <a-form-item label="选择数字人">
                <a-select v-model="formData.digitalHuman" placeholder="请选择数字人">
                  <a-option v-for="dh in digitalHumanList" :key="dh.id" :value="dh.id">
                    <div class="option-item">
                      <img :src="dh.avatar" class="option-avatar" />
                      <span>{{ dh.name }}</span>
                    </div>
                  </a-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="配音音色">
                <a-select v-model="formData.voice" placeholder="请选择配音">
                  <a-option v-for="voice in voiceList" :key="voice.id" :value="voice.id">
                    {{ voice.name }}
                  </a-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="讲解风格">
            <a-radio-group v-model="formData.style" type="button">
              <a-radio value="professional">专业严谨</a-radio>
              <a-radio value="friendly">亲切友好</a-radio>
              <a-radio value="lively">活泼生动</a-radio>
              <a-radio value="calm">沉稳平和</a-radio>
            </a-radio-group>
          </a-form-item>
        </a-form>
      </div>

      <!-- 底部操作 -->
      <div class="footer-actions" v-if="selectedFile">
        <a-button type="primary" size="large" :loading="isGenerating" @click="startGenerate">
          <template #icon><icon-play-circle /></template>
          开始生成视频
        </a-button>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { Message } from '@arco-design/web-vue';
import {
  IconLeft,
  IconStarFill,
  IconPlus,
  IconFile,
  IconDelete,
  IconFilePpt,
  IconRefresh,
  IconPlayCircle,
} from '@arco-design/web-vue/es/icon';

const router = useRouter();
const fileInput = ref<HTMLInputElement>();
const isDragOver = ref(false);
const selectedFile = ref<File | null>(null);
const isGenerating = ref(false);

const formData = reactive({
  digitalHuman: '',
  voice: '',
  style: 'professional',
});

// 数字人列表
const digitalHumanList = ref([
  { id: '1', name: '小明老师', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=1' },
  { id: '2', name: '小红老师', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=2' },
  { id: '3', name: '商务男士', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=3' },
  { id: '4', name: '职业女性', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=4' },
]);

// 配音列表
const voiceList = ref([
  { id: '1', name: '标准男声' },
  { id: '2', name: '标准女声' },
  { id: '3', name: '温柔女声' },
  { id: '4', name: '磁性男声' },
]);

// 模板标签
const templateTags = ref([
  { name: '智能手表发布会', id: '1' },
  { name: '小学语文微课', id: '2' },
  { name: '弘扬红色精神党建专题报告', id: '3' },
  { name: '幼儿园家长会', id: '4' },
  { name: '智能眼镜售后FAQ', id: '5' },
]);

const goBack = () => {
  router.back();
};

const triggerUpload = () => {
  fileInput.value?.click();
};

const handleDragOver = () => {
  isDragOver.value = true;
};

const handleDragLeave = () => {
  isDragOver.value = false;
};

const handleDrop = (e: DragEvent) => {
  isDragOver.value = false;
  const files = e.dataTransfer?.files;
  if (files && files.length > 0) {
    validateAndSetFile(files[0]);
  }
};

const handleFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement;
  const files = target.files;
  if (files && files.length > 0) {
    validateAndSetFile(files[0]);
  }
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

const removeFile = () => {
  selectedFile.value = null;
  if (fileInput.value) {
    fileInput.value.value = '';
  }
};

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

const selectTemplate = (tag: { name: string; id: string }) => {
  Message.info(`已选择模板：${tag.name}`);
};

const refreshTemplates = () => {
  // 模拟刷新模板
  const newTemplates = [
    { name: '高中数学函数讲解', id: '6' },
    { name: '公司产品培训', id: '7' },
    { name: '安全生产教育', id: '8' },
    { name: '新员工入职培训', id: '9' },
    { name: '健康知识讲座', id: '10' },
  ];
  templateTags.value = newTemplates;
};

const startGenerate = () => {
  if (!formData.digitalHuman) {
    Message.warning('请选择数字人');
    return;
  }
  if (!formData.voice) {
    Message.warning('请选择配音音色');
    return;
  }
  
  isGenerating.value = true;
  // 模拟生成过程
  setTimeout(() => {
    isGenerating.value = false;
    Message.success('视频生成任务已提交，请在"我的数字人"中查看进度');
  }, 2000);
};
</script>

<script lang="ts">
export default {
  name: 'PptToVideo',
};
</script>

<style scoped lang="less">
.container {
  padding: 0 20px 20px 20px;
}

.content {
  max-width: 900px;
  margin: 0 auto;
}

.header {
  text-align: center;
  padding: 20px 0 40px;
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
    transition: color 0.3s;

    &:hover {
      color: rgb(var(--primary-5));
    }
  }

  .title {
    font-size: 28px;
    font-weight: 600;
    color: var(--color-text-1);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;

    .star-icon {
      color: rgb(var(--warning-5));
      font-size: 20px;
    }
  }

  .subtitle {
    font-size: 15px;
    color: var(--color-text-3);
  }
}

.upload-section {
  background: var(--color-bg-2);
  border-radius: 12px;
  padding: 32px;
  border: 1px solid var(--color-border-2);
  margin-bottom: 24px;
}

.upload-area {
  border: 2px dashed var(--color-border-3);
  border-radius: 12px;
  padding: 60px 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background: var(--color-fill-1);

  &:hover,
  &.drag-over {
    border-color: rgb(var(--primary-5));
    background: rgb(var(--primary-1));
  }

  &.has-file {
    padding: 40px;
    border-style: solid;
    border-color: rgb(var(--primary-4));
    background: rgb(var(--primary-1));
  }
}

.upload-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--color-bg-2);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  color: rgb(var(--primary-5));
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.upload-text {
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text-1);
  margin-bottom: 12px;
}

.upload-hint {
  font-size: 13px;
  color: var(--color-text-3);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  .divider {
    color: var(--color-border-3);
  }
}

.file-preview {
  display: flex;
  align-items: center;
  gap: 16px;

  .file-icon {
    width: 56px;
    height: 56px;
    border-radius: 8px;
    background: rgb(var(--warning-1));
    color: rgb(var(--warning-5));
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .file-info {
    flex: 1;
    text-align: left;

    .file-name {
      font-size: 15px;
      font-weight: 500;
      color: var(--color-text-1);
      margin-bottom: 4px;
    }

    .file-size {
      font-size: 13px;
      color: var(--color-text-3);
    }
  }
}

.template-section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--color-border-2);
}

.template-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.template-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;

  .template-tag {
    cursor: pointer;
    transition: all 0.3s;

    &:hover {
      transform: translateY(-2px);
    }
  }
}

.settings-section {
  background: var(--color-bg-2);
  border-radius: 12px;
  padding: 24px 32px;
  border: 1px solid var(--color-border-2);
  margin-bottom: 24px;

  .section-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--color-text-1);
    margin-bottom: 20px;
  }
}

.option-item {
  display: flex;
  align-items: center;
  gap: 8px;

  .option-avatar {
    width: 24px;
    height: 24px;
    border-radius: 50%;
  }
}

.footer-actions {
  display: flex;
  justify-content: center;
  padding: 20px 0;
}
</style>
