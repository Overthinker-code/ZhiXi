<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    IconBook,
    IconBulb,
    IconFile,
    IconMindMapping,
    IconRobot,
    IconRight,
    IconStorage,
  } from '@arco-design/web-vue/es/icon';
  import { getClassroomCourse } from '@/data/classroomCourses';
  import { courseAgentTasks } from '@/data/courseWorkspace';
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';

  const route = useRoute();
  const router = useRouter();
  const course = computed(() => getClassroomCourse(String(route.params.courseId || '')));
  const selectedTaskKey = ref(
    String(route.query.task || courseAgentTasks[0]?.key || '')
  );

  const taskGroups = computed(() =>
    ['教学增强', '学习工具', '资料科研'].map((category) => ({
      category,
      tasks: courseAgentTasks.filter((task) => task.category === category),
    }))
  );

  const selectedTask = computed(
    () =>
      courseAgentTasks.find((task) => task.key === selectedTaskKey.value) ||
      courseAgentTasks[0]
  );

  const agentMetrics = computed(() => {
    if (!course.value) return [];
    return [
      { label: '课程进度', value: `${course.value.progress}%`, desc: '自动锁定已学章节' },
      { label: '已学课节', value: `${course.value.learned}/${course.value.total}`, desc: '用于规划下一步任务' },
      { label: '工具数量', value: `${courseAgentTasks.length}`, desc: '答疑、科研、资料全覆盖' },
    ];
  });

  const workflowSteps = computed(() => {
    const title = selectedTask.value?.title || '课程工具';
    return [
      { label: '识别任务', desc: `围绕“${title}”读取课程、章节和学习进度。` },
      { label: '选择引擎', desc: '需要对话时进入 AI 伴学，需要产物时进入资源生成中心。' },
      { label: '生成闭环', desc: '结果可继续追问、生成讲义/练习/PDF，并沉淀回课程空间。' },
    ];
  });

  function selectTask(task: (typeof courseAgentTasks)[number]) {
    selectedTaskKey.value = task.key;
    router.replace({
      query: {
        ...route.query,
        task: task.key,
      },
    });
  }

  function buildTutorPrompt(task = selectedTask.value) {
    if (!course.value || !task) return '';
    return [
      `当前课程：${course.value.title}`,
      `课程简介：${course.value.description}`,
      `学习进度：${course.value.progress}%（${course.value.learned}/${course.value.total} 节）`,
      `当前课程工具：${task.title}`,
      `工具目标：${task.description}`,
      task.prompt,
      '请先确认我的学习状态，再给出可执行的下一步，不要混入其他课程内容。',
    ].join('\n');
  }

  function openTutor(task = selectedTask.value) {
    if (!course.value || !task) return;
    router.push({
      name: 'TutorChat',
      query: {
        prompt: buildTutorPrompt(task),
        forceAgent: task.forceAgent,
        courseId: course.value.id,
        source: 'course-agent',
        task: task.key,
      },
    });
  }

  function openResourceGenerator(task = selectedTask.value) {
    if (!course.value || !task) return;
    router.push({
      name: 'StudentCourseResourceGenerator',
      params: { courseId: course.value.id },
      query: {
        subject: course.value.title,
        topic: task.title,
        goal: `${task.description}。请生成可下载的讲义、练习、思维导图和拓展材料。`,
        source: 'course-agent',
        task: task.key,
      },
    });
  }

  function openContentMindMap() {
    if (!course.value) return;
    router.push({ name: 'StudentCourseContent', params: { courseId: course.value.id }, query: { open: 'mind' } });
  }

  function openKnowledgeCenter() {
    if (!course.value) return;
    router.push(courseWorkspaceLocation(course.value.id, 'knowledge'));
  }
</script>

<template>
  <section v-if="course" class="course-agent">
    <header class="agent-hero">
      <div class="agent-hero__copy">
        <span class="eyebrow">COURSE AGENT LAB</span>
        <h1>{{ course.shortTitle }}智能工具中枢</h1>
        <p>
          这里不再放小型聊天框，而是把课程工具做成可调度的 Agent 入口：
          需要追问就进入 AI 伴学，需要产物就进入资源生成中心。
        </p>
        <div class="hero-actions">
          <button type="button" class="primary-action" @click="openTutor()">
            <icon-robot /> 在 AI 伴学中执行
          </button>
          <button type="button" @click="openResourceGenerator()">
            <icon-storage /> 生成资料包
          </button>
          <button type="button" @click="openContentMindMap">
            <icon-mind-mapping /> 课堂导图
          </button>
        </div>
      </div>
      <div class="agent-hero__panel">
        <article v-for="item in agentMetrics" :key="item.label">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.desc }}</small>
        </article>
      </div>
    </header>

    <div class="agent-layout">
      <main class="agent-market">
        <section
          v-for="group in taskGroups"
          :key="group.category"
          class="agent-section"
        >
          <div class="section-heading">
            <span class="section-icon">
              <icon-book v-if="group.category === '教学增强'" />
              <icon-robot v-else-if="group.category === '学习工具'" />
              <icon-storage v-else />
            </span>
            <div>
              <h2>{{ group.category }}</h2>
              <p>
                {{
                  group.category === '教学增强'
                    ? '把课堂、作业和评价转成可执行教学动作'
                    : group.category === '学习工具'
                      ? '围绕当前课程进度提供答疑、复习和陪练'
                      : '面向资料整理、科研写作和生成式产物'
                }}
              </p>
            </div>
          </div>

          <div class="agent-card-grid">
            <article
              v-for="task in group.tasks"
              :key="task.key"
              class="agent-card"
              :class="{ active: selectedTask?.key === task.key }"
            >
              <button type="button" class="agent-card__main" @click="selectTask(task)">
                <span class="task-icon"><component :is="task.icon" /></span>
                <span class="task-copy">
                  <strong>{{ task.title }}</strong>
                  <small>{{ task.description }}</small>
                </span>
                <em>{{ task.estimate }}</em>
              </button>
              <div class="agent-card__actions">
                <button type="button" @click="openTutor(task)">
                  <icon-robot /> 对话执行
                </button>
                <button type="button" @click="openResourceGenerator(task)">
                  <icon-file /> 生成产物
                </button>
              </div>
            </article>
          </div>
        </section>
      </main>

      <aside class="agent-command">
        <div class="command-card selected-card">
          <span class="eyebrow">SELECTED AGENT</span>
          <h2>{{ selectedTask?.title }}</h2>
          <p>{{ selectedTask?.description }}</p>
          <div class="selected-meta">
            <span>{{ selectedTask?.category }}</span>
            <span>{{ selectedTask?.estimate }}</span>
            <span>{{ selectedTask?.forceAgent }}</span>
          </div>
          <div class="command-actions">
            <button type="button" class="primary-action" @click="openTutor()">
              <icon-robot /> 打开 AI 伴学
            </button>
            <button type="button" @click="openResourceGenerator()">
              <icon-storage /> 生成可下载资源
            </button>
            <button type="button" @click="openKnowledgeCenter">
              <icon-bulb /> 进入课程图谱
            </button>
          </div>
        </div>

        <div class="command-card workflow-card">
          <h2>执行流</h2>
          <ol>
            <li v-for="step in workflowSteps" :key="step.label">
              <span />
              <div>
                <strong>{{ step.label }}</strong>
                <p>{{ step.desc }}</p>
              </div>
            </li>
          </ol>
        </div>

        <div class="command-card context-card">
          <h2>课程上下文</h2>
          <p>{{ course.description }}</p>
          <div class="context-list">
            <span v-for="concept in course.concepts" :key="concept.title">
              {{ concept.title }}
            </span>
          </div>
          <button type="button" @click="openTutor()">
            让 AI 基于这些知识点制定计划 <icon-right />
          </button>
        </div>
      </aside>
    </div>
  </section>
</template>

<style scoped lang="less">
  .course-agent {
    color: #17213a;
  }

  .agent-hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 360px;
    gap: 18px;
    margin-bottom: 18px;
    padding: 24px;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background:
      linear-gradient(135deg, rgba(255, 255, 255, .96), rgba(245, 249, 255, .94)),
      radial-gradient(circle at 88% 12%, rgba(83, 103, 248, .18), transparent 30%);
    box-shadow: 0 10px 30px rgba(31, 45, 84, .06);
  }

  .eyebrow {
    color: #5367f8;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .12em;
  }

  .agent-hero__copy {
    h1 {
      margin: 8px 0 10px;
      font-size: 32px;
      letter-spacing: 0;
    }

    p {
      max-width: 760px;
      margin: 0;
      color: #64748b;
      font-size: 14px;
      line-height: 1.8;
    }
  }

  .hero-actions,
  .command-actions,
  .agent-card__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .hero-actions {
    margin-top: 20px;
  }

  button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    min-height: 36px;
    padding: 0 13px;
    border: 1px solid #dbe2ee;
    border-radius: 8px;
    color: #334155;
    background: #fff;
    font-size: 12px;
    font-weight: 650;
    cursor: pointer;
    transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;

    &:hover {
      border-color: #b9c4ff;
      box-shadow: 0 8px 20px rgba(83, 103, 248, .12);
      transform: translateY(-1px);
    }
  }

  .primary-action {
    border-color: #5367f8;
    color: #fff;
    background: #5367f8;
  }

  .agent-hero__panel {
    display: grid;
    gap: 10px;

    article {
      padding: 14px;
      border: 1px solid #e5e9f2;
      border-radius: 10px;
      background: rgba(255, 255, 255, .82);
    }

    span,
    small {
      display: block;
      color: #8390a4;
      font-size: 11px;
    }

    strong {
      display: block;
      margin: 4px 0;
      color: #17213a;
      font-size: 24px;
    }
  }

  .agent-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 340px;
    gap: 16px;
    align-items: start;
  }

  .agent-market,
  .agent-command {
    min-width: 0;
  }

  .agent-section,
  .command-card {
    border: 1px solid #e3e8f1;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 6px 20px rgba(31, 45, 84, .045);
  }

  .agent-section {
    padding: 18px;

    & + .agent-section {
      margin-top: 14px;
    }
  }

  .section-heading {
    display: flex;
    gap: 12px;
    margin-bottom: 14px;

    h2 {
      margin: 0 0 4px;
      font-size: 18px;
    }

    p {
      margin: 0;
      color: #7b8799;
      font-size: 12px;
    }
  }

  .section-icon,
  .task-icon {
    display: grid;
    width: 36px;
    height: 36px;
    border-radius: 9px;
    color: #5367f8;
    background: #f0f3ff;
    place-items: center;
    flex-shrink: 0;
  }

  .agent-card-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .agent-card {
    padding: 12px;
    border: 1px solid #e6ebf4;
    border-radius: 10px;
    background: #fbfcff;

    &.active {
      border-color: #b9c4ff;
      background: #f5f7ff;
    }
  }

  .agent-card__main {
    width: 100%;
    display: grid;
    grid-template-columns: 36px minmax(0, 1fr) auto;
    align-items: start;
    gap: 10px;
    min-height: 0;
    padding: 0;
    border: 0;
    background: transparent;
    text-align: left;
    box-shadow: none;

    &:hover {
      box-shadow: none;
      transform: none;
    }

    em {
      color: #5367f8;
      font-size: 11px;
      font-style: normal;
      white-space: nowrap;
    }
  }

  .task-copy {
    strong,
    small {
      display: block;
    }

    strong {
      color: #243044;
      font-size: 14px;
    }

    small {
      margin-top: 5px;
      color: #7c879a;
      font-size: 12px;
      line-height: 1.6;
    }
  }

  .agent-card__actions {
    margin-top: 12px;

    button {
      min-height: 30px;
      padding: 0 10px;
      font-size: 11px;
    }
  }

  .agent-command {
    display: grid;
    gap: 14px;
    position: sticky;
    top: 76px;
  }

  .command-card {
    padding: 16px;

    h2 {
      margin: 0 0 8px;
      font-size: 17px;
    }

    p {
      margin: 0;
      color: #66758a;
      font-size: 12px;
      line-height: 1.7;
    }
  }

  .selected-card h2 {
    margin-top: 6px;
  }

  .selected-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 14px 0;

    span {
      padding: 5px 8px;
      border-radius: 7px;
      color: #5367f8;
      background: #f0f3ff;
      font-size: 10px;
    }
  }

  .command-actions {
    flex-direction: column;

    button {
      width: 100%;
    }
  }

  .workflow-card {
    ol {
      margin: 0;
      padding: 0;
      list-style: none;
    }

    li {
      display: grid;
      grid-template-columns: 12px minmax(0, 1fr);
      gap: 10px;
      padding: 10px 0;
      border-top: 1px solid #edf1f7;

      > span {
        width: 10px;
        height: 10px;
        margin-top: 4px;
        border-radius: 50%;
        background: #5367f8;
      }

      strong {
        color: #273247;
        font-size: 13px;
      }
    }
  }

  .context-list {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin: 12px 0;

    span {
      padding: 5px 8px;
      border-radius: 7px;
      color: #475569;
      background: #f4f7fb;
      font-size: 11px;
    }
  }

  .context-card button {
    width: 100%;
  }

  @media (max-width: 1080px) {
    .agent-hero,
    .agent-layout {
      grid-template-columns: 1fr;
    }

    .agent-command {
      position: static;
    }
  }

  @media (max-width: 720px) {
    .agent-hero {
      padding: 18px;
    }

    .agent-card-grid {
      grid-template-columns: 1fr;
    }

    .agent-card__main {
      grid-template-columns: 36px minmax(0, 1fr);

      em {
        grid-column: 2;
      }
    }
  }
</style>
