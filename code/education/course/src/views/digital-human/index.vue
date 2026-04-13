<template>
  <div class="container">
    <Breadcrumb :items="['menu.digitalHuman', 'menu.digitalHuman.tools']" />
    <div class="content">
      <div class="header">
        <h1 class="title">AI工具</h1>
        <p class="subtitle">利用AI技术快速生成数字人视频内容</p>
      </div>

      <div class="tools-grid">
        <!-- 文本生成视频 -->
        <div class="tool-card" @click="goToTextToVideo">
          <div class="tool-icon">
            <icon-font type="icon-text" :size="32" />
          </div>
          <div class="tool-info">
            <h3 class="tool-name">文本生成视频</h3>
            <p class="tool-desc">输入脚本，生成数字人口播视频</p>
          </div>
          <div class="tool-arrow">
            <icon-right />
          </div>
        </div>

        <!-- PPT生成视频 -->
        <div class="tool-card" @click="goToPptToVideo">
          <div class="tool-icon ppt">
            <icon-font type="icon-ppt" :size="32" />
          </div>
          <div class="tool-info">
            <h3 class="tool-name">PPT生成视频</h3>
            <p class="tool-desc">上传PPT，数字人自动进行讲解</p>
          </div>
          <div class="tool-arrow">
            <icon-right />
          </div>
        </div>

        <!-- 数字人克隆 -->
        <div class="tool-card" @click="goToClone">
          <div class="tool-icon clone">
            <icon-font type="icon-user" :size="32" />
          </div>
          <div class="tool-info">
            <h3 class="tool-name">数字人克隆</h3>
            <p class="tool-desc">上传照片，即刻克隆专属数字人</p>
          </div>
          <div class="tool-arrow">
            <icon-right />
          </div>
        </div>

        <!-- 我的数字人 -->
        <div class="tool-card" @click="goToMyDigitalHumans">
          <div class="tool-icon my">
            <icon-font type="icon-storage" :size="32" />
          </div>
          <div class="tool-info">
            <h3 class="tool-name">我的数字人</h3>
            <p class="tool-desc">管理已创建的数字人和视频作品</p>
          </div>
          <div class="tool-arrow">
            <icon-right />
          </div>
        </div>
      </div>

      <!-- 使用指南 -->
      <div class="guide-section">
        <h2 class="section-title">使用指南</h2>
        <div class="guide-steps">
          <div class="step-item">
            <div class="step-num">1</div>
            <div class="step-content">
              <h4>选择工具</h4>
              <p>根据需求选择合适的AI工具</p>
            </div>
          </div>
          <div class="step-item">
            <div class="step-num">2</div>
            <div class="step-content">
              <h4>上传内容</h4>
              <p>上传PPT、输入文本或上传照片</p>
            </div>
          </div>
          <div class="step-item">
            <div class="step-num">3</div>
            <div class="step-content">
              <h4>生成视频</h4>
              <p>等待AI处理生成数字人视频</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { useRouter } from 'vue-router';
import { IconRight } from '@arco-design/web-vue/es/icon';

const router = useRouter();

const goToTextToVideo = () => {
  router.push('/digital-human/text-to-video');
};

const goToPptToVideo = () => {
  router.push('/digital-human/ppt-to-video');
};

const goToClone = () => {
  router.push('/digital-human/clone');
};

const goToMyDigitalHumans = () => {
  router.push('/digital-human/my');
};
</script>

<script lang="ts">
export default {
  name: 'DigitalHumanTools',
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
  margin-bottom: 40px;
  padding-top: 20px;

  .title {
    font-size: 32px;
    font-weight: 600;
    color: var(--color-text-1);
    margin-bottom: 12px;
  }

  .subtitle {
    font-size: 16px;
    color: var(--color-text-3);
  }
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
  margin-bottom: 48px;
}

.tool-card {
  display: flex;
  align-items: center;
  padding: 32px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-6px);
    border-color: color-mix(in srgb, var(--zy-color-brand, #6366f1) 45%, #fff 55%);
    box-shadow:
      0 18px 42px rgba(15, 23, 42, 0.14),
      0 0 55px color-mix(in srgb, var(--zy-color-brand, #6366f1) 26%, transparent);
  }

  .tool-icon {
    width: 64px;
    height: 64px;
    border-radius: 12px;
    background: linear-gradient(135deg, rgb(var(--primary-3)), rgb(var(--primary-5)));
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    margin-right: 20px;
    flex-shrink: 0;

    &.ppt {
      background: linear-gradient(135deg, #ff6b6b, #ee5a5a);
    }

    &.clone {
      background: linear-gradient(135deg, #4ecdc4, #44a08d);
    }

    &.my {
      background: linear-gradient(135deg, #a8edea, #fed6e3);
      color: rgb(var(--primary-6));
    }
  }

  .tool-info {
    flex: 1;

    .tool-name {
      font-size: 18px;
      font-weight: 600;
      color: var(--color-text-1);
      margin-bottom: 8px;
    }

    .tool-desc {
      font-size: 14px;
      color: var(--color-text-3);
    }
  }

  .tool-arrow {
    color: var(--color-text-4);
    transition: transform 0.3s;
  }

  &:hover .tool-arrow {
    transform: translateX(4px);
    color: rgb(var(--primary-5));
  }
}

.guide-section {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  padding: 32px;
  border: 1px solid rgba(255, 255, 255, 0.5);

  .section-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--color-text-1);
    margin-bottom: 24px;
    text-align: center;
  }
}

.guide-steps {
  display: flex;
  justify-content: space-around;
  gap: 24px;
}

.step-item {
  display: flex;
  align-items: flex-start;
  flex: 1;

  .step-num {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: rgb(var(--primary-1));
    color: rgb(var(--primary-6));
    font-size: 16px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 16px;
    flex-shrink: 0;
  }

  .step-content {
    h4 {
      font-size: 16px;
      font-weight: 600;
      color: var(--color-text-1);
      margin-bottom: 6px;
    }

    p {
      font-size: 14px;
      color: var(--color-text-3);
      line-height: 1.5;
    }
  }
}

// 响应式
@media (max-width: @screen-md) {
  .tools-grid {
    grid-template-columns: 1fr;
  }

  .guide-steps {
    flex-direction: column;
  }
}
</style>
