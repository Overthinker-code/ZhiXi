<template>
  <a-card class="general-card" :title="$t('monitor.title.studioPreview')">
    <template #extra>
      <icon-more />
    </template>
    <div class="studio-wrapper hud-video-shell">
      <svg class="hud-corners" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="hudLine" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#22d3ee" />
            <stop offset="100%" stop-color="#6366f1" />
          </linearGradient>
        </defs>
        <polyline
          class="hud-l"
          points="2,18 2,2 18,2"
          fill="none"
          stroke="url(#hudLine)"
          stroke-width="1.2"
        />
        <polyline
          class="hud-l"
          points="82,2 98,2 98,18"
          fill="none"
          stroke="url(#hudLine)"
          stroke-width="1.2"
        />
        <polyline
          class="hud-l"
          points="98,82 98,98 82,98"
          fill="none"
          stroke="url(#hudLine)"
          stroke-width="1.2"
        />
        <polyline
          class="hud-l"
          points="18,98 2,98 2,82"
          fill="none"
          stroke="url(#hudLine)"
          stroke-width="1.2"
        />
      </svg>
      <div class="hud-video-inner">
        <img
          src="http://p1-arco.byteimg.com/tos-cn-i-uwbnlip3yd/c788fc704d32cf3b1136c7d45afc2669.png~tplv-uwbnlip3yd-webp.webp"
          class="studio-preview"
        />
      </div>
      <div class="studio-bar">
        <div v-if="userInfo">
          <a-space :size="12">
            <a-avatar :size="24">
              <img :src="userInfo.avatar" />
            </a-avatar>
            <a-typography-text>
              {{ userInfo.name }} {{ $t('monitor.studioPreview.studio') }}
            </a-typography-text>
          </a-space>
        </div>
        <a-typography-text type="secondary">
          36,000 {{ $t('monitor.studioPreview.watching') }}
        </a-typography-text>
      </div>
    </div>
  </a-card>
</template>

<script lang="ts" setup>
  import { useUserStore } from '@/store';

  const userInfo = useUserStore();
</script>

<style scoped lang="less">
  .hud-video-shell {
    position: relative;
    padding: 10px;
    border-radius: 4px;
    box-shadow:
      0 0 32px rgba(14, 165, 233, 0.18),
      0 0 0 1px rgba(56, 189, 248, 0.15) inset;
    background: radial-gradient(
      80% 60% at 50% 0%,
      rgba(56, 189, 248, 0.08),
      transparent 55%
    );
  }

  .hud-corners {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 2;
    filter: drop-shadow(0 0 6px rgba(14, 165, 233, 0.45));
  }

  .hud-l {
    stroke-linecap: square;
    opacity: 0.95;
  }

  .hud-video-inner {
    position: relative;
    z-index: 1;
    border-radius: 2px;
    overflow: hidden;
  }

  .studio {
    &-preview {
      display: block;
      max-width: 600px;
      margin: 0 auto;
      width: 100%;
    }

    &-bar {
      display: flex;
      justify-content: space-between;
      margin-top: 16px;
    }
  }
</style>
