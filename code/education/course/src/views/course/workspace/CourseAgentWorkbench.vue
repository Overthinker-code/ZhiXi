<script setup lang="ts">
  import { computed } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    IconBook,
    IconMindMapping,
    IconRobot,
    IconRight,
    IconStorage,
  } from '@arco-design/web-vue/es/icon';
  import { getClassroomCourse } from '@/data/classroomCourses';
  import { courseAgentTasks } from '@/data/courseWorkspace';
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';
  import LegacyAssistantPanel from '@/views/chat/LegacyAssistantPanel.vue';

  const route = useRoute();
  const router = useRouter();
  const course = computed(() => getClassroomCourse(String(route.params.courseId || '')));
  const selectedTask = computed(() => String(route.query.task || ''));
  const taskGroups = computed(() =>
    ['教学增强', '学习工具', '资料科研'].map((category) => ({
      category,
      tasks: courseAgentTasks.filter((task) => task.category === category),
    }))
  );
  const selectedTaskTitle = computed(
    () =>
      courseAgentTasks.find((task) => task.key === selectedTask.value)?.title ||
      '未选择'
  );

  function activateTask(task: (typeof courseAgentTasks)[number]) {
    if (!course.value) return;
    const nextPrompt = [
      `当前课程：${course.value.title}`,
      `课程进度：${course.value.progress}%`,
      `当前任务：${task.title}`,
      task.prompt,
      '请始终限定在当前课程上下文中，不要混入其他课程内容。',
    ].join('\n');
    router.replace({
      query: {
        ...route.query,
        task: task.key,
        forceAgent: task.forceAgent,
        prompt: nextPrompt,
      },
    });
  }

  function openKnowledgeCenter() {
    if (!course.value) return;
    router.push(courseWorkspaceLocation(course.value.id, 'knowledge'));
  }

  function openResourceGenerator() {
    if (!course.value) return;
    router.push({
      name: 'StudentCourseResourceGenerator',
      params: { courseId: course.value.id },
      query: {
        subject: course.value.title,
        topic: selectedTaskTitle.value,
        source: 'course-agent',
      },
    });
  }
</script>

<template>
  <section v-if="course" class="course-agent">
    <header class="agent-heading">
      <div>
        <span>COURSE AGENT</span>
        <h1>AI 课程助手</h1>
        <p>已锁定《{{ course.title }}》上下文，选择任务后可继续追问、上传资料或提交答案。</p>
      </div>
      <div class="agent-heading__actions">
        <button type="button" @click="openKnowledgeCenter">
          <icon-mind-mapping /> 课程图谱
        </button>
        <button type="button" @click="openResourceGenerator">
          <icon-storage /> 生成资源
        </button>
        <div class="context-pill"><icon-robot /> {{ course.shortTitle }}专属工作台</div>
      </div>
    </header>

    <div class="agent-layout">
      <aside class="agent-tasks">
        <div class="agent-tasks__heading">
          <strong>课程工具 Agent</strong>
          <span>{{ courseAgentTasks.length }} 个</span>
        </div>
        <section
          v-for="group in taskGroups"
          :key="group.category"
          class="agent-task-group"
        >
          <div class="agent-task-group__title">
            <icon-book v-if="group.category === '教学增强'" />
            <icon-robot v-else-if="group.category === '学习工具'" />
            <icon-storage v-else />
            <span>{{ group.category }}</span>
          </div>
          <button
            v-for="task in group.tasks"
            :key="task.key"
            type="button"
            :class="{ active: selectedTask === task.key }"
            @click="activateTask(task)"
          >
            <span class="task-icon"><component :is="task.icon" /></span>
            <span class="task-copy">
              <strong>{{ task.title }}</strong>
              <small>{{ task.description }}</small>
              <em>{{ task.estimate }}</em>
            </span>
            <icon-right />
          </button>
        </section>
      </aside>

      <main class="agent-chat">
        <div class="agent-context-bar">
          <div>
            <span>上下文范围</span>
            <strong>整门课程</strong>
          </div>
          <div>
            <span>课程进度</span>
            <strong>{{ course.progress }}%</strong>
          </div>
          <div>
            <span>资料范围</span>
            <strong>当前课程库</strong>
          </div>
          <div>
            <span>当前工具</span>
            <strong>{{ selectedTaskTitle }}</strong>
          </div>
          <small>任务、图谱和资源生成共享当前课程上下文</small>
        </div>
        <LegacyAssistantPanel />
      </main>
    </div>
  </section>
</template>

<style scoped lang="less">
  .course-agent {
    color: #17213a;
  }

  .agent-heading {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 20px;
    padding: 2px 2px 14px;

    > div:first-child > span {
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
  }

  .context-pill {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 11px;
    border: 1px solid #dce2ff;
    border-radius: 9px;
    color: #5367f8;
    background: #f5f7ff;
    font-size: 10px;
  }

  .agent-heading__actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;

    button {
      height: 34px;
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 0 11px;
      border: 1px solid #dce2ff;
      border-radius: 9px;
      color: #5367f8;
      background: #fff;
      font-size: 10px;
      cursor: pointer;
    }
  }

  .agent-layout {
    display: grid;
    grid-template-columns: 246px minmax(0, 1fr);
    gap: 12px;
    align-items: start;
  }

  .agent-tasks,
  .agent-chat {
    border: 1px solid #e4e8f1;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 3px 12px rgba(34, 48, 88, 0.04);
  }

  .agent-tasks {
    padding: 10px;
  }

  .agent-tasks__heading {
    display: flex;
    justify-content: space-between;
    padding: 3px 4px 10px;
    color: #37435a;
    font-size: 11px;

    span {
      color: #929bad;
      font-size: 9px;
    }
  }

  .agent-task-group + .agent-task-group {
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid #edf0f5;
  }

  .agent-task-group__title {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
    padding: 0 4px;
    color: #5367f8;
    font-size: 10px;
    font-weight: 700;
  }

  .agent-task-group > button {
    width: 100%;
    display: grid;
    grid-template-columns: 32px minmax(0, 1fr) 12px;
    align-items: start;
    gap: 8px;
    margin-bottom: 5px;
    padding: 10px 8px;
    border: 1px solid transparent;
    border-radius: 10px;
    color: #7c8799;
    background: #fafbfc;
    text-align: left;
    cursor: pointer;

    &:hover,
    &.active {
      border-color: #dce2ff;
      background: #f4f6ff;
    }

    &.active .task-icon {
      color: #5367f8;
      background: #e8ecff;
    }

    > svg {
      margin-top: 8px;
      font-size: 9px;
    }
  }

  .task-icon {
    display: grid;
    width: 30px;
    height: 30px;
    border-radius: 8px;
    color: #778298;
    background: #eef1f5;
    place-items: center;
  }

  .task-copy {
    min-width: 0;

    strong,
    small,
    em {
      display: block;
    }

    strong {
      color: #3a465d;
      font-size: 11px;
    }

    small {
      margin-top: 4px;
      color: #8d96a8;
      font-size: 8px;
      line-height: 1.55;
    }

    em {
      margin-top: 5px;
      color: #6879ec;
      font-size: 8px;
      font-style: normal;
    }
  }

  .agent-chat {
    min-width: 0;
    overflow: hidden;
  }

  .agent-context-bar {
    min-height: 46px;
    display: grid;
    grid-template-columns: repeat(4, max-content) 1fr;
    align-items: center;
    gap: 24px;
    padding: 7px 14px;
    border-bottom: 1px solid #e9edf4;
    background: #fbfcff;

    span,
    strong {
      display: block;
    }

    span {
      color: #929bad;
      font-size: 8px;
    }

    strong {
      margin-top: 2px;
      color: #44516a;
      font-size: 10px;
    }

    > small {
      justify-self: end;
      color: #9aa3b3;
      font-size: 8px;
    }
  }

  .agent-chat :deep(.chat-container) {
    height: calc(100vh - 250px);
    min-height: 580px;
    background: #fbfcff;
  }

  .agent-chat :deep(.messages-list) {
    max-width: 900px;
  }

  @media (max-width: 1050px) {
    .agent-layout {
      grid-template-columns: 210px minmax(0, 1fr);
    }

    .agent-context-bar {
      gap: 12px;
    }
  }

  @media (max-width: 820px) {
    .agent-heading {
      align-items: flex-start;
      flex-direction: column;
    }

    .agent-heading__actions {
      justify-content: flex-start;
    }

    .agent-layout {
      grid-template-columns: 1fr;
    }

    .agent-tasks {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 6px;
    }

    .agent-tasks__heading {
      grid-column: 1 / -1;
    }

    .agent-context-bar {
      grid-template-columns: repeat(4, 1fr);

      > small {
        display: none;
      }
    }
  }

  @media (max-width: 560px) {
    .agent-tasks {
      grid-template-columns: 1fr;
    }

    .agent-context-bar {
      grid-template-columns: 1fr 1fr;
    }

    .agent-context-bar > div:nth-child(3),
    .agent-context-bar > div:nth-child(4) {
      display: none;
    }
  }
</style>
