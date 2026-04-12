<template>
  <div class="home-banner-wrapper">
    <!-- 左侧：图片轮播 -->
    <div class="banner-carousel-area">
      <div class="banner-particles" aria-hidden="true" />
      <a-carousel
        :auto-play="{ interval: 4500, hoverToPause: true }"
        animation-name="fade"
        show-arrow="hover"
        indicator-type="dot"
        class="banner-carousel"
      >
        <a-carousel-item v-for="item in bannerList" :key="item.id">
          <img :src="item.image" :alt="item.title" class="banner-img" />
          <div class="banner-overlay">
            <span class="banner-tag">{{ item.tag }}</span>
            <div class="banner-title">{{ item.title }}</div>
            <div class="banner-desc">{{ item.desc }}</div>
          </div>
        </a-carousel-item>
      </a-carousel>
    </div>

    <!-- 右侧：快捷导航面板 -->
    <div class="banner-side-panel">
      <!-- 顶部标题 -->
      <div class="side-panel-header">
        <span class="header-icon">📚</span>
        <span class="header-title">学科课程</span>
      </div>

      <!-- 2x2 快捷操作按钮 -->
      <div class="quick-actions">
        <div
          v-for="btn in quickActions"
          :key="btn.id"
          class="quick-btn"
          @click="router.push(btn.path)"
        >
          <img v-if="btn.localIcon" :src="btn.localIcon" class="quick-btn-img" alt="" />
          <span v-else class="quick-btn-emoji">{{ btn.emoji }}</span>
          <span class="quick-btn-label">{{ btn.label }}</span>
        </div>
      </div>

      <!-- 分类导航列表 -->
      <div class="category-list">
        <div
          v-for="cat in categories"
          :key="cat.id"
          class="category-item"
          @click="router.push(cat.path)"
        >
          <span class="cat-icon">{{ cat.emoji }}</span>
          <span class="cat-name">{{ cat.name }}</span>
          <span class="cat-arrow">›</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';

// ── Banner 图片（按实际文件名导入）─────────────────────────
import banner1 from '@/assets/banners/banner1.png';
import banner2 from '@/assets/banners/banner2.jpg';
import banner3 from '@/assets/banners/bannner3.png'; // 原文件名多一个 n

// ── 快捷按钮图标 ─────────────────────────────────────────
import panIcon from '@/assets/icons/pan.jpg';

const router = useRouter();

// ── Banner 数据（可增减，与 bannerList 数组保持一致即可）──
const bannerList = [
  {
    id: 1,
    image: banner1,
    tag: '平台公告',
    title: '2025年「智屿」AI 智能教学平台正式上线',
    desc: '融合大模型、RAG 检索与行为分析，为高等教育提供智慧化解决方案。',
  },
  {
    id: 2,
    image: banner2,
    tag: 'AI 功能',
    title: '全新 AI 助手上线：支持 4 种教学模式',
    desc: '导师模式、考试模式、简洁模式、苏格拉底模式，满足不同学习场景。',
  },
  {
    id: 3,
    image: banner3,
    tag: '行为分析',
    title: '课堂行为智能分析系统 Beta 版开放',
    desc: '基于 YOLO 的实时专注度识别，帮助教师掌握课堂动态。',
  },
];

// ── 右侧快捷操作（2×2）──────────────────────────────────
const quickActions = [
  { id: 1, emoji: '📤',  localIcon: null,    label: '上传课件', path: '/upload' },
  { id: 2, emoji: '📖',  localIcon: null,    label: '我的课程', path: '/my-courses' },
  { id: 3, emoji: null,  localIcon: panIcon, label: '行为看板', path: '/dashboard' },
  { id: 4, emoji: '🏆',  localIcon: null,    label: '我的成就', path: '/achievements' },
];

// ── 分类导航列表（可自由增减）────────────────────────────
const categories = [
  { id: 1, emoji: '🧪', name: '实验教学',     path: '/course?category=lab' },
  { id: 2, emoji: '❤️', name: '特殊教育',     path: '/course?category=special' },
  { id: 3, emoji: '🤖', name: '人工智能教育', path: '/course?category=ai' },
  { id: 4, emoji: '📖', name: '阅读课',       path: '/course?category=reading' },
  { id: 5, emoji: '💻', name: '编程与技术',   path: '/course?category=tech' },
];
</script>

<style scoped>
/* ── 整体容器 ────────────────────────────────────────────── */
.home-banner-wrapper {
  display: flex;
  border-radius: 20px;
  overflow: hidden;
  box-shadow:
    0 4px 32px rgba(99, 102, 241, 0.12),
    0 1px 4px rgba(0, 0, 0, 0.06);
  margin-top: 40px;
  background: #ffffff;
  border: 1px solid rgba(99, 102, 241, 0.10);
  transition: box-shadow 0.3s ease;
}
.home-banner-wrapper:hover {
  box-shadow:
    0 8px 40px rgba(99, 102, 241, 0.18),
    0 2px 8px rgba(0, 0, 0, 0.08);
}

/* ── 左侧轮播区 ─────────────────────────────────────────── */
.banner-carousel-area {
  flex: 1;
  min-width: 0;
  position: relative;
}

/* 轻量粒子漂移（品牌紫 + 海洋青） */
.banner-particles {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  opacity: 0.42;
  background-image:
    radial-gradient(1.5px 1.5px at 12% 22%, rgba(99, 102, 241, 0.9), transparent),
    radial-gradient(1.5px 1.5px at 38% 18%, rgba(14, 165, 233, 0.85), transparent),
    radial-gradient(1.5px 1.5px at 72% 35%, rgba(139, 92, 246, 0.75), transparent),
    radial-gradient(1.5px 1.5px at 88% 12%, rgba(99, 102, 241, 0.7), transparent),
    radial-gradient(1.5px 1.5px at 55% 62%, rgba(14, 165, 233, 0.65), transparent),
    radial-gradient(1.5px 1.5px at 24% 78%, rgba(139, 92, 246, 0.55), transparent),
    radial-gradient(1.5px 1.5px at 66% 82%, rgba(99, 102, 241, 0.6), transparent);
  background-size: 110% 110%;
  animation: banner-particles-drift 22s linear infinite;
}

@keyframes banner-particles-drift {
  0% {
    transform: translate(0, 0);
    background-position: 0% 0%;
  }
  100% {
    transform: translate(-3%, -2%);
    background-position: 100% 100%;
  }
}

.banner-carousel {
  position: relative;
  z-index: 2;
  height: 330px;
}

.banner-img {
  width: 100%;
  height: 330px;
  object-fit: cover;
  display: block;
}

/* 渐变蒙版 + 文字 */
.banner-overlay {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 28px 32px;
  background: linear-gradient(
    to top,
    rgba(15, 23, 42, 0.82) 0%,
    rgba(30, 27, 75, 0.35) 55%,
    transparent 100%
  );
  pointer-events: none;
}

.banner-tag {
  display: inline-block;
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  color: #ffffff;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  padding: 3px 12px;
  border-radius: 9999px;
  margin-bottom: 10px;
  width: fit-content;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
}

.banner-title {
  font-size: 21px;
  font-weight: 800;
  color: #ffffff;
  line-height: 1.35;
  margin-bottom: 6px;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.3);
  letter-spacing: 0.01em;
}

.banner-desc {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.82);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.6;
}

/* Arco Carousel 覆写 */
:deep(.arco-carousel-arrow) {
  background: rgba(99, 102, 241, 0.55);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, 0.25);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  transition: background 0.2s, transform 0.2s;
}
:deep(.arco-carousel-arrow:hover) {
  background: #6366f1;
  transform: scale(1.1);
}
:deep(.arco-carousel-indicator-item) {
  background: rgba(255, 255, 255, 0.40);
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
:deep(.arco-carousel-indicator-item-active) {
  background: #ffffff;
  width: 26px;
}

/* ── 右侧快捷导航面板 ───────────────────────────────────── */
.banner-side-panel {
  width: 224px;
  flex-shrink: 0;
  background: #ffffff;
  border-left: 1px solid rgba(99, 102, 241, 0.12);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 顶部标题栏 */
.side-panel-header {
  padding: 15px 18px;
  background: linear-gradient(135deg, #f5f3ff 0%, #e8fbf1 100%);
  font-weight: 700;
  font-size: 15px;
  color: #0f172a;
  border-bottom: 1px solid rgba(99, 102, 241, 0.12);
  display: flex;
  align-items: center;
  gap: 7px;
  letter-spacing: 0.02em;
}

.header-icon {
  font-size: 17px;
  line-height: 1;
}

/* ── 2×2 快捷按钮 ─────────────────────────────────────── */
.quick-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: rgba(99, 102, 241, 0.10);
  border-bottom: 1px solid rgba(99, 102, 241, 0.10);
}

.quick-btn {
  background: #ffffff;
  padding: 14px 6px 12px;
  font-size: 12px;
  font-weight: 500;
  color: #2c4a3a;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  transition: background 0.18s ease, color 0.18s ease, transform 0.15s ease;
  user-select: none;
  position: relative;
  overflow: hidden;
}
.quick-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, rgba(99, 102, 241, 0.12) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.2s ease;
}
.quick-btn:hover {
  background: #f5f3ff;
  color: #6366f1;
}
.quick-btn:hover::after {
  opacity: 1;
}
.quick-btn:active {
  transform: scale(0.96);
}

.quick-btn-img {
  width: 24px;
  height: 24px;
  object-fit: contain;
  border-radius: 4px;
}

.quick-btn-emoji {
  font-size: 21px;
  line-height: 1;
}

.quick-btn-label {
  font-size: 12px;
  letter-spacing: 0.02em;
}

/* ── 分类列表 ─────────────────────────────────────────── */
.category-list {
  flex: 1;
  overflow-y: auto;
  scrollbar-width: none;
}
.category-list::-webkit-scrollbar {
  display: none;
}

.category-item {
  display: flex;
  align-items: center;
  padding: 11px 16px;
  cursor: pointer;
  border-bottom: 1px solid rgba(99, 102, 241, 0.07);
  font-size: 13px;
  color: #2c4a3a;
  transition: background 0.18s ease, padding-left 0.18s ease;
  user-select: none;
}
.category-item:last-child {
  border-bottom: none;
}
.category-item:hover {
  background: #f5fdf8;
  padding-left: 20px;
}
.category-item:hover .cat-arrow {
  color: #6366f1;
}

.cat-icon {
  margin-right: 9px;
  font-size: 15px;
  line-height: 1;
  flex-shrink: 0;
}

.cat-name {
  flex: 1;
  font-weight: 500;
  letter-spacing: 0.01em;
}

.cat-arrow {
  color: #8ab8a0;
  font-size: 18px;
  font-weight: 300;
  transition: color 0.18s ease;
  line-height: 1;
}

/* ── 响应式 ────────────────────────────────────────────── */
@media (max-width: 900px) {
  .banner-side-panel {
    width: 180px;
  }
}

@media (max-width: 768px) {
  .banner-side-panel {
    display: none;
  }
  .banner-carousel,
  .banner-img {
    height: 220px;
  }
  .banner-overlay {
    padding: 18px 20px;
  }
  .banner-title {
    font-size: 17px;
  }
}
</style>
