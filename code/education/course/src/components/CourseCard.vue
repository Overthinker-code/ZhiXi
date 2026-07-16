<template>
  <!--
    CourseCard.vue — 智屿品牌课程卡片
    课程总览专用：宽幅封面 | 分类 badge | 进度条 | 评分 | 继续学习
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
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
          />
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
          <img
            v-if="course.teacherAvatar"
            :src="course.teacherAvatar"
            :alt="course.teacher"
          />
          <span v-else class="teacher-avatar-fallback">{{
            course.teacher?.[0] || '师'
          }}</span>
        </div>
        <span class="teacher-name">{{ course.teacher || '未知教师' }}</span>
      </div>

      <!-- 学习进度条 -->
      <div v-if="course.progress !== undefined" class="progress-section">
        <a-progress
          :percent="normalizedProgress"
          :color="'#6366f1'"
          :track-color="'rgba(99,102,241,0.15)'"
          :show-text="false"
          size="small"
        />
        <span class="progress-text">{{ displayProgress }}% 已完成</span>
      </div>

      <!-- 底部行：评分 + 按钮 -->
      <div class="card-footer">
        <div class="rating">
          <span class="rating-star">☆</span>
          <span class="rating-score">{{ course.rating || '4.8' }}</span>
          <span v-if="course.reviewCount" class="rating-count">
            ({{ course.reviewCount }}人评价)
          </span>
        </div>
        <span class="continue-btn">
          继续学习
          <span aria-hidden="true">→</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';

  interface CourseCardData {
    id: string | number;
    name: string;
    category?: string;
    coverImage?: string;
    teacher?: string;
    teacherAvatar?: string;
    progress?: number;
    rating?: string | number;
    reviewCount?: number;
  }

  const props = defineProps<{ course: CourseCardData }>();
  defineEmits<{ (e: 'click', course: CourseCardData): void }>();

  const normalizedProgress = computed(() => {
    const value = Number(props.course.progress ?? 0);
    if (!Number.isFinite(value)) return 0;
    return Math.max(0, Math.min(1, value > 1 ? value / 100 : value));
  });

  const displayProgress = computed(() =>
    Math.round(normalizedProgress.value * 100)
  );

  const isFavorited = ref(false);
  const toggleFavorite = () => {
    isFavorited.value = !isFavorited.value;
  };
</script>

<style scoped>
  .course-card {
    display: flex;
    height: 100%;
    overflow: hidden;
    flex-direction: column;
    border: 1px solid #e7eaf2;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 3px 12px rgba(15, 23, 42, 0.045);
    cursor: pointer;
    transition: transform 200ms ease, box-shadow 200ms ease,
      border-color 200ms ease;
  }

  .course-card:hover {
    border-color: rgba(99, 102, 241, 0.3);
    box-shadow: 0 10px 24px rgba(79, 70, 229, 0.11);
    transform: translateY(-3px);
  }

  .card-cover {
    position: relative;
    width: 100%;
    overflow: hidden;
    aspect-ratio: 2.35 / 1;
    border-radius: 12px 12px 0 0;
    background: #eef2ff;
  }

  .cover-img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 260ms ease;
  }

  .course-card:hover .cover-img {
    transform: scale(1.025);
  }

  .category-badge {
    position: absolute;
    top: 10px;
    left: 10px;
    padding: 4px 10px;
    border-radius: 999px;
    background: rgba(79, 70, 229, 0.92);
    box-shadow: 0 2px 8px rgba(49, 46, 129, 0.2);
    color: #fff;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.02em;
  }

  .favorite-btn {
    position: absolute;
    top: 9px;
    right: 9px;
    display: flex;
    width: 32px;
    height: 32px;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    border: 1px solid rgba(226, 232, 240, 0.9);
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.94);
    color: #aaa;
    cursor: pointer;
    transition: color 160ms ease, background 160ms ease, border-color 160ms ease;
  }

  .favorite-btn:hover,
  .favorite-btn--active {
    border-color: #c7d2fe;
    background: #fff;
    color: #6366f1;
  }

  .favorite-btn--active svg {
    fill: #6366f1;
  }

  .card-body {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 7px;
    padding: 12px 14px 13px;
  }

  .course-name {
    display: -webkit-box;
    overflow: hidden;
    margin: 0;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 1;
    color: #0f172a;
    font-size: 15px;
    font-weight: 600;
    line-height: 1.4;
  }

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
    color: #64748b;
    font-size: 12px;
  }

  .progress-section {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .progress-section :deep(.arco-progress) {
    min-width: 0;
    flex: 1;
  }

  .progress-section :deep(.arco-progress-line-wrapper) {
    padding-right: 0;
  }

  .progress-text {
    color: #64748b;
    font-size: 11px;
    white-space: nowrap;
    flex-shrink: 0;
  }

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
    gap: 4px;
    min-width: 0;
  }

  .rating-star {
    color: #f5b400;
    font-size: 17px;
    line-height: 1;
  }

  .rating-score {
    color: #0f172a;
    font-size: 13px;
    font-weight: 600;
  }

  .rating-count {
    overflow: hidden;
    color: #94a3b8;
    font-size: 11px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .continue-btn {
    display: inline-flex;
    flex-shrink: 0;
    align-items: center;
    gap: 4px;
    color: #6366f1;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    transition: color 150ms ease;
  }

  .continue-btn:hover {
    color: #4f46e5;
  }
</style>
