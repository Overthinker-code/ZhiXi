<template>
  <ZyPageShell title="" max-width="1360px">
    <section class="course-hero">
      <div class="course-hero__bg" />
      <div class="course-hero__content">
        <div class="course-hero__text">
          <h1>课程中心</h1>
          <p>查看在学课程、续学进度和 AI 学习工具，快速回到下一节该学的内容。</p>
          <div class="course-hero__metrics">
            <span><strong>{{ totalCourses }}</strong> 门课程</span>
            <span><strong>{{ learningCount }}</strong> 门学习中</span>
            <span><strong>{{ pagination.total || courses.length }}</strong> 门符合筛选</span>
          </div>
        </div>
        <div v-if="resumeCourse" class="course-hero__resume">
          <div>
            <span>继续学习</span>
            <strong>{{ resumeCourse.name }}</strong>
            <small>当前进度 {{ resumeProgress }}% · 从上次位置继续</small>
          </div>
          <div class="resume-progress">
            <i :style="{ width: `${resumeProgress}%` }" />
          </div>
          <button type="button" @click="goToCourseDetail(resumeCourse.id)">
            进入课程
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
            aria-label="搜索课程"
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
            :aria-pressed="selectedCategory === category"
            @click="selectCategory(category)"
          >
            {{ category }}
          </button>
        </div>
        <div class="filter-panel__selects">
          <select
            v-model="statusFilter"
            aria-label="按学习状态筛选"
            class="toolbar-select"
          >
            <option value="all">全部状态</option>
            <option value="learning">学习中</option>
            <option value="done">已完成</option>
            <option value="new">未开始</option>
          </select>
          <select
            v-model="typeFilter"
            aria-label="按课程类型筛选"
            class="toolbar-select"
          >
            <option value="all">全部类型</option>
            <option value="core">专业核心</option>
            <option value="elective">专业选修</option>
          </select>
          <select
            v-model="sortBy"
            aria-label="课程排序方式"
            class="toolbar-select toolbar-select--sort"
          >
            <option value="recommend">推荐排序</option>
            <option value="progress">学习进度</option>
            <option value="rating">评分最高</option>
            <option value="newest">最新发布</option>
          </select>
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
          role="link"
          tabindex="0"
          :aria-label="`${course.name}，当前进度 ${courseProgressPercent(course)}%，${courseProgressPercent(course) > 0 ? '继续学习' : '开始学习'}`"
          @click="goToCourseDetail(course.id)"
          @keydown.enter="goToCourseDetail(course.id)"
          @keydown.space.prevent="goToCourseDetail(course.id)"
        >
          <div class="course-card__cover">
            <img :src="courseCover(course)" :alt="course.name" />
            <span>{{ courseDepartment(course) }}</span>
          </div>
          <div class="course-card__body">
            <div class="course-card__head">
              <span>{{ course.course_type || '专业课程' }}</span>
              <small>{{ courseProgressPercent(course) > 0 ? '学习中' : '未开始' }}</small>
            </div>
            <div class="course-card__title">
              <strong>{{ course.name }}</strong>
            </div>
            <p>{{ course.description || '围绕课程核心概念、学习资料和课程任务持续推进。' }}</p>
            <div class="course-card__meta">
              <span>{{ courseDepartment(course) }}</span>
              <span>{{ courseTeacher(course) }}</span>
              <span v-if="courseRating(course)">{{ courseRating(course) }} 分</span>
            </div>
          </div>
          <div class="course-card__footer">
            <div class="course-card__progress">
              <span>{{ courseProgressPercent(course) }}%</span>
              <small>{{ courseProgressPercent(course) > 0 ? '已完成' : '待开始' }}</small>
            </div>
            <div
              class="progress-track"
              role="progressbar"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-valuenow="courseProgressPercent(course)"
              :aria-label="`${course.name}学习进度`"
            >
              <i :style="{ width: `${courseProgressPercent(course)}%` }" />
            </div>
            <span class="course-card__action" aria-hidden="true">
              {{ courseProgressPercent(course) > 0 ? '继续学习' : '开始学习' }}
            </span>
          </div>
        </article>
      </div>

      <nav
        v-if="!loading && displayCourses.length > 0"
        class="pagination-container"
        aria-label="课程分页"
      >
        <button
          type="button"
          :disabled="pagination.current <= 1"
          aria-label="上一页"
          @click="handlePageChange(pagination.current - 1)"
        >
          上一页
        </button>
        <ol>
          <li v-for="page in pageCount" :key="page">
            <button
              type="button"
              :class="{ active: pagination.current === page }"
              :aria-current="pagination.current === page ? 'page' : undefined"
              :aria-label="`第 ${page} 页`"
              @click="handlePageChange(page)"
            >
              {{ page }}
            </button>
          </li>
        </ol>
        <button
          type="button"
          :disabled="pagination.current >= pageCount"
          aria-label="下一页"
          @click="handlePageChange(pagination.current + 1)"
        >
          下一页
        </button>
      </nav>
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
  import { classroomCourses } from '@/data/classroomCourses';
  import ErrorState from '@/components/state/ErrorState.vue';
  import ZyPageShell from '@/components/zy/ZyPageShell.vue';

  const router = useRouter();

  const loading = ref(false);
  const error = ref('');
  const sourceCourses = ref<Course[]>([...scenarioCourses]);
  const courses = ref<Course[]>(scenarioCourses.slice(0, 8));
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
    pageSize: 8,
    total: scenarioCourses.length,
  });
  const pageCount = computed(() =>
    Math.max(1, Math.ceil(pagination.value.total / pagination.value.pageSize))
  );

  const totalCourses = computed(
    () => pagination.value.total || sourceCourses.value.length
  );
  const learningCount = computed(() => {
    const count = scenarioCourses.filter((c) => {
      const p = scenarioCourseMetrics[c.id]?.progress ?? 0;
      return p > 0 && p < 100;
    }).length;
    return count;
  });

  const resumeCourse = computed(() => {
    const candidates = sourceCourses.value
      .map((course) => ({ course, progress: courseProgressPercent(course) }))
      .filter((item) => item.progress > 0 && item.progress < 100)
      .sort((a, b) => b.progress - a.progress);
    return candidates[0]?.course;
  });
  const resumeProgress = computed(() =>
    resumeCourse.value ? courseProgressPercent(resumeCourse.value) : 0
  );

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
    return c.teacher_name || scenarioCourseMetrics[course.id]?.teacher || '课程团队';
  }

  function courseRating(course: Course) {
    const c = course as any;
    return c.rating || '';
  }

  function courseDepartment(course: Course) {
    return scenarioCourseDepartments[course.id] || course.course_type || '课程中心';
  }

  function courseCover(course: Course) {
    return classroomCourses.find((item) => item.id === course.id)?.cover || classroomCourses[0]?.cover || '';
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
  @brand: #4f46e5;
  @text-primary: var(--zy-color-text-primary, #0f172a);
  @text-secondary: var(--zy-color-text-secondary, #64748b);
  @line: rgba(15, 23, 42, 0.08);

  .course-hero {
    position: relative;
    min-height: 112px;
    overflow: hidden;
    border: 1px solid @line;
    border-radius: 20px;
    background: #fff;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
  }

  .course-hero__bg {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(circle at 88% 8%, rgba(99, 102, 241, 0.12), transparent 24%),
      linear-gradient(135deg, #ffffff 0%, #f9fbff 64%, #f2f6ff 100%);
  }

  .course-hero__content {
    position: relative;
    display: flex;
    min-height: 112px;
    align-items: center;
    justify-content: space-between;
    gap: 22px;
    padding: 18px 22px 18px 24px;
  }

  .course-hero__text {
    h1 {
      margin: 0;
      color: @text-primary;
      font-family: var(--zy-font-display);
      font-size: 28px;
      font-weight: 700;
      letter-spacing: 0;
    }

    p {
      max-width: 620px;
      margin: 6px 0 10px;
      color: @text-secondary;
      font-size: 14px;
      line-height: 1.5;
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
      border: 1px solid rgba(15, 23, 42, 0.07);
      border-radius: 999px;
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
    width: 360px;
    flex: 0 0 360px;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 8px 14px;
    padding: 12px 14px;
    border: 1px solid rgba(99, 102, 241, 0.14);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.9);
    box-shadow: 0 10px 24px rgba(79, 70, 229, 0.06);

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
      grid-row: 1 / span 2;
      grid-column: 2;
      justify-self: end;
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
    grid-column: 1;
    height: 6px;
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
    margin-bottom: 12px;

    strong,
    span {
      display: block;
    }

    strong {
      color: @text-primary;
      font-size: 19px;
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
        border-color: #94a3b8;
        box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.08);
      }
    }

    :deep(.arco-input),
    :deep(.arco-input::placeholder) {
      color: #475569;
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
    padding: 16px;
    border: 1px solid @line;
    border-radius: 22px;
    background: #fff;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
  }

  .filter-panel {
    display: flex;
    min-height: 48px;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 14px;
    padding: 6px;
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

  .toolbar-select {
    width: 112px;
    height: 34px;
    flex: 0 0 112px;
    padding: 0 28px 0 12px;
    border: 1px solid #e0e4ed;
    border-radius: 999px;
    background: #fff;
    color: #475569;
    box-shadow: none;
    font-family: inherit;
    cursor: pointer;
  }

  .toolbar-select--sort {
    width: 132px;
    flex-basis: 132px;
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
    gap: 12px;
  }

  .course-card {
    overflow: hidden;
    display: flex;
    min-width: 0;
    min-height: 318px;
    flex-direction: column;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 16px;
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
    height: 122px;
    overflow: hidden;
    background: #eef2ff;

    img {
      display: block;
      width: 100%;
      height: 100%;
      object-fit: cover;
      transform: scale(1.01);
      transition: transform 220ms ease, filter 220ms ease;
    }

    &::after {
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(15, 23, 42, 0.04), rgba(15, 23, 42, 0.34));
    }

    span {
      position: absolute;
      right: 12px;
      bottom: 10px;
      z-index: 1;
      padding: 4px 9px;
      border: 1px solid rgba(255, 255, 255, 0.32);
      border-radius: 999px;
      color: #fff;
      background: rgba(15, 23, 42, 0.28);
      font-size: 11px;
      font-weight: 700;
      backdrop-filter: blur(6px);
    }
  }

  .course-card:hover .course-card__cover img {
    filter: saturate(1.06);
    transform: scale(1.045);
  }

  .course-card__body {
    min-width: 0;
    padding: 13px 14px 8px;
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
      font-size: 16px;
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
    margin: 7px 0 9px;
    overflow: hidden;
    color: @text-secondary;
    font-size: 13px;
    line-height: 1.5;
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
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 10px;
    padding: 0 14px 13px;

    .course-card__action {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      height: 32px;
      padding: 0 12px;
      border: 1px solid rgba(99, 102, 241, 0.18);
      border-radius: 999px;
      color: @brand;
      background: #eef2ff;
      cursor: inherit;
      font-size: 12px;
      font-weight: 700;
      transition: transform 150ms ease, background 150ms ease;

      .course-card:hover & {
        color: #fff;
        background: #4f46e5;
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
      font-size: 18px;
      font-weight: 750;
      line-height: 1;
    }

    small {
      display: none;
      color: @text-secondary;
      font-size: 12px;
    }
  }

  .progress-track {
    position: relative;
    height: 6px;
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
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-top: 20px;
    padding: 4px 0 2px;

    ol {
      display: flex;
      gap: 6px;
      margin: 0;
      padding: 0;
      list-style: none;
    }

    button {
      min-width: 34px;
      height: 34px;
      padding: 0 10px;
      border: 1px solid #e0e4ed;
      border-radius: 8px;
      color: #475569;
      background: #fff;
      cursor: pointer;

      &.active {
        border-color: @brand;
        color: #fff;
        background: @brand;
      }

      &:disabled {
        cursor: not-allowed;
        opacity: 0.55;
      }
    }
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

    .toolbar-select,
    .toolbar-select--sort {
      min-width: 120px;
      flex: 1 1 120px;
    }

    .course-hero__content {
      min-height: auto;
      padding: 20px 18px;
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

  .course-card:nth-child(2) {
    animation-delay: 30ms;
  }

  .course-card:nth-child(3) {
    animation-delay: 60ms;
  }

  .course-card:nth-child(4) {
    animation-delay: 90ms;
  }

  .course-card:nth-child(5) {
    animation-delay: 120ms;
  }

  .course-card:nth-child(6) {
    animation-delay: 150ms;
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
    .progress-track i,
    .resume-progress i {
      animation: none;
      transition: none;
    }

    .course-card:hover,
    .course-hero__resume button:hover {
      transform: none;
    }
  }

  /* 2026 refinement: course center as a compact learning dashboard, not decorative cards. */
  .course-hero {
    min-height: 96px;
    border-radius: 18px;
  }

  .course-hero__content {
    min-height: 96px;
    padding: 14px 18px 14px 20px;
  }

  .course-hero__text h1 {
    font-size: 25px;
  }

  .course-hero__text p {
    margin: 4px 0 8px;
    font-size: 13px;
  }

  .course-hero__metrics span {
    min-height: 25px;
    padding: 0 9px;
    font-size: 11px;
  }

  .course-hero__resume {
    width: 390px;
    flex-basis: 390px;
    padding: 10px 12px;
    border-radius: 14px;
  }

  .course-hero__resume strong {
    font-size: 15px;
  }

  .course-hero__resume button {
    height: 31px;
    padding: 0 12px;
    font-size: 12px;
  }

  .course-catalog {
    margin-top: 12px;
    padding: 13px;
    border-radius: 18px;
  }

  .catalog-header {
    margin-bottom: 9px;
  }

  .catalog-header strong {
    font-size: 17px;
  }

  .catalog-header span {
    margin-top: 2px;
    font-size: 12px;
  }

  .filter-panel {
    min-height: 42px;
    margin-bottom: 12px;
    padding: 5px;
    border-radius: 14px;
  }

  .category-tab {
    height: 30px;
    padding: 0 12px;
    font-size: 12px;
  }

  .toolbar-select {
    height: 30px;
    font-size: 12px;
  }

  .course-card-grid {
    gap: 10px;
  }

  .course-card {
    position: relative;
    display: flex;
    min-height: 188px;
    flex-direction: column;
    border-radius: 15px;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.035);
  }

  .course-card::after {
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(120deg, transparent 0%, rgba(99, 102, 241, 0.08) 45%, transparent 62%);
    content: '';
    opacity: 0;
    pointer-events: none;
    transform: translateX(-16%);
    transition: opacity 180ms ease, transform 240ms ease;
  }

  .course-card:hover::after {
    opacity: 1;
    transform: translateX(18%);
  }

  .course-card__body {
    display: flex;
    min-height: 0;
    flex: 1;
    flex-direction: column;
    padding: 14px 15px 8px;
  }

  .course-card__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    min-width: 0;
    margin-bottom: 10px;

    span,
    small {
      min-width: 0;
      max-width: 58%;
      overflow: hidden;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: #475569;
      background: #f1f5f9;
    }

    small {
      color: @brand;
      background: #eef2ff;
    }
  }

  .course-card__title strong {
    font-size: 15px;
    line-height: 1.35;
  }

  .course-card__body p {
    margin: 6px 0 8px;
    font-size: 12px;
    line-height: 1.45;
  }

  .course-card__meta {
    gap: 5px 8px;
  }

  .course-card__meta span {
    font-size: 11px;
  }

  .course-card__footer {
    grid-template-columns: 42px minmax(0, 1fr) auto;
    gap: 8px;
    padding: 0 15px 14px;
  }

  .course-card__progress span {
    font-size: 16px;
  }

  .course-card__footer .course-card__action {
    height: 29px;
    padding: 0 10px;
    font-size: 11px;
  }

  .progress-track {
    height: 5px;
  }

  @media (max-width: 1120px) {
    .course-card-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
