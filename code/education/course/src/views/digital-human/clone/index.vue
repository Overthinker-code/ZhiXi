<template>
  <div class="container">
    <Breadcrumb :items="['menu.digitalHuman', 'menu.digitalHuman.clone']" />
    <div class="content">
      <!-- 头部 -->
      <div class="header">
        <div class="back-btn" @click="goBack">
          <icon-left />
          <span>返回</span>
        </div>
        <h1 class="title">
          上传照片，即刻<span class="highlight">克隆</span>
        </h1>
        <p class="subtitle">上传5张不同角度的清晰照片，即可生成专属数字人</p>
      </div>

      <!-- 拍摄小课堂 -->
      <div class="tutorial-section">
        <div class="tutorial-header">
          <icon-bulb class="bulb-icon" />
          <span>拍摄小课堂</span>
        </div>
        <div class="photo-examples">
          <div v-for="(item, index) in photoExamples" :key="index" class="example-item">
            <div class="example-image">
              <img :src="item.image" :alt="item.label" />
              <span class="example-label">{{ item.label }}</span>
            </div>
          </div>
        </div>
        <p class="photo-requirement">
          请上传5张不同角度的清晰照片，支持 jpg、jpeg、png 格式，大小不超过 10M
        </p>
      </div>

      <!-- 上传区域 -->
      <div class="upload-section">
        <div class="upload-grid">
          <div
            v-for="(slot, index) in uploadSlots"
            :key="index"
            class="upload-slot"
            :class="{ 'has-file': slot.file, 'is-uploading': slot.uploading }"
            @click="triggerUpload(index)"
          >
            <input
              :ref="(el) => { if (el) fileInputs[index] = el as HTMLInputElement }"
              type="file"
              accept="image/*"
              style="display: none"
              @change="(e) => handleFileChange(e, index)"
            />
            
            <template v-if="!slot.file">
              <div class="slot-placeholder">
                <icon-plus :size="24" />
                <span class="slot-label">{{ slot.label }}</span>
              </div>
            </template>
            
            <template v-else>
              <img :src="slot.preview" class="slot-preview" />
              <div class="slot-actions" @click.stop>
                <a-button type="text" status="danger" size="mini" @click="removeFile(index)">
                  <template #icon><icon-delete /></template>
                </a-button>
              </div>
            </template>

            <div v-if="slot.uploading" class="upload-progress">
              <a-progress :percent="slot.progress" type="circle" size="small" />
            </div>
          </div>
        </div>
      </div>

      <!-- 表单设置 -->
      <div class="form-section">
        <a-form :model="formData" layout="inline">
          <a-form-item label="性别">
            <a-select v-model="formData.gender" placeholder="请选择性别" style="width: 160px">
              <a-option value="male">男</a-option>
              <a-option value="female">女</a-option>
            </a-select>
          </a-form-item>
          
          <a-form-item label="族裔">
            <a-select v-model="formData.ethnicity" placeholder="请选择族裔" style="width: 160px">
              <a-option value="asian">亚裔</a-option>
              <a-option value="caucasian">白人</a-option>
              <a-option value="african">非洲裔</a-option>
              <a-option value="hispanic">拉丁裔</a-option>
            </a-select>
          </a-form-item>
        </a-form>

        <div class="action-group">
          <a-button
            type="primary"
            size="large"
            :disabled="!canSubmit"
            :loading="isSubmitting"
            @click="submitClone"
          >
            <template #icon><icon-thunderbolt /></template>
            立即生成
          </a-button>
          
          <div class="agreement">
            <a-checkbox v-model="formData.agreed">
              我已阅读并同意
              <a-link>魔法有言形象克隆服务规范</a-link>
            </a-checkbox>
          </div>
        </div>
      </div>

      <!-- 生成实例 -->
      <div class="examples-section">
        <div class="examples-header">
          <h3>
            <icon-star-fill class="star-icon" />
            生成实例
            <icon-star-fill class="star-icon" />
          </h3>
          <a-button type="text">
            更多
            <icon-right />
          </a-button>
        </div>
        <div class="examples-grid">
          <div v-for="(example, index) in generatedExamples" :key="index" class="example-card">
            <img :src="example.image" :alt="example.name" />
            <div class="example-info">
              <span class="example-name">{{ example.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed } from 'vue';
import { useRouter } from 'vue-router';
import { Message } from '@arco-design/web-vue';
import {
  IconLeft,
  IconBulb,
  IconPlus,
  IconDelete,
  IconThunderbolt,
  IconStarFill,
  IconRight,
} from '@arco-design/web-vue/es/icon';

const router = useRouter();
const fileInputs = ref<HTMLInputElement[]>([]);

interface UploadSlot {
  label: string;
  file: File | null;
  preview: string;
  uploading: boolean;
  progress: number;
}

const uploadSlots = reactive<UploadSlot[]>([
  { label: '正面', file: null, preview: '', uploading: false, progress: 0 },
  { label: '左侧45°', file: null, preview: '', uploading: false, progress: 0 },
  { label: '左侧90°', file: null, preview: '', uploading: false, progress: 0 },
  { label: '右侧45°', file: null, preview: '', uploading: false, progress: 0 },
  { label: '右侧90°', file: null, preview: '', uploading: false, progress: 0 },
]);

const photoExamples = ref([
  { label: '正面', image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=front&gender=male' },
  { label: '左侧45°', image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=left45&gender=male' },
  { label: '左侧90°', image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=left90&gender=male' },
  { label: '右侧45°', image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=right45&gender=male' },
  { label: '右侧90°', image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=right90&gender=male' },
]);

const formData = reactive({
  gender: '',
  ethnicity: '',
  agreed: false,
});

const isSubmitting = ref(false);

const generatedExamples = ref([
  { name: '商务女性', image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=ex1&gender=female' },
  { name: '青年男性', image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=ex2&gender=male' },
  { name: '阳光男孩', image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=ex3&gender=male' },
  { name: '职业女性', image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=ex4&gender=female' },
  { name: '成熟男性', image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=ex5&gender=male' },
]);

const canSubmit = computed(() => {
  const allUploaded = uploadSlots.every((slot) => slot.file !== null);
  return allUploaded && formData.gender && formData.ethnicity && formData.agreed;
});

const goBack = () => {
  router.back();
};

const triggerUpload = (index: number) => {
  if (uploadSlots[index].file) return;
  fileInputs.value[index]?.click();
};

const handleFileChange = (e: Event, index: number) => {
  const target = e.target as HTMLInputElement;
  const files = target.files;
  
  if (!files || files.length === 0) return;
  
  const file = files[0];
  
  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    Message.error('请上传图片文件');
    return;
  }
  
  // 验证文件大小 (10MB)
  if (file.size > 10 * 1024 * 1024) {
    Message.error('文件大小不能超过 10MB');
    return;
  }
  
  // 开始上传
  uploadSlots[index].file = file;
  uploadSlots[index].uploading = true;
  
  // 生成预览
  const reader = new FileReader();
  reader.onload = (e) => {
    uploadSlots[index].preview = e.target?.result as string;
  };
  reader.readAsDataURL(file);
  
  // 模拟上传进度
  let progress = 0;
  const timer = setInterval(() => {
    progress += 10;
    uploadSlots[index].progress = progress;
    
    if (progress >= 100) {
      clearInterval(timer);
      uploadSlots[index].uploading = false;
      Message.success(`${uploadSlots[index].label}照片上传成功`);
    }
  }, 100);
};

const removeFile = (index: number) => {
  uploadSlots[index].file = null;
  uploadSlots[index].preview = '';
  uploadSlots[index].progress = 0;
  
  // 清空input
  if (fileInputs.value[index]) {
    fileInputs.value[index].value = '';
  }
};

const submitClone = () => {
  if (!canSubmit.value) {
    if (!formData.agreed) {
      Message.warning('请同意服务规范');
    }
    return;
  }
  
  isSubmitting.value = true;
  
  // 模拟提交
  setTimeout(() => {
    isSubmitting.value = false;
    Message.success('数字人克隆任务已提交，预计需要5-10分钟完成');
    router.push('/user/setting');
  }, 2000);
};
</script>

<script lang="ts">
export default {
  name: 'DigitalHumanClone',
};
</script>

<style scoped lang="less">
.container {
  padding: 0 20px 40px 20px;
}

.content {
  max-width: 1000px;
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

    .highlight {
      color: rgb(var(--primary-5));
      margin-left: 8px;
    }
  }

  .subtitle {
    font-size: 14px;
    color: var(--color-text-3);
  }
}

.tutorial-section {
  background: linear-gradient(135deg, #e0e7ff 0%, #d1e0fd 100%);
  border-radius: 16px;
  padding: 24px 32px;
  margin-bottom: 24px;

  .tutorial-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 20px;
    font-size: 15px;
    font-weight: 500;
    color: var(--color-text-1);

    .bulb-icon {
      color: rgb(var(--warning-5));
      font-size: 18px;
    }
  }

  .photo-examples {
    display: flex;
    justify-content: center;
    gap: 16px;
    margin-bottom: 16px;
  }

  .example-item {
    text-align: center;
  }

  .example-image {
    position: relative;
    width: 100px;
    height: 120px;
    border-radius: 8px;
    overflow: hidden;
    background: var(--color-bg-2);
    border: 2px solid var(--color-border-2);

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .example-label {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      background: rgba(0, 0, 0, 0.6);
      color: #fff;
      font-size: 12px;
      padding: 4px 0;
    }
  }

  .photo-requirement {
    text-align: center;
    font-size: 14px;
    color: var(--color-text-2);
    margin: 0;
  }
}

.upload-section {
  background: var(--color-bg-2);
  border-radius: 16px;
  padding: 32px;
  border: 1px solid var(--color-border-2);
  margin-bottom: 24px;
}

.upload-grid {
  display: flex;
  justify-content: center;
  gap: 20px;
  flex-wrap: wrap;
}

.upload-slot {
  position: relative;
  width: 140px;
  height: 170px;
  border: 2px dashed var(--color-border-3);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  background: var(--color-fill-1);
  overflow: hidden;

  &:hover {
    border-color: rgb(var(--primary-5));
    background: rgb(var(--primary-1));
  }

  &.has-file {
    border-style: solid;
    border-color: rgb(var(--primary-4));
  }

  &.is-uploading {
    cursor: not-allowed;
  }
}

.slot-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--color-text-3);

  .slot-label {
    font-size: 14px;
  }
}

.slot-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.slot-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  opacity: 0;
  transition: opacity 0.3s;

  .upload-slot:hover & {
    opacity: 1;
  }
}

.upload-progress {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
}

.form-section {
  background: var(--color-bg-2);
  border-radius: 16px;
  padding: 32px;
  border: 1px solid var(--color-border-2);
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 20px;

  .action-group {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }

  .agreement {
    font-size: 13px;
  }
}

.examples-section {
  .examples-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;

    h3 {
      font-size: 18px;
      font-weight: 600;
      color: var(--color-text-1);
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0;

      .star-icon {
        color: rgb(var(--warning-5));
        font-size: 14px;
      }
    }
  }

  .examples-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
  }

  .example-card {
    border-radius: 12px;
    overflow: hidden;
    background: var(--color-bg-2);
    border: 1px solid var(--color-border-2);
    transition: all 0.3s;

    &:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
    }

    img {
      width: 100%;
      aspect-ratio: 1;
      object-fit: cover;
    }

    .example-info {
      padding: 12px;
      text-align: center;

      .example-name {
        font-size: 13px;
        color: var(--color-text-1);
      }
    }
  }
}

// 响应式
@media (max-width: @screen-md) {
  .photo-examples {
    flex-wrap: wrap;
  }

  .upload-grid {
    gap: 12px;
  }

  .upload-slot {
    width: 100px;
    height: 120px;
  }

  .examples-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: @screen-sm) {
  .examples-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
