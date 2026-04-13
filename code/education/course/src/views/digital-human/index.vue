<template>
  <div class="container">
    <Breadcrumb :items="['menu.digitalHuman', 'menu.digitalHuman.tools']" />
    <div class="content">
      <div class="header">
        <h1 class="title">数字人工具台</h1>
        <p class="subtitle">利用 AI 技术快速生成数字人视频内容</p>
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
  .tools-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
  }
  .tool-card {
    display: flex;
    align-items: center;
    padding: 26px;
    min-height: 138px;
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
    min-height: 56px;
    display: flex;
    flex-direction: column;
    justify-content: center;
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
    line-height: 1.45;
    min-height: 2.9em;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .tool-arrow {
    color: var(--color-text-4);
    transition: transform 0.22s ease;
  }

  .tool-card:hover .tool-arrow {
    transform: translateX(3px);
  }

  @media (max-width: @screen-md) {
    .tools-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
