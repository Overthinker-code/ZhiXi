<template>
  <a-col class="banner">
    <div class="banner-main">
      <div class="mesh-bg" aria-hidden="true" />
      <div class="neural-layer" aria-hidden="true" />
      <div class="banner-content">
        <a-typography-title :heading="4" class="title">
          {{ $t('workplace.welcome') }} {{ userInfo.name }}
        </a-typography-title>
        <a-typography-paragraph class="subtitle">
          {{ $t('workplace.subtitle') }}
        </a-typography-paragraph>
        <a-space :size="8" wrap>
          <a-tag color="purple">{{ $t('workplace.tag.lab') }}</a-tag>
          <a-tag color="cyan">{{ $t('workplace.tag.analysis') }}</a-tag>
          <a-tag color="arcoblue">{{ $t('workplace.tag.assessment') }}</a-tag>
        </a-space>
      </div>
    </div>
    <a-divider class="panel-border" />
  </a-col>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { useUserStore } from '@/store';

  const userStore = useUserStore();
  const userInfo = computed(() => {
    return {
      name: userStore.name,
    };
  });
</script>

<style scoped lang="less">
  .banner {
    width: 100%;
    padding: 20px 20px 0;
    background-color: transparent;
    border-radius: 14px 14px 0 0;
  }

  .banner-main {
    position: relative;
    padding: 26px 28px 28px;
    border-radius: 16px;
    overflow: hidden;
    min-height: 148px;
    border: 1px solid rgba(255, 255, 255, 0.35);
    box-shadow: 0 12px 40px rgba(15, 23, 42, 0.12);
  }

  .mesh-bg {
    position: absolute;
    inset: 0;
    z-index: 0;
    background:
      radial-gradient(at 12% 18%, rgba(99, 102, 241, 0.55) 0%, transparent 42%),
      radial-gradient(at 88% 12%, rgba(139, 92, 246, 0.5) 0%, transparent 38%),
      radial-gradient(at 72% 88%, rgba(14, 165, 233, 0.45) 0%, transparent 45%),
      radial-gradient(at 8% 92%, rgba(37, 99, 235, 0.35) 0%, transparent 40%),
      linear-gradient(125deg, #1e1b4b 0%, #312e81 28%, #1e3a5f 55%, #0f172a 100%);
    animation: mesh-shift 18s ease-in-out infinite alternate;
  }

  @keyframes mesh-shift {
    0% {
      filter: hue-rotate(0deg) saturate(1.05);
    }
    100% {
      filter: hue-rotate(18deg) saturate(1.15);
    }
  }

  .neural-layer {
    position: absolute;
    inset: 0;
    z-index: 1;
    opacity: 0.22;
    background-image:
      radial-gradient(circle at 20% 30%, rgba(255, 255, 255, 0.9) 0, rgba(255, 255, 255, 0) 2px),
      radial-gradient(circle at 45% 55%, rgba(255, 255, 255, 0.75) 0, rgba(255, 255, 255, 0) 1.5px),
      radial-gradient(circle at 70% 25%, rgba(255, 255, 255, 0.85) 0, rgba(255, 255, 255, 0) 2px),
      radial-gradient(circle at 82% 70%, rgba(255, 255, 255, 0.65) 0, rgba(255, 255, 255, 0) 1.5px),
      radial-gradient(circle at 35% 78%, rgba(255, 255, 255, 0.7) 0, rgba(255, 255, 255, 0) 2px),
      linear-gradient(
        105deg,
        transparent 0%,
        rgba(255, 255, 255, 0.06) 40%,
        rgba(255, 255, 255, 0.12) 50%,
        rgba(255, 255, 255, 0.06) 60%,
        transparent 100%
      );
    background-size:
      100% 100%,
      100% 100%,
      100% 100%,
      100% 100%,
      100% 100%,
      200% 100%;
    animation: neural-sweep 12s linear infinite;
    pointer-events: none;
  }

  @keyframes neural-sweep {
    0% {
      background-position:
        0 0,
        0 0,
        0 0,
        0 0,
        0 0,
        0% 0;
    }
    100% {
      background-position:
        8px 4px,
        -6px 2px,
        4px -8px,
        -4px 6px,
        2px 8px,
        100% 0;
    }
  }

  .banner-content {
    position: relative;
    z-index: 2;
    max-width: 760px;
  }

  .title {
    margin-top: 0;
    margin-bottom: 8px;
    color: #f8fafc;
    text-shadow: 0 1px 24px rgba(99, 102, 241, 0.45);
  }

  .subtitle {
    margin-bottom: 12px;
    color: rgba(248, 250, 252, 0.88);
  }

  :deep(.arco-icon-home) {
    margin-right: 6px;
  }
</style>
