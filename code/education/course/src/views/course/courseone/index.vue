<template>
  <ZyPageShell title="" max-width="1320px">
    <div class="course-info-page">
      <nav v-if="!route.params.courseId" class="breadcrumb" aria-label="面包屑">
        <button type="button" @click="router.push({ name: 'CourseList' })">课程资源管理</button>
        <span>/</span>
        <strong>课程信息</strong>
      </nav>

      <header class="page-header">
        <div>
          <h1>课程信息</h1>
          <p>全面了解课程详情、资源分布与学生学习情况</p>
        </div>
        <a-button class="export-button" @click="exportOverview">
          <template #icon><icon-download /></template>
          导出数据
        </a-button>
      </header>

      <div class="overview-grid">
        <section class="panel course-summary">
          <div class="course-main">
            <img class="course-cover" :src="courseCover" :alt="courseTitle" />
            <div class="course-copy">
              <div class="course-title-row">
                <h2>{{ courseTitle }}</h2>
                <span class="status-badge">进行中</span>
              </div>
              <p class="course-description">{{ courseDescription }}</p>

              <div class="metadata-grid">
                <div class="metadata-item">
                  <span class="metadata-icon indigo"><icon-file /></span>
                  <div>
                    <span>课程编号</span>
                    <strong>{{ course?.identifier || 'CS-DB' }}</strong>
                  </div>
                </div>
                <div class="metadata-item">
                  <span class="metadata-icon cyan"><icon-apps /></span>
                  <div>
                    <span>课程分类</span>
                    <strong>{{ courseCategory }}</strong>
                  </div>
                </div>
                <div class="metadata-item">
                  <span class="metadata-icon violet"><icon-calendar /></span>
                  <div>
                    <span>创建时间</span>
                    <strong>{{ createdDate }}</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="class-strip">
            <div class="class-item">
              <span class="class-icon"><icon-user /></span>
              <div>
                <span>授课教师</span>
                <strong>{{ teacherName }}</strong>
              </div>
            </div>
            <div class="class-divider"></div>
            <div class="class-item">
              <span class="class-icon"><icon-user-group /></span>
              <div>
                <span>教学班级</span>
                <strong>{{ className }}</strong>
              </div>
            </div>
          </div>
        </section>

        <section class="panel learning-panel">
          <div class="homework-pane">
            <div class="panel-title">
              <span class="title-mark"></span>
              <h3>作业完成情况</h3>
            </div>
            <div class="homework-table">
              <div class="table-row table-head">
                <span>作业名称</span>
                <span>已提交/总人数</span>
                <span>平均分</span>
              </div>
              <div v-for="item in homeworkRows" :key="item.name" class="table-row">
                <strong>{{ item.name }}</strong>
                <span class="submit-count">{{ item.submitted }}</span>
                <span class="score">{{ item.score }}</span>
              </div>
            </div>
            <button class="text-action" type="button" @click="showMore('作业')">
              查看更多 <icon-right />
            </button>
          </div>

          <div class="activity-pane">
            <div class="activity-header">
              <div class="panel-title">
                <span class="title-mark"></span>
                <h3>动态</h3>
              </div>
              <div class="activity-tabs">
                <button
                  v-for="tab in activityTabs"
                  :key="tab.value"
                  type="button"
                  :class="{ active: activeActivityTab === tab.value }"
                  @click="activeActivityTab = tab.value"
                >
                  {{ tab.label }}
                </button>
              </div>
            </div>

            <div class="timeline">
              <div v-for="item in currentActivities" :key="item.title" class="timeline-item">
                <span class="timeline-dot"></span>
                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.detail }}</p>
                  <time>{{ item.time }}</time>
                </div>
              </div>
            </div>
            <button class="text-action" type="button" @click="showMore('动态')">
              查看更多 <icon-right />
            </button>
          </div>
        </section>
      </div>

      <div class="analytics-grid">
        <section class="panel analytics-panel resource-panel">
          <div class="analytics-heading">
            <div>
              <h3>资源概览</h3>
              <p>课程资源类型及数量分布</p>
            </div>
            <button class="period-select" type="button">全部资源 <icon-down /></button>
          </div>

          <div class="resource-content">
            <div class="donut-wrap">
              <div class="donut-chart">
                <div class="donut-center">
                  <strong>{{ resourceTotal }}</strong>
                  <span>资源总数</span>
                </div>
              </div>
              <div class="donut-label label-video"><i></i>视频 31%</div>
              <div class="donut-label label-document"><i></i>文档 27%</div>
              <div class="donut-label label-courseware"><i></i>课件 24%</div>
              <div class="donut-label label-other"><i></i>其他 18%</div>
            </div>

            <div class="resource-list">
              <div v-for="item in resourceItems" :key="item.label" class="resource-item">
                <img :src="item.icon" alt="" />
                <div>
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
                <small>{{ item.meta }}</small>
              </div>
            </div>
          </div>
        </section>

        <section class="panel analytics-panel mode-panel">
          <div class="analytics-heading">
            <div>
              <h3>课程模式</h3>
              <p>多维度教学模式应用情况</p>
            </div>
          </div>

          <div class="mode-content">
            <div class="mode-stats">
              <div v-for="item in modeStats" :key="item.label" class="mode-stat">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}%</strong>
                <div class="progress-track">
                  <i :style="{ width: `${item.value}%` }"></i>
                </div>
              </div>
            </div>

            <div class="radar-wrap">
              <svg viewBox="0 0 240 220" role="img" aria-label="课程模式雷达图">
                <g class="radar-grid">
                  <polygon points="120,30 200,110 120,190 40,110" />
                  <polygon points="120,50 180,110 120,170 60,110" />
                  <polygon points="120,70 160,110 120,150 80,110" />
                  <line x1="120" y1="30" x2="120" y2="190" />
                  <line x1="40" y1="110" x2="200" y2="110" />
                </g>
                <polygon class="radar-data" points="120,61 176,110 120,156 50,110" />
                <g class="radar-points">
                  <circle cx="120" cy="61" r="4" />
                  <circle cx="176" cy="110" r="4" />
                  <circle cx="120" cy="156" r="4" />
                  <circle cx="50" cy="110" r="4" />
                </g>
                <g class="radar-labels">
                  <text x="120" y="17" text-anchor="middle">讲授</text>
                  <text x="221" y="114" text-anchor="middle">混合</text>
                  <text x="120" y="213" text-anchor="middle">讨论</text>
                  <text x="18" y="114" text-anchor="middle">实践</text>
                </g>
              </svg>
            </div>
          </div>
          <p class="analytics-note">课堂互动与实践教学占比较高，课程结构均衡</p>
        </section>

        <section class="panel analytics-panel traffic-panel">
          <div class="analytics-heading">
            <div>
              <h3>访问流量</h3>
              <p>近 7 天课程访问趋势</p>
            </div>
            <button class="period-select" type="button">近 7 天 <icon-down /></button>
          </div>

          <div class="traffic-chart">
            <svg viewBox="0 0 520 240" role="img" aria-label="近七天访问流量折线图">
              <defs>
                <linearGradient id="trafficArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#536dfe" stop-opacity=".26" />
                  <stop offset="100%" stop-color="#536dfe" stop-opacity="0" />
                </linearGradient>
              </defs>
              <g class="chart-grid">
                <line v-for="y in [40, 80, 120, 160, 200]" :key="y" x1="42" :y1="y" x2="490" :y2="y" />
              </g>
              <path class="chart-area" d="M42 154 L115 124 L188 140 L261 92 L334 116 L407 164 L480 81 L480 200 L42 200 Z" />
              <polyline class="chart-line" points="42,154 115,124 188,140 261,92 334,116 407,164 480,81" />
              <g class="chart-points">
                <circle v-for="point in trafficPoints" :key="point.x" :cx="point.x" :cy="point.y" r="4.5" />
              </g>
              <g class="chart-axis-labels">
                <text v-for="(day, index) in trafficDays" :key="day" :x="trafficPoints[index].x" y="225" text-anchor="middle">{{ day }}</text>
              </g>
            </svg>
          </div>

          <div class="traffic-metrics">
            <div>
              <span>总访问量</span>
              <strong>806</strong>
            </div>
            <div>
              <span>日均访问</span>
              <strong>115</strong>
            </div>
            <div>
              <span>较上周</span>
              <strong class="increase">+18.4%</strong>
            </div>
          </div>
        </section>
      </div>
    </div>
  </ZyPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Message } from '@arco-design/web-vue';
import {
  IconApps,
  IconCalendar,
  IconDown,
  IconDownload,
  IconFile,
  IconRight,
  IconUser,
  IconUserGroup,
} from '@arco-design/web-vue/es/icon';
import ZyPageShell from '@/components/zy/ZyPageShell.vue';
import {
  fetchCourseById,
  fetchCourseResourceAnalysis,
  fetchTeachingClasses,
  type Course,
  type CourseResourceAnalysis,
  type TeachingClass,
} from '@/api/course';
import {
  getScenarioCourseById,
  getScenarioResourceAnalysis,
  getScenarioTeachingClasses,
  scenarioCourseMetrics,
} from '@/data/teachingScenario';
import { getClassroomCourse } from '@/data/classroomCourses';
import DatabaseImg from '@/assets/images/数据库图片.png';
import VideoIcon from '@/assets/images/视频.png';
import DocumentIcon from '@/assets/images/文档.png';
import CoursewareIcon from '@/assets/images/笔记.png';
import OtherIcon from '@/assets/images/作业.png';

type ActivityTab = 'latest' | 'all';

const route = useRoute();
const router = useRouter();
const activeActivityTab = ref<ActivityTab>('latest');
const course = ref<Course | null>(null);
const teachingClasses = ref<TeachingClass[]>([]);
const resourceAnalysis = ref<CourseResourceAnalysis>({
  document_size: 0,
  document_count: 0,
  video_size: 0,
  video_count: 0,
  image_size: 0,
  image_count: 0,
  homework_count: 0,
});

const activityTabs: Array<{ label: string; value: ActivityTab }> = [
  { label: '最新动态', value: 'latest' },
  { label: '全部', value: 'all' },
];

const homeworkRows = [
  { name: '第三章课后作业', submitted: '47/50', score: '89.5' },
  { name: 'SQL 综合练习', submitted: '45/50', score: '86.2' },
  { name: '数据库设计实验', submitted: '42/50', score: '91.8' },
];

const activityData = {
  latest: [
    { title: '发布了新作业', detail: '第三章课后作业', time: '10 分钟前' },
    { title: '上传了课程资源', detail: '事务管理与并发控制.pdf', time: '2 小时前' },
    { title: '更新了课程公告', detail: '本周实验课安排', time: '昨天 16:30' },
  ],
  all: [
    { title: '发布了新作业', detail: '第三章课后作业', time: '10 分钟前' },
    { title: '上传了课程资源', detail: '事务管理与并发控制.pdf', time: '2 小时前' },
    { title: '更新了课程公告', detail: '本周实验课安排', time: '昨天 16:30' },
    { title: '完成课堂统计', detail: '第二章课堂互动分析', time: '3 天前' },
  ],
};

const modeStats = [
  { label: '讲授式', value: 67 },
  { label: '混合式', value: 52 },
  { label: '讨论式', value: 43 },
  { label: '实践式', value: 38 },
];

const trafficPoints = [
  { x: 42, y: 154 },
  { x: 115, y: 124 },
  { x: 188, y: 140 },
  { x: 261, y: 92 },
  { x: 334, y: 116 },
  { x: 407, y: 164 },
  { x: 480, y: 81 },
];
const trafficDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

const resourceItems = computed(() => [
  { label: '教学视频', value: '10GB', meta: '3,643 次播放', icon: VideoIcon },
  { label: '课程文档', value: '15.9GB', meta: '1,743 次下载', icon: DocumentIcon },
  { label: '教学课件', value: '20.5GB', meta: '2,164 次浏览', icon: CoursewareIcon },
  { label: '其他资源', value: '2,633', meta: '累计使用', icon: OtherIcon },
]);

const courseId = computed(() => {
  const id = route.params.courseId || route.params.id || route.query.id;
  return typeof id === 'string' ? id : '';
});
const classroomProfile = computed(() => getClassroomCourse(courseId.value));
const scenarioMetrics = computed(() => scenarioCourseMetrics[courseId.value]);
const currentActivities = computed(() => activityData[activeActivityTab.value]);
const courseTitle = computed(() => {
  const name = course.value?.name || classroomProfile.value?.title || '课程信息';
  return name === '数据库系统' ? '数据库系统原理' : name;
});
const courseDescription = computed(
  () =>
    course.value?.description ||
    classroomProfile.value?.description ||
    '课程介绍暂未发布。',
);
const courseCategory = computed(() => {
  const type = course.value?.course_type;
  if (type === 'required') return '计算机科学';
  if (type === 'elective') return '专业选修';
  return '计算机科学';
});
const createdDate = computed(() => {
  const raw = course.value?.created_at;
  if (!raw) return '2026/4/3';
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return '2026/4/3';
  return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()}`;
});
const teacherName = computed(() => scenarioMetrics.value?.teacher || '林老师');
const className = computed(() => {
  const name = teachingClasses.value[0]?.name;
  if (name && !name.includes('春季教学班')) return name;
  return `2026春-${courseTitle.value}-01班`;
});
const courseCover = computed(() => classroomProfile.value?.cover || DatabaseImg);
const resourceTotal = computed(() => '2,856');

function hydrateScenario(id: string) {
  course.value = getScenarioCourseById(id);
  teachingClasses.value = getScenarioTeachingClasses(id);
  resourceAnalysis.value = getScenarioResourceAnalysis(id);
}

async function syncCourseData(id: string) {
  if (!id) return;
  const [courseResult, classesResult, resourceResult] = await Promise.allSettled([
    fetchCourseById(id),
    fetchTeachingClasses(id),
    fetchCourseResourceAnalysis(id),
  ]);

  if (courseResult.status === 'fulfilled' && courseResult.value) {
    course.value = courseResult.value;
  }
  if (
    classesResult.status === 'fulfilled' &&
    Array.isArray(classesResult.value?.data) &&
    classesResult.value.data.length
  ) {
    teachingClasses.value = classesResult.value.data;
  }
  if (resourceResult.status === 'fulfilled' && resourceResult.value) {
    resourceAnalysis.value = resourceResult.value;
  }
}

function loadCourseDetail() {
  if (!courseId.value) {
    course.value = null;
    return;
  }
  hydrateScenario(courseId.value);
  void syncCourseData(courseId.value);
}

function showMore(type: string) {
  Message.info(`${type}详情将在对应模块中展示`);
}

function exportOverview() {
  const rows = [
    ['课程名称', courseTitle.value],
    ['课程编号', course.value?.identifier || 'CS-DB'],
    ['授课教师', teacherName.value],
    ['教学班级', className.value],
    ['资源总数', String(resourceTotal.value)],
  ];
  const csv = `\uFEFF${rows.map((row) => row.join(',')).join('\n')}`;
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${courseTitle.value}-课程信息.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
  Message.success('课程数据已导出');
}

watch(courseId, loadCourseDetail);
onMounted(loadCourseDetail);
</script>

<style scoped lang="less">
.course-info-page {
  --brand: #536dfe;
  --brand-dark: #4054d7;
  --text: #17213a;
  --muted: #7d879d;
  --line: #e6eaf2;
  color: var(--text);
}

:deep(.zy-page-shell__body) {
  gap: 0;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 17px;
  color: #9aa3b5;
  font-size: 13px;

  button {
    padding: 0;
    border: 0;
    color: #8b95a9;
    background: transparent;
    cursor: pointer;
  }

  strong {
    color: #59647a;
    font-weight: 500;
  }
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;

  h1 {
    margin: 0 0 8px;
    font-size: 25px;
    line-height: 1.2;
    letter-spacing: -.5px;
  }

  p {
    margin: 0;
    color: var(--muted);
    font-size: 14px;
  }
}

.export-button {
  height: 37px;
  padding: 0 17px;
  border: 1px solid #dfe4ee;
  border-radius: 7px;
  color: #505b70;
  background: #fff;
}

.panel {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 5px 18px rgba(25, 39, 82, .045);
}

.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, .96fr) minmax(0, 1.14fr);
  gap: 16px;
  margin-bottom: 16px;
}

.course-summary {
  display: flex;
  min-height: 327px;
  padding: 24px 24px 0;
  flex-direction: column;
}

.course-main {
  display: flex;
  gap: 23px;
  min-height: 216px;
}

.course-cover {
  width: 174px;
  height: 202px;
  flex: 0 0 auto;
  border-radius: 9px;
  object-fit: cover;
  box-shadow: 0 10px 22px rgba(36, 56, 118, .13);
}

.course-copy {
  min-width: 0;
  padding-top: 3px;
}

.course-title-row {
  display: flex;
  align-items: center;
  gap: 11px;

  h2 {
    margin: 0;
    font-size: 21px;
    letter-spacing: -.35px;
  }
}

.status-badge {
  padding: 3px 9px;
  border: 1px solid #cad4ff;
  border-radius: 5px;
  color: #536dfe;
  background: #f3f5ff;
  font-size: 11px;
}

.course-description {
  min-height: 42px;
  margin: 13px 0 19px;
  color: #7d8799;
  font-size: 13px;
  line-height: 1.7;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 13px;
}

.metadata-item {
  min-width: 0;

  .metadata-icon {
    display: grid;
    width: 31px;
    height: 31px;
    margin-bottom: 9px;
    border-radius: 7px;
    place-items: center;
    font-size: 16px;
  }

  .indigo {
    color: #536dfe;
    background: #eef1ff;
  }

  .cyan {
    color: #27a9c5;
    background: #eafafd;
  }

  .violet {
    color: #8d70dc;
    background: #f4efff;
  }

  span {
    display: block;
    margin-bottom: 4px;
    color: #9aa3b4;
    font-size: 11px;
  }

  strong {
    display: block;
    overflow: hidden;
    color: #48536a;
    font-size: 12px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.class-strip {
  display: flex;
  align-items: center;
  min-height: 74px;
  margin: auto -24px 0;
  padding: 0 24px;
  border-top: 1px solid #edf0f5;
  background: #fbfcff;
  border-radius: 0 0 12px 12px;
}

.class-item {
  display: flex;
  align-items: center;
  width: 50%;
  min-width: 0;
  gap: 11px;

  .class-icon {
    display: grid;
    width: 35px;
    height: 35px;
    flex: 0 0 auto;
    border-radius: 50%;
    color: #536dfe;
    background: #edf0ff;
    place-items: center;
    font-size: 17px;
  }

  span {
    display: block;
    margin-bottom: 4px;
    color: #9aa3b5;
    font-size: 11px;
  }

  strong {
    display: block;
    overflow: hidden;
    color: #475268;
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.class-divider {
  width: 1px;
  height: 33px;
  margin: 0 22px;
  background: #e7eaf1;
}

.learning-panel {
  display: grid;
  min-height: 327px;
  grid-template-columns: 1.07fr .93fr;
}

.homework-pane,
.activity-pane {
  padding: 22px 22px 17px;
}

.activity-pane {
  border-left: 1px solid #edf0f5;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;

  h3 {
    margin: 0;
    font-size: 15px;
  }
}

.title-mark {
  width: 3px;
  height: 15px;
  border-radius: 2px;
  background: var(--brand);
}

.homework-table {
  margin-top: 16px;
}

.table-row {
  display: grid;
  min-height: 48px;
  align-items: center;
  grid-template-columns: 1.45fr .9fr .55fr;
  border-bottom: 1px solid #f0f2f6;
  color: #7f899c;
  font-size: 12px;

  strong {
    color: #424d63;
    font-weight: 500;
  }
}

.table-head {
  min-height: 31px;
  border-bottom: 1px solid #e8ebf1;
  color: #a0a8b8;
  font-size: 11px;
}

.submit-count {
  color: #667187;
}

.score {
  color: #536dfe;
  font-weight: 600;
}

.text-action {
  display: flex;
  align-items: center;
  gap: 3px;
  margin: 13px 0 0 auto;
  padding: 0;
  border: 0;
  color: #7f8a9f;
  background: transparent;
  font-size: 11px;
  cursor: pointer;
}

.activity-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.activity-tabs {
  display: flex;
  gap: 4px;
  padding: 3px;
  border-radius: 6px;
  background: #f3f5f9;

  button {
    padding: 4px 8px;
    border: 0;
    border-radius: 4px;
    color: #8d96a7;
    background: transparent;
    font-size: 10px;
    cursor: pointer;
  }

  .active {
    color: #536dfe;
    background: #fff;
    box-shadow: 0 1px 4px rgba(30, 48, 92, .08);
  }
}

.timeline {
  margin-top: 19px;
}

.timeline-item {
  position: relative;
  display: flex;
  min-height: 67px;
  padding-left: 20px;

  &::before {
    position: absolute;
    top: 12px;
    bottom: -3px;
    left: 4px;
    width: 1px;
    background: #e2e6ef;
    content: '';
  }

  &:last-child::before {
    display: none;
  }

  strong {
    display: block;
    color: #475167;
    font-size: 12px;
    font-weight: 600;
  }

  p {
    margin: 4px 0 3px;
    color: #7f899b;
    font-size: 11px;
  }

  time {
    color: #b0b7c4;
    font-size: 10px;
  }
}

.timeline-dot {
  position: absolute;
  top: 4px;
  left: 0;
  width: 9px;
  height: 9px;
  border: 2px solid #fff;
  border-radius: 50%;
  background: #647bff;
  box-shadow: 0 0 0 1px #9eabff;
}

.analytics-grid {
  display: grid;
  grid-template-columns: 1.06fr .94fr 1fr;
  gap: 16px;
}

.analytics-panel {
  min-height: 350px;
  padding: 21px 22px 18px;
}

.analytics-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;

  h3 {
    margin: 0 0 6px;
    font-size: 15px;
  }

  p {
    margin: 0;
    color: #9aa3b5;
    font-size: 11px;
  }
}

.period-select {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 9px;
  border: 1px solid #e2e6ee;
  border-radius: 6px;
  color: #727c90;
  background: #fff;
  font-size: 10px;
  cursor: pointer;
}

.resource-content {
  display: grid;
  align-items: center;
  grid-template-columns: 1.03fr .97fr;
  gap: 12px;
  margin-top: 23px;
}

.donut-wrap {
  position: relative;
  min-height: 239px;
}

.donut-chart {
  position: absolute;
  top: 41px;
  left: 50%;
  display: grid;
  width: 137px;
  height: 137px;
  border-radius: 50%;
  background: conic-gradient(#536dfe 0 31%, #28b6d1 31% 58%, #9b7adf 58% 82%, #f4b85d 82% 100%);
  place-items: center;
  transform: translateX(-50%);

  &::before {
    width: 82px;
    height: 82px;
    border-radius: 50%;
    background: #fff;
    content: '';
  }
}

.donut-center {
  position: absolute;
  z-index: 1;
  text-align: center;

  strong,
  span {
    display: block;
  }

  strong {
    font-size: 21px;
  }

  span {
    margin-top: 4px;
    color: #9aa3b5;
    font-size: 10px;
  }
}

.donut-label {
  position: absolute;
  color: #7e889a;
  font-size: 10px;
  white-space: nowrap;

  i {
    display: inline-block;
    width: 6px;
    height: 6px;
    margin-right: 4px;
    border-radius: 50%;
  }
}

.label-video {
  top: 9px;
  right: 3px;

  i { background: #536dfe; }
}

.label-document {
  top: 98px;
  right: -2px;

  i { background: #28b6d1; }
}

.label-courseware {
  bottom: 13px;
  left: 51%;

  i { background: #9b7adf; }
}

.label-other {
  top: 98px;
  left: -1px;

  i { background: #f4b85d; }
}

.resource-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.resource-item {
  display: grid;
  align-items: center;
  grid-template-columns: 34px 1fr auto;
  gap: 9px;
  min-height: 45px;

  img {
    width: 34px;
    height: 34px;
    border-radius: 7px;
    object-fit: cover;
  }

  span,
  strong {
    display: block;
  }

  span {
    margin-bottom: 3px;
    color: #858fa1;
    font-size: 10px;
  }

  strong {
    color: #3f4a61;
    font-size: 12px;
  }

  small {
    color: #a6adbb;
    font-size: 9px;
    text-align: right;
  }
}

.mode-content {
  display: grid;
  align-items: center;
  grid-template-columns: .82fr 1.18fr;
  gap: 7px;
  margin-top: 19px;
}

.mode-stats {
  display: flex;
  flex-direction: column;
  gap: 17px;
}

.mode-stat {
  display: grid;
  align-items: center;
  grid-template-columns: 1fr auto;
  gap: 7px;

  span {
    color: #727d91;
    font-size: 11px;
  }

  strong {
    color: #505c72;
    font-size: 11px;
  }
}

.progress-track {
  height: 4px;
  overflow: hidden;
  grid-column: 1 / -1;
  border-radius: 4px;
  background: #eef1f6;

  i {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, #536dfe, #8ca0ff);
  }
}

.radar-wrap svg {
  display: block;
  width: 100%;
  max-height: 219px;
}

.radar-grid {
  fill: none;
  stroke: #dfe4ed;
  stroke-width: 1;
}

.radar-data {
  fill: rgba(83, 109, 254, .22);
  stroke: #536dfe;
  stroke-width: 2;
}

.radar-points {
  fill: #536dfe;
  stroke: #fff;
  stroke-width: 2;
}

.radar-labels {
  fill: #8c96a7;
  font-size: 10px;
}

.analytics-note {
  margin: 5px 0 0;
  padding-top: 12px;
  border-top: 1px solid #eef1f5;
  color: #99a2b2;
  font-size: 10px;
  text-align: center;
}

.traffic-chart {
  margin-top: 10px;

  svg {
    display: block;
    width: 100%;
  }
}

.chart-grid line {
  stroke: #edf0f5;
  stroke-width: 1;
}

.chart-area {
  fill: url(#trafficArea);
}

.chart-line {
  fill: none;
  stroke: #536dfe;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2.5;
}

.chart-points circle {
  fill: #fff;
  stroke: #536dfe;
  stroke-width: 2.5;
}

.chart-axis-labels {
  fill: #a0a8b7;
  font-size: 10px;
}

.traffic-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-top: 1px;
  padding-top: 12px;
  border-top: 1px solid #eef1f5;

  div {
    text-align: center;

    & + div {
      border-left: 1px solid #edf0f5;
    }
  }

  span,
  strong {
    display: block;
  }

  span {
    margin-bottom: 5px;
    color: #9aa3b3;
    font-size: 10px;
  }

  strong {
    color: #3f4a61;
    font-size: 14px;
  }

  .increase {
    color: #28a972;
  }
}

@media (max-width: 1120px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }

  .analytics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .traffic-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 760px) {
  .page-header,
  .course-main {
    align-items: flex-start;
    flex-direction: column;
  }

  .course-cover {
    width: 100%;
    height: 220px;
  }

  .learning-panel,
  .analytics-grid {
    grid-template-columns: 1fr;
  }

  .activity-pane {
    border-top: 1px solid #edf0f5;
    border-left: 0;
  }

  .traffic-panel {
    grid-column: auto;
  }

  .metadata-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .class-strip {
    align-items: flex-start;
    gap: 16px;
    padding-top: 16px;
    padding-bottom: 16px;
    flex-direction: column;
  }

  .class-item {
    width: 100%;
  }

  .class-divider {
    display: none;
  }

  .resource-content {
    grid-template-columns: 1fr;
  }
}
</style>
