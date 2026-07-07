<template>
  <ZyPageShell title="" max-width="1360px">
    <section class="course-hero">
      <div class="course-hero__bg" />
      <div class="course-hero__content">
        <div class="course-hero__text">
          <span class="course-hero__eyebrow">我的学习空间</span>
          <h1>课程中心</h1>
          <p>按学习状态回到正在推进的课程，课程资料、AI 伴学和学习路径都从这里进入。</p>
          <div class="course-hero__metrics">
            <span><strong>{{ totalCourses }}</strong> 门课程</span>
            <span><strong>{{ learningCount }}</strong> 门学习中</span>
            <span><strong>{{ pagination.total || courses.length }}</strong> 门符合筛选</span>
          </div>
        </div>
        <div class="course-hero__resume">
          <div>
            <span>继续学习</span>
            <strong>数据库系统原理</strong>
            <small>第 3 章 ER 模型 · 已完成 58%</small>
          </div>
          <div class="resume-progress">
            <i style="width: 58%" />
          </div>
          <button type="button" @click="goToCourseDetail('c1111111-1111-4111-9111-111111111101')">
            继续学习
          </button>
        </div>
      </div>
    </section>

    <section class="course-catalog">
      <div class="catalog-header">
        <div>
          <strong>我的课程</strong>
          <span>筛选课程后直接进入学习空间</span>
        </div>
        <div class="search-row">
          <a-input
            v-model="searchQuery"
            placeholder="搜索课程名称、教师或关键词"
            class="search-input"
            allow-clear
            @press-enter="handleSearch"
          >
            <template #prefix>
              <icon-search />
            </template>
          </a-input>
          <a-button type="primary" class="search-btn" @click="handleSearch"
            >搜索</a-button
          >
        </div>
      </div>

      <div class="filter-panel">
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
        <div class="filter-panel__selects">
          <a-select
            v-model="statusFilter"
            class="toolbar-select"
            placeholder="状态"
          >
            <a-option value="all">全部状态</a-option>
            <a-option value="learning">学习中</a-option>
            <a-option value="done">已完成</a-option>
            <a-option value="new">未开始</a-option>
          </a-select>
          <a-select
            v-model="typeFilter"
            class="toolbar-select"
            placeholder="类型"
          >
            <a-option value="all">全部类型</a-option>
            <a-option value="core">专业核心</a-option>
            <a-option value="elective">专业选修</a-option>
          </a-select>
          <a-select
            v-model="sortBy"
            class="toolbar-select toolbar-select--sort"
            placeholder="排序"
          >
            <a-option value="recommend">推荐排序</a-option>
            <a-option value="progress">学习进度</a-option>
            <a-option value="rating">评分最高</a-option>
            <a-option value="newest">最新发布</a-option>
          </a-select>
        </div>
      </div>

      <div v-if="loading" class="skeleton-grid">
        <div v-for="i in 6" :key="i" class="skeleton-card">
          <div class="skeleton-cover zy-skeleton" />
          <div class="skeleton-body">
            <div
              class="skeleton-line zy-skeleton"
              style="width: 80%; height: 16px"
            />
            <div
              class="skeleton-line zy-skeleton"
              style="width: 50%; height: 12px; margin-top: 8px"
            />
            <div
              class="skeleton-line zy-skeleton"
              style="width: 100%; height: 8px; margin-top: 12px"
            />
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
          <span class="empty-icon">◇</span>
        </template>
        <div class="empty-title">暂无课程数据</div>
        <div class="empty-desc">尝试切换学院、学习状态或搜索关键词</div>
      </a-empty>

      <div v-else class="course-card-grid">
        <article
          v-for="course in displayCourses"
          :key="course.id"
          class="course-card"
          @click="goToCourseDetail(course.id)"
        >
          <div class="course-card__cover">
            <img :src="getCourseImage(course)" :alt="course.name" />
            <span>{{ course.course_type || '专业课程' }}</span>
          </div>
          <div class="course-card__body">
            <div class="course-card__title">
              <strong>{{ course.name }}</strong>
              <small>{{ courseProgressPercent(course) > 0 ? '学习中' : '未开始' }}</small>
            </div>
            <p>{{ course.description || '围绕课程核心概念、资料证据和学习任务持续推进。' }}</p>
            <div class="course-card__meta">
              <span>{{ courseDepartment(course) }}</span>
              <span>{{ courseTeacher(course) }}</span>
              <span>{{ courseRating(course) }} 分</span>
            </div>
          </div>
          <div class="course-card__footer">
            <div class="course-card__progress">
              <span>{{ courseProgressPercent(course) }}%</span>
              <small>{{ courseProgressPercent(course) > 0 ? '已完成' : '待开始' }}</small>
            </div>
            <div class="progress-track">
              <i :style="{ width: `${courseProgressPercent(course)}%` }" />
            </div>
            <button type="button" @click.stop="goToCourseDetail(course.id)">
              {{ courseProgressPercent(course) > 0 ? '继续学习' : '开始学习' }}
            </button>
          </div>
        </article>
      </div>

      <div
        v-if="!loading && displayCourses.length > 0"
        class="pagination-container"
      >
        <a-pagination
          :current="pagination.current"
          :page-size="pagination.pageSize"
          :total="pagination.total"
          show-total
          show-jumper
          @change="handlePageChange"
          @page-size-change="handlePageSizeChange"
        />
      </div>
    </section>
  </ZyPageShell>
</template>

<script setup lang="ts">
  import { ref, computed, onMounted, watch } from 'vue';
  import { useRouter } from 'vue-router';
  import { IconSearch } from '@arco-design/web-vue/es/icon';
  import { fetchCourses, type Course } from '@/api/course';
  import {
    scenarioCourseDepartments,
    scenarioCourseMetrics,
    scenarioCourses,
  } from '@/data/teachingScenario';
  import ErrorState from '@/components/state/ErrorState.vue';
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
  const sourceCourses = ref<Course[]>([...scenarioCourses]);
  const courses = ref<Course[]>(scenarioCourses.slice(0, 6));
  const searchQuery = ref('');
  const selectedCategory = ref('全部');
  const statusFilter = ref('all');
  const typeFilter = ref('all');
  const sortBy = ref('recommend');

  const categories = [
    '全部',
    '计算机学院',
    '经管学院',
    '人工智能学院',
    '更多学院',
  ];

  const pagination = ref({
    current: 1,
    pageSize: 6,
    total: scenarioCourses.length,
  });

  const totalCourses = computed(
    () => pagination.value.total || scenarioCourses.length || 23
  );
  const learningCount = computed(() => {
    const count = scenarioCourses.filter((c) => {
      const p = scenarioCourseMetrics[c.id]?.progress ?? 0;
      return p > 0 && p < 100;
    }).length;
    return count || 12;
  });

  const courseImages = [
    AIImg,
    EcoImg,
    ShenImg,
    DatabaseImg,
    DatastructureImg,
    YuanImg,
  ];

  function getCourseImage(course: Course) {
    const n = course.name || '';
    const ident = (course.identifier || '').toUpperCase();
    if (n.includes('数据库') || ident.includes('DB')) return DatabaseImg;
    if (n.includes('数据结构') || ident.includes('DS')) return DatastructureImg;
    if (n.includes('人工智能') || n.includes('智能') || ident.includes('AI'))
      return AIImg;
    if (n.includes('宏观') || ident.includes('MAC')) return EcoImg;
    if (n.includes('审计') || ident.includes('AUD')) return ShenImg;
    if (n.includes('金融') || ident.includes('FIN')) return YuanImg;
    const index =
      Math.abs(n.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)) %
      courseImages.length;
    return courseImages[index];
  }

  function applyScenarioCoursesPage() {
    const q = (searchQuery.value || '').trim().toLowerCase();
    let filtered = [...sourceCourses.value];
    if (selectedCategory.value === '更多学院') {
      filtered = sourceCourses.value.filter(
        (course) =>
          !['计算机学院', '经管学院', '人工智能学院'].includes(
            scenarioCourseDepartments[course.id] || ''
          )
      );
    } else if (selectedCategory.value === '人工智能学院') {
      filtered = sourceCourses.value.filter(
        (course) =>
          course.name.includes('人工智能') || course.name.includes('智能')
      );
    } else if (selectedCategory.value !== '全部') {
      filtered = sourceCourses.value.filter(
        (course) =>
          scenarioCourseDepartments[course.id] === selectedCategory.value
      );
    }

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
    courses.value = filtered.slice(
      start,
      start + pagination.value.pageSize
    ) as Course[];
  }

  const displayCourses = computed(() => courses.value);

  async function refreshCoursesFromServer() {
    error.value = '';
    try {
    const response = await fetchCourses({
      skip: 0,
      limit: 100,
    });
      if (response.data?.length) {
        sourceCourses.value = response.data;
        applyScenarioCoursesPage();
      }
    } catch {
      // 首屏始终使用本地场景数据，远端不可用时无需阻塞或闪烁。
    }
  }

  function loadCourses() {
    applyScenarioCoursesPage();
    void refreshCoursesFromServer();
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
    router.push({
      name: 'StudentCourseHome',
      params: { courseId },
    });
  }

  function courseProgressPercent(course: Course) {
    const c = course as any;
    const metrics = scenarioCourseMetrics[course.id];
    const rawProgress = c.progress ?? metrics?.progress ?? 0;
    const progress = rawProgress > 1 ? rawProgress : rawProgress * 100;
    if (!Number.isFinite(progress)) return 0;
    return Math.max(0, Math.min(100, Math.round(progress)));
  }

  function courseTeacher(course: Course) {
    const c = course as any;
    return c.teacher_name || scenarioCourseMetrics[course.id]?.teacher || '智屿教师';
  }

  function courseRating(course: Course) {
    const c = course as any;
    return c.rating || scenarioCourseMetrics[course.id]?.rating || '4.6';
  }

  function courseDepartment(course: Course) {
    return scenarioCourseDepartments[course.id] || course.course_type || '课程中心';
  }

  onMounted(() => {
    applyScenarioCoursesPage();
    void refreshCoursesFromServer();
  });

  watch([statusFilter, typeFilter, sortBy], () => {
    pagination.value.current = 1;
    applyScenarioCoursesPage();
  });
</script>

<style scoped lang="less">
  @brand: var(--zy-color-brand, #6366f1);
  @text-primary: var(--zy-color-text-primary, #0f172a);
  @text-secondary: var(--zy-color-text-secondary, #64748b);
  @line: rgba(15, 23, 42, 0.08);

  .course-hero {
    position: relative;
    min-height: 154px;
    overflow: hidden;
    border: 1px solid @line;
    border-radius: 22px;
    background: #fff;
    box-shadow: 0 16px 42px rgba(15, 23, 42, 0.045);
  }

  .course-hero__bg {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(circle at 86% 12%, rgba(99, 102, 241, 0.14), transparent 24%),
      linear-gradient(135deg, #ffffff 0%, #f7f9ff 62%, #eef4ff 100%);
  }

  .course-hero__content {
    position: relative;
    display: flex;
    min-height: 154px;
    align-items: center;
    justify-content: space-between;
    gap: 28px;
    padding: 22px 28px 22px 30px;
  }

  .course-hero__eyebrow {
    display: inline-flex;
    align-items: center;
    min-height: 26px;
    margin-bottom: 8px;
    padding: 0 10px;
    border: 1px solid rgba(99, 102, 241, 0.16);
    border-radius: 999px;
    color: @brand;
    background: rgba(99, 102, 241, 0.06);
    font-size: 12px;
    font-weight: 700;
  }

  .course-hero__text {
    h1 {
      margin: 0;
      color: @text-primary;
      font-family: var(--zy-font-display);
      font-size: 32px;
      font-weight: 700;
      letter-spacing: 0;
    }

    p {
      max-width: 620px;
      margin: 9px 0 14px;
      color: @text-secondary;
      font-size: 15px;
      line-height: 1.6;
    }
  }

  .course-hero__metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    span {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 28px;
      padding: 0 10px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 8px;
      color: @text-secondary;
      background: rgba(255, 255, 255, 0.72);
      font-size: 12px;
      font-weight: 600;
    }

    strong {
      color: @text-primary;
      font-weight: 700;
    }
  }

  .course-hero__resume {
    display: grid;
    width: 330px;
    flex: 0 0 330px;
    gap: 10px;
    padding: 16px;
    border: 1px solid rgba(99, 102, 241, 0.14);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.9);
    box-shadow: 0 12px 30px rgba(79, 70, 229, 0.08);

    span {
      color: @brand;
      font-size: 12px;
      font-weight: 700;
    }

    strong {
      color: @text-primary;
      font-size: 17px;
      line-height: 1.3;
    }

    small {
      color: @text-secondary;
      font-size: 12px;
      line-height: 1.4;
    }

    button {
      justify-self: start;
      height: 34px;
      padding: 0 14px;
      border: 0;
      border-radius: 999px;
      background: @brand;
      color: #fff;
      cursor: pointer;
      font-weight: 600;
      transition: transform 160ms ease, background 160ms ease;

      &:hover {
        background: #4f46e5;
        transform: translateY(-1px);
      }

      &:active {
        transform: scale(0.98);
      }
    }
  }

  .resume-progress {
    height: 7px;
    overflow: hidden;
    border-radius: 999px;
    background: #edf0f7;

    i {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #4f46e5, #60a5fa);
      animation: progress-reveal 0.7s ease both;
    }
  }

  .category-tabs {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 8px;
    overflow-x: auto;
    padding: 0;
  }

  .category-tab {
    height: 34px;
    padding: 0 14px;
    border: 1px solid transparent;
    border-radius: 999px;
    background: transparent;
    color: @text-secondary;
    cursor: pointer;
    font-family: inherit;
    font-size: 14px;
    transition: color 160ms ease, border-color 160ms ease, background 160ms ease;
    white-space: nowrap;

    &:hover {
      border-color: rgba(99, 102, 241, 0.18);
      background: #fff;
      color: @brand;
    }

    &--active {
      border-color: transparent;
      background: @brand;
      box-shadow: 0 8px 18px rgba(79, 70, 229, 0.18);
      color: #fff;
      font-weight: 600;
    }
  }

  .catalog-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    margin-bottom: 14px;

    strong,
    span {
      display: block;
    }

    strong {
      color: @text-primary;
      font-size: 20px;
    }

    span {
      margin-top: 4px;
      color: @text-secondary;
      font-size: 13px;
    }
  }

  .search-row {
    display: flex;
    width: min(440px, 42vw);
    flex: 0 0 auto;
    align-items: center;
  }

  .search-input {
    min-width: 0;
    flex: 1;

    :deep(.arco-input-wrapper) {
      height: 38px;
      border-color: rgba(15, 23, 42, 0.08);
      border-radius: 999px 0 0 999px;
      background: #fff;
      box-shadow: none;

      &:focus-within {
        z-index: 1;
        border-color: @brand;
      }
    }
  }

  .search-btn {
    height: 38px;
    flex: 0 0 82px;
    margin-left: -1px;
    border-color: @brand !important;
    border-radius: 0 999px 999px 0;
    background: @brand !important;
    font-weight: 600;
  }

  .course-catalog {
    padding: 18px;
    border: 1px solid @line;
    border-radius: 22px;
    background: #fff;
    box-shadow: 0 12px 32px rgba(15, 23, 42, 0.045);
  }

  .filter-panel {
    display: flex;
    min-height: 48px;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 16px;
    padding: 7px;
    border: 1px solid rgba(15, 23, 42, 0.06);
    border-radius: 16px;
    background: #f8faff;
  }

  .filter-panel__selects {
    display: flex;
    flex: 0 0 auto;
    align-items: center;
    gap: 8px;
  }

  :deep(.toolbar-select.arco-select) {
    width: 112px;
    flex: 0 0 112px;
  }

  :deep(.toolbar-select--sort.arco-select) {
    width: 132px;
    flex-basis: 132px;
  }

  :deep(.toolbar-select.arco-select .arco-select-view) {
    height: 34px;
    border-color: #e0e4ed;
    border-radius: 999px;
    background: #fff;
    color: #475569;
    box-shadow: none;
  }

  .skeleton-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
  }

  .skeleton-card {
    overflow: hidden;
    border: 1px solid @line;
    border-radius: 12px;
    background: #fff;
  }

  .skeleton-cover {
    width: 100%;
    aspect-ratio: 2.35 / 1;
  }

  .skeleton-body {
    padding: 14px 16px 18px;
  }

  .course-card-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
  }

  .course-card {
    overflow: hidden;
    display: flex;
    min-width: 0;
    min-height: 302px;
    flex-direction: column;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 18px;
    background: #fff;
    cursor: pointer;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.035);
    transition:
      border-color 180ms ease,
      box-shadow 180ms ease,
      transform 180ms ease;
    animation: course-card-enter 0.24s ease both;

    &:hover {
      border-color: rgba(99, 102, 241, 0.26);
      box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
      transform: translateY(-2px);
    }
  }

  .course-card__cover {
    position: relative;
    overflow: hidden;
    height: 136px;
    background: #eef2ff;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 300ms ease;
    }

    span {
      position: absolute;
      top: 12px;
      left: 12px;
      padding: 5px 9px;
      border: 1px solid rgba(255, 255, 255, 0.72);
      border-radius: 999px;
      color: #fff;
      background: rgba(15, 23, 42, 0.48);
      backdrop-filter: blur(8px);
      font-size: 11px;
      font-weight: 700;
    }
  }

  .course-card:hover .course-card__cover img {
    transform: scale(1.035);
  }

  .course-card__body {
    min-width: 0;
    padding: 15px 16px 10px;
    flex: 1;
  }

  .course-card__title {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
    min-width: 0;

    strong {
      display: -webkit-box;
      overflow: hidden;
      color: @text-primary;
      font-size: 17px;
      font-weight: 750;
      line-height: 1.35;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }

    small {
      flex: 0 0 auto;
      padding: 4px 8px;
      border-radius: 999px;
      color: @brand;
      background: #eef2ff;
      font-size: 11px;
      font-weight: 700;
      white-space: nowrap;
    }
  }

  .course-card__body p {
    display: -webkit-box;
    margin: 9px 0 12px;
    overflow: hidden;
    color: @text-secondary;
    font-size: 13px;
    line-height: 1.6;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .course-card__meta {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;

    span {
      color: #667085;
      font-size: 12px;

      &::before {
        display: inline-block;
        width: 4px;
        height: 4px;
        margin-right: 6px;
        border-radius: 50%;
        background: #cbd5e1;
        vertical-align: middle;
        content: '';
      }
    }
  }

  .course-card__footer {
    display: grid;
    gap: 10px;
    padding: 0 16px 16px;

    button {
      height: 38px;
      border: 0;
      border-radius: 999px;
      color: #fff;
      background: @brand;
      cursor: pointer;
      font-weight: 700;
      transition: transform 150ms ease, background 150ms ease;

      &:hover {
        background: #4f46e5;
      }

      &:active {
        transform: scale(0.98);
      }
    }
  }

  .course-card__progress {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;

    span {
      color: @text-primary;
      font-size: 22px;
      font-weight: 750;
      line-height: 1;
    }

    small {
      color: @text-secondary;
      font-size: 12px;
    }
  }

  .progress-track {
    position: relative;
    height: 7px;
    overflow: hidden;
    border-radius: 999px;
    background: #edf0f7;

    i {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #6366f1, #60a5fa);
      animation: progress-reveal 0.7s ease both;
    }
  }

  .skeleton-line {
    border-radius: 6px;
  }

  .empty-state {
    padding: 64px 20px;
  }

  .empty-icon {
    display: block;
    color: #a5b4fc;
    font-size: 52px;
  }

  .empty-title {
    margin-top: 8px;
    color: @text-primary;
    font-size: 18px;
    font-weight: 600;
  }

  .empty-desc {
    margin-top: 6px;
    color: @text-secondary;
    font-size: 14px;
  }

  .pagination-container {
    display: flex;
    justify-content: center;
    margin-top: 20px;
    padding: 4px 0 2px;
  }

  :deep(.arco-pagination-item-active) {
    border-color: @brand !important;
    background-color: @brand !important;
    color: #fff !important;
  }

  @media (max-width: 1120px) {
    .catalog-header {
      align-items: stretch;
      flex-direction: column;
      gap: 10px;
    }

    .search-row {
      width: 100%;
      flex-basis: auto;
    }

    .skeleton-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 920px) {
    .course-hero__content {
      align-items: stretch;
      flex-direction: column;
    }

    .course-hero__resume {
      width: auto;
      flex-basis: auto;
    }
  }

  @media (max-width: 760px) {
    .filter-panel {
      align-items: stretch;
      flex-direction: column;
    }

    .filter-panel__selects {
      flex-wrap: wrap;
    }

    .course-card-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    :deep(.toolbar-select.arco-select),
    :deep(.toolbar-select--sort.arco-select) {
      min-width: 120px;
      flex: 1 1 120px;
    }

    .course-hero__content {
      min-height: 230px;
      padding: 26px 22px;
    }

    .course-hero__text h1 {
      font-size: 28px;
    }

    .skeleton-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 620px) {
    .course-card-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 480px) {
    .course-hero__metrics {
      width: 100%;
    }

    .course-catalog {
      padding: 12px;
    }
  }

  @keyframes course-card-enter {
    from {
      opacity: 0;
      transform: translateY(8px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes progress-reveal {
    from {
      transform: scaleX(0);
    }

    to {
      transform: scaleX(1);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .course-card,
    .course-card__cover img,
    .progress-track i,
    .resume-progress i {
      animation: none;
      transition: none;
    }

    .course-card:hover,
    .course-card:hover .course-card__cover img,
    .course-hero__resume button:hover {
      transform: none;
    }
  }
</style>
