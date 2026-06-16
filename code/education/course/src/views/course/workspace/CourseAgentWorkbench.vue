<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    IconBook,
    IconBulb,
    IconCode,
    IconEdit,
    IconExperiment,
    IconFile,
    IconHeart,
    IconHeartFill,
    IconMindMapping,
    IconPlayArrowFill,
    IconRobot,
    IconSearch,
    IconStar,
    IconStorage,
    IconVideoCamera,
  } from '@arco-design/web-vue/es/icon';
  import { Message } from '@arco-design/web-vue';
  import { getClassroomCourse } from '@/data/classroomCourses';
  import { courseAgentTasks } from '@/data/courseWorkspace';
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';

  type AgentCategory = '全部智能体' | '自学中心' | '效率工具' | '学习助手' | '资料科研';
  type AgentLaunchMode = 'chat' | 'resource' | 'graph';

  const route = useRoute();
  const router = useRouter();
  const course = computed(() => getClassroomCourse(String(route.params.courseId || '')));
  const activeCategory = ref<AgentCategory>('全部智能体');
  const keyword = ref('');
  const selectedAgentKey = ref(String(route.query.task || 'resource'));
  const favoriteKeys = ref(new Set<string>(['resource', 'practice', 'reader']));

  const categoryTabs: AgentCategory[] = ['全部智能体', '自学中心', '效率工具', '学习助手', '资料科研'];

  const agentCatalog = computed(() => {
    const taskByKey = new Map(courseAgentTasks.map((task) => [task.key, task]));
    return [
      {
        key: 'resource',
        title: '资料助手',
        category: '资料科研' as AgentCategory,
        desc: '基于课程画像、章节和薄弱点生成讲义、练习、导图和阅读路径。',
        icon: IconStorage,
        source: '课程内置',
        launch: 'resource' as AgentLaunchMode,
        estimate: '6 分钟',
        task: taskByKey.get('resource'),
      },
      {
        key: 'research',
        title: 'AI科研助手',
        category: '资料科研' as AgentCategory,
        desc: '把课程主题转成检索式、研究问题、文献阅读框架和可验证资料清单。',
        icon: IconExperiment,
        source: '课程内置',
        launch: 'chat' as AgentLaunchMode,
        estimate: '8 分钟',
        task: taskByKey.get('research'),
      },
      {
        key: 'practice',
        title: 'AI陪练',
        category: '学习助手' as AgentCategory,
        desc: '按当前进度个性化出题，先提示思路，再根据作答追练薄弱点。',
        icon: IconBulb,
        source: '课程内置',
        launch: 'chat' as AgentLaunchMode,
        estimate: '8 分钟',
        task: taskByKey.get('quiz'),
      },
      {
        key: 'reader',
        title: 'AI阅读助手',
        category: '自学中心' as AgentCategory,
        desc: '解析课件、论文或讲义，输出摘要、问题清单、思维导图和引用依据。',
        icon: IconBook,
        source: '资料增强',
        launch: 'chat' as AgentLaunchMode,
        estimate: '5 分钟',
        task: taskByKey.get('resource'),
      },
      {
        key: 'writer',
        title: '智能编写',
        category: '效率工具' as AgentCategory,
        desc: '生成课程报告、实验说明、讨论发言和结构化学习复盘。',
        icon: IconEdit,
        source: '写作工具',
        launch: 'resource' as AgentLaunchMode,
        estimate: '7 分钟',
        task: taskByKey.get('review'),
      },
      {
        key: 'graph',
        title: '课程知识图谱',
        category: '自学中心' as AgentCategory,
        desc: '进入可筛选课程图谱，查看章节、问题、能力和资源之间的关系。',
        icon: IconMindMapping,
        source: '图谱类',
        launch: 'graph' as AgentLaunchMode,
        estimate: '即时',
        task: taskByKey.get('map'),
      },
      {
        key: 'video',
        title: '视频理解',
        category: '学习助手' as AgentCategory,
        desc: '从课堂视频或截图提炼讲解结构、关键节点和复习动作。',
        icon: IconVideoCamera,
        source: '多模态',
        launch: 'chat' as AgentLaunchMode,
        estimate: '7 分钟',
        task: taskByKey.get('video'),
      },
      {
        key: 'formula',
        title: '公式识别',
        category: '效率工具' as AgentCategory,
        desc: '把公式转成标准 LaTeX，并解释符号含义、推导步骤和适用条件。',
        icon: IconCode,
        source: '学习工具',
        launch: 'chat' as AgentLaunchMode,
        estimate: '5 分钟',
        task: taskByKey.get('formula'),
      },
      {
        key: 'grade',
        title: '作业批改',
        category: '学习助手' as AgentCategory,
        desc: '按得分点、错因、订正步骤和掌握度给出结构化反馈。',
        icon: IconFile,
        source: '评价类',
        launch: 'chat' as AgentLaunchMode,
        estimate: '4 分钟',
        task: taskByKey.get('grade'),
      },
    ];
  });

  const filteredAgents = computed(() => {
    const key = keyword.value.trim().toLowerCase();
    return agentCatalog.value.filter((agent) => {
      const categoryMatches =
        activeCategory.value === '全部智能体' || agent.category === activeCategory.value;
      const keywordMatches =
        !key ||
        agent.title.toLowerCase().includes(key) ||
        agent.desc.toLowerCase().includes(key) ||
        agent.category.toLowerCase().includes(key);
      return categoryMatches && keywordMatches;
    });
  });

  const selectedAgent = computed(
    () =>
      agentCatalog.value.find((agent) => agent.key === selectedAgentKey.value) ||
      filteredAgents.value[0] ||
      agentCatalog.value[0]
  );

  const favoriteAgents = computed(() =>
    agentCatalog.value.filter((agent) => favoriteKeys.value.has(agent.key))
  );

  const categoryStats = computed(() =>
    categoryTabs.map((category) => ({
      category,
      count:
        category === '全部智能体'
          ? agentCatalog.value.length
          : agentCatalog.value.filter((agent) => agent.category === category).length,
    }))
  );

  function selectAgent(key: string) {
    selectedAgentKey.value = key;
    router.replace({ query: { ...route.query, task: key } });
  }

  function toggleFavorite(key: string) {
    const next = new Set(favoriteKeys.value);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    favoriteKeys.value = next;
  }

  function buildTutorPrompt(agent = selectedAgent.value) {
    if (!course.value || !agent) return '';
    const taskPrompt = agent.task?.prompt || agent.desc;
    return [
      `当前课程：${course.value.title}`,
      `课程简介：${course.value.description}`,
      `学习进度：${course.value.progress}%（${course.value.learned}/${course.value.total} 节）`,
      `当前智能体：${agent.title}`,
      `智能体能力：${agent.desc}`,
      taskPrompt,
      '请先确认我的学习状态，再给出可执行的下一步，并且只围绕当前课程内容展开。',
    ].join('\n');
  }

  function launchAgent(agent = selectedAgent.value) {
    if (!course.value || !agent) return;
    selectAgent(agent.key);
    if (agent.launch === 'resource') {
      openResourceGenerator(agent);
      return;
    }
    if (agent.launch === 'graph') {
      openKnowledgeCenter();
      return;
    }
    router.push({
      name: 'TutorChat',
      query: {
        prompt: buildTutorPrompt(agent),
        forceAgent: agent.task?.forceAgent || 'tutor_agent',
        courseId: course.value.id,
        source: 'course-agent',
        task: agent.key,
      },
    });
  }

  function openResourceGenerator(agent = selectedAgent.value) {
    if (!course.value || !agent) return;
    router.push({
      name: 'StudentCourseResourceGenerator',
      params: { courseId: course.value.id },
      query: {
        subject: course.value.title,
        topic: agent.title,
        goal: `${agent.desc}。请结合当前课程章节、课堂笔记、知识图谱和学习进度生成可下载资料。`,
        source: 'course-agent',
        task: agent.key,
      },
    });
  }

  function openKnowledgeCenter() {
    if (!course.value) return;
    router.push(courseWorkspaceLocation(course.value.id, 'knowledge'));
  }

  function copyAgent(agent = selectedAgent.value) {
    if (!agent) return;
    navigator.clipboard?.writeText(`${agent.title}：${agent.desc}`).catch(() => null);
    Message.success('已复制智能体说明');
  }
</script>

<template>
  <section v-if="course" class="agent-hub">
    <header class="hub-top">
      <div class="hub-title">
        <span><icon-robot /> AI智能体</span>
        <h1>课程智能体中心</h1>
        <p>围绕当前课程提供资料生成、知识图谱、陪练答疑、科研阅读和学习规划。</p>
      </div>
      <label class="hub-search">
        <icon-search />
        <input v-model="keyword" type="search" placeholder="搜索智能体、资料或知识点" />
      </label>
    </header>

    <nav class="category-tabs" aria-label="AI智能体分类">
      <button
        v-for="item in categoryStats"
        :key="item.category"
        type="button"
        :class="{ active: activeCategory === item.category }"
        @click="activeCategory = item.category"
      >
        <span>{{ item.category }}</span>
        <small>{{ item.count }}</small>
      </button>
    </nav>

    <div class="hub-layout">
      <main class="agent-market">
        <section v-if="favoriteAgents.length" class="quick-row">
          <div class="section-heading">
            <strong><icon-star /> 常用智能体</strong>
            <span>收藏后可直接从这里启动</span>
          </div>
          <div class="quick-list">
            <button
              v-for="agent in favoriteAgents"
              :key="agent.key"
              type="button"
              @click="launchAgent(agent)"
            >
              <component :is="agent.icon" />
              <span>{{ agent.title }}</span>
            </button>
          </div>
        </section>

        <section class="agent-section">
          <div class="section-heading">
            <strong>{{ activeCategory }}</strong>
            <span>{{ filteredAgents.length }} 个可用智能体</span>
          </div>

          <div class="agent-grid">
            <article
              v-for="agent in filteredAgents"
              :key="agent.key"
              class="agent-card"
              :class="{ active: selectedAgent?.key === agent.key }"
            >
              <button type="button" class="agent-main" @click="selectAgent(agent.key)">
                <span class="agent-icon"><component :is="agent.icon" /></span>
                <span class="agent-copy">
                  <strong>{{ agent.title }}</strong>
                  <small>{{ agent.desc }}</small>
                </span>
              </button>
              <div class="agent-meta">
                <span>{{ agent.category }}</span>
                <span>{{ agent.source }}</span>
                <span>{{ agent.estimate }}</span>
              </div>
              <div class="agent-actions">
                <button type="button" class="launch-btn" @click="launchAgent(agent)">
                  <icon-play-arrow-fill /> 即用
                </button>
                <button type="button" @click="openResourceGenerator(agent)">
                  <icon-storage /> 资料
                </button>
                <button
                  type="button"
                  class="favorite-btn"
                  :aria-label="favoriteKeys.has(agent.key) ? '取消收藏' : '收藏智能体'"
                  @click="toggleFavorite(agent.key)"
                >
                  <icon-heart-fill v-if="favoriteKeys.has(agent.key)" />
                  <icon-heart v-else />
                </button>
              </div>
            </article>
          </div>
        </section>
      </main>

      <aside class="agent-panel">
        <section class="selected-agent">
          <span>当前智能体</span>
          <div class="selected-head">
            <span class="agent-icon agent-icon--large">
              <component :is="selectedAgent?.icon" />
            </span>
            <div>
              <h2>{{ selectedAgent?.title }}</h2>
              <p>{{ selectedAgent?.desc }}</p>
            </div>
          </div>
          <div class="selected-actions">
            <button type="button" class="primary" @click="launchAgent()">
              <icon-robot /> 启动智能体
            </button>
            <button type="button" @click="openResourceGenerator()">
              <icon-storage /> 生成资料
            </button>
            <button type="button" @click="openKnowledgeCenter">
              <icon-mind-mapping /> 课程图谱
            </button>
          </div>
        </section>

        <section class="course-context">
          <strong>课程上下文</strong>
          <p>{{ course.description }}</p>
          <div class="context-tags">
            <span v-for="concept in course.concepts" :key="concept.title">
              {{ concept.title }}
            </span>
          </div>
          <button type="button" @click="copyAgent()">
            复制智能体说明
          </button>
        </section>
      </aside>
    </div>
  </section>
</template>

<style scoped lang="less">
  .agent-hub {
    min-height: calc(100vh - 150px);
    color: #172033;
  }

  .hub-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 4px 2px 18px;
  }

  .hub-title {
    span {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 13px;
      border-radius: 999px;
      background: #2563eb;
      color: #fff;
      font-size: 13px;
      font-weight: 800;
      box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18);
    }

    h1 {
      margin: 12px 0 5px;
      font-size: 30px;
      letter-spacing: 0;
    }

    p {
      margin: 0;
      color: #6b768a;
      font-size: 14px;
    }
  }

  .hub-search {
    width: min(360px, 38vw);
    height: 44px;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 15px;
    border: 1px solid #e2e7f0;
    border-radius: 999px;
    background: #fff;
    color: #8b96aa;
    box-shadow: 0 8px 24px rgba(37, 51, 91, 0.06);

    input {
      min-width: 0;
      width: 100%;
      border: 0;
      outline: 0;
      color: #253047;
      background: transparent;
      font-size: 14px;
    }
  }

  .category-tabs {
    display: flex;
    gap: 26px;
    padding: 0 24px;
    border: 1px solid #e8edf5;
    border-radius: 18px 18px 0 0;
    background: #fff;

    button {
      position: relative;
      height: 68px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 0;
      color: #596275;
      background: transparent;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;

      &::after {
        content: '';
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 4px;
        border-radius: 999px 999px 0 0;
        background: transparent;
      }

      &.active {
        color: #111827;

        &::after {
          background: #3b82f6;
        }
      }

      small {
        color: #94a3b8;
        font-size: 12px;
      }
    }
  }

  .hub-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 310px;
    gap: 16px;
    padding: 22px;
    border: 1px solid #e8edf5;
    border-top: 0;
    border-radius: 0 0 18px 18px;
    background: #fff;
  }

  .agent-market {
    min-width: 0;
  }

  .quick-row,
  .agent-section,
  .agent-panel section {
    border: 1px solid #e7ecf4;
    border-radius: 12px;
    background: #fff;
  }

  .quick-row {
    padding: 14px;
    margin-bottom: 14px;
  }

  .section-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;

    strong {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      color: #202b42;
      font-size: 15px;
    }

    span {
      color: #8a94a6;
      font-size: 12px;
    }
  }

  .quick-list {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;

    button {
      height: 36px;
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 0 12px;
      border: 1px solid #dce5f5;
      border-radius: 10px;
      color: #315181;
      background: #f8fbff;
      cursor: pointer;
    }
  }

  .agent-section {
    padding: 14px;
  }

  .agent-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
  }

  .agent-card {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-height: 190px;
    padding: 16px;
    border: 1px solid #e5ebf3;
    border-radius: 12px;
    background: #fff;
    transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;

    &.active,
    &:hover {
      border-color: #bcd0ff;
      box-shadow: 0 16px 34px rgba(39, 65, 121, 0.1);
      transform: translateY(-2px);
    }
  }

  .agent-main {
    display: grid;
    grid-template-columns: 58px minmax(0, 1fr);
    gap: 14px;
    align-items: flex-start;
    padding: 0;
    border: 0;
    background: transparent;
    text-align: left;
    cursor: pointer;
  }

  .agent-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 58px;
    height: 58px;
    border: 1px solid #dfe6f2;
    border-radius: 14px;
    color: #3b82f6;
    background: linear-gradient(145deg, #f8fbff, #edf6ff);
    font-size: 26px;

    &--large {
      width: 64px;
      height: 64px;
      flex-shrink: 0;
    }
  }

  .agent-copy {
    strong,
    small {
      display: block;
    }

    strong {
      margin: 4px 0 8px;
      color: #111827;
      font-size: 18px;
    }

    small {
      color: #596579;
      font-size: 13px;
      line-height: 1.6;
    }
  }

  .agent-meta,
  .agent-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
  }

  .agent-meta {
    margin-top: auto;

    span {
      padding: 4px 8px;
      border-radius: 999px;
      background: #f2f5fa;
      color: #728096;
      font-size: 11px;
    }
  }

  .agent-actions {
    button {
      height: 32px;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 0 10px;
      border: 1px solid #dfe6f2;
      border-radius: 9px;
      color: #36506f;
      background: #fff;
      cursor: pointer;

      &.launch-btn {
        border-color: transparent;
        color: #fff;
        background: #2563eb;
      }

      &.favorite-btn {
        width: 34px;
        justify-content: center;
        padding: 0;
        color: #ef5b7a;
      }
    }
  }

  .agent-panel {
    display: grid;
    gap: 14px;
    align-content: start;
  }

  .selected-agent,
  .course-context {
    padding: 16px;
  }

  .selected-agent > span {
    color: #2563eb;
    font-size: 11px;
    font-weight: 800;
  }

  .selected-head {
    display: flex;
    gap: 13px;
    margin: 12px 0 16px;

    h2 {
      margin: 0 0 6px;
      color: #172033;
      font-size: 20px;
    }

    p {
      margin: 0;
      color: #657286;
      font-size: 13px;
      line-height: 1.55;
    }
  }

  .selected-actions {
    display: grid;
    gap: 9px;

    button {
      height: 38px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      border: 1px solid #dfe6f2;
      border-radius: 10px;
      color: #334155;
      background: #fff;
      cursor: pointer;

      &.primary {
        border-color: transparent;
        color: #fff;
        background: #2563eb;
      }
    }
  }

  .course-context {
    strong {
      color: #172033;
      font-size: 15px;
    }

    p {
      color: #68758a;
      font-size: 13px;
      line-height: 1.65;
    }

    button {
      width: 100%;
      height: 36px;
      margin-top: 12px;
      border: 1px solid #dfe6f2;
      border-radius: 10px;
      color: #334155;
      background: #fff;
      cursor: pointer;
    }
  }

  .context-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;

    span {
      padding: 5px 8px;
      border-radius: 999px;
      color: #2563eb;
      background: #eff6ff;
      font-size: 12px;
    }
  }

  @media (max-width: 1180px) {
    .hub-layout {
      grid-template-columns: 1fr;
    }

    .agent-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 760px) {
    .hub-top,
    .category-tabs {
      align-items: stretch;
      flex-direction: column;
    }

    .hub-search {
      width: 100%;
    }

    .category-tabs {
      gap: 6px;
      padding: 10px;

      button {
        height: 40px;
      }
    }

    .hub-layout {
      padding: 12px;
    }

    .agent-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
