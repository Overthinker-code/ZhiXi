<template>
  <ZyPageShell title="" max-width="1320px">
    <nav class="page-breadcrumb" aria-label="面包屑">
      <router-link to="/course/list" class="crumb-link">课程中心</router-link>
      <span class="crumb-sep">/</span>
      <span class="crumb-current">课程信息</span>
    </nav>

    <header class="page-header">
      <div>
        <h1 class="page-title">课程信息</h1>
        <p v-if="course" class="page-subtitle">{{ course.name }}</p>
      </div>
      <a-button type="outline" class="export-btn" @click="handleExport">
        <template #icon><icon-download /></template>
        导出数据
      </a-button>
    </header>

    <LoadingState v-if="loading" text="加载课程详情..." />

    <ErrorState
      v-else-if="error"
      :text="error"
      @retry="loadCourseDetail"
      @back="goBack"
      back-text="返回列表"
    />

    <div v-else-if="course" class="dashboard-grid">
      <!-- 1. 课程详情卡 -->
      <a-card class="grid-card grid-card--detail" :bordered="false">
        <template #title>
          <div class="card-title">
            <icon-book />
            <span>课程详情</span>
          </div>
        </template>
        <h2 class="course-name">{{ course.name }}</h2>
        <p class="course-desc">{{ course.description || '暂无课程描述' }}</p>
        <div class="detail-chips">
          <div class="detail-chip">
            <span class="detail-chip__label">课程标识</span>
            <span class="detail-chip__value">{{ course.identifier }}</span>
          </div>
          <div class="detail-chip">
            <span class="detail-chip__label">课程类型</span>
            <span class="detail-chip__value">{{ course.course_type || '专业核心' }}</span>
          </div>
          <div class="detail-chip">
            <span class="detail-chip__label">创建时间</span>
            <span class="detail-chip__value">{{ formatDate(course.created_at) }}</span>
          </div>
        </div>
        <a-divider />
        <div class="class-section">
          <div class="class-header">
            <span>授课老师</span>
            <span>教学班名称</span>
            <span>创建时间</span>
          </div>
          <LoadingState v-if="loadingClasses" text="加载教学班..." :size="24" />
          <EmptyState
            v-else-if="teachingClasses.length === 0"
            text="暂无教学班"
            :icon-size="32"
          />
          <div
            v-for="(classInfo, index) in teachingClasses"
            :key="index"
            class="class-row"
          >
            <span>{{ classInfo.lecturer_id }}</span>
            <span>{{ classInfo.name || '未命名' }}</span>
            <span>{{ formatDate(classInfo.created_at) }}</span>
          </div>
        </div>
      </a-card>

      <!-- 2. 学生作业排名表 -->
      <a-card class="grid-card grid-card--homework" :bordered="false">
        <template #title>
          <div class="card-title">
            <icon-file />
            <span>学生作业排名</span>
          </div>
        </template>
        <a-table
          :columns="homeworkColumns"
          :data="homeworkData"
          :pagination="false"
          :bordered="false"
          size="small"
          class="homework-table"
        />
      </a-card>

      <!-- 3. 最新动态时间线 -->
      <a-card class="grid-card grid-card--timeline" :bordered="false">
        <template #title>
          <div class="card-title">
            <icon-notification />
            <span>最新动态</span>
          </div>
        </template>
        <a-timeline class="activity-timeline">
          <a-timeline-item dot-color="#6366f1">
            <span class="name-highlight">潘*瑞</span> 提交了作业「SQL 查询练习」
            <div class="timeline-time">10 分钟前</div>
          </a-timeline-item>
          <a-timeline-item dot-color="#8b5cf6">
            <span class="name-highlight">林老师</span> 批改了 3 份作业
            <div class="timeline-time">1 小时前</div>
          </a-timeline-item>
          <a-timeline-item dot-color="#6366f1">
            <span class="name-highlight">王*楚</span> 完成了第 1 章测验
            <div class="timeline-time">2 小时前</div>
          </a-timeline-item>
          <a-timeline-item dot-color="#a78bfa">
            <span class="name-highlight">陈*</span> 上传了课堂笔记
            <div class="timeline-time">昨天 16:30</div>
          </a-timeline-item>
        </a-timeline>
        <a-link class="view-more">查看更多</a-link>
      </a-card>

      <!-- 4. 资源占比环形图 -->
      <a-card class="grid-card grid-card--resource" :bordered="false">
        <template #title>
          <div class="card-title">
            <icon-storage />
            <span>资源占比</span>
          </div>
        </template>
        <div class="resource-layout">
          <div class="resource-chart">
            <ResorceRationVue />
          </div>
          <div class="resource-list">
            <div class="resource-item">
              <img src="@/assets/icons/teenyicons--ms-word-outline.png" alt="文档" />
              <div>
                <div class="resource-type">文档</div>
                <div class="resource-size">{{ resourceAnalysis.document_size }}GB</div>
                <div class="resource-count">{{ resourceAnalysis.document_count }} 个</div>
              </div>
            </div>
            <div class="resource-item">
              <img src="@/assets/icons/mingcute--video-line.png" alt="视频" />
              <div>
                <div class="resource-type">视频</div>
                <div class="resource-size">{{ resourceAnalysis.video_size }}GB</div>
                <div class="resource-count">{{ resourceAnalysis.video_count }} 个</div>
              </div>
            </div>
            <div class="resource-item">
              <img src="@/assets/icons/mingcute--pic-ai-fill.png" alt="图片" />
              <div>
                <div class="resource-type">图片</div>
                <div class="resource-size">{{ resourceAnalysis.image_size }}GB</div>
                <div class="resource-count">{{ resourceAnalysis.image_count }} 个</div>
              </div>
            </div>
            <div class="resource-item">
              <img src="@/assets/icons/ph--exam.png" alt="作业" />
              <div>
                <div class="resource-type">作业/测验</div>
                <div class="resource-count">{{ resourceAnalysis.homework_count }} 份</div>
              </div>
            </div>
          </div>
        </div>
      </a-card>

      <!-- 5. 课程模式雷达图 -->
      <a-card class="grid-card grid-card--mode" :bordered="false">
        <template #title>
          <div class="card-title">
            <icon-apps />
            <span>课程模式</span>
          </div>
        </template>
        <div class="mode-layout">
          <div class="mode-stats">
            <div class="mode-stat">
              <span class="mode-stat__pct">67%</span>
              <span class="mode-stat__label">讲授型</span>
            </div>
            <div class="mode-stat">
              <span class="mode-stat__pct">52%</span>
              <span class="mode-stat__label">混合型</span>
            </div>
            <div class="mode-stat">
              <span class="mode-stat__pct">43%</span>
              <span class="mode-stat__label">对话型</span>
            </div>
            <div class="mode-stat">
              <span class="mode-stat__pct">17%</span>
              <span class="mode-stat__label">练习型</span>
            </div>
          </div>
          <div class="mode-chart">
            <ClassMode />
          </div>
        </div>
      </a-card>

      <!-- 6. 近7日访问量折线图 -->
      <a-card class="grid-card grid-card--traffic" :bordered="false">
        <template #title>
          <div class="card-title">
            <icon-bar-chart />
            <span>近 7 日访问量</span>
          </div>
        </template>
        <div class="traffic-chart">
          <PlatUseVue />
        </div>
      </a-card>
    </div>
  </ZyPageShell>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Message } from '@arco-design/web-vue';
import {
  IconBook,
  IconApps,
  IconFile,
  IconStorage,
  IconBarChart,
  IconDownload,
  IconNotification,
} from '@arco-design/web-vue/es/icon';
import {
  fetchCourseById,
  fetchCourses,
  fetchTeachingClasses,
  fetchCourseResourceAnalysis,
  type Course,
  type TeachingClass,
  type CourseResourceAnalysis,
} from '@/api/course';
import {
  SCENARIO_COURSE_IDS,
  getScenarioCourseById,
  getScenarioResourceAnalysis,
  getScenarioTeachingClasses,
} from '@/data/teachingScenario';
import LoadingState from '@/components/state/LoadingState.vue';
import EmptyState from '@/components/state/EmptyState.vue';
import ErrorState from '@/components/state/ErrorState.vue';
import ZyPageShell from '@/components/zy/ZyPageShell.vue';
import ClassMode from './components/ClassMode.vue';
import PlatUseVue from './components/PlatUse.vue';
import ResorceRationVue from './components/ResorceRation.vue';

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const error = ref('');
const course = ref<Course | null>(null);
const teachingClasses = ref<TeachingClass[]>([]);
const loadingClasses = ref(false);

const homeworkColumns = [
  { title: '排名', dataIndex: 'rank', width: 64 },
  { title: '姓名', dataIndex: 'name' },
  { title: '作业综合评价', dataIndex: 'score' },
];

const homeworkData = [
  { rank: 1, name: '张三', score: '99.62' },
  { rank: 2, name: '李四', score: '98.42' },
  { rank: 3, name: '陈晨', score: '96.17' },
  { rank: 4, name: '王五', score: '95.08' },
  { rank: 5, name: '赵六', score: '93.51' },
];

const resourceAnalysis = ref<CourseResourceAnalysis>({
  ...getScenarioResourceAnalysis(SCENARIO_COURSE_IDS[0]),
});

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('zh-CN');
}

function handleExport() {
  Message.info('课程数据导出功能开发中');
}

async function loadTeachingClasses(courseId: string, useDemoFallback: boolean) {
  loadingClasses.value = true;
  try {
    const response = await fetchTeachingClasses(courseId);
    teachingClasses.value = response.data;
  } catch {
    teachingClasses.value = useDemoFallback
      ? (getScenarioTeachingClasses(courseId) as TeachingClass[])
      : [];
  } finally {
    loadingClasses.value = false;
  }
}

async function loadResourceAnalysis(courseId: string) {
  try {
    resourceAnalysis.value = await fetchCourseResourceAnalysis(courseId);
  } catch {
    resourceAnalysis.value = getScenarioResourceAnalysis(courseId);
  }
}

async function resolveCourseId(): Promise<string> {
  const fromParam = (route.params.id as string) || '';
  if (fromParam) return fromParam;
  const q = route.query.id;
  if (typeof q === 'string' && q) return q;

  if (route.name === 'CourseOne') {
    try {
      const r = await fetchCourses({ skip: 0, limit: 1 });
      const first = r.data[0];
      if (first?.id) return first.id;
    } catch {
      /* 使用内置课程场景 */
    }
    return SCENARIO_COURSE_IDS[0];
  }
  return '';
}

async function loadCourseDetail() {
  loading.value = true;
  error.value = '';

  const courseId = await resolveCourseId();
  if (!courseId) {
    error.value = '课程ID不存在';
    loading.value = false;
    return;
  }

  try {
    course.value = await fetchCourseById(courseId);
    await loadTeachingClasses(courseId, false);
    await loadResourceAnalysis(courseId);
  } catch {
    const scenarioCourse = getScenarioCourseById(courseId);
    if (scenarioCourse) {
      course.value = { ...scenarioCourse } as Course;
      error.value = '';
      await loadTeachingClasses(courseId, true);
      await loadResourceAnalysis(courseId);
    } else {
      error.value = '无法加载课程，请从课程总览选择课程或检查后端是否已启动';
    }
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.push('/course/list');
}

onMounted(() => {
  loadCourseDetail();
});

watch(
  () => [route.name, route.params.id, route.query.id] as const,
  () => {
    loadCourseDetail();
  }
);
</script>

<style scoped lang="less">
.page-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  margin-bottom: 12px;
}

.crumb-link {
  color: var(--zy-color-text-secondary, #64748b);
  text-decoration: none;
  transition: color 0.15s ease;

  &:hover {
    color: var(--zy-color-brand, #6366f1);
  }
}

.crumb-sep {
  color: #cbd5e1;
}

.crumb-current {
  color: var(--zy-color-text-primary, #0f172a);
  font-weight: 500;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: var(--zy-color-text-primary, #0f172a);
  letter-spacing: -0.02em;
}

.page-subtitle {
  margin: 6px 0 0;
  font-size: 14px;
  color: var(--zy-color-text-secondary, #64748b);
}

.export-btn {
  border-color: rgba(99, 102, 241, 0.35) !important;
  color: var(--zy-color-brand, #6366f1) !important;
  border-radius: 10px;
  flex-shrink: 0;
}

/* ===== 6 宫格 ===== */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (max-width: 900px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

.grid-card {
  border-radius: var(--zy-radius-card, 16px);
  box-shadow: var(--zy-shadow-card);
  border: 1px solid rgba(99, 102, 241, 0.1);
  transition: box-shadow 0.2s ease;

  &:hover {
    box-shadow: var(--zy-shadow-card-hover);
  }

  &--detail {
    grid-column: 1;
    grid-row: span 1;
  }

  &--homework {
    grid-column: 2;
  }

  &--timeline {
    grid-column: 1;
  }

  &--resource {
    grid-column: 2;
  }

  &--mode {
    grid-column: 1;
  }

  &--traffic {
    grid-column: 2;
  }
}

@media (max-width: 900px) {
  .grid-card {
    grid-column: 1 !important;
  }
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--zy-color-text-primary, #0f172a);
}

.course-name {
  margin: 0 0 8px;
  font-size: var(--zy-text-xl, 20px);
  font-weight: 700;
  color: var(--zy-color-brand, #6366f1);
  line-height: 1.3;
}

.course-desc {
  margin: 0 0 16px;
  font-size: var(--zy-text-sm, 14px);
  color: var(--zy-color-text-secondary, #64748b);
  line-height: 1.6;
}

.detail-chips {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.detail-chip {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border-radius: var(--zy-radius-sm, 8px);
  background: var(--zy-bg-tag, #eef2ff);
  text-align: center;

  &__label {
    font-size: var(--zy-text-xs, 12px);
    color: var(--zy-color-brand, #6366f1);
    font-weight: 600;
  }

  &__value {
    font-size: var(--zy-text-sm, 14px);
    font-weight: 600;
    color: var(--zy-color-text-primary, #0f172a);
  }
}

.class-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.class-header,
.class-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  text-align: center;
  font-size: var(--zy-text-sm, 14px);
}

.class-header {
  font-weight: 600;
  color: var(--zy-color-brand, #6366f1);
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.12);
}

.class-row {
  padding: 12px 8px;
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: var(--zy-radius-sm, 8px);
  color: var(--zy-color-text-primary, #0f172a);
  transition: box-shadow 0.2s ease;

  &:hover {
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.1);
  }
}

.homework-table {
  :deep(.arco-table-th) {
    background: var(--zy-bg-tag, #eef2ff);
    color: var(--zy-color-text-primary, #0f172a);
    font-weight: 600;
  }
}

.activity-timeline {
  margin-top: 4px;
}

.timeline-time {
  font-size: 12px;
  color: var(--zy-color-text-secondary, #64748b);
  margin-top: 4px;
}

.name-highlight {
  color: var(--zy-color-brand, #6366f1);
  font-weight: 600;
}

.view-more {
  margin-top: 12px;
  font-size: var(--zy-text-sm, 14px);
}

.mode-layout {
  display: flex;
  gap: 12px;
  align-items: center;
  min-height: 260px;
}

.mode-stats {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mode-stat {
  display: flex;
  align-items: baseline;
  gap: 10px;
  justify-content: center;

  &__pct {
    font-size: 24px;
    font-weight: 700;
    color: var(--zy-color-brand, #6366f1);
    min-width: 56px;
    text-align: right;
  }

  &__label {
    font-size: var(--zy-text-base, 14px);
    color: var(--zy-color-text-secondary, #64748b);
  }
}

.mode-chart {
  flex: 1;
  min-width: 0;
}

.resource-layout {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.resource-chart {
  flex: 1;
  min-width: 180px;
}

.resource-list {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  min-width: 200px;
}

.resource-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: var(--zy-radius-sm, 8px);
  background: var(--zy-bg-tag, #eef2ff);

  img {
    width: 36px;
    height: 36px;
    flex-shrink: 0;
  }
}

.resource-type {
  font-size: var(--zy-text-xs, 12px);
  color: var(--zy-color-text-secondary, #64748b);
}

.resource-size {
  font-weight: 600;
  color: var(--zy-color-brand, #6366f1);
  font-size: var(--zy-text-sm, 14px);
}

.resource-count {
  font-size: var(--zy-text-xs, 12px);
  color: var(--zy-color-text-secondary, #64748b);
}

.traffic-chart {
  min-height: 220px;
}

:deep(.arco-card-header) {
  border-bottom: 1px solid rgba(99, 102, 241, 0.1);
}
</style>
