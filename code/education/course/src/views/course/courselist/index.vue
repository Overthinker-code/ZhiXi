<template>
  <div class="course-list-page">
    <!-- ===== 页面标题 ===== -->
    <div class="page-header">
      <h1 class="page-title">课程中心</h1>
      <p class="page-subtitle">探索智屿的知识岛屿，开启你的智慧航行 🏝️</p>
    </div>

    <!-- ===== 筛选栏 ===== -->
    <div class="filter-bar">
      <!-- 分类 Tabs -->
      <div class="category-tabs">
        <span
          v-for="category in categories"
          :key="category"
          class="category-tab"
          :class="{ 'category-tab--active': selectedCategory === category }"
          @click="selectCategory(category)"
        >
          {{ category }}
        </span>
      </div>

      <!-- 搜索框 -->
      <a-input-search
        :style="{ width: '280px' }"
        placeholder="搜索课程名称..."
        v-model="searchQuery"
        class="search-input"
        search-button
        @search="handleSearch"
        @press-enter="handleSearch"
      >
        <template #button-icon>
          <icon-search />
        </template>
        <template #button-default>搜索</template>
      </a-input-search>
    </div>

    <!-- ===== 骨架屏加载态 ===== -->
    <div v-if="loading" class="skeleton-grid">
      <div v-for="i in 8" :key="i" class="skeleton-card">
        <div class="skeleton-cover zy-skeleton"></div>
        <div class="skeleton-body">
          <div class="skeleton-line zy-skeleton" style="width: 80%; height: 16px;"></div>
          <div class="skeleton-line zy-skeleton" style="width: 50%; height: 12px; margin-top: 8px;"></div>
          <div class="skeleton-line zy-skeleton" style="width: 100%; height: 8px; margin-top: 12px;"></div>
        </div>
      </div>
    </div>

    <!-- ===== 错误态 ===== -->
    <ErrorState
      v-else-if="error"
      :text="error"
      description="请检查网络连接或稍后重试"
      @retry="loadCourses"
    />

    <!-- ===== 空态 ===== -->
    <div v-else-if="courses.length === 0" class="empty-state">
      <div class="empty-icon">🏝️</div>
      <p class="empty-title">暂无课程数据</p>
      <p class="empty-desc">去探索更多知识岛屿吧，或者检查后台课程配置</p>
    </div>

    <!-- ===== 课程网格 ===== -->
    <div v-else class="courses-grid">
      <CourseCard
        v-for="course in courses"
        :key="course.id"
        :course="adaptCourse(course)"
        @click="goToCourseDetail(course.id)"
      />
    </div>

    <!-- ===== 分页 ===== -->
    <div v-if="!loading && courses.length > 0" class="pagination-container">
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
  </div>
</template>


<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { fetchCourses, type Course } from '@/api/course';
import { demoCourses } from '@/mock/demoData';
import LoadingState from '@/components/state/LoadingState.vue';
import EmptyState from '@/components/state/EmptyState.vue';
import ErrorState from '@/components/state/ErrorState.vue';
import CourseCard from '@/components/CourseCard.vue';


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
const categories = ['全部', '计算机学院', '经管学院'];

const pagination = ref({
  current: 1,
  pageSize: 9,
  total: 0,
});

const courseImages = [AIImg, EcoImg, ShenImg, DatabaseImg, DatastructureImg, YuanImg];

/** 按课程名/课号匹配封面，避免哈希随机错配 */
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

function applyDemoCoursesPage() {
  const q = (searchQuery.value || '').trim().toLowerCase();
  const filtered = q
    ? demoCourses.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          (c.description && c.description.toLowerCase().includes(q)) ||
          c.identifier.toLowerCase().includes(q)
      )
    : [...demoCourses];
  const start = (pagination.value.current - 1) * pagination.value.pageSize;
  courses.value = filtered.slice(start, start + pagination.value.pageSize) as Course[];
  pagination.value.total = filtered.length;
}

async function loadCourses() {
  loading.value = true;
  error.value = '';
  try {
    const response = await fetchCourses({
      skip: (pagination.value.current - 1) * pagination.value.pageSize,
      limit: pagination.value.pageSize,
      name: searchQuery.value || undefined,
    });
    courses.value = response.data;
    pagination.value.total = response.count;
  } catch {
    applyDemoCoursesPage();
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

/** 将原始 Course 适配为 CourseCard 组件所需的格式 */
function adaptCourse(course: Course) {
  const c = course as any; // 后端动态字段，类型定义暂未覆盖
  return {
    id: course.id,
    name: course.name,
    category: course.course_type || '专业课程',
    coverImage: getCourseImage(course),
    teacher: c.teacher_name || '未知教师',
    teacherAvatar: undefined,
    progress: c.progress ?? Math.floor(Math.random() * 80 + 10),
    rating: c.rating || (4.5 + Math.random() * 0.5).toFixed(1),
  };
}


onMounted(() => {
  loadCourses();
});
</script>

<style scoped>
/* 智屿课程中心页 - 品牌升级
   文档：designup.md §3
*/

.course-list-page {
  padding: 24px 28px;
  min-height: 100%;
}

/* ===== 页面标题 ===== */
.page-header {
  text-align: center;
  padding: 32px 0 8px;
}

.page-title {
  font-size: 32px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 8px;
  font-family: var(--zy-font-display, "PingFang SC", sans-serif);
}

.page-subtitle {
  font-size: 15px;
  color: #64748b;
  margin: 0;
}

/* ===== 筛选栏 ===== */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 20px 0 16px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.12);
  margin-bottom: 24px;
}

.category-tabs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.category-tab {
  padding: 6px 16px;
  border-radius: 9999px;
  font-size: 14px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.category-tab:hover {
  color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
}

.category-tab--active {
  color: #6366f1;
  background: rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.3);
  font-weight: 600;
}

/* 搜索框结尾按鈕品牌化 */
:deep(.arco-btn-primary) {
  background-color: #6366f1 !important;
  border-color: #6366f1 !important;
}

/* ===== 骨架屏 ===== */
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

@media (max-width: 1200px) { .skeleton-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 768px)  { .skeleton-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 480px)  { .skeleton-grid { grid-template-columns: 1fr; } }

.skeleton-card {
  border-radius: 16px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 4px 24px rgba(99, 102, 241, 0.08);
}

.skeleton-cover {
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 0;
}

.skeleton-body {
  padding: 14px 16px 18px;
}

.skeleton-line {
  border-radius: 8px;
  height: 12px;
  margin-bottom: 4px;
}

/* ===== 空态 ===== */
.empty-state {
  text-align: center;
  padding: 80px 20px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  animation: zy-float 3s ease-in-out infinite;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 8px;
}

.empty-desc {
  font-size: 14px;
  color: #64748b;
  margin: 0;
}

/* ===== 课程网格 ===== */
.courses-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

@media (max-width: 1200px) { .courses-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 900px)  { .courses-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 480px)  { .courses-grid { grid-template-columns: 1fr; } }

/* ===== 分页 ===== */
.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 40px;
  padding-bottom: 32px;
}

:deep(.arco-pagination-item-active) {
  background-color: #6366f1 !important;
  border-color: #6366f1 !important;
  color: #fff !important;
}
</style>

