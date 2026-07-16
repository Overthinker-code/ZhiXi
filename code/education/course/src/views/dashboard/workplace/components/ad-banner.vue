<template>
  <div class="ad-banner-wrap">
    <div class="ad-banner-inner">
      <div class="ad-banner-track" :style="trackStyle">
        <div
          v-for="(img, idx) in banners"
          :key="idx"
          class="ad-banner-slide"
        >
          <img :src="img.src" :alt="img.alt" class="ad-banner-img" />
        </div>
      </div>

      <!-- 指示点 -->
      <div class="ad-banner-dots">
        <span
          v-for="(_, idx) in banners"
          :key="idx"
          class="dot"
          :class="{ active: current === idx }"
          @click="goTo(idx)"
        />
      </div>

      <!-- 左右箭头 -->
      <button class="arrow arrow-left" aria-label="上一张" @click="prev">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
      <button class="arrow arrow-right" aria-label="下一张" @click="next">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="9 6 15 12 9 18" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';

import banner1 from '@/assets/banners/banner1.png';
import banner2 from '@/assets/banners/banner2.jpg';
import banner3 from '@/assets/banners/bannner3.png';

const banners = [
  { src: banner1, alt: '推广图1' },
  { src: banner2, alt: '推广图2' },
  { src: banner3, alt: '推广图3' },
];

const current = ref(0);
const trackStyle = computed(() => ({
  transform: `translateX(-${current.value * 100}%)`,
}));

function goTo(idx: number) {
  current.value = idx;
}
function next() {
  current.value = (current.value + 1) % banners.length;
}
function prev() {
  current.value = (current.value - 1 + banners.length) % banners.length;
}

let timer: ReturnType<typeof setInterval>;
onMounted(() => {
  timer = setInterval(next, 4000);
});
onBeforeUnmount(() => {
  clearInterval(timer);
});
</script>

<style scoped lang="less">
/* 外层：与紫色 banner 对齐，左右各 20px padding */
.ad-banner-wrap {
  position: relative;
  padding: 0 20px 20px;   /* 左右收窄，底部留间距 */
  background: transparent;

  &:hover .ad-banner-inner .arrow {
    opacity: 1;
  }
}

/* 内层：aspect-ratio 与图片原始尺寸 1638×1080 保持一致，宽度自适应后高度自动跟随 */
.ad-banner-inner {
  position: relative;
  width: 100%;
  aspect-ratio: 1638 / 1080;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(31, 38, 135, 0.08);
}

.ad-banner-track {
  display: flex;
  width: 100%;
  height: 100%;
  transition: transform 0.55s cubic-bezier(0.4, 0, 0.2, 1);
}

.ad-banner-slide {
  flex: 0 0 100%;
  height: 100%;
}

.ad-banner-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
  display: block;
}

/* 指示点 */
.ad-banner-dots {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 6px;
  z-index: 10;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.55);
  cursor: pointer;
  transition: all 0.3s;

  &.active {
    width: 18px;
    border-radius: 4px;
    background: #fff;
  }
}

/* 箭头 */
.arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.28);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.25s, background 0.2s;
  z-index: 10;
  padding: 0;

  &:hover {
    background: rgba(0, 0, 0, 0.48);
  }

  svg {
    width: 16px;
    height: 16px;
  }
}

.arrow-left  { left: 10px; }
.arrow-right { right: 10px; }
</style>
