<template>
  <a-col class="banner">
    <div class="banner-main">
      <div class="banner-content">
        <a-typography-title :heading="4" class="title">
          {{ $t('workplace.welcome') }} {{ userInfo.name }}
        </a-typography-title>
        <a-typography-paragraph class="subtitle">
          {{ $t('workplace.subtitle') }}
        </a-typography-paragraph>
        <a-space :size="8" wrap>
          <a-tag color="arcoblue">{{ $t('workplace.tag.lab') }}</a-tag>
          <a-tag color="cyan">{{ $t('workplace.tag.analysis') }}</a-tag>
          <a-tag color="green">{{ $t('workplace.tag.assessment') }}</a-tag>
        </a-space>
      </div>
      <div class="banner-grid" aria-hidden="true"></div>
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
    background-color: var(--color-bg-2);
    border-radius: 14px 14px 0 0;
  }

  .banner-main {
    position: relative;
    padding: 22px 24px;
    border-radius: 12px;
    background: linear-gradient(
      135deg,
      rgba(11, 51, 94, 0.96),
      rgba(0, 111, 145, 0.92)
    );
    overflow: hidden;
  }

  .banner-content {
    position: relative;
    z-index: 2;
    max-width: 760px;
  }

  .title {
    margin-top: 0;
    margin-bottom: 8px;
    color: #f3f8ff;
  }

  .subtitle {
    margin-bottom: 12px;
    color: rgba(243, 248, 255, 0.86);
  }

  .banner-grid {
    position: absolute;
    top: -40px;
    right: -20px;
    width: 360px;
    height: 220px;
    z-index: 1;
    opacity: 0.28;
    background-image:
      linear-gradient(rgba(255, 255, 255, 0.4) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255, 255, 255, 0.4) 1px, transparent 1px);
    background-size: 18px 18px;
    transform: rotate(-8deg);
  }

  :deep(.arco-icon-home) {
    margin-right: 6px;
  }
</style>
