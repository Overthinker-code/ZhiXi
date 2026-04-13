<template>
  <div class="container">
    <Breadcrumb :items="['menu.digitalHuman', 'menu.digitalHuman.textToVideo']" />
    <div class="content">
      <div class="header">
        <a-button type="text" class="back-btn" @click="goBack">返回数字人工具台</a-button>
        <h1 class="title">文本生成视频 Studio</h1>
        <p class="subtitle">已接入你的封面素材，点击生成后展示扫描动效与封面预览</p>
      </div>

      <div class="studio-layout">
        <section class="left-panel">
          <h3>脚本输入</h3>
          <a-textarea
            v-model="scriptContent"
            :auto-size="{ minRows: 10, maxRows: 12 }"
            placeholder="请输入文本内容，例如：大家好，欢迎来到今天的课程..."
          />
          <div class="actions">
            <a-button type="primary" :loading="isGenerating" @click="generateVideo">
              生成视频
            </a-button>
          </div>
        </section>

        <section class="right-panel">
          <div class="preview-canvas">
            <img :src="studioCoverImage" class="studio-cover" alt="数字人封面" />
            <div v-if="isGenerating" class="scan-line"></div>
            <div class="play-mask">▶</div>
          </div>
          <p class="preview-tip">当前显示：`studio-cover.png` 封面预览</p>
        </section>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { Message } from '@arco-design/web-vue';
import studioCover from '@/assets/digital-human/studio-cover.png';

const router = useRouter();
const scriptContent = ref('');
const isGenerating = ref(false);
const studioCoverImage = ref(studioCover);

const goBack = () => {
  router.push('/digital-human');
};

const generateVideo = () => {
  isGenerating.value = true;
  setTimeout(() => {
    isGenerating.value = false;
    Message.success('渲染完成，已展示封面预览');
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
  padding: 0 20px 24px;
}
.content {
  max-width: 1280px;
  margin: 0 auto;
}
.header {
  text-align: center;
  margin-bottom: 16px;
}
.back-btn {
  float: left;
  margin-bottom: 8px;
}
.title {
  margin: 0;
  font-size: 30px;
  font-weight: 700;
  color: #0f172a;
}
.subtitle {
  margin: 8px 0 0;
  color: #64748b;
}
.studio-layout {
  display: grid;
  grid-template-columns: 38% 62%;
  gap: 20px;
}
.left-panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 18px;
}
.actions {
  margin-top: 14px;
}
.right-panel {
  border-radius: 16px;
  padding: 18px;
  background-color: #0f172a;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 24px 24px;
}
.preview-canvas {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: 14px;
  border: 1px solid rgba(56, 189, 248, 0.4);
}
.studio-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.scan-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #38bdf8, transparent);
  box-shadow: 0 0 15px rgba(56, 189, 248, 0.9);
  animation: scan 1.1s linear infinite;
}
.play-mask {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 74px;
  height: 74px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.45);
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(8px);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
}
.preview-tip {
  margin: 12px 0 0;
  color: #cbd5e1;
}
@keyframes scan {
  0% { top: 0; }
  100% { top: calc(100% - 2px); }
}
@media (max-width: @screen-lg) {
  .studio-layout {
    grid-template-columns: 1fr;
  }
}
</style>
