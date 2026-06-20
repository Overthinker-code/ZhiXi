<script setup lang="ts">
  import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    IconArrowLeft,
    IconBarChart,
    IconBook,
    IconBulb,
    IconFile,
    IconHome,
    IconMindMapping,
    IconRight,
    IconRobot,
    IconStorage,
  } from '@arco-design/web-vue/es/icon';
  import { getClassroomCourse } from '@/data/classroomCourses';
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';
  import {
    fetchCourseWorkspace,
    type CourseWorkspaceData,
  } from '@/api/course';

  const route = useRoute();
  const router = useRouter();
  const courseId = computed(() => String(route.params.courseId || ''));
  const course = computed(() => getClassroomCourse(courseId.value));
  const workspaceData = ref<CourseWorkspaceData | null>(null);
  const localCompletedLessonIds = ref<string[]>([]);
  const navRef = ref<HTMLElement | null>(null);

  const navItems = [
    { key: 'home', label: '课程首页', desc: '概览与动态', icon: IconHome },
    { key: 'content', label: '课堂内容', desc: '章节、笔记与导图', icon: IconBook },
    { key: 'tasks', label: '任务中心', desc: '作业、测验与复习', icon: IconFile },
    { key: 'resources', label: '课程资料', desc: '课件与资源分配', icon: IconStorage },
    { key: 'knowledge', label: '课程图谱', desc: '知识、问题与能力', icon: IconMindMapping },
    { key: 'analytics', label: '课程学情', desc: '进度与薄弱点', icon: IconBarChart },
    { key: 'agent', label: 'AI 课程助手', desc: '定制任务工作台', icon: IconRobot },
  ] as const;

  const activeSection = computed(() => String(route.meta.courseSection || 'home'));
  const currentLabel = computed(
    () => navItems.find((item) => item.key === activeSection.value)?.label || '课程首页'
  );
  const totalLessons = computed(
    () => course.value?.chapters.flatMap((chapter) => chapter.lessons).length || 0
  );
  const lessonIds = computed(
    () =>
      new Set(
        course.value?.chapters
          .flatMap((chapter) => chapter.lessons)
          .map((lesson) => lesson.id) || []
      )
  );
  const completedLessons = computed(() => {
    const base =
      course.value?.chapters
        .flatMap((chapter) => chapter.lessons)
        .filter((lesson) => lesson.status === 'done')
        .map((lesson) => lesson.id) || [];
    const merged = new Set([
      ...base,
      ...localCompletedLessonIds.value.filter((id) => lessonIds.value.has(id)),
    ]);
    return merged.size;
  });
  const displayProgress = computed(() => {
    if (!course.value) return 0;
    if (!totalLessons.value) return course.value.progress;
    return Math.min(Math.round((completedLessons.value / totalLessons.value) * 100), 100);
  });
  const dataCaption = computed(() => {
    const summary = workspaceData.value?.summary;
    if (!summary) return `${completedLessons.value} / ${totalLessons.value} 个课节已完成`;
    return `${summary.plan_count} 个教学计划 · ${summary.assignment_count} 项课程作业`;
  });

  function readLocalCompletedLessons(id: string) {
    if (!id) {
      localCompletedLessonIds.value = [];
      return;
    }
    try {
      const raw = window.localStorage.getItem(`zhixi:classroom-learning:${id}`);
      const parsed = raw ? JSON.parse(raw) : {};
      localCompletedLessonIds.value = Array.isArray(parsed.completedLessonIds)
        ? parsed.completedLessonIds.filter((lessonId: unknown): lessonId is string =>
            typeof lessonId === 'string'
          )
        : [];
    } catch {
      localCompletedLessonIds.value = [];
    }
  }

  function handleLearningStateUpdated(event: Event) {
    const detail = (event as CustomEvent<{ courseId?: string }>).detail;
    if (detail?.courseId === courseId.value) {
      readLocalCompletedLessons(courseId.value);
    }
  }

  function handleStorageUpdated() {
    readLocalCompletedLessons(courseId.value);
  }

  function navigate(section: (typeof navItems)[number]['key']) {
    router.push(courseWorkspaceLocation(courseId.value, section));
  }

  async function scrollActiveNavIntoView() {
    await nextTick();
    await new Promise((resolve) => requestAnimationFrame(resolve));
    const nav = navRef.value;
    const active = navRef.value?.querySelector<HTMLButtonElement>('button.active');
    if (!nav || !active) return;
    const targetLeft = active.offsetLeft - (nav.clientWidth - active.offsetWidth) / 2;
    nav.scrollTo({ left: Math.max(0, targetLeft), behavior: 'auto' });
  }

  watch(
    courseId,
    async (id) => {
      workspaceData.value = null;
      if (!id) return;
      readLocalCompletedLessons(id);
      try {
        workspaceData.value = await fetchCourseWorkspace(id);
      } catch {
        workspaceData.value = null;
      }
    },
    { immediate: true }
  );

  watch(activeSection, () => {
    scrollActiveNavIntoView();
  });

  onMounted(() => {
    window.addEventListener('storage', handleStorageUpdated);
    window.addEventListener('zhixi-classroom-learning-updated', handleLearningStateUpdated);
    scrollActiveNavIntoView();
  });

  onUnmounted(() => {
    window.removeEventListener('storage', handleStorageUpdated);
    window.removeEventListener('zhixi-classroom-learning-updated', handleLearningStateUpdated);
  });
</script>

<template>
  <div v-if="course" class="course-workspace">
    <aside class="course-workspace__sidebar">
      <button class="back-link" type="button" @click="router.push({ name: 'CourseList' })">
        <icon-arrow-left /> 返回课程总览
      </button>

      <section class="course-identity">
        <img :src="course.cover" :alt="course.title" />
        <div>
          <span>{{ course.department }}</span>
          <h1>{{ course.title }}</h1>
          <p>{{ course.teacher }} · {{ course.team }}</p>
        </div>
        <div class="identity-progress">
          <span>课程进度</span>
          <strong>{{ displayProgress }}%</strong>
          <div><i :style="{ width: `${displayProgress}%` }"></i></div>
          <small>{{ dataCaption }}</small>
        </div>
      </section>

      <nav ref="navRef" class="workspace-nav" aria-label="课程导航">
        <button
          v-for="item in navItems"
          :key="item.key"
          type="button"
          :class="{ active: activeSection === item.key }"
          @click="navigate(item.key)"
        >
          <span class="workspace-nav__icon"><component :is="item.icon" /></span>
          <span>
            <strong>{{ item.label }}</strong>
            <small>{{ item.desc }}</small>
          </span>
          <icon-right />
        </button>
      </nav>

      <button class="study-cta" type="button" @click="navigate('content')">
        <icon-bulb />
        <span><strong>继续学习</strong><small>从上次课节接着看</small></span>
        <icon-right />
      </button>
    </aside>

    <main class="course-workspace__main">
      <header class="workspace-header">
        <nav aria-label="面包屑">
          <button type="button" @click="router.push({ name: 'CourseList' })">课程中心</button>
          <icon-right />
          <button type="button" @click="navigate('home')">{{ course.shortTitle }}</button>
          <icon-right />
          <strong>{{ currentLabel }}</strong>
        </nav>
        <div class="workspace-header__actions">
          <span>{{ course.type }}</span>
          <button type="button" @click="navigate('agent')">
            <icon-robot /> 问小智
          </button>
        </div>
      </header>

      <div class="course-workspace__content">
        <router-view />
      </div>
    </main>
  </div>

  <section v-else class="course-missing">
    <icon-book />
    <h1>未找到这门课程</h1>
    <p>课程可能已下架，或当前账号暂未加入该课程。</p>
    <a-button type="primary" @click="router.push({ name: 'CourseList' })">
      返回课程总览
    </a-button>
  </section>
</template>

<style scoped lang="less">
  .course-workspace {
    width: min(1760px, 100%);
    min-height: calc(100vh - 64px);
    margin: 0 auto;
    display: grid;
    grid-template-columns: 244px minmax(0, 1fr);
    color: #17213a;
    background: #f7f8fc;
  }

  .course-workspace__sidebar {
    position: sticky;
    top: 64px;
    align-self: start;
    height: calc(100vh - 64px);
    padding: 18px 14px;
    border-right: 1px solid #e5e9f2;
    background: #fff;
    overflow-y: auto;
  }

  .back-link {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 6px 8px;
    border: 0;
    color: #7a8497;
    background: transparent;
    font-size: 12px;
    cursor: pointer;
  }

  .course-identity {
    margin: 13px 0 16px;
    padding: 12px;
    border: 1px solid #e6eaf2;
    border-radius: 12px;
    background: #fbfcff;

    > img {
      width: 100%;
      height: 92px;
      border-radius: 9px;
      object-fit: cover;
    }

    h1 {
      margin: 5px 0 3px;
      font-size: 16px;
      line-height: 1.35;
    }

    p,
    span,
    small {
      margin: 0;
      color: #8993a6;
      font-size: 10px;
    }

    > div:nth-child(2) {
      padding: 10px 2px 8px;
    }
  }

  .identity-progress {
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: center;
    gap: 5px;
    padding-top: 10px;
    border-top: 1px solid #eceff5;

    strong {
      color: #5266f6;
      font-size: 12px;
    }

    > div {
      grid-column: 1 / -1;
      height: 5px;
      overflow: hidden;
      border-radius: 99px;
      background: #e9edf7;
    }

    i {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: #5b6cf7;
    }

    small {
      grid-column: 1 / -1;
    }
  }

  .workspace-nav {
    display: flex;
    flex-direction: column;
    gap: 4px;

    button {
      width: 100%;
      display: grid;
      grid-template-columns: 34px minmax(0, 1fr) 14px;
      align-items: center;
      gap: 9px;
      padding: 9px 10px;
      border: 1px solid transparent;
      border-radius: 10px;
      color: #6c778c;
      background: transparent;
      text-align: left;
      cursor: pointer;
      transition: 160ms ease;

      > span:nth-child(2) {
        min-width: 0;
      }

      strong,
      small {
        display: block;
      }

      strong {
        color: #344058;
        font-size: 13px;
      }

      small {
        margin-top: 2px;
        color: #98a1b2;
        font-size: 9px;
      }

      > svg {
        font-size: 10px;
        opacity: 0;
      }

      &:hover,
      &.active {
        border-color: #dfe4ff;
        background: #f3f5ff;
      }

      &.active {
        color: #5367f8;

        strong {
          color: #4356dc;
        }

        > svg {
          opacity: 1;
        }
      }
    }
  }

  .workspace-nav__icon {
    display: grid;
    width: 32px;
    height: 32px;
    border-radius: 9px;
    color: #6f7a90;
    background: #f2f4f8;
    place-items: center;
  }

  .workspace-nav button.active .workspace-nav__icon {
    color: #5367f8;
    background: #e9edff;
  }

  .study-cta {
    width: 100%;
    margin-top: 16px;
    display: grid;
    grid-template-columns: 30px 1fr 12px;
    align-items: center;
    gap: 8px;
    padding: 11px;
    border: 0;
    border-radius: 12px;
    color: #fff;
    background: #5367f8;
    text-align: left;
    cursor: pointer;
    box-shadow: 0 8px 18px rgba(83, 103, 248, 0.2);

    strong,
    small {
      display: block;
    }

    small {
      margin-top: 2px;
      color: rgba(255, 255, 255, 0.72);
      font-size: 9px;
    }
  }

  .course-workspace__main {
    min-width: 0;
  }

  .workspace-header {
    min-height: 52px;
    padding: 8px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    border-bottom: 1px solid #e5e9f2;
    background: rgba(255, 255, 255, 0.96);

    nav {
      display: flex;
      align-items: center;
      gap: 7px;
      color: #9aa3b3;
      font-size: 11px;
    }

    nav button {
      padding: 0;
      border: 0;
      color: #7d8799;
      background: transparent;
      cursor: pointer;
    }

    nav strong {
      color: #3e4a60;
      font-weight: 600;
    }
  }

  .workspace-header__actions {
    display: flex;
    align-items: center;
    gap: 10px;

    > span {
      padding: 4px 8px;
      border-radius: 7px;
      color: #687388;
      background: #f1f3f7;
      font-size: 10px;
    }

    button {
      display: flex;
      align-items: center;
      gap: 5px;
      height: 30px;
      padding: 0 11px;
      border: 1px solid #dce2ff;
      border-radius: 8px;
      color: #5367f8;
      background: #f6f7ff;
      font-size: 11px;
      cursor: pointer;
    }
  }

  .course-workspace__content {
    min-width: 0;
    padding: 0 18px 26px;

    :deep(.zy-page-shell) {
      max-width: none;
      padding: 18px 0 24px;
    }
  }

  .course-missing {
    min-height: calc(100vh - 64px);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    color: #6f7b91;

    > svg {
      font-size: 48px;
      color: #8090ff;
    }

    h1 {
      margin: 16px 0 6px;
      color: #1d2940;
    }

    p {
      margin: 0 0 18px;
    }
  }

  @media (max-width: 1100px) {
    .course-workspace {
      grid-template-columns: 208px minmax(0, 1fr);
    }

    .course-workspace__sidebar {
      padding-inline: 10px;
    }
  }

  @media (max-width: 820px) {
    .course-workspace {
      display: block;
    }

    .course-workspace__sidebar {
      position: static;
      height: auto;
      padding: 10px 14px;
      border-right: 0;
      border-bottom: 1px solid #e5e9f2;
    }

    .course-identity,
    .study-cta,
    .back-link {
      display: none;
    }

    .workspace-nav {
      overflow-x: auto;
      flex-direction: row;

      button {
        min-width: 116px;
        grid-template-columns: 28px 1fr;
        padding: 7px 9px;

        > svg,
        small {
          display: none;
        }
      }
    }

    .workspace-nav__icon {
      width: 28px;
      height: 28px;
    }

    .workspace-header {
      padding-inline: 14px;
    }

    .course-workspace__content {
      padding-inline: 12px;
    }
  }
</style>
