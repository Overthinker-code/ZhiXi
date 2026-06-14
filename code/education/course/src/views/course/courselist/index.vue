<template>
  <ZyPageShell title="" max-width="1320px">
    <!-- Hero Banner -->
    <section class="course-hero">
      <div class="course-hero__bg" />
      <div class="course-hero__content">
        <div class="course-hero__text">
          <h1>课程中心</h1>
          <p>探索知识的边界，系统化学习专业课程，成就更好的自己。</p>
          <div class="course-hero__stats">
            <div class="stat-box">
              <span class="stat-box__icon">
                <icon-apps />
              </span>
              <span class="stat-box__content">
                <span class="stat-box__label">全部课程</span>
                <span class="stat-box__value"
                  >{{ totalCourses }}<small> 门</small></span
                >
              </span>
            </div>
            <div class="stat-box">
              <span class="stat-box__icon stat-box__icon--learning">◆</span>
              <span class="stat-box__content">
                <span class="stat-box__label">正在学习</span>
                <span class="stat-box__value"
                  >{{ learningCount }}<small> 门</small></span
                >
              </span>
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
        <a-button type="primary" class="search-btn" @click="handleSearch"
          >搜索</a-button
        >
      </div>
    </div>

    <section class="course-catalog">
      <!-- 列表工具栏 -->
      <div class="list-toolbar">
        <span class="list-toolbar__count">
          共 <strong>{{ pagination.total || courses.length }}</strong> 门课程
        </span>
        <div class="list-toolbar__controls">
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
          <div class="view-toggle">
            <button
              type="button"
              class="view-toggle__btn"
              :class="{ 'view-toggle__btn--active': viewMode === 'grid' }"
              :aria-pressed="viewMode === 'grid'"
              aria-label="网格视图"
              @click="viewMode = 'grid'"
            >
              <icon-apps />
            </button>
            <button
              type="button"
              class="view-toggle__btn"
              :class="{ 'view-toggle__btn--active': viewMode === 'list' }"
              :aria-pressed="viewMode === 'list'"
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
  import {
    IconSearch,
    IconApps,
    IconUnorderedList,
  } from '@arco-design/web-vue/es/icon';
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
  const sourceCourses = ref<Course[]>([...scenarioCourses]);
  const courses = ref<Course[]>(scenarioCourses.slice(0, 6));
  const searchQuery = ref('');
  const selectedCategory = ref('全部');
  const viewMode = ref<'grid' | 'list'>('grid');
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
      reviewCount: c.review_count || metrics?.learners || 0,
    };
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
  @line: #e7eaf2;

  .course-hero {
    position: relative;
    min-height: 210px;
    overflow: hidden;
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: 12px;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
  }

  .course-hero__bg {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        90deg,
        rgba(10, 20, 48, 0.94) 0%,
        rgba(15, 27, 61, 0.83) 48%,
        rgba(22, 32, 77, 0.54) 100%
      ),
      url('@/assets/media/banner-lecture.jpg') center 48% / cover no-repeat;
    transform: scale(1.01);
  }

  .course-hero__content {
    position: relative;
    display: flex;
    min-height: 210px;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
    padding: 30px 34px;
  }

  .course-hero__text {
    h1 {
      margin: 0;
      color: #fff;
      font-family: var(--zy-font-display);
      font-size: 32px;
      font-weight: 700;
      letter-spacing: 0.01em;
    }

    p {
      max-width: 560px;
      margin: 10px 0 22px;
      color: rgba(255, 255, 255, 0.82);
      font-size: 15px;
      line-height: 1.6;
    }
  }

  .course-hero__stats {
    display: flex;
    gap: 14px;
  }

  .stat-box {
    display: flex;
    min-width: 118px;
    align-items: center;
    gap: 11px;
    padding: 9px 12px;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);

    &__icon {
      display: inline-flex;
      width: 32px;
      height: 32px;
      align-items: center;
      justify-content: center;
      border-radius: 9px;
      background: rgba(129, 140, 248, 0.22);
      color: #c7d2fe;
      font-size: 16px;

      &--learning {
        color: #fff;
        font-size: 12px;
      }
    }

    &__content {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    &__label {
      color: rgba(255, 255, 255, 0.7);
      font-size: 11px;
    }

    &__value {
      color: #fff;
      font-size: 20px;
      font-weight: 700;
      line-height: 1;

      small {
        font-size: 11px;
        font-weight: 500;
      }
    }
  }

  .course-hero__deco {
    position: relative;
    width: 170px;
    height: 142px;
    flex: 0 0 170px;

    &::before,
    &::after {
      position: absolute;
      border: 1px solid rgba(199, 210, 254, 0.36);
      border-radius: 50%;
      content: '';
      transform: rotate(-18deg);
    }

    &::before {
      right: 0;
      bottom: 8px;
      width: 150px;
      height: 74px;
    }

    &::after {
      right: 18px;
      bottom: 20px;
      width: 114px;
      height: 114px;
      background: radial-gradient(
        circle at 42% 36%,
        rgba(139, 92, 246, 0.42),
        rgba(30, 41, 90, 0.08) 68%
      );
      box-shadow: inset 0 0 28px rgba(129, 140, 248, 0.34),
        0 0 36px rgba(99, 102, 241, 0.24);
    }
  }

  .grad-cap {
    position: absolute;
    right: 38px;
    top: 52px;
    z-index: 2;

    &__board {
      width: 80px;
      height: 15px;
      border-radius: 3px 3px 8px 8px;
      background: linear-gradient(135deg, #5b5bd6, #8b5cf6);
      box-shadow: 0 8px 22px rgba(15, 23, 42, 0.38);
    }

    &__top {
      position: absolute;
      top: -19px;
      left: -9px;
      width: 98px;
      height: 50px;
      background: linear-gradient(145deg, #a78bfa, #4338ca);
      clip-path: polygon(50% 0, 100% 38%, 50% 76%, 0 38%);
    }

    &__tassel {
      position: absolute;
      top: 3px;
      right: -11px;
      width: 2px;
      height: 37px;
      border-radius: 2px;
      background: #c7d2fe;

      &::after {
        position: absolute;
        bottom: -5px;
        left: -3px;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #c7d2fe;
        content: '';
      }
    }
  }

  .deco-orb {
    display: none;
  }

  .filter-section {
    display: flex;
    min-height: 48px;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
  }

  .category-tabs {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 8px;
  }

  .category-tab {
    height: 38px;
    padding: 0 17px;
    border: 1px solid transparent;
    border-radius: 9px;
    background: transparent;
    color: @text-secondary;
    cursor: pointer;
    font-family: inherit;
    font-size: 14px;
    transition: color 160ms ease, border-color 160ms ease, background 160ms ease;
    white-space: nowrap;

    &:hover {
      border-color: #dfe3f4;
      background: #fff;
      color: @brand;
    }

    &--active {
      border-color: #cfd3ff;
      background: #fff;
      box-shadow: 0 2px 8px rgba(99, 102, 241, 0.08);
      color: @brand;
      font-weight: 600;
    }
  }

  .search-row {
    display: flex;
    width: 390px;
    flex: 0 0 390px;
    align-items: center;
  }

  .search-input {
    min-width: 0;
    flex: 1;

    :deep(.arco-input-wrapper) {
      height: 38px;
      border-color: #dfe3ed;
      border-radius: 9px 0 0 9px;
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
    border-radius: 0 9px 9px 0;
    background: @brand !important;
    font-weight: 600;
  }

  .course-catalog {
    padding: 14px 16px 16px;
    border: 1px solid @line;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 6px 20px rgba(15, 23, 42, 0.045);
  }

  .list-toolbar {
    display: flex;
    min-height: 42px;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 14px;

    &__count {
      color: @text-secondary;
      font-size: 14px;

      strong {
        color: @text-primary;
        font-weight: 600;
      }
    }

    &__controls {
      display: flex;
      align-items: center;
      gap: 10px;
    }
  }

  :deep(.toolbar-select.arco-select) {
    width: 120px;
    flex: 0 0 120px;
  }

  :deep(.toolbar-select--sort.arco-select) {
    width: 142px;
    flex-basis: 142px;
  }

  :deep(.toolbar-select.arco-select .arco-select-view) {
    height: 36px;
    border-color: #e0e4ed;
    border-radius: 8px;
    background: #fff;
    color: #475569;
    box-shadow: none;
  }

  .view-toggle {
    display: flex;
    height: 36px;
    overflow: hidden;
    border: 1px solid #e0e4ed;
    border-radius: 8px;
    background: #fff;

    &__btn {
      display: flex;
      width: 40px;
      height: 34px;
      align-items: center;
      justify-content: center;
      border: 0;
      border-right: 1px solid #edf0f5;
      background: #fff;
      color: #94a3b8;
      cursor: pointer;
      transition: color 160ms ease, background 160ms ease;

      &:last-child {
        border-right: 0;
      }

      &:hover {
        color: @brand;
      }

      &--active {
        background: #f2f3ff;
        color: @brand;
      }
    }
  }

  .skeleton-grid,
  .courses-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
  }

  .courses-list {
    display: flex;
    flex-direction: column;
    gap: 12px;

    :deep(.course-card) {
      min-height: 164px;
      flex-direction: row;

      .card-cover {
        width: 280px;
        flex: 0 0 280px;
        aspect-ratio: auto;
        border-radius: 12px 0 0 12px;
      }

      .card-body {
        justify-content: center;
        padding: 18px 20px;
      }
    }
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
    .filter-section {
      align-items: stretch;
      flex-direction: column;
      gap: 10px;
    }

    .category-tabs {
      overflow-x: auto;
      padding-bottom: 2px;
    }

    .search-row {
      width: 100%;
      flex-basis: auto;
    }

    .skeleton-grid,
    .courses-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 760px) {
    .course-hero__content {
      min-height: 230px;
      align-items: flex-start;
      padding: 26px 22px;
    }

    .course-hero__deco {
      display: none;
    }

    .course-hero__text h1 {
      font-size: 28px;
    }

    .list-toolbar {
      align-items: flex-start;
      flex-direction: column;
    }

    .list-toolbar__controls {
      width: 100%;
      flex-wrap: wrap;
    }

    :deep(.toolbar-select.arco-select) {
      min-width: 120px;
      flex: 1 1 120px;
    }

    .skeleton-grid,
    .courses-grid {
      grid-template-columns: 1fr;
    }

    .courses-list :deep(.course-card) {
      flex-direction: column;

      .card-cover {
        width: 100%;
        aspect-ratio: 2.35 / 1;
        border-radius: 12px 12px 0 0;
      }
    }
  }

  @media (max-width: 480px) {
    .course-hero__stats {
      width: 100%;
    }

    .stat-box {
      min-width: 0;
      flex: 1;
    }

    .course-catalog {
      padding: 12px;
    }

    .view-toggle {
      width: 100%;
    }

    .view-toggle__btn {
      flex: 1;
    }
  }
</style>
