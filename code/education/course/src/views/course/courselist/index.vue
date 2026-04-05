<template>
  <div>
    <a-container>
      <el-main>
        <div class="page-header">
          <h1>课程总览</h1>
        </div>

        <a-row :gutter="20" class="navbar-container">
          <a-col :span="12">
            <div class="navbar">
              <span
                v-for="category in categories"
                :key="category"
                class="navbar-item"
                :class="{ active: selectedCategory === category }"
                @click="selectCategory(category)"
              >
                {{ category }}
              </span>
            </div>
          </a-col>

          <a-col :span="12" class="search-container">
            <a-input-search
              :style="{ width: '320px' }"
              placeholder="搜索课程名称"
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
          </a-col>
        </a-row>

        <LoadingState v-if="loading" text="加载课程列表..." />

        <ErrorState
          v-else-if="error"
          :text="error"
          description="请检查网络连接或稍后重试"
          @retry="loadCourses"
        />

        <EmptyState
          v-else-if="courses.length === 0"
          text="暂无课程数据"
          description="请先在后台添加课程"
        />

        <template v-else>
          <a-row :gutter="10" justify="start" style="margin: 10px 20px">
            <a-col
              v-for="course in courses"
              :key="course.id"
              :span="8"
            >
              <div class="teacher-card" @click="goToCourseDetail(course.id)">
                <div class="teacher-image">
                  <img :src="getCourseImage(course)" :alt="course.name" />
                </div>
                <div class="teacher-details">
                  <p class="teacher-name">{{ course.name }}</p>
                  <p class="teacher-title">{{ course.course_type || '专业课程' }}</p>
                  <p class="teacher-department">{{ course.identifier }}</p>
                  <p class="teacher-email">{{ course.description || '暂无描述' }}</p>
                </div>
              </div>
            </a-col>
          </a-row>

          <div class="pagination-container">
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
        </template>
      </el-main>
    </a-container>
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

onMounted(() => {
  loadCourses();
});
</script>

<style scoped>
a-container {
  padding: 20px;
}

.page-header {
  margin-top: 30px;
  text-align: center;
}

h1 {
  font-weight: bold;
  font-size: 28px;
}

.navbar-container {
  margin-top: 20px;
  padding-left: 30px;
}

.navbar {
  display: flex;
  flex-direction: row;
  gap: 30px;
  justify-content: flex-start;
}

.navbar-item {
  padding: 5px 0;
  color: #555;
  font-size: 16px;
  white-space: nowrap;
  cursor: pointer;
}

.navbar-item:hover {
  color: #007bff;
}

.navbar-item.active {
  color: #007bff;
  font-weight: bold;
}

.search-container {
  display: flex;
  justify-content: flex-end;
}

.search-input {
  width: 300px;
  margin: 0 20px;
  font-size: 14px;
  background-color: #fff;
  border: 1px solid #007bff;
  border-radius: 4px;
}

.teacher-card {
  display: flex;
  flex-direction: column;
  margin-top: 20px;
  padding: 20px;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 8px rgb(0 0 0 / 10%);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.teacher-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgb(0 0 0 / 15%);
}

.teacher-image {
  width: 100%;
  margin: 0 auto;
}

.teacher-image img {
  width: 80%;
  margin-left: 10%;
  object-fit: cover;
  border-radius: 8px;
}

.teacher-details {
  flex-grow: 1;
  text-align: center;
}

.teacher-name {
  margin-top: 20px;
  color: #007bff;
  font-weight: bold;
  font-size: 20px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.teacher-title {
  color: #007bff;
  font-size: 18px;
}

.teacher-department,
.teacher-email {
  color: #888;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 30px;
  padding-bottom: 20px;
}
</style>
