<template>
  <div class="container">
    <Breadcrumb :items="['menu.digitalHuman', 'menu.digitalHuman.textToVideo']" />
    <div class="content">
      <!-- 头部 -->
      <div class="header">
        <div class="back-btn" @click="goBack">
          <icon-left />
          <span>返回</span>
        </div>
        <h1 class="title">文本生成视频</h1>
        <p class="subtitle">输入脚本内容，生成数字人口播视频</p>
      </div>

      <div class="studio-workbench">
        <!-- 左侧：控制台 -->
        <div class="studio-control-panel">
          <div class="panel-card">
            <div class="panel-header">
              <h3>输入脚本内容</h3>
              <a-button type="text" size="small" @click="showTemplates = true">
                <template #icon><icon-apps /></template>
                选择模板
              </a-button>
            </div>
            <a-textarea
              v-model="scriptContent"
              :placeholder="placeholderText"
              :auto-size="{ minRows: 10, maxRows: 15 }"
              class="script-input"
              show-word-limit
              :max-length="5000"
            />
            <div class="quick-phrases">
              <span class="label">快捷短语：</span>
              <a-space wrap>
                <a-tag
                  v-for="phrase in quickPhrases"
                  :key="phrase"
                  class="phrase-tag"
                  @click="insertPhrase(phrase)"
                >
                  {{ phrase }}
                </a-tag>
              </a-space>
            </div>
          </div>

          <!-- AI润色 -->
          <div class="panel-card" v-if="scriptContent">
            <div class="ai-polish">
              <div class="polish-info">
                <icon-robot class="robot-icon" />
                <span>AI 可以帮助润色脚本，让表达更流畅自然</span>
              </div>
              <a-button type="primary" status="success" :loading="isPolishing" @click="polishScript">
                <template #icon><icon-magic /></template>
                AI润色
              </a-button>
            </div>
          </div>
        </div>

        <!-- 中间：参数设置 -->
        <div class="studio-control-panel">
          <div class="panel-card">
            <h3 class="panel-title">视频设置</h3>
            
            <a-form :model="formData" layout="vertical">
              <a-form-item label="选择数字人">
                <div class="digital-human-grid">
                  <div
                    v-for="dh in digitalHumanList"
                    :key="dh.id"
                    class="human-item"
                    :class="{ active: formData.digitalHuman === dh.id }"
                    @click="formData.digitalHuman = dh.id"
                  >
                    <img :src="dh.avatar" class="human-avatar" />
                    <span class="human-name">{{ dh.name }}</span>
                    <div v-if="formData.digitalHuman === dh.id" class="selected-mark">
                      <icon-check />
                    </div>
                  </div>
                </div>
              </a-form-item>

              <a-form-item label="配音音色">
                <a-select v-model="formData.voice" placeholder="请选择配音">
                  <a-option v-for="voice in voiceList" :key="voice.id" :value="voice.id">
                    <div class="voice-option">
                      <span>{{ voice.name }}</span>
                      <a-button
                        type="text"
                        size="mini"
                        @click.stop="playVoiceDemo(voice)"
                      >
                        <template #icon><icon-play-circle /></template>
                        试听
                      </a-button>
                    </div>
                  </a-option>
                </a-select>
              </a-form-item>

              <a-form-item label="语速">
                <a-slider v-model="formData.speed" :min="0.5" :max="2" :step="0.1" show-tooltip>
                  <template #marks>
                    <span style="left: 0%">慢</span>
                    <span style="left: 50%">标准</span>
                    <span style="left: 100%">快</span>
                  </template>
                </a-slider>
              </a-form-item>

              <a-form-item label="背景设置">
                <a-radio-group v-model="formData.backgroundType" type="button">
                  <a-radio value="blur">毛玻璃</a-radio>
                  <a-radio value="color">纯色</a-radio>
                  <a-radio value="image">图片</a-radio>
                </a-radio-group>
              </a-form-item>

              <a-form-item v-if="formData.backgroundType === 'color'" label="背景颜色">
                <div class="color-picker">
                  <div
                    v-for="color in bgColors"
                    :key="color"
                    class="color-item"
                    :style="{ background: color }"
                    :class="{ active: formData.backgroundColor === color }"
                    @click="formData.backgroundColor = color"
                  />
                </div>
              </a-form-item>

              <a-form-item label="视频比例">
                <a-radio-group v-model="formData.ratio" type="button">
                  <a-radio value="16:9">16:9 横屏</a-radio>
                  <a-radio value="9:16">9:16 竖屏</a-radio>
                  <a-radio value="1:1">1:1 方形</a-radio>
                </a-radio-group>
              </a-form-item>
            </a-form>
          </div>

          <!-- 生成按钮 -->
          <a-button
            type="primary"
            size="large"
            long
            :disabled="!canGenerate"
            :loading="isGenerating"
            @click="generateVideo"
          >
            <template #icon><icon-video-camera /></template>
            生成视频
          </a-button>
        </div>

        <!-- 右侧：专业预览区 -->
        <div class="studio-preview-shell">
          <div class="studio-preview-bg">
            <div class="studio-preview-canvas">
              <div class="canvas-frame" :class="{ 'is-rendering': isStudioRendering }">
                <template v-if="!studioResultReady">
                  <div class="canvas-waiting">
                    <icon-video-camera :size="32" />
                    <p>AI Studio 预览画布</p>
                    <span>点击「生成视频」后展示渲染结果</span>
                  </div>
                </template>
                <template v-else>
                  <img :src="studioCoverImage" class="studio-cover" alt="数字人视频封面" />
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

    <!-- 模板选择弹窗 -->
    <a-modal
      v-model:visible="showTemplates"
      title="选择脚本模板"
      width="700px"
      @ok="applyTemplate"
      @cancel="showTemplates = false"
    >
      <div class="template-list">
        <div
          v-for="template in scriptTemplates"
          :key="template.id"
          class="template-card"
          :class="{ active: selectedTemplate?.id === template.id }"
          @click="selectedTemplate = template"
        >
          <h4>{{ template.title }}</h4>
          <p>{{ template.desc }}</p>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed } from 'vue';
import { useRouter } from 'vue-router';
import { Message } from '@arco-design/web-vue';
import studioCover from '@/assets/digital-human/studio-cover.png';
import {
  IconLeft,
  IconApps,
  IconRobot,
  IconMagic,
  IconPlayCircle,
  IconPlayArrow,
  IconVideoCamera,
  IconCheck,
} from '@arco-design/web-vue/es/icon';

const router = useRouter();
const scriptContent = ref('');
const isPolishing = ref(false);
const isGenerating = ref(false);
const showTemplates = ref(false);
const selectedTemplate = ref<any>(null);
const isStudioRendering = ref(false);
const studioResultReady = ref(false);
const studioCoverImage = ref(studioCover);

const placeholderText = `请输入您想要数字人讲解的内容...

示例：
大家好，欢迎来到今天的课程。今天我们将学习如何有效地管理时间。时间管理是一项重要的技能，它可以帮助我们提高工作效率，减少压力，并实现工作与生活的平衡。`;

const formData = reactive({
  digitalHuman: '1',
  voice: '1',
  speed: 1,
  backgroundType: 'blur',
  backgroundColor: '#f5f5f5',
  ratio: '16:9',
});

const quickPhrases = [
  '大家好，欢迎来到今天的课程',
  '让我们开始今天的学习',
  '总结一下今天的内容',
  '感谢大家的聆听',
  '请记得复习今天的内容',
];

const digitalHumanList = ref([
  { id: '1', name: '小明老师', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=1' },
  { id: '2', name: '小红老师', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=2' },
  { id: '3', name: '商务男士', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=3' },
  { id: '4', name: '职业女性', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=4' },
]);

const voiceList = ref([
  { id: '1', name: '标准男声' },
  { id: '2', name: '标准女声' },
  { id: '3', name: '温柔女声' },
  { id: '4', name: '磁性男声' },
]);

const bgColors = ['#f5f5f5', '#e8f4f8', '#fff8e7', '#f0e6ff', '#ffe6e6', '#e6ffe6'];

const scriptTemplates = ref([
  {
    id: '1',
    title: '课程开场',
    desc: '标准的课程开场白，包含自我介绍和课程概述',
    content: '大家好，我是[姓名]，很高兴能和大家一起学习今天的课程。今天我们将探讨[主题]，希望通过今天的学习，大家能够掌握[目标]。',
  },
  {
    id: '2',
    title: '知识点讲解',
    desc: '适合讲解单个知识点的脚本模板',
    content: '今天我们要学习的是[知识点]。首先，让我们了解一下什么是[概念]...[知识点]在实际生活中的应用非常广泛，比如[例子]。',
  },
  {
    id: '3',
    title: '课程总结',
    desc: '课程结束时的总结模板',
    content: '今天我们学习了[主要内容]。回顾一下，我们重点掌握了[要点1]、[要点2]和[要点3]。希望大家课后能够复习巩固，下节课我们将继续学习[预告]。',
  },
]);

const canGenerate = computed(() => {
  return scriptContent.value.trim().length > 10 && formData.digitalHuman && formData.voice;
});

const goBack = () => {
  router.back();
};

const insertPhrase = (phrase: string) => {
  scriptContent.value += (scriptContent.value ? '\n' : '') + phrase;
};

const polishScript = () => {
  isPolishing.value = true;
  setTimeout(() => {
    scriptContent.value = scriptContent.value
      .replace(/。/g, '，')
      .replace(/，/g, '。')
      .trim() + '（已润色）';
    isPolishing.value = false;
    Message.success('脚本润色完成');
  }, 1500);
};

const playVoiceDemo = (voice: any) => {
  Message.info(`播放 ${voice.name} 试听`);
};

const applyTemplate = () => {
  if (selectedTemplate.value) {
    scriptContent.value = selectedTemplate.value.content;
    showTemplates.value = false;
    Message.success('模板已应用');
  }
};

const generateVideo = () => {
  isGenerating.value = true;
  isStudioRendering.value = true;
  studioResultReady.value = false;
  setTimeout(() => {
    isStudioRendering.value = false;
    studioResultReady.value = true;
    isGenerating.value = false;
    Message.success('视频生成任务已提交，请在"我的数字人"中查看进度');
  }, 3000);
};
</script>

<script lang="ts">
export default {
  name: 'TextToVideo',
};
</script>

<style scoped lang="less">
.container {
  padding: 0 20px 20px 20px;
}

.content {
  max-width: 1200px;
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
  flex: 1;
  min-width: 0;
}

.panel-card {
  background: var(--color-bg-2);
  border-radius: 12px;
  padding: 24px;
  border: 1px solid var(--color-border-2);
  margin-bottom: 16px;

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;

    h3 {
      font-size: 16px;
      font-weight: 600;
      color: var(--color-text-1);
    }
  }

  .panel-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--color-text-1);
    margin-bottom: 20px;
  }
}

.studio-preview-shell {
  width: 60%;
  min-width: 420px;
  flex-shrink: 0;
}

.studio-preview-bg {
  height: 100%;
  min-height: 560px;
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
  width: min(100%, 720px);
  aspect-ratio: 16 / 9;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.95), rgba(2, 6, 23, 0.98));
  border: 1px solid rgba(59, 130, 246, 0.35);
  overflow: hidden;
  position: relative;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.05) inset,
    0 18px 50px rgba(2, 6, 23, 0.65);
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

.script-input {
  font-size: 14px;
  line-height: 1.8;
}

.quick-phrases {
  margin-top: 16px;
  display: flex;
  align-items: flex-start;
  gap: 8px;

  .label {
    font-size: 13px;
    color: var(--color-text-3);
    flex-shrink: 0;
    padding-top: 4px;
  }

  .phrase-tag {
    cursor: pointer;
    transition: all 0.3s;

    &:hover {
      color: rgb(var(--primary-6));
      border-color: rgb(var(--primary-4));
    }
  }
}

.ai-polish {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: linear-gradient(135deg, rgb(var(--success-1)), rgb(var(--primary-1)));
  border-radius: 8px;

  .polish-info {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--color-text-2);

    .robot-icon {
      color: rgb(var(--success-5));
      font-size: 20px;
    }
  }
}

.digital-human-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.human-item {
  position: relative;
  padding: 16px;
  border: 2px solid var(--color-border-2);
  border-radius: 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;

  &:hover,
  &.active {
    border-color: rgb(var(--primary-5));
    background: rgb(var(--primary-1));
  }

  .human-avatar {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    margin-bottom: 8px;
  }

  .human-name {
    font-size: 13px;
    color: var(--color-text-1);
  }

  .selected-mark {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: rgb(var(--primary-5));
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
  }
}

.voice-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.color-picker {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.color-item {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;

  &:hover,
  &.active {
    border-color: rgb(var(--primary-5));
    transform: scale(1.1);
  }
}

.template-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.template-card {
  padding: 16px;
  border: 2px solid var(--color-border-2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;

  &:hover,
  &.active {
    border-color: rgb(var(--primary-5));
    background: rgb(var(--primary-1));
  }

  h4 {
    font-size: 15px;
    font-weight: 600;
    color: var(--color-text-1);
    margin-bottom: 8px;
  }

  p {
    font-size: 13px;
    color: var(--color-text-3);
    line-height: 1.5;
  }
}

// 响应式
@media (max-width: @screen-lg) {
  .studio-workbench {
    flex-direction: column;
  }

  .studio-preview-shell {
    width: 100%;
    min-width: 0;
  }
}
</style>
