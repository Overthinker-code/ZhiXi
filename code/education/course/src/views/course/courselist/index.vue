<template>
  <ZyPageShell title="" max-width="1320px">
    <!-- Hero Banner -->
    <section class="course-hero">
      <div class="course-hero__bg" />
      <div class="course-hero__content">
        <div class="course-hero__text">
          <h1>课程中心</h1>
          <p>探索智屿知识岛屿，按学院筛选并进入你的学习旅程</p>
          <div class="course-hero__stats">
            <div class="stat-box">
              <span class="stat-box__value">{{ totalCourses }}</span>
              <span class="stat-box__label">全部课程</span>
            </div>
            <div class="stat-box">
              <span class="stat-box__value">{{ learningCount }}</span>
              <span class="stat-box__label">正在学习</span>
            </div>
          </div>
        </div>
        <div class="course-hero__deco" aria-hidden="true">
          <div class="grad-cap">
            <div class="grad-cap__top" />
            <div class="grad-cap__board" />
            <div class="grad-cap__tassel" />
          </div>
          <div class="deco-orb deco-orb--1" />
          <div class="deco-orb deco-orb--2" />
        </div>
      </div>
    </section>

    <!-- 学院 Tabs + 搜索 -->
    <div class="filter-section">
      <div class="category-tabs">
        <button
          v-for="category in categories"
          :key="category"
          type="button"
          class="category-tab"
          :class="{ 'category-tab--active': selectedCategory === category }"
          @click="selectCategory(category)"
        >
          {{ category }}
        </button>
      </div>

      <div class="search-row">
        <a-input
          v-model="searchQuery"
          placeholder="搜索课程名称、教师或关键词..."
          class="search-input"
          allow-clear
          @press-enter="handleSearch"
        >
          <template #prefix>
            <icon-search />
          </template>
        </a-input>
        <a-button type="primary" class="search-btn" @click="handleSearch">搜索</a-button>
      </div>
    </div>

    <!-- 列表工具栏 -->
    <div class="list-toolbar">
      <span class="list-toolbar__count">共 <strong>{{ pagination.total || courses.length }}</strong> 门课程</span>
      <div class="list-toolbar__controls">
        <a-select v-model="statusFilter" size="small" class="toolbar-select" placeholder="状态">
          <a-option value="all">全部状态</a-option>
          <a-option value="learning">学习中</a-option>
          <a-option value="done">已完成</a-option>
          <a-option value="new">未开始</a-option>
        </a-select>
        <a-select v-model="typeFilter" size="small" class="toolbar-select" placeholder="类型">
          <a-option value="all">全部类型</a-option>
          <a-option value="core">专业核心</a-option>
          <a-option value="elective">专业选修</a-option>
        </a-select>
        <a-select v-model="sortBy" size="small" class="toolbar-select" placeholder="排序">
          <a-option value="recommend">推荐排序</a-option>
          <a-option value="progress">学习进度</a-option>
          <a-option value="rating">评分最高</a-option>
          <a-option value="newest">最新发布</a-option>
        </a-select>
        <div class="view-toggle">
          <button
            type="button"
            class="view-toggle__btn"
            :class="{ 'view-toggle__btn--active': viewMode === 'grid' }"
            aria-label="网格视图"
            @click="viewMode = 'grid'"
          >
            <icon-apps />
          </button>
          <button
            type="button"
            class="view-toggle__btn"
            :class="{ 'view-toggle__btn--active': viewMode === 'list' }"
            aria-label="列表视图"
            @click="viewMode = 'list'"
          >
            <icon-unordered-list />
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="skeleton-grid">
      <div v-for="i in 6" :key="i" class="skeleton-card">
        <div class="skeleton-cover zy-skeleton" />
        <div class="skeleton-body">
          <div class="skeleton-line zy-skeleton" style="width: 80%; height: 16px;" />
          <div class="skeleton-line zy-skeleton" style="width: 50%; height: 12px; margin-top: 8px;" />
          <div class="skeleton-line zy-skeleton" style="width: 100%; height: 8px; margin-top: 12px;" />
        </div>
      </div>
    </div>

    <ErrorState
      v-else-if="error"
      :text="error"
      description="请检查网络连接或稍后重试"
      @retry="loadCourses"
    />

    <a-empty v-else-if="displayCourses.length === 0" class="empty-state">
      <template #image>
        <span class="empty-icon">🏝️</span>
      </template>
      <div class="empty-title">暂无课程数据</div>
      <div class="empty-desc">去探索更多知识岛屿吧，或者检查后台课程配置</div>
    </a-empty>

    <div
      v-else
      :class="viewMode === 'grid' ? 'courses-grid' : 'courses-list'"
    >
      <CourseCard
        v-for="course in displayCourses"
        :key="course.id"
        :course="adaptCourse(course)"
        @click="goToCourseDetail(course.id)"
      />
    </div>

    <div v-if="!loading && displayCourses.length > 0" class="pagination-container">
      <a-pagination
        :current="pagination.current"
        :pageSize="pagination.pageSize"
        :total="pagination.total"
        show-total
        show-jumper
        @change="handlePageChange"
        @pageSizeChange="handlePageSizeChange"
      />
    </div>
  </ZyPageShell>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { IconSearch, IconApps, IconUnorderedList } from '@arco-design/web-vue/es/icon';
import { fetchCourses, type Course } from '@/api/course';
import {
  scenarioCourseDepartments,
  scenarioCourseMetrics,
  scenarioCourses,
} from '@/data/teachingScenario';
import ErrorState from '@/components/state/ErrorState.vue';
import CourseCard from '@/components/CourseCard.vue';
import ZyPageShell from '@/components/zy/ZyPageShell.vue';

import AIImg from '@/assets/images/AI.jpg';
import EcoImg from '@/assets/images/宏观经济学.jpg';
import ShenImg from '@/assets/images/审计学.jpg';
import DatabaseImg from '@/assets/images/数据库图片.png';
import DatastructureImg from '@/assets/images/数据结构.jpg';
import YuanImg from '@/assets/images/金融学.jpg';

const router = useRouter();

const loading = ref(false);
const error = ref('');
const courses = ref<Course[]>([]);
const searchQuery = ref('');
const selectedCategory = ref('全部');
const viewMode = ref<'grid' | 'list'>('grid');
const statusFilter = ref('all');
const typeFilter = ref('all');
const sortBy = ref('recommend');

const categories = ['全部', '计算机学院', '经管学院', '人工智能学院', '更多学院'];

const pagination = ref({
  current: 1,
  pageSize: 6,
  total: 0,
});

const totalCourses = computed(() => pagination.value.total || scenarioCourses.length || 23);
const learningCount = computed(() => {
  const count = scenarioCourses.filter((c) => {
    const p = scenarioCourseMetrics[c.id]?.progress ?? 0;
    return p > 0 && p < 100;
  }).length;
  return count || 12;
});

const courseImages = [AIImg, EcoImg, ShenImg, DatabaseImg, DatastructureImg, YuanImg];

function getCourseImage(course: Course) {
  const n = course.name || '';
  const ident = (course.identifier || '').toUpperCase();
  if (n.includes('数据库') || ident.includes('DB')) return DatabaseImg;
  if (n.includes('数据结构') || ident.includes('DS')) return DatastructureImg;
  if (n.includes('人工智能') || n.includes('智能') || ident.includes('AI')) return AIImg;
  if (n.includes('宏观') || ident.includes('MAC')) return EcoImg;
  if (n.includes('审计') || ident.includes('AUD')) return ShenImg;
  if (n.includes('金融') || ident.includes('FIN')) return YuanImg;
  const index = Math.abs(
    n.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  ) % courseImages.length;
  return courseImages[index];
}

function applyScenarioCoursesPage() {
  const q = (searchQuery.value || '').trim().toLowerCase();
  let filtered =
    selectedCategory.value === '全部'
      ? [...scenarioCourses]
      : selectedCategory.value === '更多学院'
        ? scenarioCourses.filter(
            (c) => !['计算机学院', '经管学院', '人工智能学院'].includes(
              scenarioCourseDepartments[c.id] || ''
            )
          )
        : selectedCategory.value === '人工智能学院'
          ? scenarioCourses.filter((c) =>
              c.name.includes('人工智能') || c.name.includes('智能')
            )
          : scenarioCourses.filter(
              (course) => scenarioCourseDepartments[course.id] === selectedCategory.value
            );

  if (q) {
    filtered = filtered.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        (c.description && c.description.toLowerCase().includes(q)) ||
        c.identifier.toLowerCase().includes(q)
    );
  }

  if (typeFilter.value === 'core') {
    filtered = filtered.filter((c) => c.course_type === '专业核心');
  } else if (typeFilter.value === 'elective') {
    filtered = filtered.filter((c) => c.course_type === '专业选修');
  }

  if (statusFilter.value !== 'all') {
    filtered = filtered.filter((c) => {
      const p = scenarioCourseMetrics[c.id]?.progress ?? 0;
      if (statusFilter.value === 'learning') return p > 0 && p < 100;
      if (statusFilter.value === 'done') return p >= 100;
      if (statusFilter.value === 'new') return p === 0;
      return true;
    });
  }

  if (sortBy.value === 'progress') {
    filtered.sort(
      (a, b) =>
        (scenarioCourseMetrics[b.id]?.progress ?? 0) -
        (scenarioCourseMetrics[a.id]?.progress ?? 0)
    );
  } else if (sortBy.value === 'rating') {
    filtered.sort(
      (a, b) =>
        parseFloat(scenarioCourseMetrics[b.id]?.rating ?? '0') -
        parseFloat(scenarioCourseMetrics[a.id]?.rating ?? '0')
    );
  } else if (sortBy.value === 'newest') {
    filtered.sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }

  pagination.value.total = filtered.length;
  const start = (pagination.value.current - 1) * pagination.value.pageSize;
  courses.value = filtered.slice(start, start + pagination.value.pageSize) as Course[];
}

const displayCourses = computed(() => courses.value);

async function loadCourses() {
  loading.value = true;
  error.value = '';
  try {
    const response = await fetchCourses({
      skip: (pagination.value.current - 1) * pagination.value.pageSize,
      limit: pagination.value.pageSize,
      name: searchQuery.value || undefined,
    });
    if (response.data?.length || searchQuery.value) {
      courses.value = response.data || [];
      pagination.value.total = response.count || 0;
    } else {
      applyScenarioCoursesPage();
    }
  } catch {
    applyScenarioCoursesPage();
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.value.current = 1;
  loadCourses();
}

function selectCategory(category: string) {
  selectedCategory.value = category;
  pagination.value.current = 1;
  loadCourses();
}

function handlePageChange(page: number) {
  pagination.value.current = page;
  loadCourses();
}

function handlePageSizeChange(pageSize: number) {
  pagination.value.pageSize = pageSize;
  pagination.value.current = 1;
  loadCourses();
}

function goToCourseDetail(courseId: string) {
  router.push(`/course/detail/${courseId}`);
}

function adaptCourse(course: Course) {
  const c = course as any;
  const metrics = scenarioCourseMetrics[course.id];
  const rawProgress = c.progress ?? metrics?.progress ?? 0;
  const progress = rawProgress > 1 ? rawProgress / 100 : rawProgress;
  return {
    id: course.id,
    name: course.name,
    category: course.course_type || '专业课程',
    coverImage: getCourseImage(course),
    teacher: c.teacher_name || metrics?.teacher || '智屿教师',
    teacherAvatar: undefined,
    progress,
    rating: c.rating || metrics?.rating || '4.6',
  };
}

onMounted(() => {
  loadCourses();
});

watch([statusFilter, typeFilter, sortBy], () => {
  pagination.value.current = 1;
  loadCourses();
});
</script>

<style scoped lang="less">
/* ===== Hero Banner ===== */
.course-hero {
  position: relative;
  border-radius: var(--zy-radius-card, 16px);
  overflow: hidden;
  min-height: 200px;
  margin-bottom: 24px;
}

.course-hero__bg {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(135deg, rgba(15, 23, 42, 0.88) 0%, rgba(49, 46, 129, 0.75) 55%, rgba(79, 70, 229, 0.6) 100%),
    url('@/assets/media/banner-lecture.jpg') center / cover no-repeat;
}

.course-hero__content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 36px 40px;
  gap: 24px;
  min-height: 200px;
}

.course-hero__text {
  h1 {
    margin: 0;
    font-size: 32px;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.02em;
  }

  p {
    margin: 10px 0 20px;
    font-size: 15px;
    color: rgba(255, 255, 255, 0.78);
    max-width: 480px;
    line-height: 1.6;
  }
}

.course-hero__stats {
  display: flex;
  gap: 16px;
}

.stat-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 22px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.18);
  min-width: 120px;

  &__value {
    font-size: 28px;
    font-weight: 700;
    color: #fff;
    line-height: 1;
  }

  &__label {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.72);
  }
}

.course-hero__deco {
  position: relative;
  width: 160px;
  height: 140px;
  flex-shrink: 0;
}

.grad-cap {
  position: absolute;
  right: 20px;
  top: 10px;
  z-index: 2;

  &__board {
    width: 80px;
    height: 14px;
    background: linear-gradient(135deg, #1e1b4b, #312e81);
    border-radius: 4px;
    transform: perspective(120px) rotateX(25deg);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  }

  &__top {
    position: absolute;
    top: -18px;
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 42px solid transparent;
    border-right: 42px solid transparent;
    border-bottom: 28px solid #4338ca;
    filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3));
  }

  &__tassel {
    position: absolute;
    top: 8px;
    right: -8px;
    width: 3px;
    height: 36px;
    background: linear-gradient(180deg, #fbbf24, #f59e0b);
    border-radius: 2px;

    &::after {
      content: '';
      position: absolute;
      bottom: -6px;
      left: -4px;
      width: 11px;
      height: 11px;
      background: #fbbf24;
      border-radius: 50%;
    }
  }
}

.deco-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(1px);

  &--1 {
    width: 90px;
    height: 90px;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at 30% 30%, rgba(139, 92, 246, 0.7), rgba(99, 102, 241, 0.2));
    animation: float-orb 4s ease-in-out infinite;
  }

  &--2 {
    width: 50px;
    height: 50px;
    right: 60px;
    top: 0;
    background: radial-gradient(circle at 30% 30%, rgba(167, 139, 250, 0.6), transparent);
    animation: float-orb 3s ease-in-out infinite reverse;
  }
}

@keyframes float-orb {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

/* ===== Filter Section ===== */
.filter-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

.category-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.category-tab {
  padding: 7px 18px;
  border-radius: var(--zy-radius-pill, 9999px);
  font-size: var(--zy-text-sm, 14px);
  color: var(--zy-color-text-secondary, #64748b);
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1.5px solid transparent;
  background: #fff;
  font-family: inherit;
  box-shadow: 0 1px 4px rgba(99, 102, 241, 0.08);

  &:hover {
    color: var(--zy-color-brand, #6366f1);
    border-color: rgba(99, 102, 241, 0.25);
  }

  &--active {
    color: var(--zy-color-brand, #6366f1);
    background: var(--zy-bg-tag, #eef2ff);
    border-color: var(--zy-color-brand, #6366f1);
    font-weight: 600;
  }
}

.search-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-input {
  flex: 1;
  max-width: 100%;

  :deep(.arco-input-wrapper) {
    border-radius: 10px;
    border-color: rgba(99, 102, 241, 0.2);
    height: 42px;
    background: #fff;
  }
}

.search-btn {
  height: 42px;
  padding: 0 28px;
  border-radius: 10px;
  background: var(--zy-color-brand, #6366f1) !important;
  border-color: var(--zy-color-brand, #6366f1) !important;
  font-weight: 600;
  flex-shrink: 0;
}

/* ===== List Toolbar ===== */
.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px 0 16px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.12);
  margin-bottom: 20px;

  &__count {
    font-size: var(--zy-text-sm, 14px);
    color: var(--zy-color-text-secondary, #64748b);

    strong {
      color: var(--zy-color-brand, #6366f1);
      font-weight: 700;
    }
  }

  &__controls {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }
}

.toolbar-select {
  width: 120px;

  :deep(.arco-select-view-single) {
    border-radius: 8px;
    border-color: rgba(99, 102, 241, 0.15);
  }
}

.view-toggle {
  display: flex;
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 8px;
  overflow: hidden;

  &__btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 32px;
    border: none;
    background: #fff;
    color: var(--zy-color-text-secondary, #64748b);
    cursor: pointer;
    transition: all 0.15s ease;

    &--active {
      background: var(--zy-bg-tag, #eef2ff);
      color: var(--zy-color-brand, #6366f1);
    }

    &:hover:not(&--active) {
      background: rgba(99, 102, 241, 0.06);
    }
  }
}

/* ===== Course Grid / List ===== */
.skeleton-grid,
.courses-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.courses-list {
  display: flex;
  flex-direction: column;
  gap: 12px;

  :deep(.course-card) {
    flex-direction: row;

    .card-cover {
      width: 220px;
      flex-shrink: 0;
      aspect-ratio: 16 / 9;
      border-radius: 16px 0 0 16px;
    }

    .card-body {
      flex: 1;
      justify-content: center;
    }
  }
}

@media (max-width: 1200px) {
  .skeleton-grid,
  .courses-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .course-hero__content {
    flex-direction: column;
    padding: 28px 24px;
  }

  .course-hero__deco {
    display: none;
  }

  .skeleton-grid,
  .courses-grid {
    grid-template-columns: 1fr;
  }

  .courses-list :deep(.course-card) {
    flex-direction: column;

    .card-cover {
      width: 100%;
      border-radius: 16px 16px 0 0;
    }
  }
}

.skeleton-card {
  border-radius: var(--zy-radius-card, 16px);
  overflow: hidden;
  background: #fff;
  box-shadow: var(--zy-shadow-card);
}

.skeleton-cover {
  width: 100%;
  aspect-ratio: 16 / 9;
}

.skeleton-body {
  padding: 14px 16px 18px;
}

.skeleton-line {
  border-radius: var(--zy-radius-sm, 6px);
}

.empty-state {
  padding: 64px 20px;
}

.empty-icon {
  font-size: 56px;
  display: block;
  animation: zy-float 3s ease-in-out infinite;
}

.empty-title {
  font-size: var(--zy-text-lg, 18px);
  font-weight: 600;
  color: var(--zy-color-text-primary, #0f172a);
  margin-top: 8px;
}

.empty-desc {
  font-size: var(--zy-text-sm, 14px);
  color: var(--zy-color-text-secondary, #64748b);
  margin-top: 6px;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 32px;
  padding-bottom: 8px;
}

:deep(.arco-pagination-item-active) {
  background-color: var(--zy-color-brand, #6366f1) !important;
  border-color: var(--zy-color-brand, #6366f1) !important;
  color: #fff !important;
}
</style>
