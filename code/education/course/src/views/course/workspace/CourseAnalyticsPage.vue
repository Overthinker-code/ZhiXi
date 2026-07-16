<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    IconArrowRight,
    IconBarChart,
    IconBulb,
    IconCheckCircle,
    IconClockCircle,
    IconRobot,
  } from '@arco-design/web-vue/es/icon';
  import { getClassroomCourse } from '@/data/classroomCourses';
  import { buildCourseTasks } from '@/data/courseWorkspace';
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';

  const route = useRoute();
  const router = useRouter();
  const isCourseHome = computed(() => route.name === 'StudentCourseHome');
  const detailDrawerVisible = ref(false);
  const course = computed(() => getClassroomCourse(String(route.params.courseId || '')));
  const allLessons = computed(
    () => course.value?.chapters.flatMap((chapter) => chapter.lessons) || []
  );
  const doneLessons = computed(
    () => allLessons.value.filter((lesson) => lesson.status === 'done').length
  );
  const chapterMastery = computed(() =>
    (course.value?.chapters || []).map((chapter, index) => {
      const done = chapter.lessons.filter((lesson) => lesson.status === 'done').length;
      const base = Math.round((done / Math.max(chapter.lessons.length, 1)) * 100);
      return {
        title: chapter.title,
        value: Math.max(18, Math.min(96, base || course.value!.progress - index * 7)),
      };
    })
  );
  const weakPoints = computed(() => {
    const concepts = course.value?.concepts || [];
    return concepts
      .slice(-2)
      .flatMap((item) => item.points.slice(0, 2))
      .slice(0, 4);
  });
  const nextTasks = computed(() =>
    course.value
      ? buildCourseTasks(course.value).filter((task) => task.status !== 'done').slice(0, 3)
      : []
  );
  const masteryLevel = computed(() => {
    const progress = course.value?.progress || 0;
    if (progress >= 80) return '稳定掌握';
    if (progress >= 60) return '持续推进';
    return '需要补强';
  });
  const profileSignals = computed(() => [
    {
      label: '知识基础',
      value: `${course.value?.progress || 0}%`,
      desc: '结合课程进度和近期学习表现整理',
    },
    {
      label: '学习节奏',
      value: doneLessons.value >= 6 ? '稳定' : '待建立',
      desc: '建议保持短时高频复习',
    },
    {
      label: '资源偏好',
      value: '讲义 + 练习',
      desc: '适合先看讲解，再用练习检查理解',
    },
  ]);
  const topWeakPoints = computed(() => weakPoints.value.slice(0, 3));
  const priorityTask = computed(() => nextTasks.value[0]);

  function openDetailDrawer() {
    detailDrawerVisible.value = true;
  }

  function askForPlan() {
    if (!course.value) return;
    router.push(
      courseWorkspaceLocation(course.value.id, 'agent', {
        prompt: `请根据《${course.value.title}》当前 ${course.value.progress}% 的进度和薄弱点 ${weakPoints.value.join('、')}，生成下一周复习计划。`,
        source: 'analytics',
      })
    );
  }
</script>

<template>
  <section v-if="course" class="course-analytics">
    <header class="analytics-heading">
      <div>
        <span>{{ isCourseHome ? '课程概览' : '学情概览' }}</span>
        <h1>{{ isCourseHome ? '继续学习' : '课程学情' }}</h1>
        <p>{{ isCourseHome ? '查看当前进度、学习重点和下一步安排。' : '结合当前课程进度和需要加强的内容，帮助你明确下一步学习重点。' }}</p>
      </div>
      <button type="button" @click="askForPlan"><icon-robot /> 生成个性化计划</button>
    </header>

    <section class="learning-profile-card" aria-label="课程学情总览">
      <div class="profile-main">
        <span>{{ course.shortTitle }}</span>
        <h2>{{ masteryLevel }}</h2>
        <p>已完成 {{ doneLessons }}/{{ allLessons.length }} 个课节，当前应优先处理 {{ weakPoints.slice(0, 2).join('、') }}。</p>
      </div>
      <div class="profile-ring" :style="{ '--progress': `${course.progress * 3.6}deg` }">
        <strong>{{ course.progress }}%</strong>
        <small>课程进度</small>
      </div>
      <div class="profile-signals">
        <div v-for="item in profileSignals" :key="item.label">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <p>{{ item.desc }}</p>
        </div>
      </div>
    </section>

    <div class="insight-summary">
      <article>
        <span class="summary-icon"><icon-bar-chart /></span>
        <div><small>课程进度</small><strong>{{ course.progress }}%</strong></div>
        <em>{{ masteryLevel }}</em>
      </article>
      <article>
        <span class="summary-icon"><icon-check-circle /></span>
        <div><small>已完成课节</small><strong>{{ doneLessons }}/{{ allLessons.length }}</strong></div>
        <em>继续保持</em>
      </article>
      <article>
        <span class="summary-icon"><icon-clock-circle /></span>
        <div><small>近期学习节奏</small><strong>待积累</strong></div>
        <em>完成学习后更新</em>
      </article>
    </div>

    <div class="analytics-grid">
      <section class="panel mastery-panel">
        <div class="panel-title">
          <div><icon-bar-chart /><strong>章节掌握度</strong></div>
          <span>基于课节、练习与对话综合估算</span>
        </div>
        <div class="mastery-list">
          <article v-for="item in chapterMastery" :key="item.title">
            <div><strong>{{ item.title }}</strong><span>{{ item.value }}%</span></div>
            <div class="mastery-track"><i :style="{ width: `${item.value}%` }"></i></div>
          </article>
        </div>
      </section>

      <section class="panel focus-panel">
        <div class="panel-title">
          <div><icon-bulb /><strong>本周优先行动</strong></div>
          <span>从低负担任务开始</span>
        </div>
        <div class="focus-brief">
          <strong>{{ priorityTask?.title || '完成一次章节复盘' }}</strong>
          <p>{{ priorityTask?.chapter || '围绕薄弱知识点补齐证据、练习和错因记录。' }}</p>
          <button type="button" @click="askForPlan">生成复习计划 <icon-arrow-right /></button>
        </div>
        <div class="weak-list">
          <div v-for="(item, index) in topWeakPoints" :key="item">
            <span>{{ index + 1 }}</span>
            <div>
              <strong>{{ item }}</strong>
              <small>{{ index < 2 ? '需要结合例题再练习' : '建议回看课堂笔记' }}</small>
            </div>
          </div>
        </div>
        <button type="button" class="ghost-action" @click="openDetailDrawer">
          查看薄弱点与任务详情 <icon-arrow-right />
        </button>
      </section>

      <section class="panel rhythm-panel">
        <div class="panel-title">
          <div><icon-clock-circle /><strong>本周学习节奏</strong></div>
          <span>完成学习任务后自动更新</span>
        </div>
        <div class="rhythm-empty" role="status">
          <icon-clock-circle />
          <strong>还没有足够的学习记录</strong>
          <p>完成课程任务后，这里会展示你的每周学习节奏。</p>
        </div>
      </section>

      <section class="panel next-panel">
        <div class="panel-title">
          <div><icon-check-circle /><strong>本次学习安排</strong></div>
          <span>预计 45 分钟完成</span>
        </div>
        <div class="loop-steps">
          <div>
            <span>01</span>
            <div>
              <strong>回看讲解</strong>
              <small>复习章节资料与课堂笔记</small>
            </div>
          </div>
          <div>
            <span>02</span>
            <div>
              <strong>做练习</strong>
              <small>围绕薄弱点完成检查题</small>
            </div>
          </div>
          <div>
            <span>03</span>
            <div>
              <strong>问小智</strong>
              <small>记录错因并更新后续学习建议</small>
            </div>
          </div>
        </div>
        <button type="button" @click="router.push(courseWorkspaceLocation(course.id, 'tasks'))">
          查看课程任务 <icon-arrow-right />
        </button>
      </section>
    </div>

    <a-drawer
      v-model:visible="detailDrawerVisible"
      :width="420"
      :footer="false"
      placement="right"
      unmount-on-close
    >
      <template #title>学情行动详情</template>
      <div class="analytics-drawer">
        <section>
          <span>薄弱知识点</span>
          <div class="drawer-list">
            <div v-for="(item, index) in weakPoints" :key="item">
              <strong>{{ index + 1 }}. {{ item }}</strong>
              <p>{{ index < 2 ? '建议先看概念证据，再完成 2 道检查题。' : '建议回看课堂笔记并向 AI 伴学追问。' }}</p>
            </div>
          </div>
        </section>
        <section>
          <span>待处理任务</span>
          <div class="drawer-list">
            <div v-for="task in nextTasks" :key="task.id">
              <strong>{{ task.title }}</strong>
              <p>{{ task.chapter }} · {{ task.dueLabel }} · {{ task.duration }} 分钟</p>
            </div>
          </div>
        </section>
        <div class="drawer-actions">
          <button type="button" class="primary" @click="askForPlan">生成个性化计划</button>
          <button type="button" @click="router.push(courseWorkspaceLocation(course.id, 'tasks'))">
            打开任务中心
          </button>
        </div>
      </div>
    </a-drawer>
  </section>
</template>

<style scoped lang="less">
  .course-analytics {
    color: #17213a;
  }

  .analytics-heading {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 20px;
    padding: 2px 2px 18px;

    > div > span {
      color: #5367f8;
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.14em;
    }

    h1 {
      margin: 6px 0 5px;
      font-size: 26px;
    }

    p {
      margin: 0;
      color: #7d879a;
      font-size: 12px;
    }

    > button {
      display: flex;
      align-items: center;
      gap: 6px;
      height: 36px;
      padding: 0 14px;
      border: 0;
      border-radius: 9px;
      color: #fff;
      background: #5367f8;
      cursor: pointer;
    }
  }

  .insight-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 12px;

    article {
      display: grid;
      grid-template-columns: 38px 1fr auto;
      align-items: center;
      gap: 11px;
      padding: 15px 16px;
      border: 1px solid #e4e8f1;
      border-radius: 12px;
      background: #fff;
    }

    small,
    strong {
      display: block;
    }

    small {
      color: #8e98a9;
      font-size: 10px;
    }

    strong {
      margin-top: 4px;
      color: #29364d;
      font-size: 20px;
    }

    em {
      color: #168a65;
      font-size: 9px;
      font-style: normal;
    }
  }

  .summary-icon {
    display: grid;
    width: 38px;
    height: 38px;
    border-radius: 10px;
    color: #596bfa;
    background: #edf0ff;
    place-items: center;
  }

  .analytics-grid {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 12px;
  }

  .panel {
    min-width: 0;
    padding: 16px;
    border: 1px solid #e4e8f1;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 3px 12px rgba(34, 48, 88, 0.04);
  }

  .panel-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding-bottom: 13px;
    border-bottom: 1px solid #edf0f5;

    > div {
      display: flex;
      align-items: center;
      gap: 7px;
      color: #5367f8;
    }

    strong {
      color: #2d394f;
      font-size: 13px;
    }

    > span {
      color: #98a1b1;
      font-size: 9px;
    }
  }

  .mastery-list {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding-top: 15px;

    article > div:first-child {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 6px;
      font-size: 10px;
    }

    strong {
      color: #566177;
      font-weight: 600;
    }

    span {
      color: #5367f8;
    }
  }

  .mastery-track {
    height: 6px;
    overflow: hidden;
    border-radius: 99px;
    background: #edf0f5;

    i {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: #5b6cf7;
    }
  }

  .rhythm-chart {
    height: 170px;
    display: flex;
    align-items: flex-end;
    justify-content: space-around;
    gap: 12px;
    padding: 22px 12px 0;
    border-bottom: 1px solid #edf0f5;

    > div {
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      flex-direction: column;
      flex: 1;
    }

    i {
      width: min(24px, 60%);
      min-height: 16px;
      border-radius: 6px 6px 2px 2px;
      background: #7a88f8;
    }

    span {
      margin: 7px 0 8px;
      color: #919aac;
      font-size: 9px;
    }
  }

  .rhythm-empty {
    min-height: 170px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 8px;
    padding: 24px;
    text-align: center;
    color: #98a1b1;

    svg {
      font-size: 28px;
      color: #7a88f8;
    }

    strong {
      color: #566177;
      font-size: 12px;
    }

    p {
      margin: 0;
      font-size: 10px;
      line-height: 1.6;
    }
  }

  .next-panel > button {
    margin-top: 13px;
    display: flex;
    align-items: center;
    gap: 4px;
    border: 0;
    color: #5367f8;
    background: transparent;
    font-size: 9px;
    cursor: pointer;
  }

  @media (max-width: 900px) {
    .analytics-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 640px) {
    .analytics-heading {
      align-items: flex-start;
      flex-direction: column;
    }

    .insight-summary {
      grid-template-columns: 1fr;
    }
  }

  /* Refined learning analytics surface. */
  .course-analytics {
    --zy-brand: #4f46e5;
    --zy-brand-2: #6366f1;
    --zy-text: #101828;
    --zy-muted: #667085;
    --zy-border: rgba(15, 23, 42, 0.08);
    animation: analytics-enter 180ms ease both;
  }

  .analytics-heading {
    align-items: center;
    padding: 0 2px 14px;

    > div > span {
      color: var(--zy-brand);
      letter-spacing: 0;
    }

    h1 {
      color: var(--zy-text);
      font-size: 26px;
      letter-spacing: 0;
    }

    p {
      color: var(--zy-muted);
      line-height: 1.6;
    }

    > button {
      height: 38px;
      border-radius: 999px;
      background: var(--zy-brand);
      box-shadow: 0 10px 22px rgba(79, 70, 229, 0.14);
      transition: transform 160ms ease, background 160ms ease;

      &:hover {
        background: var(--zy-brand-2);
        transform: translateY(-1px);
      }
    }
  }

  .learning-profile-card {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 124px minmax(360px, 0.9fr);
    gap: 18px;
    align-items: center;
    margin-bottom: 12px;
    padding: 18px;
    border: 1px solid var(--zy-border);
    border-radius: 18px;
    background:
      radial-gradient(circle at 100% 0, rgba(99, 102, 241, 0.11), transparent 30%),
      #ffffff;
    box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05);
  }

  .profile-main {
    min-width: 0;

    span {
      color: var(--zy-brand);
      font-size: 12px;
      font-weight: 800;
    }

    h2 {
      margin: 7px 0 8px;
      color: var(--zy-text);
      font-size: 28px;
      line-height: 1.18;
    }

    p {
      max-width: 620px;
      margin: 0;
      color: var(--zy-muted);
      font-size: 13px;
      line-height: 1.7;
    }
  }

  .profile-ring {
    width: 108px;
    height: 108px;
    display: grid;
    place-items: center;
    justify-self: center;
    border-radius: 50%;
    background:
      radial-gradient(circle, #fff 58%, transparent 60%),
      conic-gradient(var(--zy-brand-2) var(--progress), #eef2ff 0);

    strong,
    small {
      display: block;
      grid-area: 1 / 1;
      text-align: center;
    }

    strong {
      margin-top: -10px;
      color: var(--zy-brand);
      font-size: 24px;
    }

    small {
      margin-top: 34px;
      color: #98a2b3;
      font-size: 10px;
    }
  }

  .profile-signals {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 9px;
  }

  .profile-signals > div {
    min-width: 0;
    padding: 12px;
    border: 1px solid var(--zy-border);
    border-radius: 14px;
    background: #fbfdff;

    span,
    strong,
    p {
      display: block;
      min-width: 0;
    }

    span {
      color: #98a2b3;
      font-size: 11px;
      font-weight: 800;
    }

    strong {
      margin-top: 5px;
      color: var(--zy-text);
      font-size: 15px;
    }

    p {
      margin: 5px 0 0;
      color: var(--zy-muted);
      font-size: 11px;
      line-height: 1.55;
    }
  }

  .insight-summary {
    gap: 10px;
  }

  .insight-summary article,
  .panel {
    border-color: var(--zy-border);
    border-radius: 16px;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.045);
  }

  .summary-icon {
    color: var(--zy-brand);
    background: #eef2ff;
  }

  .analytics-grid {
    grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
    gap: 12px;
  }

  .panel-title {
    border-bottom-color: var(--zy-border);

    > div {
      color: var(--zy-brand);
    }
  }

  .mastery-track i,
  .rhythm-chart i {
    background: linear-gradient(180deg, #6366f1, #4f46e5);
  }

  .weak-list > div,
  .loop-steps > div {
    border: 1px solid transparent;
    transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;

    &:hover {
      border-color: rgba(99, 102, 241, 0.18);
      background: #ffffff;
      transform: translateY(-1px);
    }
  }

  .weak-list > div > span,
  .loop-steps > div > span {
    color: var(--zy-brand);
    background: #eef2ff;
  }

  .next-panel > button {
    height: 32px;
    margin-top: 14px;
    padding: 0 12px;
    border: 1px solid rgba(99, 102, 241, 0.16);
    border-radius: 999px;
    color: var(--zy-brand);
    background: #fff;
    font-size: 12px;
    font-weight: 800;
  }

  .weak-list {
    display: grid;
    gap: 8px;
    padding-top: 12px;
  }

  .weak-list > div {
    display: grid;
    grid-template-columns: 26px 1fr;
    align-items: center;
    gap: 9px;
    padding: 9px 0;
    border-bottom: 1px solid #eff1f5;
    border-radius: 10px;

    > span {
      display: grid;
      width: 24px;
      height: 24px;
      border-radius: 8px;
      font-size: 10px;
      font-weight: 800;
      place-items: center;
    }

    strong,
    small {
      display: block;
    }

    strong {
      color: #344054;
      font-size: 12px;
    }

    small {
      margin-top: 3px;
      color: #98a2b3;
      font-size: 10px;
    }
  }

  .focus-brief {
    margin-top: 14px;
    padding: 14px;
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: 14px;
    background: #f8f9ff;

    strong,
    p {
      display: block;
      margin: 0;
    }

    strong {
      color: var(--zy-text);
      font-size: 14px;
    }

    p {
      margin-top: 6px;
      color: var(--zy-muted);
      font-size: 12px;
      line-height: 1.6;
    }

    button {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      height: 30px;
      margin-top: 10px;
      padding: 0 11px;
      border: 0;
      border-radius: 999px;
      color: #fff;
      background: var(--zy-brand);
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;
    }
  }

  .ghost-action {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    height: 30px;
    margin-top: 12px;
    padding: 0;
    border: 0;
    color: var(--zy-brand);
    background: transparent;
    font-size: 12px;
    font-weight: 800;
    cursor: pointer;
  }

  .loop-steps {
    display: grid;
    gap: 8px;
    padding-top: 14px;

    > div {
      display: grid;
      grid-template-columns: 34px 1fr;
      column-gap: 10px;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid #eff1f5;
      border-radius: 10px;
    }

    span {
      display: grid;
      width: 30px;
      height: 30px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 800;
      place-items: center;
    }

    strong,
    small {
      display: block;
    }

    strong {
      color: #344054;
      font-size: 12px;
    }

    small {
      margin-top: 3px;
      color: #98a2b3;
      font-size: 10px;
    }
  }

  .analytics-drawer {
    display: grid;
    gap: 18px;

    section > span {
      display: block;
      margin-bottom: 10px;
      color: #98a2b3;
      font-size: 12px;
      font-weight: 800;
    }
  }

  .drawer-list {
    display: grid;
    gap: 10px;

    > div {
      padding: 12px;
      border: 1px solid var(--zy-border);
      border-radius: 14px;
      background: #fbfdff;
    }

    strong,
    p {
      display: block;
      margin: 0;
    }

    strong {
      color: var(--zy-text);
      font-size: 13px;
    }

    p {
      margin-top: 6px;
      color: var(--zy-muted);
      font-size: 12px;
      line-height: 1.6;
    }
  }

  .drawer-actions {
    display: flex;
    gap: 10px;
    padding-top: 4px;

    button {
      height: 34px;
      padding: 0 13px;
      border: 1px solid rgba(99, 102, 241, 0.16);
      border-radius: 999px;
      color: var(--zy-brand);
      background: #fff;
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;

      &.primary {
        border-color: transparent;
        color: #fff;
        background: var(--zy-brand);
      }
    }
  }

  @keyframes analytics-enter {
    from {
      opacity: 0;
      transform: translateY(8px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .course-analytics,
    .analytics-heading > button,
    .weak-list > div,
    .loop-steps > div {
      animation: none;
      transition: none;
    }
  }

  @media (max-width: 1180px) {
    .learning-profile-card {
      grid-template-columns: minmax(0, 1fr) 110px;
    }

    .profile-signals {
      grid-column: 1 / -1;
    }
  }

  @media (max-width: 900px) {
    .learning-profile-card,
    .analytics-grid {
      grid-template-columns: 1fr;
    }

    .profile-ring {
      justify-self: start;
    }
  }

  @media (max-width: 640px) {
    .profile-signals,
    .insight-summary {
      grid-template-columns: 1fr;
    }
  }
</style>
