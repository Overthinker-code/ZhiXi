<template>
  <!--
    CourseCard.vue — 智屿品牌课程卡片
    规格：designup.md §3.1
    16:9 封面 | 分类 badge | 进度条 | 评分 | 继续学习按钮
    hover: translateY(-4px) + 阴影加深
  -->
  <div class="course-card" @click="$emit('click', course)">
    <!-- ===== 封面图 ===== -->
    <div class="card-cover">
      <img :src="course.coverImage" :alt="course.name" class="cover-img" />

      <!-- 左上角：分类 Badge -->
      <span v-if="course.category" class="category-badge">
        {{ course.category }}
      </span>

      <!-- 右上角：收藏按钮 -->
      <button
        class="favorite-btn"
        :class="{ 'favorite-btn--active': isFavorited }"
        @click.stop="toggleFavorite"
        aria-label="收藏课程"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
        </svg>
      </button>
    </div>

    <!-- ===== 卡片主体 ===== -->
    <div class="card-body">
      <!-- 课程名 -->
      <h3 class="course-name">{{ course.name }}</h3>

      <!-- 教师行 -->
      <div class="teacher-row">
        <div class="teacher-avatar">
          <img v-if="course.teacherAvatar" :src="course.teacherAvatar" :alt="course.teacher" />
          <span v-else class="teacher-avatar-fallback">{{ course.teacher?.[0] || '师' }}</span>
        </div>
        <span class="teacher-name">{{ course.teacher || '未知教师' }}</span>
      </div>

      <!-- 学习进度条 -->
      <div v-if="course.progress !== undefined" class="progress-section">
        <a-progress
          :percent="course.progress"
          :color="'#6366f1'"
          :track-color="'rgba(99,102,241,0.15)'"
          size="small"
        />
        <span class="progress-text">已完成 {{ course.progress }}%</span>
      </div>

      <!-- 底部行：评分 + 按钮 -->
      <div class="card-footer">
        <div class="rating">
          <span class="rating-star">⭐</span>
          <span class="rating-score">{{ course.rating || '4.8' }}</span>
        </div>
        <span class="continue-btn">继续学习 →</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

interface CourseCardData {
  id: string | number;
  name: string;
  category?: string;
  coverImage?: string;
  teacher?: string;
  teacherAvatar?: string;
  progress?: number;
  rating?: string | number;
}

const props = defineProps<{ course: CourseCardData }>();
const emit = defineEmits<{ (e: 'click', course: CourseCardData): void }>();

const isFavorited = ref(false);
const toggleFavorite = () => {
  isFavorited.value = !isFavorited.value;
};
</script>

<style scoped>
/* 智屿课程卡片
   规格：洁白背景，16px 圆角，绿色阴影，hover 上浮
   文档：designup.md §3.1
*/
.course-card {
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 16px;
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.08);
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1),
    box-shadow 0.3s cubic-bezier(0.25, 0.8, 0.25, 1),
    border-color 0.25s ease;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.course-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 20px 40px -10px rgba(99, 102, 241, 0.32);
  border-color: rgba(99, 102, 241, 0.22);
}

/* ===== 封面 ===== */
.card-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: 16px 16px 0 0;
  background: linear-gradient(135deg, #eef2ff, #e0f2fe);
}

.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.4s ease;
}

.course-card:hover .cover-img {
  transform: scale(1.04);
}

/* 分类 Badge */
.category-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.95), rgba(139, 92, 246, 0.9));
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 9999px;
  letter-spacing: 0.03em;
  backdrop-filter: blur(4px);
}

/* 收藏按钮 */
.favorite-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #aaa;
  transition: color 0.2s ease, background 0.2s ease;
}

.favorite-btn:hover { color: #F97316; background: rgba(255,255,255,0.95); }
.favorite-btn--active { color: #F97316; fill: #F97316; }
.favorite-btn--active svg { fill: #F97316; }

/* ===== 卡片主体 ===== */
.card-body {
  padding: 14px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.course-name {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.4;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* 教师行 */
.teacher-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.teacher-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.teacher-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.teacher-avatar-fallback {
  font-size: 11px;
  color: #fff;
  font-weight: 600;
}

.teacher-name {
  font-size: 12px;
  color: #64748b;
}

/* 进度条 */
.progress-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-text {
  font-size: 11px;
  color: #64748b;
  white-space: nowrap;
  flex-shrink: 0;
}

/* 底部行 */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 4px;
}

.rating {
  display: flex;
  align-items: center;
  gap: 3px;
}

.rating-star { font-size: 13px; }
.rating-score { font-size: 13px; font-weight: 600; color: #0f172a; }

.continue-btn {
  font-size: 13px;
  font-weight: 500;
  color: #6366f1;
  cursor: pointer;
  transition: color 0.15s ease;
}

.continue-btn:hover { color: #4f46e5; }
</style>
