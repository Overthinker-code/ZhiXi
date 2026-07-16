<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { useUserStore } from '@/store';
  import {
    fetchAchievements,
    fetchPracticeSummary,
    fetchStudentMessages,
    fetchStudyGroups,
  } from '@/api/student-hub';
  import { fetchCourses, type Course } from '@/api/course';
  import { classroomCourses } from '@/data/classroomCourses';

  const userStore = useUserStore();
  const router = useRouter();
  const loading = ref(true);
  const courseCount = ref(0);
  const practiceTotal = ref(0);
  const points = ref(0);
  const studyHours = ref(0);
  const studyProgress = ref(0);
  const groupCount = ref(0);
  const unread = ref(0);
  const messages = ref<any[]>([]);
  const groups = ref<any[]>([]);
  const courses = ref<Course[]>([]);

  const displayCourses = computed(() => {
    if (courses.value.length) {
      return courses.value.slice(0, 3).map((course, index) => ({
        id: course.id,
        name: course.name,
        progress: [68, 42, 85][index] ?? 50,
        nextStudy: ['第 4 章 函数式编程', '第 6 章 二叉树', '第 3 章 Vue 组件'][index] ?? '继续学习',
      }));
    }
    return classroomCourses.slice(0, 3).map((course) => ({
      id: course.id,
      name: course.title,
      progress: course.progress,
      nextStudy:
        course.chapters
          .flatMap((chapter) => chapter.lessons)
          .find((lesson) => lesson.status === 'pending')?.label || '继续学习',
    }));
  });

  const activityFeed = computed(() => {
    const items = messages.value.slice(0, 3).map((m) => ({
      title: m.title,
      time: m.created_at ? new Date(m.created_at).toLocaleDateString() : '今天',
      type: m.category || '通知',
    }));
    if (items.length) return items;
    return [
      { title: '完成 Python 第 3 章练习', time: '今天', type: '学习' },
      { title: '获得「连续学习 7 天」徽章', time: '昨天', type: '成就' },
      { title: '加入数据结构学习小组', time: '2 天前', type: '协作' },
    ];
  });

  const weekTodos = [
    { text: '完成题库分层练习 20 题', route: 'LearningPractice' },
    { text: '更新学情诊断报告', route: 'ProfileLearningData' },
    { text: 'AI 伴学追问薄弱知识点', route: 'TutorChat' },
  ];

  onMounted(async () => {
    loading.value = true;
    try {
      const [coursesRes, practice, ach, msgs, grps] = await Promise.all([
        fetchCourses({ limit: 6 }).catch(() => ({ data: [], count: 0 })),
        fetchPracticeSummary().catch(() => null),
        fetchAchievements().catch(() => null),
        fetchStudentMessages(5).catch(() => []),
        fetchStudyGroups().catch(() => []),
      ]);
      courses.value = coursesRes?.data ?? [];
      courseCount.value = coursesRes?.count ?? coursesRes?.data?.length ?? 0;
      practiceTotal.value = practice?.total_questions ?? 0;
      studyHours.value = Math.max(1, Math.round((practice?.total_sessions ?? 3) * 1.5));
      studyProgress.value = Math.round((practice?.correct_rate ?? 0.62) * 100);
      points.value = ach?.total_points ?? 0;
      messages.value = msgs;
      unread.value = msgs.filter((m) => !m.is_read).length;
      groups.value = grps;
      groupCount.value = grps.length;
    } finally {
      loading.value = false;
    }
  });

  function goCourse(id: string) {
    router.push({
      name: 'StudentCourseContent',
      params: { courseId: id },
    });
  }
</script>

<template>
  <ZyPageShell title="个人中心" subtitle="学习进度、课程与通知一站总览">
    <ZyPageEnter>
      <section class="profile-hero zy-stagger-child">
        <div class="hero-avatar-wrap">
          <a-avatar :size="88" class="hero-avatar">
            {{ (userStore.name || 'S').slice(0, 1) }}
          </a-avatar>
          <button type="button" class="camera-btn" aria-label="更换头像">
            <icon-camera />
          </button>
        </div>
        <div class="hero-info">
          <div class="hero-name-row">
            <h2>{{ userStore.name || 'student' }}</h2>
            <a-tag color="arcoblue" size="small">学生</a-tag>
          </div>
          <p class="hero-school">智屿大学 · 计算机科学与技术 · 2022 级</p>
          <p class="hero-quote">在知识的岛屿上，开启智慧航行。</p>
        </div>
        <a-button type="primary" class="edit-btn" @click="router.push({ name: 'ProfileUserInfo' })">
          <template #icon><icon-edit /></template>
          编辑资料
        </a-button>
      </section>

      <div class="kpi-grid zy-stagger-child">
        <article class="kpi-card" @click="router.push({ name: 'CourseList' })">
          <span class="kpi-icon"><icon-book /></span>
          <div>
            <span class="kpi-label">我的课程</span>
            <strong><MetricCountUp :value="courseCount" suffix=" 门" /></strong>
          </div>
        </article>
        <article class="kpi-card" @click="router.push({ name: 'ProfileLearningData' })">
          <span class="kpi-icon"><icon-clock-circle /></span>
          <div>
            <span class="kpi-label">学习时长</span>
            <strong><MetricCountUp :value="studyHours" suffix=" 小时" /></strong>
          </div>
        </article>
        <article class="kpi-card" @click="router.push({ name: 'ProfileLearningData' })">
          <span class="kpi-icon"><icon-bar-chart /></span>
          <div>
            <span class="kpi-label">学习进度</span>
            <strong><MetricCountUp :value="studyProgress" suffix="%" /></strong>
          </div>
        </article>
        <article class="kpi-card" @click="router.push({ name: 'ProfileAchievements' })">
          <span class="kpi-icon"><icon-trophy /></span>
          <div>
            <span class="kpi-label">积分成就</span>
            <strong><MetricCountUp :value="points" suffix=" 分" /></strong>
          </div>
        </article>
      </div>

      <section class="section-card zy-stagger-child">
        <div class="section-head">
          <h3>我的课程</h3>
          <a-button type="text" @click="router.push({ name: 'CourseList' })">全部 →</a-button>
        </div>
        <a-skeleton v-if="loading" :animation="true" />
        <div v-else class="course-scroll">
          <article
            v-for="course in displayCourses"
            :key="course.id"
            class="course-card"
            @click="goCourse(course.id)"
          >
            <div class="course-card__head">
              <strong>{{ course.name }}</strong>
              <span>{{ course.progress }}%</span>
            </div>
            <a-progress :percent="course.progress" :show-text="false" size="small" />
            <p class="course-next">下次学习：{{ course.nextStudy }}</p>
          </article>
        </div>
      </section>

      <section class="section-card zy-stagger-child">
        <div class="section-head">
          <h3>我的小组</h3>
          <a-button type="text" @click="router.push({ name: 'LearningGroups' })">全部 →</a-button>
        </div>
        <div v-if="groups.length" class="group-list">
          <article v-for="item in groups.slice(0, 3)" :key="item.id" class="group-item">
            <div class="group-avatar">{{ (item.name || '组').slice(0, 1) }}</div>
            <div class="group-body">
              <strong>{{ item.name }}</strong>
              <span>{{ item.description || '协作学习小组' }}</span>
            </div>
            <span class="group-count">{{ item.member_count }} 人</span>
          </article>
        </div>
        <a-empty v-else description="暂无小组，去学习中心加入">
          <a-button type="primary" @click="router.push({ name: 'LearningGroups' })">查看小组</a-button>
        </a-empty>
      </section>

      <div class="bottom-grid zy-stagger-child">
        <section class="bottom-card">
          <h3>最新动态</h3>
          <ul class="feed-list">
            <li v-for="(item, i) in activityFeed" :key="i">
              <span class="feed-type">{{ item.type }}</span>
              <div>
                <strong>{{ item.title }}</strong>
                <small>{{ item.time }}</small>
              </div>
            </li>
          </ul>
        </section>

        <section class="bottom-card">
          <div class="bottom-head">
            <h3>站内通知</h3>
            <a-badge :count="unread" />
          </div>
          <ul v-if="messages.length" class="notify-list">
            <li v-for="item in messages.slice(0, 3)" :key="item.id">
              <strong>{{ item.title }}</strong>
              <p>{{ item.body }}</p>
            </li>
          </ul>
          <a-empty v-else description="暂无通知" />
          <a-button type="text" long @click="router.push({ name: 'ProfileMessages' })">查看全部</a-button>
        </section>

        <section class="bottom-card">
          <h3>本周待办</h3>
          <ul class="todo-list">
            <li
              v-for="todo in weekTodos"
              :key="todo.text"
              @click="router.push({ name: todo.route })"
            >
              <icon-check-circle />
              <span>{{ todo.text }}</span>
            </li>
          </ul>
        </section>
      </div>
    </ZyPageEnter>
  </ZyPageShell>
</template>

<style scoped lang="less">
  .profile-hero {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 28px 32px;
    margin-bottom: 16px;
    border-radius: 20px;
    background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 45%, #ecfeff 100%);
    border: 1px solid rgba(99, 102, 241, 0.12);
    box-shadow: var(--zy-shadow-card);
  }

  .hero-avatar-wrap {
    position: relative;
    flex-shrink: 0;
  }

  .hero-avatar {
    background: var(--zy-gradient-brand);
    color: #fff;
    font-size: 32px;
    font-weight: 800;
    border: 4px solid #fff;
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.25);
  }

  .camera-btn {
    position: absolute;
    right: -4px;
    bottom: -4px;
    width: 30px;
    height: 30px;
    border: 2px solid #fff;
    border-radius: 50%;
    background: var(--zy-color-brand);
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 14px;
  }

  .hero-info {
    flex: 1;
    min-width: 0;
  }

  .hero-name-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;

    h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 800;
      color: var(--zy-color-text-primary);
    }
  }

  .hero-school {
    margin: 0 0 4px;
    color: var(--zy-color-text-secondary);
    font-size: var(--zy-text-sm);
  }

  .hero-quote {
    margin: 0;
    font-style: italic;
    color: var(--zy-color-brand);
    font-size: var(--zy-text-sm);
  }

  .edit-btn {
    flex-shrink: 0;
    border-radius: var(--zy-radius-pill);
  }

  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }

  .kpi-card {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px 20px;
    border-radius: var(--zy-radius-card);
    background: #fff;
    border: 1px solid rgba(99, 102, 241, 0.1);
    box-shadow: var(--zy-shadow-card);
    cursor: pointer;
    transition: box-shadow var(--zy-duration-fast) ease;

    &:hover {
      box-shadow: var(--zy-shadow-card-hover);
    }
  }

  .kpi-icon {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: var(--zy-bg-tag);
    color: var(--zy-color-brand);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
  }

  .kpi-label {
    display: block;
    font-size: var(--zy-text-sm);
    color: var(--zy-color-text-secondary);
    margin-bottom: 4px;
  }

  .kpi-card strong {
    font-size: 22px;
    font-weight: 800;
    color: var(--zy-color-text-primary);
  }

  .section-card {
    margin-bottom: 16px;
    padding: 20px 22px;
    border-radius: var(--zy-radius-card);
    background: #fff;
    border: 1px solid rgba(99, 102, 241, 0.1);
    box-shadow: var(--zy-shadow-card);
  }

  .section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;

    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 700;
      color: var(--zy-color-text-primary);
    }
  }

  .course-scroll {
    display: flex;
    gap: 14px;
    overflow-x: auto;
    padding-bottom: 4px;

    &::-webkit-scrollbar {
      height: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: rgba(99, 102, 241, 0.25);
      border-radius: 4px;
    }
  }

  .course-card {
    flex: 0 0 240px;
    padding: 16px;
    border-radius: 14px;
    border: 1px solid rgba(99, 102, 241, 0.12);
    background: linear-gradient(135deg, #fbfaff, #f5f3ff);
    cursor: pointer;
    transition: transform var(--zy-duration-fast) ease;

    &:hover {
      transform: translateY(-2px);
    }
  }

  .course-card__head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;

    strong {
      font-size: 15px;
      color: var(--zy-color-text-primary);
    }

    span {
      font-size: 13px;
      font-weight: 700;
      color: var(--zy-color-brand);
    }
  }

  .course-next {
    margin: 10px 0 0;
    font-size: 12px;
    color: var(--zy-color-text-secondary);
  }

  .group-list {
    display: grid;
    gap: 10px;
  }

  .group-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 14px;
    border-radius: 12px;
    background: #f8fafc;
    border: 1px solid rgba(99, 102, 241, 0.08);
  }

  .group-avatar {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    background: var(--zy-gradient-brand);
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    flex-shrink: 0;
  }

  .group-body {
    flex: 1;
    min-width: 0;

    strong {
      display: block;
      font-size: 14px;
      color: var(--zy-color-text-primary);
    }

    span {
      display: block;
      font-size: 12px;
      color: var(--zy-color-text-secondary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .group-count {
    font-size: 12px;
    color: var(--zy-color-text-secondary);
    flex-shrink: 0;
  }

  .bottom-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
  }

  .bottom-card {
    padding: 18px 20px;
    border-radius: var(--zy-radius-card);
    background: #fff;
    border: 1px solid rgba(99, 102, 241, 0.1);
    box-shadow: var(--zy-shadow-card);

    h3 {
      margin: 0 0 14px;
      font-size: 15px;
      font-weight: 700;
      color: var(--zy-color-text-primary);
    }
  }

  .bottom-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;

    h3 {
      margin: 0;
    }
  }

  .feed-list,
  .notify-list,
  .todo-list {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .feed-list li {
    display: flex;
    gap: 10px;
    padding: 10px 0;
    border-bottom: 1px solid #f1f5f9;

    &:last-child {
      border-bottom: none;
    }

    strong {
      display: block;
      font-size: 13px;
      color: var(--zy-color-text-primary);
    }

    small {
      color: var(--zy-color-text-secondary);
      font-size: 11px;
    }
  }

  .feed-type {
    flex-shrink: 0;
    padding: 2px 8px;
    border-radius: var(--zy-radius-pill);
    background: var(--zy-bg-tag);
    color: var(--zy-color-brand);
    font-size: 11px;
    font-weight: 700;
    height: fit-content;
  }

  .notify-list li {
    padding: 10px 0;
    border-bottom: 1px solid #f1f5f9;

    strong {
      display: block;
      font-size: 13px;
      color: var(--zy-color-text-primary);
      margin-bottom: 4px;
    }

    p {
      margin: 0;
      font-size: 12px;
      color: var(--zy-color-text-secondary);
      line-height: 1.5;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
  }

  .todo-list li {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 0;
    cursor: pointer;
    color: #334155;
    font-size: 13px;
    border-bottom: 1px solid #f1f5f9;

    &:hover {
      color: var(--zy-color-brand);
    }

    &:last-child {
      border-bottom: none;
    }

    svg {
      color: var(--zy-color-brand);
      flex-shrink: 0;
    }
  }

  @media (max-width: 900px) {
    .profile-hero {
      flex-wrap: wrap;
    }

    .kpi-grid,
    .bottom-grid {
      grid-template-columns: 1fr;
    }

    .kpi-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>
