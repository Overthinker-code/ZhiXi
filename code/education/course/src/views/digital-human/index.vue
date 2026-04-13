<template>
  <div class="container">
    <Breadcrumb :items="['menu.digitalHuman', 'menu.digitalHuman.tools']" />
    <div class="content">
      <div class="header">
        <h1 class="title">数字人工具台</h1>
        <p class="subtitle">利用 AI 技术快速生成数字人视频内容</p>
      </div>

      <div class="studio-entry-card">
        <div class="studio-entry-left">
          <h3>文本生成视频 Studio</h3>
          <p>这里是可进入的具体创作界面入口，已接入你上传的数字人封面预览。</p>
          <a-button type="primary" @click="goToTextToVideo">
            进入文本生成视频
          </a-button>
        </div>
        <div class="studio-entry-preview" aria-label="数字人封面视频预览（不可点击）">
          <img :src="studioCover" alt="数字人封面预览" />
          <span class="scan-line" />
          <span class="play-mask">▶</span>
        </div>
      </div>

      <div class="tools-grid">
        <button type="button" class="tool-card" @click="goToTextToVideo">
          <div class="tool-icon">📝</div>
          <div class="tool-info">
            <h3 class="tool-name">文本生成视频</h3>
            <p class="tool-desc">输入脚本，生成数字人口播视频</p>
          </div>
          <div class="tool-arrow"><icon-right /></div>
        </button>

        <button type="button" class="tool-card" @click="goToPptToVideo">
          <div class="tool-icon ppt">📊</div>
          <div class="tool-info">
            <h3 class="tool-name">PPT生成视频</h3>
            <p class="tool-desc">上传PPT，数字人自动进行讲解</p>
          </div>
          <div class="tool-arrow"><icon-right /></div>
        </button>

        <button type="button" class="tool-card" @click="goToClone">
          <div class="tool-icon clone">🧬</div>
          <div class="tool-info">
            <h3 class="tool-name">数字人克隆</h3>
            <p class="tool-desc">上传照片，即刻克隆专属数字人</p>
          </div>
          <div class="tool-arrow"><icon-right /></div>
        </button>

        <button type="button" class="tool-card" @click="goToMyDigitalHumans">
          <div class="tool-icon my">🎬</div>
          <div class="tool-info">
            <h3 class="tool-name">我的数字人</h3>
            <p class="tool-desc">管理已创建的数字人和视频作品</p>
          </div>
          <div class="tool-arrow"><icon-right /></div>
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { useRouter } from 'vue-router';
  import { IconRight } from '@arco-design/web-vue/es/icon';
  import studioCover from '@/assets/digital-human/studio-cover.png';

  const router = useRouter();
  const goToTextToVideo = () => router.push('/digital-human/text-to-video');
  const goToPptToVideo = () => router.push('/digital-human/ppt-to-video');
  const goToClone = () => router.push('/digital-human/clone');
  const goToMyDigitalHumans = () => router.push('/digital-human/my');
</script>

<script lang="ts">
  export default {
    name: 'DigitalHumanTools',
  };
</script>

<style scoped lang="less">
  .container {
    padding: 0 20px 20px;
  }
  .content {
    max-width: 1200px;
    margin: 0 auto;
  }
  .header {
    text-align: center;
    margin-bottom: 20px;
    padding-top: 20px;
    .title {
      font-size: 30px;
      font-weight: 700;
      color: var(--color-text-1);
      margin-bottom: 10px;
    }
    .subtitle {
      font-size: 15px;
      color: var(--color-text-3);
    }
  }
  .studio-entry-card {
    margin-bottom: 24px;
    display: grid;
    grid-template-columns: 1.1fr 1fr;
    gap: 18px;
    align-items: center;
    padding: 18px;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.78);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.5);
  }
  .studio-entry-left {
    h3 {
      margin: 0 0 8px;
      font-size: 20px;
      color: #0f172a;
    }
    p {
      margin: 0 0 12px;
      color: #64748b;
      line-height: 1.5;
    }
  }
  .studio-entry-preview {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(99, 102, 241, 0.26);
    pointer-events: none;
    img {
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
      box-shadow: 0 0 14px rgba(56, 189, 248, 0.8);
      animation: entry-scan 1.4s linear infinite;
    }
    .play-mask {
      position: absolute;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      width: 62px;
      height: 62px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.24);
      color: #fff;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 1px solid rgba(255, 255, 255, 0.55);
      backdrop-filter: blur(8px);
      font-size: 20px;
    }
  }
  @keyframes entry-scan {
    0% {
      top: 0;
    }
    100% {
      top: calc(100% - 2px);
    }
  }
  .tools-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
  }
  .tool-card {
    display: flex;
    align-items: center;
    padding: 24px;
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.5);
    cursor: pointer;
    transition: all 0.3s ease;
    text-align: left;
    &:hover {
      transform: translateY(-6px);
      border-color: color-mix(in srgb, var(--zy-color-brand, #6366f1) 45%, #fff 55%);
      box-shadow:
        0 18px 42px rgba(15, 23, 42, 0.14),
        0 0 55px color-mix(in srgb, var(--zy-color-brand, #6366f1) 26%, transparent);
    }
  }
  .tool-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    background: linear-gradient(135deg, rgb(var(--primary-3)), rgb(var(--primary-5)));
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    margin-right: 16px;
    flex-shrink: 0;
    &.ppt {
      background: linear-gradient(135deg, #ff6b6b, #ee5a5a);
    }
    &.clone {
      background: linear-gradient(135deg, #14b8a6, #0ea5e9);
    }
    &.my {
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
    }
  }
  .tool-info {
    flex: 1;
  }
  .tool-name {
    font-size: 18px;
    font-weight: 600;
    color: var(--color-text-1);
    margin: 0 0 6px;
  }
  .tool-desc {
    margin: 0;
    font-size: 14px;
    color: var(--color-text-3);
  }
  .tool-arrow {
    color: var(--color-text-4);
  }

  @media (max-width: @screen-md) {
    .studio-entry-card {
      grid-template-columns: 1fr;
    }
    .tools-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
