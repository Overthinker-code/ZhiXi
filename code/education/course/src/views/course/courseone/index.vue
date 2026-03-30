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
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  fetchCourseById,
  fetchTeachingClasses,
  fetchCourseResourceAnalysis,
  type Course,
  type TeachingClass,
  type CourseResourceAnalysis,
} from '@/api/course';
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

async function loadCourseDetail() {
  const courseId = route.params.id as string;
  if (!courseId) {
    error.value = '课程ID不存在';
    return;
  }

  loading.value = true;
  error.value = '';
  try {
    course.value = await fetchCourseById(courseId);
    loadTeachingClasses(courseId);
    loadResourceAnalysis(courseId);
  } catch (e: any) {
    error.value = e.message || '加载失败';
  } finally {
    loading.value = false;
  }
}

async function loadTeachingClasses(courseId: string) {
  loadingClasses.value = true;
  try {
    const response = await fetchTeachingClasses(courseId);
    teachingClasses.value = response.data;
  } catch {
    teachingClasses.value = [];
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

function goBack() {
  router.push('/course/list');
}

onMounted(() => {
  loadCourseDetail();
});
</script>

<style scoped>
.main {
  display: flex;
  flex-direction: row;
  width: 100%;
  height: 1100px;
  padding: 10px;
  overflow-y: hidden;
  background: #e8e8e8;
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

.Course-info {
  height: 70%;
  margin: 10px;
  background: #fff;
}

.course-mode {
  height: 35%;
  margin: 10px;
  background: #fff;
}

.homework-finish {
  height: 33%;
  margin: 10px;
  background: #fff;
}

.course-resource {
  height: 33%;
  margin: 10px;
  background: #fff;
}

.platform-use {
  height: 33%;
  margin: 10px;
  background: #fff;
}

.title-div {
  margin: 20px;
  font-weight: 600;
  font-size: 20px;
}

.bar {
  width: 90%;
  margin-left: 5%;
  border: 1px solid #f0f2f6;
}

.course-title {
  margin: 15px 20px;
  color: #1f63ff;
  font-weight: 600;
  font-size: 25px;
}

.course-description {
  margin: 10px;
  padding: 0 20px 10px;
  line-height: 20px;
}

.course-meta {
  display: flex;
  flex-direction: row;
  width: 100%;
}

.meta-item {
  width: 33.33%;
}

.meta-label {
  color: #1f63ff;
  font-weight: 600;
  font-size: 15px;
  text-align: center;
}

.meta-value {
  font-weight: 600;
  font-size: 15px;
  text-align: center;
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
  border: 2px solid rgb(147 142 142 / 50%);
  border-radius: 20px;
}

.class-info {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 33.33%;
  text-align: center;
}

.info-label {
  color: #1f63ff;
  font-weight: 600;
  font-size: 15px;
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

.mode-percent {
  color: #4ed6ff;
  font-weight: 600;
  font-size: 35px;
}

.mode-label {
  color: #9a9a9a;
  font-size: 20px;
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
  background: #f2f3f8;
  border-bottom: 1px solid #e5e8ef;
  height: 40px;
}

.homework-table td {
  border-bottom: 1px solid #e5e8ef;
  height: 40px;
}

.view-more {
  color: #3270ff;
  cursor: pointer;
}

.activity-feed {
  margin-left: 90px;
  text-align: center;
}

.name-color {
  color: #3270ff;
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
  color: #9a9a9a;
}

.resource-size {
  font-weight: 500;
}

.resource-count {
  color: #666;
}
</style>
