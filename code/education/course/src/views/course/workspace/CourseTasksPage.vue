<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
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
  const activeFilter = ref<TaskFilter>('active');
  const selectedTaskId = ref('');
  const detailDrawerVisible = ref(false);
  const assistantDrawerVisible = ref(false);
  const course = computed(() => getClassroomCourse(String(route.params.courseId || '')));
  const tasks = computed(() => (course.value ? buildCourseTasks(course.value) : []));
  const taskStatusRank: Record<CourseTaskStatus, number> = {
    active: 0,
    upcoming: 1,
    done: 2,
  };
  const sortedTasks = computed(() =>
    [...tasks.value].sort((a, b) => {
      const rankDiff = taskStatusRank[a.status] - taskStatusRank[b.status];
      if (rankDiff) return rankDiff;
      return b.progress - a.progress;
    })
  );
  const visibleTasks = computed(() =>
    activeFilter.value === 'all'
      ? sortedTasks.value
      : sortedTasks.value.filter((task) => task.status === activeFilter.value)
  );
  const completedCount = computed(
    () => tasks.value.filter((task) => task.status === 'done').length
  );
  const activeCount = computed(
    () => tasks.value.filter((task) => task.status === 'active').length
  );
  const filters: Array<{ key: TaskFilter; label: string }> = [
    { key: 'active', label: '进行中' },
    { key: 'upcoming', label: '待开始' },
    { key: 'all', label: '全部任务' },
    { key: 'done', label: '已完成' },
  ];
  const selectedTask = computed(() => {
    const fromVisible = visibleTasks.value.find((task) => task.id === selectedTaskId.value);
    return fromVisible || visibleTasks.value[0] || tasks.value[0] || null;
  });
  const completionRate = computed(() =>
    Math.round((completedCount.value / Math.max(tasks.value.length, 1)) * 100)
  );
  const detailSteps = computed(() => {
    if (!selectedTask.value) return [];
    if (selectedTask.value.status === 'done') {
      return ['回看提交结果和错因记录', '整理一个可复用的答题模板', '把仍不稳定的知识点加入下一次复习'];
    }
    if (selectedTask.value.type === '测验') {
      return ['先复盘相关课节的定义和例题', '限时完成测验并标记不确定题', '测后把错因交给 AI 伴学追问'];
    }
    if (selectedTask.value.type === 'AI 任务') {
      return ['确认当前章节和任务目标', '让 AI 生成结构化总结或练习', '把产物同步到课程资料或笔记'];
    }
    return ['阅读任务要求并确认提交物', '完成核心步骤并记录卡点', '提交前让 AI 做一次检查'];
  });

  function taskStatusLabel(status: CourseTaskStatus) {
    if (status === 'done') return '已完成';
    if (status === 'active') return '进行中';
    return '待开始';
  }

  function taskActionLabel(task: { status: CourseTaskStatus; type: string }) {
    if (task.status === 'done') return '复盘';
    if (task.type === 'AI 任务') return '开始';
    return '处理';
  }

  function selectTask(taskId: string, openDrawer = false) {
    selectedTaskId.value = taskId;
    detailDrawerVisible.value = openDrawer;
  }

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
        <h1>任务中心</h1>
        <p>按截止时间查看作业、测验和复习任务；点击任务查看执行步骤和 AI 检查。</p>
      </div>
      <button type="button" @click="assistantDrawerVisible = true">
        <icon-robot /> 任务助手
      </button>
    </header>

    <div class="task-summary">
      <article>
        <span>本周待完成</span>
        <strong>{{ activeCount }}</strong>
        <small>按截止时间优先处理</small>
      </article>
      <article>
        <span>已完成</span>
        <strong>{{ completedCount }}</strong>
        <small>完成率 {{ completionRate }}%</small>
      </article>
      <article class="task-summary__focus">
        <span>建议投入</span>
        <strong>45<small> 分钟</small></strong>
        <small>完成一次学习闭环</small>
      </article>
    </div>

    <div class="task-board">
      <section class="task-board__main">
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
            :class="[
              `task-row--${task.status}`,
              { active: selectedTask?.id === task.id }
            ]"
            @click="selectTask(task.id, true)"
          >
            <span class="task-status">
              <icon-check-circle v-if="task.status === 'done'" />
              <icon-clock-circle v-else />
            </span>
            <div class="task-copy">
              <div>
                <span>{{ task.type }}</span>
                <em>{{ taskStatusLabel(task.status) }}</em>
              </div>
              <h2>{{ task.title }}</h2>
              <p>{{ task.chapter }}</p>
              <div class="task-meta">
                <span><icon-calendar /> {{ task.dueLabel }}</span>
                <span><icon-clock-circle /> {{ task.duration }} 分钟</span>
              </div>
            </div>
            <div class="task-progress">
              <span>{{ task.progress }}%</span>
              <div><i :style="{ width: `${task.progress}%` }"></i></div>
            </div>
            <span class="task-row__cta">详情</span>
          </article>
        </div>
      </section>
    </div>

    <a-drawer
      v-model:visible="detailDrawerVisible"
      :width="420"
      :footer="false"
      placement="right"
      unmount-on-close
    >
      <template #title>任务详情</template>
      <div v-if="selectedTask" class="task-detail task-detail--drawer">
        <div class="task-detail__head">
          <span>{{ selectedTask.type }} · {{ taskStatusLabel(selectedTask.status) }}</span>
          <h2>{{ selectedTask.title }}</h2>
          <p>{{ selectedTask.chapter }}</p>
        </div>
        <div class="task-detail__metrics">
          <span>截止 {{ selectedTask.dueLabel }}</span>
          <span>预计 {{ selectedTask.duration }} 分钟</span>
          <span>进度 {{ selectedTask.progress }}%</span>
        </div>
        <section>
          <strong>建议执行步骤</strong>
          <ol>
            <li v-for="step in detailSteps" :key="step">{{ step }}</li>
          </ol>
        </section>
        <details class="task-checklist">
          <summary>提交前检查</summary>
          <ul>
            <li>任务要求是否已经明确</li>
            <li>是否留下可复盘的错因或笔记</li>
            <li>需要时生成一次结构化检查</li>
          </ul>
        </details>
        <div class="task-detail__actions">
          <button type="button" class="primary" @click="askAgent(selectedTask.title)">
            {{ taskActionLabel(selectedTask) }}
          </button>
          <button type="button" @click="askAgent(`${selectedTask.title}复盘`)">
            生成复盘
          </button>
        </div>
      </div>
    </a-drawer>

    <a-drawer
      v-model:visible="assistantDrawerVisible"
      :width="400"
      :footer="false"
      placement="right"
      unmount-on-close
    >
      <template #title>任务助手</template>
      <div class="task-assistant-drawer">
        <section class="assistant-panel">
          <div class="assistant-panel__head">
            <span>本周任务</span>
            <p>只保留能推动行动的辅助能力，默认不占用主屏。</p>
          </div>
          <div class="assistant-stats">
            <article>
              <strong>{{ activeCount }}</strong>
              <span>进行中</span>
            </article>
            <article>
              <strong>{{ completedCount }}</strong>
              <span>已完成</span>
            </article>
            <article>
              <strong>{{ completionRate }}%</strong>
              <span>完成率</span>
            </article>
          </div>
        </section>

        <section class="assistant-panel">
          <div class="assistant-panel__head">
            <span>快捷处理</span>
            <p>围绕当前选中任务生成计划、复盘或检查。</p>
          </div>
          <div class="assistant-actions">
            <button type="button" @click="askAgent('根据课程进度规划本周任务')">
              <icon-calendar />
              <strong>生成本周计划</strong>
              <small>按截止时间排序</small>
            </button>
            <button
              type="button"
              :disabled="!selectedTask"
              @click="selectedTask && askAgent(selectedTask.title)"
            >
              <icon-robot />
              <strong>处理当前任务</strong>
              <small>{{ selectedTask?.title || '先选择任务' }}</small>
            </button>
            <button
              type="button"
              :disabled="!selectedTask"
              @click="selectedTask && askAgent(`${selectedTask.title}复盘`)"
            >
              <icon-check-circle />
              <strong>生成复盘</strong>
              <small>整理错因和下一步</small>
            </button>
          </div>
        </section>

        <section class="assistant-panel">
          <div class="assistant-panel__head">
            <span>提交检查</span>
            <p>保持任务完成质量，不在列表中堆额外说明。</p>
          </div>
          <ul class="assistant-checklist">
            <li>任务要求是否已经明确</li>
            <li>是否留下可复盘的错因或笔记</li>
            <li>是否需要生成一次结构化检查</li>
          </ul>
        </section>
      </div>
    </a-drawer>
  </section>
</template>

<style scoped lang="less">
  @brand: #6366f1;
  @text-primary: #101828;
  @text-secondary: #667085;
  @line: rgba(15, 23, 42, 0.08);

  .course-tasks {
    color: @text-primary;
    animation: task-enter 0.18s ease both;
  }

  .section-heading {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 20px;
    padding: 2px 2px 18px;

    h1 {
      margin: 0 0 6px;
      color: @text-primary;
      font-size: 26px;
      font-weight: 760;
      letter-spacing: 0;
    }

    p {
      max-width: 560px;
      margin: 0;
      color: @text-secondary;
      font-size: 13px;
      line-height: 1.6;
    }

    > button {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      height: 38px;
      padding: 0 15px;
      border: 0;
      border-radius: 999px;
      color: #fff;
      background: @brand;
      cursor: pointer;
      font-weight: 650;
      box-shadow: 0 10px 22px rgba(99, 102, 241, 0.18);
      transition: transform 160ms ease, background 160ms ease;

      &:hover {
        background: #4f46e5;
        transform: translateY(-1px);
      }
    }
  }

  .task-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;

    article {
      min-height: 70px;
      padding: 12px 15px;
      border: 1px solid @line;
      border-radius: 16px;
      background: #fff;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.035);
      transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;

      &:hover {
        border-color: rgba(99, 102, 241, 0.18);
        box-shadow: 0 12px 26px rgba(15, 23, 42, 0.055);
        transform: translateY(-1px);
      }
    }

    span,
    small {
      display: block;
      color: @text-secondary;
      font-size: 12px;
      line-height: 1.45;
    }

    strong {
      display: block;
      margin: 4px 0 3px;
      color: @text-primary;
      font-size: 23px;
      line-height: 1;

      small {
        display: inline;
        color: inherit;
        font-size: 13px;
      }
    }
  }

  .task-summary__focus {
    border-color: rgba(99, 102, 241, 0.18) !important;
    background: #f7f9ff !important;

    strong {
      color: @brand !important;
    }
  }

  .task-board {
    display: block;
    margin-top: 16px;
    align-items: start;
  }

  .task-board__main,
  .task-detail {
    border: 1px solid @line;
    border-radius: 16px;
    background: #fff;
    box-shadow: 0 10px 26px rgba(15, 23, 42, 0.035);
  }

  .task-board__main {
    padding: 12px;
  }

  .task-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;

    > div {
      display: flex;
      gap: 4px;
      padding: 4px;
      border: 1px solid @line;
      border-radius: 999px;
      background: #f8fafc;
    }

    button {
      height: 30px;
      padding: 0 12px;
      border: 0;
      border-radius: 999px;
      color: @text-secondary;
      background: transparent;
      font-size: 12px;
      cursor: pointer;
      transition: color 140ms ease, background 140ms ease;

      &.active {
        color: @brand;
        background: #fff;
        font-weight: 700;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.06);
      }
    }

    > span {
      color: @text-secondary;
      font-size: 12px;
      white-space: nowrap;
    }
  }

  .task-list {
    display: grid;
    gap: 8px;
  }

  .task-row {
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr) 126px 46px;
    align-items: center;
    gap: 12px;
    min-height: 76px;
    padding: 10px 12px;
    border: 1px solid transparent;
    border-radius: 14px;
    background: #fbfcff;
    cursor: pointer;
    transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease, background 160ms ease;
    animation: task-row-enter 0.22s ease both;

    &:hover,
    &.active {
      border-color: rgba(99, 102, 241, 0.18);
      background: #fff;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
      transform: translateY(-1px);
    }
  }

  .task-row:nth-child(2) { animation-delay: 0.025s; }
  .task-row:nth-child(3) { animation-delay: 0.05s; }
  .task-row:nth-child(4) { animation-delay: 0.075s; }
  .task-row:nth-child(5) { animation-delay: 0.1s; }
  .task-row:nth-child(6) { animation-delay: 0.125s; }
  .task-row:nth-child(7) { animation-delay: 0.15s; }
  .task-row:nth-child(8) { animation-delay: 0.175s; }

  .task-status {
    display: grid;
    width: 34px;
    height: 34px;
    border-radius: 11px;
    color: @brand;
    background: #eef2ff;
    place-items: center;
  }

  .task-row--done .task-status {
    color: #079455;
    background: #ecfdf3;
  }

  .task-copy {
    min-width: 0;

    > div:first-child {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 5px;
    }

    > div:first-child span,
    > div:first-child em {
      padding: 3px 7px;
      border-radius: 999px;
      font-size: 11px;
      font-style: normal;
      line-height: 1.2;
      white-space: nowrap;
    }

    > div:first-child span {
      color: @brand;
      background: #eef2ff;
      font-weight: 650;
    }

    > div:first-child em {
      color: @text-secondary;
      background: #f2f4f7;
    }

    h2 {
      margin: 0;
      overflow: hidden;
      color: @text-primary;
      font-size: 14px;
      font-weight: 700;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    p {
      margin: 5px 0;
      color: @text-secondary;
      font-size: 12px;
    }
  }

  .task-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    color: @text-secondary;
    font-size: 11px;

    span {
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
  }

  .task-progress {
    > span {
      display: block;
      margin-bottom: 6px;
      color: @text-secondary;
      font-size: 11px;
      text-align: right;
    }

    > div {
      height: 6px;
      overflow: hidden;
      border-radius: 999px;
      background: #eef2f6;
    }

    i {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: @brand;
      transition: width 220ms ease;
    }
  }

  .task-row__cta {
    justify-self: end;
    padding: 5px 9px;
    border-radius: 999px;
    color: #4f46e5;
    background: rgba(79, 70, 229, 0.08);
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
  }

  .task-detail {
    position: sticky;
    top: 82px;
    display: grid;
    gap: 14px;
    padding: 18px;
  }

  .task-detail__head {
    span {
      color: @brand;
      font-size: 12px;
      font-weight: 700;
    }

    h2 {
      margin: 7px 0 6px;
      color: @text-primary;
      font-size: 18px;
      line-height: 1.35;
    }

    p {
      margin: 0;
      color: @text-secondary;
      font-size: 13px;
      line-height: 1.5;
    }
  }

  .task-detail__metrics {
    display: grid;
    gap: 8px;

    span {
      padding: 9px 10px;
      border-radius: 11px;
      background: #f8fafc;
      color: #475467;
      font-size: 12px;
    }
  }

  .task-detail section {
    strong {
      display: block;
      margin-bottom: 8px;
      color: @text-primary;
      font-size: 13px;
    }

    ol,
    ul {
      display: grid;
      gap: 7px;
      margin: 0;
      padding-left: 18px;
      color: @text-secondary;
      font-size: 12px;
      line-height: 1.55;
    }
  }

  .task-checklist {
    overflow: hidden;
    border: 1px solid @line;
    border-radius: 13px;
    background: #fbfcff;

    summary {
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-height: 38px;
      padding: 0 12px;
      color: @text-primary;
      cursor: pointer;
      font-size: 13px;
      font-weight: 700;
      list-style: none;

      &::-webkit-details-marker {
        display: none;
      }

      &::after {
        color: #98a2b3;
        font-size: 12px;
        content: '+';
        transition: transform 160ms ease;
      }
    }

    &[open] summary::after {
      transform: rotate(45deg);
    }

    ul {
      display: grid;
      gap: 7px;
      margin: 0;
      padding: 0 14px 13px 30px;
      color: @text-secondary;
      font-size: 12px;
      line-height: 1.55;
    }
  }

  .task-detail__actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;

    button {
      height: 34px;
      padding: 0 13px;
      border: 1px solid @line;
      border-radius: 999px;
      color: #475467;
      background: #fff;
      cursor: pointer;
      font-size: 12px;
      font-weight: 650;

      &.primary {
        color: #fff;
        border-color: @brand;
        background: @brand;
      }
    }
  }

  .task-detail--drawer {
    border: 0;
    box-shadow: none;
    padding: 0;
  }

  .task-assistant-drawer {
    display: grid;
    gap: 14px;
  }

  .assistant-panel {
    padding: 14px;
    border: 1px solid @line;
    border-radius: 16px;
    background: #fff;
  }

  .assistant-panel__head {
    margin-bottom: 12px;

    span {
      color: @brand;
      font-size: 12px;
      font-weight: 750;
    }

    p {
      margin: 4px 0 0;
      color: @text-secondary;
      font-size: 12px;
      line-height: 1.5;
    }
  }

  .assistant-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;

    article {
      padding: 10px;
      border-radius: 13px;
      background: #f8faff;
    }

    strong,
    span {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      color: @text-primary;
      font-size: 18px;
    }

    span {
      margin-top: 3px;
      color: @text-secondary;
      font-size: 12px;
    }
  }

  .assistant-actions {
    display: grid;
    gap: 8px;

    button {
      min-width: 0;
      display: grid;
      grid-template-columns: 32px minmax(0, 1fr);
      gap: 9px;
      align-items: center;
      min-height: 60px;
      padding: 10px;
      border: 1px solid @line;
      border-radius: 14px;
      color: #475467;
      background: #f8fafc;
      cursor: pointer;
      text-align: left;
      transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease;

      &:hover:not(:disabled) {
        border-color: rgba(99, 102, 241, 0.24);
        box-shadow: 0 10px 20px rgba(15, 23, 42, 0.06);
        transform: translateY(-1px);
      }

      &:disabled {
        cursor: not-allowed;
        opacity: 0.5;
      }
    }

    svg {
      grid-row: 1 / span 2;
      width: 32px;
      height: 32px;
      padding: 8px;
      border-radius: 11px;
      color: @brand;
      background: #eef2ff;
    }

    strong,
    small {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      color: @text-primary;
      font-size: 13px;
    }

    small {
      color: @text-secondary;
      font-size: 11px;
    }
  }

  .assistant-checklist {
    display: grid;
    gap: 8px;
    margin: 0;
    padding: 0;
    list-style: none;

    li {
      position: relative;
      padding: 9px 10px 9px 28px;
      border-radius: 12px;
      color: #475467;
      background: #f8fafc;
      font-size: 12px;
      line-height: 1.45;

      &::before {
        position: absolute;
        top: 15px;
        left: 12px;
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: @brand;
        content: '';
      }
    }
  }

  @keyframes task-enter {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes task-row-enter {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 1180px) {
    .task-board {
      grid-template-columns: 1fr;
    }

    .task-detail {
      display: none;
    }
  }

  @media (max-width: 980px) {
    .task-row {
      grid-template-columns: 34px minmax(0, 1fr);
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

    .task-toolbar {
      align-items: stretch;
      flex-direction: column;

      > div {
        overflow-x: auto;
      }
    }

    .task-row {
      grid-template-columns: 32px minmax(0, 1fr);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .course-tasks {
      animation: none;
    }

    .task-row {
      animation: none;
    }

    .task-row,
    .section-heading > button,
    .task-summary article,
    .task-checklist summary::after,
    .assistant-actions button {
      transition: none;
    }

    .task-row:hover,
    .task-row.active,
    .section-heading > button:hover,
    .task-summary article:hover,
    .assistant-actions button:hover {
      transform: none;
    }
  }
</style>
