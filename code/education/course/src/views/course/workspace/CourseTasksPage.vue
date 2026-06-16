<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    IconArrowRight,
    IconCalendar,
    IconCheckCircle,
    IconClockCircle,
    IconRobot,
  } from '@arco-design/web-vue/es/icon';
  import { getClassroomCourse } from '@/data/classroomCourses';
  import { buildCourseTasks, type CourseTaskStatus } from '@/data/courseWorkspace';
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';

  type TaskFilter = 'all' | CourseTaskStatus;

  const route = useRoute();
  const router = useRouter();
  const activeFilter = ref<TaskFilter>('all');
  const course = computed(() => getClassroomCourse(String(route.params.courseId || '')));
  const tasks = computed(() => (course.value ? buildCourseTasks(course.value) : []));
  const visibleTasks = computed(() =>
    activeFilter.value === 'all'
      ? tasks.value
      : tasks.value.filter((task) => task.status === activeFilter.value)
  );
  const completedCount = computed(
    () => tasks.value.filter((task) => task.status === 'done').length
  );
  const activeCount = computed(
    () => tasks.value.filter((task) => task.status === 'active').length
  );
  const filters: Array<{ key: TaskFilter; label: string }> = [
    { key: 'all', label: '全部任务' },
    { key: 'active', label: '进行中' },
    { key: 'upcoming', label: '待开始' },
    { key: 'done', label: '已完成' },
  ];

  function askAgent(taskTitle: string) {
    if (!course.value) return;
    router.push(
      courseWorkspaceLocation(course.value.id, 'agent', {
        prompt: `当前课程是《${course.value.title}》。请协助我完成“${taskTitle}”，先帮我确认任务要求和已有基础。`,
        source: 'task',
      })
    );
  }
</script>

<template>
  <section v-if="course" class="course-tasks">
    <header class="section-heading">
      <div>
        <span>COURSE TASKS</span>
        <h1>任务中心</h1>
        <p>把作业、测验、复习和 AI 学习任务放在同一条课程节奏中。</p>
      </div>
      <button type="button" @click="askAgent('根据课程进度规划本周任务')">
        <icon-robot /> AI 规划本周任务
      </button>
    </header>

    <div class="task-summary">
      <article>
        <span>本周待完成</span>
        <strong>{{ activeCount }}</strong>
        <small>优先处理临近截止任务</small>
      </article>
      <article>
        <span>已完成</span>
        <strong>{{ completedCount }}</strong>
        <small>完成率 {{ Math.round((completedCount / Math.max(tasks.length, 1)) * 100) }}%</small>
      </article>
      <article class="task-summary__focus">
        <span>建议投入</span>
        <strong>45<small> 分钟</small></strong>
        <small>完成一次学习闭环</small>
      </article>
    </div>

    <div class="task-toolbar">
      <div>
        <button
          v-for="filter in filters"
          :key="filter.key"
          type="button"
          :class="{ active: activeFilter === filter.key }"
          @click="activeFilter = filter.key"
        >
          {{ filter.label }}
        </button>
      </div>
      <span>{{ visibleTasks.length }} 项任务</span>
    </div>

    <div class="task-list">
      <article
        v-for="task in visibleTasks"
        :key="task.id"
        class="task-row"
        :class="`task-row--${task.status}`"
      >
        <span class="task-status">
          <icon-check-circle v-if="task.status === 'done'" />
          <icon-clock-circle v-else />
        </span>
        <div class="task-copy">
          <div>
            <span>{{ task.type }}</span>
            <h2>{{ task.title }}</h2>
          </div>
          <p>{{ task.chapter }}</p>
          <div class="task-meta">
            <span><icon-calendar /> {{ task.dueLabel }}</span>
            <span><icon-clock-circle /> 预计 {{ task.duration }} 分钟</span>
          </div>
        </div>
        <div class="task-progress">
          <span>{{ task.progress }}%</span>
          <div><i :style="{ width: `${task.progress}%` }"></i></div>
        </div>
        <button class="task-action" type="button" @click="askAgent(task.title)">
          {{ task.status === 'done' ? '复盘' : task.type === 'AI 任务' ? '开始' : 'AI 辅导' }}
          <icon-arrow-right />
        </button>
      </article>
    </div>
  </section>
</template>

<style scoped lang="less">
  .course-tasks {
    color: #17213a;
  }

  .section-heading {
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
      letter-spacing: -0.5px;
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
      box-shadow: 0 7px 16px rgba(83, 103, 248, 0.2);
    }
  }

  .task-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;

    article {
      padding: 17px 18px;
      border: 1px solid #e4e8f1;
      border-radius: 12px;
      background: #fff;
      box-shadow: 0 3px 12px rgba(34, 48, 88, 0.04);
    }

    span,
    small {
      display: block;
      color: #8b95a7;
      font-size: 10px;
    }

    strong {
      display: block;
      margin: 6px 0 4px;
      color: #27334a;
      font-size: 25px;

      small {
        display: inline;
        color: inherit;
        font-size: 12px;
      }
    }
  }

  .task-summary__focus {
    border-color: #dfe4ff !important;
    background: #f7f8ff !important;

    strong {
      color: #5367f8 !important;
    }
  }

  .task-toolbar {
    margin: 16px 0 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;

    > div {
      display: flex;
      gap: 4px;
      padding: 4px;
      border: 1px solid #e4e8f1;
      border-radius: 10px;
      background: #fff;
    }

    button {
      height: 28px;
      padding: 0 11px;
      border: 0;
      border-radius: 7px;
      color: #778196;
      background: transparent;
      font-size: 11px;
      cursor: pointer;

      &.active {
        color: #4d61e9;
        background: #edf0ff;
        font-weight: 650;
      }
    }

    > span {
      color: #929bad;
      font-size: 10px;
    }
  }

  .task-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .task-row {
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr) 120px 88px;
    align-items: center;
    gap: 12px;
    min-height: 84px;
    padding: 12px 14px;
    border: 1px solid #e4e8f1;
    border-radius: 12px;
    background: #fff;
    transition: border-color 160ms ease, box-shadow 160ms ease;

    &:hover {
      border-color: #d2d9ff;
      box-shadow: 0 8px 20px rgba(48, 61, 122, 0.07);
    }
  }

  .task-status {
    display: grid;
    width: 32px;
    height: 32px;
    border-radius: 9px;
    color: #596bfa;
    background: #edf0ff;
    place-items: center;
  }

  .task-row--done .task-status {
    color: #168a65;
    background: #e9f8f2;
  }

  .task-copy {
    min-width: 0;

    > div:first-child {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    > div:first-child span {
      padding: 3px 7px;
      border-radius: 6px;
      color: #5f70ed;
      background: #f0f2ff;
      font-size: 9px;
      white-space: nowrap;
    }

    h2 {
      margin: 0;
      overflow: hidden;
      color: #2a364d;
      font-size: 13px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    p {
      margin: 5px 0;
      color: #8a94a6;
      font-size: 10px;
    }
  }

  .task-meta {
    display: flex;
    gap: 14px;
    color: #929bad;
    font-size: 9px;

    span {
      display: flex;
      align-items: center;
      gap: 4px;
    }
  }

  .task-progress {
    > span {
      display: block;
      margin-bottom: 5px;
      color: #778196;
      font-size: 9px;
      text-align: right;
    }

    > div {
      height: 5px;
      overflow: hidden;
      border-radius: 99px;
      background: #edf0f5;
    }

    i {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: #5b6cf7;
    }
  }

  .task-action {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    height: 30px;
    border: 1px solid #dce2ff;
    border-radius: 8px;
    color: #5367f8;
    background: #f7f8ff;
    font-size: 10px;
    cursor: pointer;
  }

  @media (max-width: 980px) {
    .task-row {
      grid-template-columns: 34px minmax(0, 1fr) 82px;
    }

    .task-progress {
      display: none;
    }
  }

  @media (max-width: 640px) {
    .section-heading {
      align-items: flex-start;
      flex-direction: column;
    }

    .task-summary {
      grid-template-columns: 1fr;
    }

    .task-row {
      grid-template-columns: 32px minmax(0, 1fr);
    }

    .task-action {
      grid-column: 2;
      justify-self: start;
      padding: 0 10px;
    }
  }
</style>
