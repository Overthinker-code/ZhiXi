<template>
  <div>
    <el-container>
      <el-main>
        <div class="main">
          <LoadingState v-if="loading" text="加载课程详情..." />

          <ErrorState
            v-else-if="error"
            :text="error"
            @retry="loadCourseDetail"
            @back="goBack"
            back-text="返回列表"
          />

          <template v-else-if="course">
            <div class="left">
              <div class="Course-info">
                <p class="title-div">课程信息</p>
                <div class="bar"></div>
                <p class="course-title">{{ course.name }}</p>
                <p class="course-description">
                  {{ course.description || '暂无课程描述' }}
                </p>
                <div class="course-meta">
                  <div class="meta-item">
                    <p class="meta-label">课程标识</p>
                    <p class="meta-value">{{ course.identifier }}</p>
                  </div>
                  <div class="meta-item">
                    <p class="meta-label">课程类型</p>
                    <p class="meta-value">{{ course.course_type || '专业课程' }}</p>
                  </div>
                  <div class="meta-item">
                    <p class="meta-label">创建时间</p>
                    <p class="meta-value">{{ formatDate(course.created_at) }}</p>
                  </div>
                </div>
                <div class="bar"></div>
                <div class="bottom1">
                  <div class="title1">
                    <div class="class-info">
                      <p class="info-label">授课老师</p>
                    </div>
                    <div class="class-info">
                      <p class="info-label">教学班名称</p>
                    </div>
                    <div class="class-info">
                      <p class="info-label">创建时间</p>
                    </div>
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
                    class="all-classes"
                  >
                    <div class="class-info">
                      <p>{{ classInfo.lecturer_id }}</p>
                    </div>
                    <div class="class-info">
                      <p>{{ classInfo.name || '未命名' }}</p>
                    </div>
                    <div class="class-info">
                      <p>{{ formatDate(classInfo.created_at) }}</p>
                    </div>
                  </div>
                </div>
              </div>
              <div class="course-mode">
                <p class="title-div">课程模式</p>
                <div class="mode-content">
                  <div class="class-type">
                    <p>
                      <span class="mode-percent">67%</span>
                      <span class="mode-label">讲授型</span>
                    </p>
                    <p>
                      <span class="mode-percent">52%</span>
                      <span class="mode-label">混合型</span>
                    </p>
                    <p>
                      <span class="mode-percent">43%</span>
                      <span class="mode-label">对话型</span>
                    </p>
                    <p>
                      <span class="mode-percent">17%</span>
                      <span class="mode-label">练习型</span>
                    </p>
                  </div>
                  <div class="radar-graphic">
                    <ClassMode />
                  </div>
                </div>
              </div>
            </div>
            <div class="right">
              <div class="homework-finish">
                <p class="title-div">学生作业完成情况</p>
                <div class="homework-content">
                  <table class="homework-table">
                    <tr>
                      <th>排名</th>
                      <th>姓名</th>
                      <th>作业综合评价</th>
                    </tr>
                    <tr>
                      <td>1</td>
                      <td>张三</td>
                      <td>99.62</td>
                    </tr>
                    <tr>
                      <td>2</td>
                      <td>李四</td>
                      <td>98.42</td>
                    </tr>
                    <tr>
                      <td>3</td>
                      <td>陈晨</td>
                      <td>96.17</td>
                    </tr>
                    <tr>
                      <td>……</td>
                      <td></td>
                      <td class="view-more">查看更多</td>
                    </tr>
                  </table>
                  <div class="activity-feed">
                    <p><span class="name-color">潘*瑞</span> 提交了作业</p>
                    <p><span class="name-color">陈*</span> 老师批改了作业</p>
                    <p><span class="name-color">王*楚</span> 提交了作业</p>
                    <p>……</p>
                  </div>
                </div>
              </div>
              <div class="course-resource">
                <p class="title-div">课程资源占比</p>
                <div class="resource-content">
                  <ResorceRationVue />
                  <div class="right-resource">
                    <div class="resource-list">
                      <div class="resource-item">
                        <img src="@/assets/icons/teenyicons--ms-word-outline.png" alt="文档" />
                        <div class="resource-text">
                          <div class="resource-type">文档</div>
                          <div class="resource-size">{{ resourceAnalysis.document_size }}GB</div>
                          <div class="resource-count">{{ resourceAnalysis.document_count }}</div>
                        </div>
                      </div>
                      <div class="resource-item">
                        <img src="@/assets/icons/mingcute--video-line.png" alt="视频" />
                        <div class="resource-text">
                          <div class="resource-type">视频</div>
                          <div class="resource-size">{{ resourceAnalysis.video_size }}GB</div>
                          <div class="resource-count">{{ resourceAnalysis.video_count }}</div>
                        </div>
                      </div>
                      <div class="resource-item">
                        <img src="@/assets/icons/mingcute--pic-ai-fill.png" alt="图片" />
                        <div class="resource-text">
                          <div class="resource-type">图片</div>
                          <div class="resource-size">{{ resourceAnalysis.image_size }}GB</div>
                          <div class="resource-count">{{ resourceAnalysis.image_count }}</div>
                        </div>
                      </div>
                      <div class="resource-item">
                        <img src="@/assets/icons/ph--exam.png" alt="作业" />
                        <div class="resource-text">
                          <div class="resource-type">作业/测验</div>
                          <div class="resource-count">{{ resourceAnalysis.homework_count }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="platform-use">
                <p class="title-div">课程资源访问量（近七日）</p>
                <PlatUseVue />
              </div>
            </div>
          </template>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
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
  DEMO_COURSE_IDS,
  getDemoCourseById,
  getDemoTeachingClasses,
} from '@/mock/demoData';
import LoadingState from '@/components/state/LoadingState.vue';
import EmptyState from '@/components/state/EmptyState.vue';
import ErrorState from '@/components/state/ErrorState.vue';
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

const resourceAnalysis = ref<CourseResourceAnalysis>({
  document_size: 8.5,
  document_count: 76692,
  video_size: 10.2,
  video_count: 148,
  image_size: 13.2,
  image_count: 96,
  homework_count: 1535,
});

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('zh-CN');
}

async function loadTeachingClasses(courseId: string, useDemoFallback: boolean) {
  loadingClasses.value = true;
  try {
    const response = await fetchTeachingClasses(courseId);
    teachingClasses.value = response.data;
  } catch {
    teachingClasses.value = useDemoFallback
      ? (getDemoTeachingClasses(courseId) as TeachingClass[])
      : [];
  } finally {
    loadingClasses.value = false;
  }
}

async function loadResourceAnalysis(courseId: string) {
  try {
    resourceAnalysis.value = await fetchCourseResourceAnalysis(courseId);
  } catch {
    // 使用默认值
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
      /* 使用演示 id */
    }
    return DEMO_COURSE_IDS[0];
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
    const demo = getDemoCourseById(courseId);
    if (demo) {
      course.value = { ...demo } as Course;
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

<style scoped>
  /* ===== 智屿课程详情页 — 品牌化改造 ===== */
  .main {
    display: flex;
    flex-direction: row;
    width: 100%;
    height: 1100px;
    padding: 10px;
    overflow-y: hidden;
    /* 品牌浅绿背景（原灰色 #e8e8e8）*/
    background: var(--zy-bg-page, #f5f3ff);
    gap: 10px;
  }

  .left {
    display: flex;
    flex-direction: column;
    width: 50%;
    height: 100%;
  }

  .right {
    display: flex;
    flex-direction: column;
    width: 60%;
    height: 100%;
  }

  /* 卡片加品牌绿边框 */
  .Course-info {
    height: 70%;
    margin: 10px;
    background: #fff;
    border-radius: 16px;
    border: 1px solid rgba(99, 102, 241, 0.12);
    box-shadow: 0 4px 24px rgba(99, 102, 241, 0.08);
    overflow: hidden;
  }

  .course-mode {
    height: 35%;
    margin: 10px;
    background: #fff;
    border-radius: 16px;
    border: 1px solid rgba(99, 102, 241, 0.12);
    box-shadow: 0 4px 24px rgba(99, 102, 241, 0.08);
    overflow: hidden;
  }

  .homework-finish {
    height: 33%;
    margin: 10px;
    background: #fff;
    border-radius: 16px;
    border: 1px solid rgba(99, 102, 241, 0.12);
    box-shadow: 0 4px 24px rgba(99, 102, 241, 0.08);
    overflow: hidden;
  }

  .course-resource {
    height: 33%;
    margin: 10px;
    background: #fff;
    border-radius: 16px;
    border: 1px solid rgba(99, 102, 241, 0.12);
    box-shadow: 0 4px 24px rgba(99, 102, 241, 0.08);
    overflow: hidden;
  }

  .platform-use {
    height: 33%;
    margin: 10px;
    background: #fff;
    border-radius: 16px;
    border: 1px solid rgba(99, 102, 241, 0.12);
    box-shadow: 0 4px 24px rgba(99, 102, 241, 0.08);
    overflow: hidden;
  }

  /* 卡片标题（品牌绿左边条）*/
  .title-div {
    margin: 20px;
    font-weight: 600;
    font-size: 18px;
    color: #0f172a;
    padding-left: 12px;
    border-left: 3px solid #6366f1;
  }

  .bar {
    width: 90%;
    margin-left: 5%;
    border: 1px solid rgba(99, 102, 241, 0.12);
  }

  /* 课程标题：从蓝色改为品牌绿 */
  .course-title {
    margin: 15px 20px;
    color: #6366f1;
    font-weight: 600;
    font-size: 24px;
  }

  .course-description {
    margin: 10px;
    padding: 0 20px 10px;
    line-height: 20px;
    color: #64748b;
  }

  .course-meta {
    display: flex;
    flex-direction: row;
    width: 100%;
  }

  .meta-item {
    width: 33.33%;
  }

  /* 元数据标签：蓝色 → 品牌绿 */
  .meta-label {
    color: #6366f1;
    font-weight: 600;
    font-size: 14px;
    text-align: center;
  }

  .meta-value {
    font-weight: 600;
    font-size: 14px;
    text-align: center;
    color: #0f172a;
  }

  .bottom1 {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin-top: 10px;
  }

  .title1 {
    display: flex;
    flex-direction: row;
    width: 90%;
  }

  .all-classes {
    display: flex;
    flex-direction: row;
    width: 90%;
    height: 80px;
    margin-bottom: 15px;
    border: 1.5px solid rgba(99, 102, 241, 0.20);
    border-radius: 12px;
    transition: box-shadow 0.2s ease;
  }

  .all-classes:hover {
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.12);
  }

  .class-info {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 33.33%;
    text-align: center;
  }

  /* 教学班标签：蓝色 → 品牌绿 */
  .info-label {
    color: #6366f1;
    font-weight: 600;
    font-size: 14px;
  }

  .mode-content {
    display: flex;
    flex-direction: row;
    width: 100%;
    height: 90%;
  }

  .class-type {
    width: 50%;
    height: 100%;
    text-align: center;
  }

  .class-type p {
    display: flex;
    flex-direction: row;
    gap: 10px;
    align-items: center;
    justify-content: center;
  }

  /* 模式百分比：原蓝色 #4ed6ff → 品牌绿 */
  .mode-percent {
    color: #6366f1;
    font-weight: 700;
    font-size: 32px;
  }

  .mode-label {
    color: #64748b;
    font-size: 18px;
  }

  .radar-graphic {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 50%;
    height: 105%;
  }

  .homework-content {
    display: flex;
    flex-direction: row;
  }

  .homework-table {
    width: 100%;
    margin-left: 30px;
    padding: 0;
    font-size: 12px;
    text-align: center;
    border-collapse: collapse;
  }

  .homework-table th {
    width: 25%;
    padding-bottom: 3px;
    font-size: 13px;
    background: #f5f3ff;
    border-bottom: 1px solid rgba(99, 102, 241, 0.15);
    height: 40px;
    color: #0f172a;
  }

  .homework-table td {
    border-bottom: 1px solid rgba(99, 102, 241, 0.10);
    height: 40px;
    color: #0f172a;
  }

  /* 查看更多：品牌绿 */
  .view-more {
    color: #6366f1;
    cursor: pointer;
    font-weight: 500;
  }

  .view-more:hover {
    text-decoration: underline;
  }

  .activity-feed {
    margin-left: 90px;
    text-align: center;
    color: #64748b;
  }

  /* 学生姓名：品牌绿 */
  .name-color {
    color: #6366f1;
    font-weight: 600;
  }

  .resource-content {
    display: flex;
    flex-direction: row;
    width: 100%;
    height: 100%;
  }

  .right-resource {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
  }

  .resource-list {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .resource-item {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    width: 150px;
    margin-top: 20px;
  }

  .resource-item img {
    width: 55px;
    height: 55px;
    margin: 5px;
  }

  .resource-text {
    width: 50%;
    line-height: 25px;
  }

  .resource-type {
    color: #64748b;
    font-size: 13px;
  }

  .resource-size {
    font-weight: 600;
    color: #6366f1;
  }

  .resource-count {
    color: #64748b;
    font-size: 12px;
  }
</style>
