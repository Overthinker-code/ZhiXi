<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    IconBulb,
    IconCheckCircle,
    IconDownload,
    IconFile,
    IconMindMapping,
    IconRobot,
    IconSearch,
    IconStorage,
  } from '@arco-design/web-vue/es/icon';
  import { getClassroomCourse } from '@/data/classroomCourses';
  import {
    buildCourseResources,
    type CourseResourceItem,
  } from '@/data/courseWorkspace';
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';

  const route = useRoute();
  const router = useRouter();
  const query = ref('');
  const activeType = ref<'全部' | CourseResourceItem['type']>('全部');
  const course = computed(() => getClassroomCourse(String(route.params.courseId || '')));
  const resources = computed(() =>
    course.value ? buildCourseResources(course.value) : []
  );
  const completedChapterCount = computed(
    () =>
      course.value?.chapters.filter((chapter) =>
        chapter.lessons.some((lesson) => lesson.status === 'done')
      ).length || 0
  );
  const resourceTypes = computed(() => [
    '全部' as const,
    ...Array.from(new Set(resources.value.map((item) => item.type))),
  ]);
  const visibleResources = computed(() => {
    const keyword = query.value.trim().toLowerCase();
    return resources.value.filter((item) => {
      const typeMatches = activeType.value === '全部' || item.type === activeType.value;
      const searchMatches =
        !keyword ||
        item.title.toLowerCase().includes(keyword) ||
        item.chapter.toLowerCase().includes(keyword);
      return typeMatches && searchMatches;
    });
  });
  const resourceQuality = computed(() => [
    {
      label: '资料定位',
      value: '章节 / 知识点 / 任务',
      desc: '每份资料都写入课程节点和使用场景',
    },
    {
      label: '学习闭环',
      value: '预习 / 练习 / 追问',
      desc: '下载后可直接进入 AI 伴学和课程图谱',
    },
    {
      label: '质量核查',
      value: '目标 / 证据 / 产物',
      desc: '导出文件包含可检查的学习交付标准',
    },
  ]);

  function resourceIndex(item: CourseResourceItem) {
    return Math.max(resources.value.findIndex((resource) => resource.id === item.id), 0);
  }

  function relatedConcept(item: CourseResourceItem) {
    if (!course.value) return undefined;
    return course.value.concepts[resourceIndex(item) % Math.max(course.value.concepts.length, 1)];
  }

  function relatedLesson(item: CourseResourceItem) {
    if (!course.value) return undefined;
    const lessons = course.value.chapters.flatMap((chapter) => chapter.lessons);
    return lessons[resourceIndex(item) % Math.max(lessons.length, 1)];
  }

  function resourcePlan(item: CourseResourceItem) {
    const concept = relatedConcept(item);
    const lesson = relatedLesson(item);
    const primaryPoint = concept?.points[0] || item.chapter;
    return {
      concept,
      lesson,
      goals: concept?.outcomes?.slice(0, 3) || [
        `能解释 ${primaryPoint} 的核心定义和适用边界。`,
        `能把 ${item.chapter} 的资料内容整理成可复述路径。`,
        '能完成 1 组检查题并记录错因。',
      ],
      graphNodes: [
        item.chapter.replace(/^第\d+章\s*/, ''),
        ...(concept?.points.slice(0, 3) || [primaryPoint]),
      ],
      tasks: [
        `用 8 分钟扫读《${item.title}》，标出定义、条件和例题证据。`,
        `把 ${primaryPoint} 与相邻概念做成一张三列表格。`,
        '完成资料末尾自测，并把错因交给 AI 伴学继续追问。',
      ],
      prompts: [
        `请基于《${item.title}》解释 ${primaryPoint} 的常见误区。`,
        `把 ${item.chapter} 整理成 20 分钟复习路径，并给出检查题。`,
      ],
    };
  }

  function buildResourceMarkdown(item: CourseResourceItem) {
    const plan = resourcePlan(item);
    const concept = plan.concept;
    const courseTitle = course.value?.title || '';
    const lessonTitle = plan.lesson?.title || item.chapter;
    const lines = [
      `# ${item.title}`,
      '',
      `课程：${courseTitle}`,
      `章节：${item.chapter}`,
      `课节：${lessonTitle}`,
      `资料类型：${item.type}`,
      `更新时间：${item.updatedAt}`,
      '',
      '## 学习目标',
      ...plan.goals.map((goal, index) => `${index + 1}. ${goal}`),
      '',
      '## 图谱定位',
      `核心节点：${plan.graphNodes.join(' / ')}`,
      `前置关系：先复盘 ${item.chapter} 的基本定义，再进入 ${concept?.title || lessonTitle} 的应用边界。`,
      `后续动作：把本资料生成的错题、摘要和追问同步到课程图谱。`,
      '',
      '## 课堂笔记骨架',
      `- 关键概念：${concept?.title || lessonTitle}`,
      `- 证据材料：${concept?.resources?.slice(0, 3).join('；') || `${item.title}、课堂讲义、例题卡片`}`,
      `- 易错点：${concept?.misconceptions?.slice(0, 2).join('；') || '定义边界不清；只背结论不写条件'}`,
      '',
      '## 练习与交付',
      ...plan.tasks.map((task, index) => `${index + 1}. ${task}`),
      '',
      '## AI 伴学追问提示',
      ...plan.prompts.map((prompt, index) => `${index + 1}. ${prompt}`),
      '',
      '## 质量核查清单',
      '- [ ] 能说清资料对应的章节、知识点和学习目标。',
      '- [ ] 能指出至少 2 个题目或案例中的证据。',
      '- [ ] 已完成自测并记录错因。',
      '- [ ] 已把薄弱点同步到课程图谱或 AI 伴学。'
    ];
    return `${lines.join('\n')}\n`;
  }

  function askAboutResource(item: CourseResourceItem) {
    if (!course.value) return;
    router.push(
      courseWorkspaceLocation(course.value.id, 'agent', {
        task: 'reader',
        prompt: `当前课程是《${course.value.title}》。我想围绕资料《${item.title}》提问，请先告诉我可以从哪些角度阅读这份资料。`,
        resourceId: item.id,
        source: 'resource',
      })
    );
  }

  function openGenerator() {
    if (!course.value) return;
    router.push({
      name: 'StudentCourseResourceGenerator',
      params: { courseId: course.value.id },
      query: {
        subject: course.value.title,
        topic: course.value.chapters[0]?.title || course.value.title,
        source: 'course-workspace',
      },
    });
  }

  function openKnowledgeMap() {
    if (!course.value) return;
    router.push(courseWorkspaceLocation(course.value.id, 'knowledge'));
  }

  function downloadResourceBrief(item: CourseResourceItem) {
    const content = buildResourceMarkdown(item);
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${course.value?.shortTitle || 'course'}-${item.title}-学习包.md`;
    link.click();
    URL.revokeObjectURL(url);
    Message.success('学习资源包已生成');
  }
</script>

<template>
  <section v-if="course" class="course-resources">
    <header class="resource-heading">
      <div>
        <span>COURSE LIBRARY</span>
        <h1>课程资料</h1>
        <p>按章节组织课件、讲义、案例和练习，所有资料都保留课程上下文。</p>
      </div>
      <button type="button" @click="openGenerator">
        <icon-robot /> AI 生成课程资源
      </button>
    </header>

    <div class="resource-overview">
      <article>
        <span class="overview-icon"><icon-storage /></span>
        <div><small>资料总数</small><strong>{{ resources.length }}</strong></div>
      </article>
      <article>
        <span class="overview-icon"><icon-file /></span>
        <div><small>覆盖章节</small><strong>{{ course.chapters.length }}</strong></div>
      </article>
      <article>
        <span class="overview-icon"><icon-download /></span>
        <div><small>本周新增</small><strong>6</strong></div>
      </article>
      <article>
        <span class="overview-icon"><icon-check-circle /></span>
        <div><small>图谱绑定</small><strong>{{ completedChapterCount }}</strong></div>
      </article>
    </div>

    <section class="resource-flow">
      <div>
        <span>RESOURCE TO GRAPH</span>
        <h2>把资料接入课程图谱</h2>
        <p>把章节资料、作业任务和讨论节点统一放进学习路径里，下载、追问、生成和图谱复盘形成同一条闭环。</p>
      </div>
      <div class="flow-steps">
        <button type="button" @click="openKnowledgeMap">
          <icon-mind-mapping />
          <strong>查看课程图谱</strong>
          <small>知识 / 问题 / 能力 / 目标</small>
        </button>
        <button type="button" @click="openGenerator">
          <icon-robot />
          <strong>生成图谱资源</strong>
          <small>讲义、练习、笔记、知识卡</small>
        </button>
        <button type="button" @click="askAboutResource(resources[0])" :disabled="!resources[0]">
          <icon-file />
          <strong>资料助手问答</strong>
          <small>基于当前课程资料追问</small>
        </button>
      </div>
    </section>

    <section class="quality-strip" aria-label="课程资料质量标准">
      <article v-for="item in resourceQuality" :key="item.label">
        <icon-bulb />
        <div>
          <strong>{{ item.label }}</strong>
          <span>{{ item.value }}</span>
          <small>{{ item.desc }}</small>
        </div>
      </article>
    </section>

    <div class="resource-toolbar">
      <label>
        <icon-search />
        <input v-model="query" type="search" placeholder="搜索资料或章节" />
      </label>
      <div>
        <button
          v-for="type in resourceTypes"
          :key="type"
          type="button"
          :class="{ active: activeType === type }"
          @click="activeType = type"
        >
          {{ type }}
        </button>
      </div>
    </div>

    <div class="resource-grid">
      <article v-for="item in visibleResources" :key="item.id" class="resource-card">
        <div class="resource-card__top">
          <span class="resource-type">{{ item.type }}</span>
          <small>{{ item.updatedAt }}</small>
        </div>
        <span class="resource-file-icon"><icon-file /></span>
        <h2>{{ item.title }}</h2>
        <p>{{ item.chapter }}</p>
        <div class="resource-path">
          <span v-for="node in resourcePlan(item).graphNodes.slice(0, 3)" :key="node">
            {{ node }}
          </span>
        </div>
        <ul class="resource-checks">
          <li v-for="task in resourcePlan(item).tasks.slice(0, 2)" :key="task">
            {{ task }}
          </li>
        </ul>
        <div class="resource-meta">
          <span>{{ item.size }}</span>
          <span>{{ item.downloads }} 次使用</span>
        </div>
        <div class="resource-actions">
          <button type="button" @click="downloadResourceBrief(item)">
            <icon-download /> 学习包
          </button>
          <button type="button" @click="askAboutResource(item)">
            <icon-robot /> 围绕资料提问
          </button>
        </div>
      </article>
    </div>

    <a-empty v-if="!visibleResources.length" description="没有匹配的课程资料" />
  </section>
</template>

<style scoped lang="less">
  .course-resources {
    color: #17213a;
  }

  .resource-heading {
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

  .resource-overview {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;

    article {
      display: flex;
      align-items: center;
      gap: 12px;
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
  }

  .quality-strip {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-top: 12px;

    article {
      min-width: 0;
      display: grid;
      grid-template-columns: 34px minmax(0, 1fr);
      gap: 10px;
      padding: 13px 14px;
      border: 1px solid #e3e9f5;
      border-radius: 12px;
      background: linear-gradient(135deg, #fff, #f8fbff);
      box-shadow: 0 8px 22px rgba(33, 48, 78, 0.04);
    }

    svg {
      width: 34px;
      height: 34px;
      padding: 8px;
      border-radius: 10px;
      color: #2e7d6a;
      background: #eaf8f2;
    }

    strong,
    span,
    small {
      display: block;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      color: #27344c;
      font-size: 12px;
    }

    span {
      margin-top: 2px;
      color: #5367f8;
      font-size: 10px;
      font-weight: 700;
    }

    small {
      margin-top: 5px;
      color: #8a95a8;
      font-size: 9px;
    }
  }

  .resource-flow {
    margin-top: 12px;
    display: grid;
    grid-template-columns: minmax(220px, 0.75fr) minmax(0, 1fr);
    gap: 12px;
    padding: 16px;
    border: 1px solid #dfe5ff;
    border-radius: 12px;
    background:
      radial-gradient(circle at right top, rgba(83, 103, 248, 0.11), transparent 34%),
      #fff;

    span {
      color: #5367f8;
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.14em;
    }

    h2 {
      margin: 6px 0 5px;
      color: #26334b;
      font-size: 18px;
    }

    p {
      margin: 0;
      color: #7f899b;
      font-size: 11px;
      line-height: 1.7;
    }
  }

  .flow-steps {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;

    button {
      min-width: 0;
      display: grid;
      grid-template-columns: 30px minmax(0, 1fr);
      align-items: center;
      gap: 8px;
      padding: 10px;
      border: 1px solid #e5e9f4;
      border-radius: 10px;
      color: #667188;
      background: rgba(255, 255, 255, 0.86);
      text-align: left;
      cursor: pointer;

      &:disabled {
        cursor: not-allowed;
        opacity: 0.55;
      }

      svg {
        grid-row: 1 / span 2;
        color: #5367f8;
      }

      strong,
      small {
        display: block;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      strong {
        color: #334059;
        font-size: 11px;
      }

      small {
        margin-top: 2px;
        font-size: 9px;
      }
    }
  }

  .overview-icon {
    display: grid;
    width: 38px;
    height: 38px;
    border-radius: 10px;
    color: #596bfa;
    background: #edf0ff;
    place-items: center;
  }

  .resource-toolbar {
    margin: 16px 0 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;

    label {
      width: min(320px, 100%);
      height: 36px;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 11px;
      border: 1px solid #e1e6ef;
      border-radius: 9px;
      color: #929cad;
      background: #fff;
    }

    input {
      width: 100%;
      border: 0;
      outline: 0;
      color: #354158;
      background: transparent;
      font-size: 11px;
    }

    > div {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }

    > div button {
      height: 30px;
      padding: 0 10px;
      border: 1px solid #e3e7ef;
      border-radius: 8px;
      color: #778196;
      background: #fff;
      font-size: 10px;
      cursor: pointer;

      &.active {
        border-color: #d9dfff;
        color: #5367f8;
        background: #eef1ff;
      }
    }
  }

  .resource-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .resource-card {
    min-width: 0;
    padding: 15px;
    border: 1px solid #e4e8f1;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 3px 12px rgba(34, 48, 88, 0.04);
    transition: transform 160ms ease, box-shadow 160ms ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 24px rgba(46, 59, 116, 0.08);
    }

    h2 {
      margin: 11px 0 6px;
      overflow: hidden;
      color: #2b374e;
      font-size: 13px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    p {
      min-height: 30px;
      margin: 0;
      color: #8993a5;
      font-size: 10px;
      line-height: 1.5;
    }
  }

  .resource-path {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    min-height: 24px;
    margin-top: 10px;

    span {
      max-width: 100%;
      padding: 4px 7px;
      overflow: hidden;
      border-radius: 999px;
      color: #50617f;
      background: #f3f6fb;
      font-size: 9px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .resource-checks {
    display: grid;
    gap: 6px;
    min-height: 74px;
    margin: 10px 0 0;
    padding: 10px 11px;
    border-radius: 10px;
    background: #f8fafc;
    list-style: none;

    li {
      position: relative;
      padding-left: 12px;
      color: #657188;
      font-size: 10px;
      line-height: 1.5;

      &::before {
        position: absolute;
        top: 7px;
        left: 0;
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: #5367f8;
        content: '';
      }
    }
  }

  .resource-card__top,
  .resource-meta,
  .resource-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .resource-card__top small,
  .resource-meta {
    color: #98a1b1;
    font-size: 9px;
  }

  .resource-type {
    padding: 3px 7px;
    border-radius: 6px;
    color: #596bfa;
    background: #eef1ff;
    font-size: 9px;
  }

  .resource-file-icon {
    display: grid;
    width: 38px;
    height: 38px;
    margin-top: 14px;
    border-radius: 10px;
    color: #5367f8;
    background: #f0f2ff;
    place-items: center;
  }

  .resource-meta {
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid #edf0f5;
  }

  .resource-actions {
    gap: 6px;
    margin-top: 12px;

    button {
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      flex: 1;
      border: 1px solid #e0e5ee;
      border-radius: 8px;
      color: #687389;
      background: #fafbfc;
      font-size: 9px;
      cursor: pointer;
    }

    button:last-child {
      border-color: #dce2ff;
      color: #5367f8;
      background: #f5f7ff;
    }
  }

  @media (max-width: 1080px) {
    .resource-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 720px) {
    .resource-heading,
    .resource-toolbar,
    .resource-flow {
      align-items: flex-start;
      flex-direction: column;
    }

    .resource-overview,
    .resource-grid,
    .resource-flow,
    .quality-strip,
    .flow-steps {
      grid-template-columns: 1fr;
    }
  }
</style>
