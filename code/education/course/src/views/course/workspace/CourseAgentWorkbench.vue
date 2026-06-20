<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
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
  import { resolveCourseResourceReference } from '@/utils/courseResourceReference';

  type AgentCategory = '全部智能体' | '自学中心' | '效率工具' | '学习助手' | '资料科研';
  type AgentLaunchMode = 'chat' | 'resource' | 'graph';

  const route = useRoute();
  const router = useRouter();
  const course = computed(() => getClassroomCourse(String(route.params.courseId || '')));
  const activeCategory = ref<AgentCategory>('全部智能体');
  const keyword = ref('');
  const selectedAgentKey = ref(normalizeAgentKey(route.query.task || 'resource'));
  const favoriteKeys = ref(new Set<string>(['resource', 'practice', 'reader']));

  const categoryTabs: AgentCategory[] = ['全部智能体', '自学中心', '效率工具', '学习助手', '资料科研'];
  const categoryCopy: Record<AgentCategory, string> = {
    全部智能体: '覆盖资料、陪练、阅读、图谱和科研任务',
    自学中心: '面向预习、复习和课程理解',
    效率工具: '面向写作、公式和产物整理',
    学习助手: '面向答疑、陪练和作业反馈',
    资料科研: '面向资料检索、阅读和研究问题',
  };

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
        status: '高频',
        usage: '2,184',
        accuracy: 94,
        outputs: ['讲义', '练习', '思维导图', '阅读清单'],
        workflow: ['读取课程画像', '绑定章节与薄弱点', '生成资料包', '回到图谱验证'],
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
        status: '推荐',
        usage: '1,372',
        accuracy: 91,
        outputs: ['检索式', '研究问题', '阅读框架', '引用清单'],
        workflow: ['提炼课程主题', '生成检索策略', '拆分阅读任务', '形成资料证据'],
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
        status: '高频',
        usage: '3,016',
        accuracy: 93,
        outputs: ['梯度题', '提示', '错因', '追练'],
        workflow: ['定位薄弱点', '生成分层题', '等待作答', '给出追练路径'],
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
        status: '精选',
        usage: '1,948',
        accuracy: 92,
        outputs: ['摘要', '问题清单', '引用依据', '导图'],
        workflow: ['识别资料结构', '抽取关键段落', '生成阅读问题', '沉淀可追溯摘要'],
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
        status: '新',
        usage: '846',
        accuracy: 89,
        outputs: ['报告', '复盘', '讨论稿', '实验说明'],
        workflow: ['确定写作目标', '读取课程证据', '生成结构草稿', '输出可下载文档'],
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
        status: '高频',
        usage: '2,637',
        accuracy: 95,
        outputs: ['知识图谱', '问题图谱', '能力路径', '资料关系'],
        workflow: ['汇总章节节点', '映射资源与任务', '高亮薄弱路径', '启动图谱伴学'],
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
        status: '多模态',
        usage: '713',
        accuracy: 87,
        outputs: ['讲解结构', '关键帧', '复习点', '疑问清单'],
        workflow: ['接收视频线索', '提炼讲解层级', '标记关键节点', '生成复习动作'],
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
        status: '工具',
        usage: '1,106',
        accuracy: 90,
        outputs: ['LaTeX', '符号解释', '推导步骤', '适用条件'],
        workflow: ['识别公式结构', '标准化排版', '解释符号含义', '关联题目场景'],
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
        status: '评价',
        usage: '1,562',
        accuracy: 92,
        outputs: ['评分点', '错因', '订正步骤', '掌握度'],
        workflow: ['读取题目与答案', '匹配评分点', '定位错因', '生成订正计划'],
        task: taskByKey.get('grade'),
      },
      {
        key: 'planner',
        title: '学习规划师',
        category: '自学中心' as AgentCategory,
        desc: '把课程进度、图谱薄弱点和近期任务合成可执行的每日学习计划。',
        icon: IconStar,
        source: '规划类',
        launch: 'chat' as AgentLaunchMode,
        estimate: '3 分钟',
        status: '推荐',
        usage: '2,041',
        accuracy: 93,
        outputs: ['学习日程', '优先级', '检查点', '复盘提示'],
        workflow: ['读取当前进度', '排序薄弱节点', '安排每日任务', '设置复盘检查'],
        task: taskByKey.get('project'),
      },
      {
        key: 'checker',
        title: '作业查重',
        category: '效率工具' as AgentCategory,
        desc: '对照课程资料、作业要求和参考结构，生成相似片段与改写建议。',
        icon: IconSearch,
        source: '审查类',
        launch: 'chat' as AgentLaunchMode,
        estimate: '6 分钟',
        status: '审查',
        usage: '624',
        accuracy: 88,
        outputs: ['相似片段', '风险等级', '改写建议', '引用提醒'],
        workflow: ['读取作业文本', '比对课程资料', '标记相似风险', '给出改写路径'],
        task: taskByKey.get('grade'),
      },
      {
        key: 'translator',
        title: '术语翻译',
        category: '效率工具' as AgentCategory,
        desc: '围绕课程术语提供中英互译、定义解释和上下文用法，避免直译误差。',
        icon: IconBook,
        source: '语言工具',
        launch: 'chat' as AgentLaunchMode,
        estimate: '2 分钟',
        status: '工具',
        usage: '932',
        accuracy: 91,
        outputs: ['术语表', '双语解释', '例句', '易混提醒'],
        workflow: ['提取术语', '匹配课程语境', '给出双语解释', '补充例句与误区'],
        task: taskByKey.get('explain'),
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
  const incomingPrompt = computed(() => routeQueryText(route.query.prompt));
  const incomingSource = computed(() => routeQueryText(route.query.source));
  const incomingResourceId = computed(() => routeQueryText(route.query.resourceId));
  const incomingResource = computed(() =>
    course.value && incomingResourceId.value
      ? resolveCourseResourceReference(course.value.id, incomingResourceId.value)
      : null
  );

  const activeChapter = computed(() => {
    if (!course.value) return null;
    const pendingChapter = course.value.chapters.find((chapter) =>
      chapter.lessons.some((lesson) => lesson.status === 'pending')
    );
    return pendingChapter || course.value.chapters[course.value.chapters.length - 1] || null;
  });

  const activeConcepts = computed(() => course.value?.concepts.slice(0, 3) || []);

  const favoriteAgents = computed(() =>
    agentCatalog.value.filter((agent) => favoriteKeys.value.has(agent.key))
  );

  const highlightedAgents = computed(() => agentCatalog.value.filter((agent) => agent.status === '高频').slice(0, 3));

  const categoryStats = computed(() =>
    categoryTabs.map((category) => ({
      category,
      count:
        category === '全部智能体'
          ? agentCatalog.value.length
          : agentCatalog.value.filter((agent) => agent.category === category).length,
      desc: categoryCopy[category],
    }))
  );

  const hubStats = computed(() => [
    { label: '可用智能体', value: `${agentCatalog.value.length}` },
    { label: '课程进度', value: `${course.value?.progress || 0}%` },
    { label: '已收藏', value: `${favoriteAgents.value.length}` },
  ]);

  const launchLabel = computed(() => {
    if (incomingResource.value && selectedAgent.value?.launch === 'chat') return '带着这份资料提问';
    if (selectedAgent.value?.launch === 'resource') return '生成学习资料';
    if (selectedAgent.value?.launch === 'graph') return '进入课程图谱';
    return '开始对话执行';
  });

  const launchTarget = computed(() => {
    if (selectedAgent.value?.launch === 'resource') return '资料生成器';
    if (selectedAgent.value?.launch === 'graph') return '课程知识图谱';
    return selectedAgent.value?.task?.forceAgent || 'tutor_agent';
  });

  const inputContextCards = computed(() => {
    if (!course.value || !selectedAgent.value) return [];
    const concepts = activeConcepts.value.map((concept) => concept.title).join('、') || '课程核心概念';
    return [
      {
        label: '课程画像',
        value: course.value.shortTitle,
        detail: `${course.value.progress}% 进度 · ${course.value.learned}/${course.value.total} 节已学`,
      },
      {
        label: '当前章节',
        value: activeChapter.value?.title || '课程总览',
        detail: '优先结合未完成章节与近期学习任务',
      },
      {
        label: '知识焦点',
        value: concepts,
        detail: `会限制在 ${selectedAgent.value.title} 的能力边界内执行`,
      },
      ...(incomingResource.value
        ? [
            {
              label: '当前引用资料',
              value: incomingResource.value.title,
              detail: `${incomingResource.value.chapter} · ${incomingResource.value.type} · ${incomingResource.value.file_id}`,
            },
          ]
        : []),
      ...(incomingPrompt.value
        ? [
            {
              label: incomingSource.value === 'resource' ? '资料指令' : '外部任务',
              value: incomingResource.value?.title || incomingResourceId.value || incomingSource.value || '来自课程入口',
              detail: incomingPrompt.value,
            },
          ]
        : []),
    ];
  });

  const deliverablePreview = computed(() =>
    (selectedAgent.value?.outputs || []).map((output, index) => ({
      title: output,
      detail: `${index + 1}. 结合课程证据生成，可继续复制、下载或进入下一步任务。`,
    }))
  );

  const preflightChecks = computed(() => [
    {
      label: '课程数据',
      detail: course.value ? `${course.value.chapters.length} 个章节已接入` : '等待课程数据',
      ready: Boolean(course.value),
    },
    {
      label: '执行入口',
      detail: `将启动到 ${launchTarget.value}`,
      ready: Boolean(selectedAgent.value),
    },
    {
      label: '上下文约束',
      detail: incomingPrompt.value || selectedAgent.value?.task?.prompt || '使用智能体默认任务说明',
      ready: Boolean(selectedAgent.value?.task),
    },
    {
      label: '资料引用',
      detail: incomingResource.value
        ? `已带入《${incomingResource.value.title}》的章节、类型和知识点线索`
        : '未从资料卡进入，将使用课程整体上下文',
      ready: Boolean(incomingResource.value || course.value),
    },
    {
      label: '依据要求',
      detail: incomingResource.value
        ? '回答需说明依据；证据不足时必须明确标注'
        : '回答需限定在当前课程范围内',
      ready: true,
    },
  ]);

  function routeQueryText(value: unknown) {
    if (Array.isArray(value)) return String(value[0] || '');
    return typeof value === 'string' ? value : '';
  }

  function normalizeAgentKey(value: unknown) {
    const key = routeQueryText(value) || 'resource';
    return key === 'map' ? 'graph' : key;
  }

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
    const reference = incomingResource.value;
    return [
      `当前课程：${course.value.title}`,
      `课程简介：${course.value.description}`,
      `学习进度：${course.value.progress}%（${course.value.learned}/${course.value.total} 节）`,
      `当前智能体：${agent.title}`,
      `智能体能力：${agent.desc}`,
      incomingPrompt.value ? `入口传入任务：${incomingPrompt.value}` : '',
      reference
        ? [
            `当前引用资料：${reference.title}`,
            `资料ID：${reference.resourceId}`,
            `资料文件标识：${reference.file_id}`,
            `资料章节：${reference.chapter}`,
            `资料类型：${reference.type}`,
            `可用证据线索：${reference.evidence.join('；')}`,
            '回答开头请确认将围绕这份资料回答；结尾必须列出“依据”和“证据不足之处”。',
          ].join('\n')
        : incomingResourceId.value
          ? `关联资料ID：${incomingResourceId.value}。当前只获得资料线索，证据不足时必须说明。`
          : '',
      taskPrompt,
      '请先确认我的学习状态，再给出可执行的下一步，并且只围绕当前课程内容展开。',
    ].filter(Boolean).join('\n');
  }

  function openKnowledgeCenter() {
    if (!course.value) return;
    router.push(courseWorkspaceLocation(course.value.id, 'knowledge'));
  }

  function openResourceGenerator(agent = selectedAgent.value) {
    if (!course.value || !agent) return;
    const normalizedDesc = agent.desc.replace(/[。.!！?？]+$/u, '');
    router.push({
      name: 'StudentCourseResourceGenerator',
      params: { courseId: course.value.id },
      query: {
        subject: course.value.title,
        topic: incomingResource.value?.title || incomingResourceId.value || agent.title,
        goal: `${normalizedDesc}。${incomingPrompt.value || '请结合当前课程章节、课堂笔记、知识图谱和学习进度生成可下载资料。'}`,
        source: 'course-agent',
        task: agent.key,
        ...(incomingResource.value
          ? {
              resourceId: incomingResource.value.resourceId,
              resourceTitle: incomingResource.value.title,
              resourceChapter: incomingResource.value.chapter,
              resourceType: incomingResource.value.type,
            }
          : {}),
      },
    });
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
        ...(incomingResource.value
          ? {
              resourceId: incomingResource.value.resourceId,
              resourceTitle: incomingResource.value.title,
              resourceChapter: incomingResource.value.chapter,
              resourceType: incomingResource.value.type,
            }
          : {}),
      },
    });
  }

  function copyAgent(agent = selectedAgent.value) {
    if (!agent) return;
    const brief = [
      `${agent.title}：${agent.desc}`,
      `启动入口：${launchTarget.value}`,
      `输入上下文：${inputContextCards.value.map((item) => `${item.label}-${item.value}`).join('；')}`,
      incomingPrompt.value ? `入口任务：${incomingPrompt.value}` : '',
      incomingResource.value
        ? `引用资料：${incomingResource.value.title}（${incomingResource.value.chapter} / ${incomingResource.value.type}）`
        : '',
      `预计交付：${agent.outputs.join('、')}`,
    ].filter(Boolean).join('\n');
    navigator.clipboard?.writeText(brief).catch(() => null);
    Message.success('已复制启动简报');
  }

  watch(
    () => route.query.task,
    (task) => {
      selectedAgentKey.value = normalizeAgentKey(task || 'resource');
    }
  );

  watch([activeCategory, keyword], () => {
    const agents = filteredAgents.value;
    if (agents.length && !agents.some((agent) => agent.key === selectedAgentKey.value)) {
      selectedAgentKey.value = agents[0].key;
    }
  });
</script>

<template>
  <section v-if="course" class="agent-hub">
    <div class="hub-shell">
      <header class="hub-top">
        <div class="hub-title">
          <span><icon-robot /> AI智能体</span>
          <h1>{{ course.shortTitle }}智能体中心</h1>
          <p>把资料、阅读、陪练、图谱和科研任务集中到可直接执行的课程 Agent 工作台。</p>
        </div>
        <label class="hub-search">
          <icon-search />
          <input v-model="keyword" type="search" placeholder="搜索智能体、资料或知识点" />
        </label>
      </header>

      <section class="hub-overview">
        <article v-for="item in hubStats" :key="item.label">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </article>
        <div class="spotlight-strip">
          <span>高频推荐</span>
          <button
            v-for="agent in highlightedAgents"
            :key="agent.key"
            type="button"
            @click="launchAgent(agent)"
          >
            <component :is="agent.icon" />
            {{ agent.title }}
          </button>
        </div>
      </section>

      <nav class="category-tabs" aria-label="AI智能体分类">
        <button
          v-for="item in categoryStats"
          :key="item.category"
          type="button"
          :class="{ active: activeCategory === item.category }"
          @click="activeCategory = item.category"
        >
          <span>{{ item.category }}</span>
          <small>{{ item.count }} 个 · {{ item.desc }}</small>
        </button>
      </nav>

      <div class="hub-layout">
        <main class="agent-market">
          <section v-if="favoriteAgents.length" class="quick-row">
            <div class="section-heading">
              <strong><icon-star /> 我的收藏</strong>
              <span>常用智能体可直接启动</span>
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

            <div v-if="filteredAgents.length" class="agent-grid">
              <article
                v-for="agent in filteredAgents"
                :key="agent.key"
                class="agent-card"
                :class="{ active: selectedAgent?.key === agent.key }"
              >
                <button type="button" class="agent-main" @click="selectAgent(agent.key)">
                  <span class="agent-icon"><component :is="agent.icon" /></span>
                  <span class="agent-copy">
                    <span class="agent-status">{{ agent.status }}</span>
                    <strong>{{ agent.title }}</strong>
                    <small>{{ agent.desc }}</small>
                  </span>
                </button>
                <div class="agent-meta">
                  <span>{{ agent.category }}</span>
                  <span>{{ agent.source }}</span>
                  <span>{{ agent.estimate }}</span>
                  <span>{{ agent.accuracy }}% 匹配</span>
                </div>
                <div class="output-list">
                  <em v-for="item in agent.outputs.slice(0, 4)" :key="`${agent.key}-${item}`">
                    {{ item }}
                  </em>
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
            <div v-else class="empty-agents">
              <icon-search />
              <strong>没有匹配的智能体</strong>
              <p>换一个关键词，或切回“全部智能体”查看课程可用能力。</p>
              <button type="button" @click="activeCategory = '全部智能体'; keyword = ''">查看全部智能体</button>
            </div>
          </section>
        </main>

        <aside class="agent-panel">
          <section class="selected-agent">
            <div class="panel-kicker">Selected Agent</div>
            <div class="selected-head">
              <span class="agent-icon agent-icon--large">
                <component :is="selectedAgent?.icon" />
              </span>
              <div>
                <h2>{{ selectedAgent?.title }}</h2>
                <p>{{ selectedAgent?.desc }}</p>
              </div>
            </div>
            <div class="confidence-row">
              <span>课程匹配度</span>
              <strong>{{ selectedAgent?.accuracy }}%</strong>
              <i :style="{ width: `${selectedAgent?.accuracy || 0}%` }"></i>
            </div>
            <div class="app-runtime">
              <div>
                <span>启动入口</span>
                <strong>{{ launchTarget }}</strong>
              </div>
              <div>
                <span>预计耗时</span>
                <strong>{{ selectedAgent?.estimate }}</strong>
              </div>
              <div>
                <span>本周调用</span>
                <strong>{{ selectedAgent?.usage }}</strong>
              </div>
            </div>
            <div class="selected-actions">
              <button type="button" class="primary" @click="launchAgent()">
                <icon-robot /> {{ launchLabel }}
              </button>
              <button type="button" @click="openResourceGenerator()">
                <icon-storage /> 生成资料
              </button>
              <button type="button" @click="openKnowledgeCenter">
                <icon-mind-mapping /> 课程图谱
              </button>
            </div>
          </section>

          <section class="context-package">
            <div class="panel-heading">
              <strong>输入上下文</strong>
              <span>启动时带入</span>
            </div>
            <div class="context-stack">
              <article v-for="item in inputContextCards" :key="item.label">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <p>{{ item.detail }}</p>
              </article>
            </div>
          </section>

          <section v-if="incomingResource" class="reference-package">
            <div class="panel-heading">
              <strong>当前引用资料</strong>
              <span>课程内置线索</span>
            </div>
            <div class="reference-card">
              <span class="reference-type">{{ incomingResource.type }}</span>
              <h3>{{ incomingResource.title }}</h3>
              <p>{{ incomingResource.chapter }} · {{ incomingResource.sizeLabel }} · {{ incomingResource.downloads }} 次使用</p>
              <div class="reference-id">
                <span>文件标识</span>
                <strong>{{ incomingResource.file_id }}</strong>
              </div>
              <div class="reference-evidence">
                <span v-for="item in incomingResource.evidence" :key="item">
                  {{ item }}
                </span>
              </div>
            </div>
            <div class="reference-prompts">
              <button
                v-for="prompt in incomingResource.prompts"
                :key="prompt"
                type="button"
                @click="router.replace({ query: { ...route.query, prompt } })"
              >
                {{ prompt }}
              </button>
            </div>
          </section>

          <section class="deliverable-preview">
            <div class="panel-heading">
              <strong>交付物预览</strong>
              <span>{{ deliverablePreview.length }} 项</span>
            </div>
            <div class="deliverable-grid">
              <article v-for="item in deliverablePreview" :key="item.title">
                <strong>{{ item.title }}</strong>
                <p>{{ item.detail }}</p>
              </article>
            </div>
          </section>

          <section class="preflight-checks">
            <div class="panel-heading">
              <strong>启动前检查</strong>
              <span>已就绪</span>
            </div>
            <ul>
              <li v-for="item in preflightChecks" :key="item.label" :class="{ ready: item.ready }">
                <span>{{ item.ready ? '通过' : '待补' }}</span>
                <div>
                  <strong>{{ item.label }}</strong>
                  <p>{{ item.detail }}</p>
                </div>
              </li>
            </ul>
          </section>

          <section class="agent-flow">
            <strong>执行流</strong>
            <ol>
              <li v-for="(step, index) in selectedAgent?.workflow || []" :key="step">
                <span>{{ index + 1 }}</span>
                <p>{{ step }}</p>
              </li>
            </ol>
          </section>

          <section class="course-context">
            <strong>课程上下文</strong>
            <p>{{ course.description }}</p>
            <div class="context-tags">
              <span v-for="concept in course.concepts" :key="concept.title">
                {{ concept.title }}
              </span>
            </div>
            <button type="button" @click="copyAgent()">复制智能体说明</button>
          </section>
        </aside>
      </div>
    </div>
  </section>
</template>

<style scoped lang="less">
  .agent-hub {
    min-height: calc(100vh - 150px);
    color: #172033;
  }

  .hub-shell {
    padding: 24px;
    border: 1px solid #e7edf7;
    border-radius: 30px;
    background:
      radial-gradient(circle at 6% 0%, rgba(65, 125, 246, 0.13), transparent 32%),
      radial-gradient(circle at 94% 0%, rgba(95, 205, 184, 0.12), transparent 30%),
      linear-gradient(180deg, #fbfdff, #f4f8fc);
    box-shadow: 0 24px 62px rgba(31, 45, 83, 0.08);
  }

  .hub-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 2px 2px 18px;
  }

  .hub-title {
    span {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 10px 18px;
      border: 4px solid rgba(255, 255, 255, 0.88);
      border-radius: 999px;
      color: #fff;
      background: linear-gradient(135deg, #3677f7, #4f63ef);
      font-size: 17px;
      font-weight: 800;
      box-shadow: 0 12px 24px rgba(56, 104, 235, 0.22);
    }

    h1 {
      margin: 14px 0 5px;
      color: #121c31;
      font-size: 30px;
      font-weight: 900;
      letter-spacing: 0;
    }

    p {
      margin: 0;
      color: #6b768a;
      font-size: 14px;
    }
  }

  .hub-search {
    width: min(390px, 38vw);
    height: 46px;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 17px;
    border: 1px solid #e5ebf5;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.92);
    color: #8b96aa;
    box-shadow: 0 10px 28px rgba(37, 51, 91, 0.07);

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

  .hub-overview {
    display: grid;
    grid-template-columns: repeat(3, 118px) minmax(0, 1fr);
    gap: 12px;
    margin-bottom: 16px;

    article,
    .spotlight-strip {
      min-width: 0;
      border: 1px solid #e7edf6;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.86);
      box-shadow: 0 10px 24px rgba(35, 48, 82, 0.05);
    }

    article {
      padding: 13px 15px;

      span,
      strong {
        display: block;
      }

      span {
        color: #7b8799;
        font-size: 12px;
      }

      strong {
        margin-top: 6px;
        color: #172033;
        font-size: 22px;
      }
    }
  }

  .spotlight-strip {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 9px;
    padding: 12px;

    > span {
      color: #647086;
      font-size: 12px;
      font-weight: 800;
    }

    button {
      height: 34px;
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 0 12px;
      border: 1px solid #dce6f5;
      border-radius: 999px;
      color: #315181;
      background: #f8fbff;
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;

      &:hover {
        border-color: #bfd3ff;
        color: #2f68df;
        background: #eef5ff;
      }
    }
  }

  .category-tabs {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0;
    padding: 0;
    border: 1px solid #e8edf5;
    border-radius: 22px 22px 0 0;
    background: rgba(255, 255, 255, 0.94);
    overflow: hidden;

    button {
      position: relative;
      min-width: 0;
      min-height: 72px;
      display: inline-flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 5px;
      padding: 0 12px;
      border: 0;
      border-right: 1px solid #eef2f8;
      color: #596275;
      background: transparent;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;

      &:last-child {
        border-right: 0;
      }

      &::after {
        content: '';
        position: absolute;
        left: 50%;
        bottom: 0;
        width: 34px;
        height: 4px;
        transform: translateX(-50%);
        border-radius: 999px 999px 0 0;
        background: transparent;
      }

      &.active {
        color: #111827;
        background: #fff;

        &::after {
          background: #3b82f6;
        }
      }

      small {
        max-width: 100%;
        overflow: hidden;
        color: #94a3b8;
        font-size: 11px;
        font-weight: 600;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }

  .hub-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 330px;
    gap: 18px;
    padding: 18px;
    border: 1px solid #e8edf5;
    border-top: 0;
    border-radius: 0 0 22px 22px;
    background: rgba(255, 255, 255, 0.96);
  }

  .agent-market {
    min-width: 0;
  }

  .quick-row,
  .agent-section,
  .agent-panel section {
    border: 1px solid #e7ecf4;
    border-radius: 18px;
    background: #fff;
    box-shadow: 0 12px 28px rgba(42, 56, 90, 0.055);
  }

  .quick-row {
    padding: 16px;
    margin-bottom: 16px;
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
      font-size: 16px;
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
      height: 38px;
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 0 13px;
      border: 1px solid #dce5f5;
      border-radius: 12px;
      color: #315181;
      background: #f8fbff;
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;
    }
  }

  .agent-section {
    padding: 16px;
  }

  .agent-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .empty-agents {
    min-height: 260px;
    display: grid;
    place-items: center;
    align-content: center;
    gap: 10px;
    padding: 32px;
    border: 1px dashed #cfd9ea;
    border-radius: 18px;
    color: #7a879b;
    background: #fbfdff;
    text-align: center;

    svg {
      color: #3b82f6;
      font-size: 28px;
    }

    strong {
      color: #172033;
      font-size: 17px;
    }

    p {
      margin: 0;
      font-size: 13px;
    }

    button {
      height: 34px;
      padding: 0 13px;
      border: 1px solid #bfd3ff;
      border-radius: 10px;
      color: #2f68df;
      background: #eef5ff;
      font-weight: 800;
      cursor: pointer;
    }
  }

  .agent-card {
    display: flex;
    flex-direction: column;
    gap: 13px;
    min-height: 238px;
    padding: 16px;
    border: 1px solid #e5ebf3;
    border-radius: 18px;
    background:
      linear-gradient(180deg, rgba(248, 251, 255, 0.96), #fff 42%),
      #fff;
    transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease, background 0.18s ease;

    &.active,
    &:hover {
      border-color: #bcd0ff;
      background:
        linear-gradient(180deg, rgba(239, 246, 255, 0.98), #fff 48%),
        #fff;
      box-shadow: 0 18px 38px rgba(39, 65, 121, 0.11);
      transform: translateY(-2px);
    }
  }

  .agent-main {
    display: grid;
    grid-template-columns: 60px minmax(0, 1fr);
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
    width: 60px;
    height: 60px;
    border: 1px solid #dfe7f3;
    border-radius: 16px;
    color: #3b82f6;
    background:
      linear-gradient(145deg, #f8fbff, #edf6ff);
    font-size: 26px;

    &--large {
      width: 66px;
      height: 66px;
      flex-shrink: 0;
    }
  }

  .agent-copy {
    .agent-status,
    strong,
    small {
      display: block;
    }

    .agent-status {
      width: fit-content;
      margin-bottom: 7px;
      padding: 3px 8px;
      border-radius: 999px;
      color: #2f68df;
      background: #edf4ff;
      font-size: 10px;
      font-weight: 900;
    }

    strong {
      margin: 0 0 8px;
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
  .agent-actions,
  .output-list {
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

  .output-list {
    em {
      padding: 5px 8px;
      border-radius: 9px;
      color: #25744d;
      background: #effaf4;
      font-size: 11px;
      font-style: normal;
      line-height: 1.3;
    }
  }

  .agent-actions {
    margin-top: auto;

    button {
      height: 34px;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 0 11px;
      border: 1px solid #dfe6f2;
      border-radius: 10px;
      color: #36506f;
      background: #fff;
      font-size: 12px;
      font-weight: 800;
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
  .course-context,
  .agent-flow,
  .context-package,
  .reference-package,
  .deliverable-preview,
  .preflight-checks {
    padding: 16px;
  }

  .panel-kicker {
    color: #2563eb;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
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

  .confidence-row {
    position: relative;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    margin-bottom: 14px;
    padding-bottom: 12px;
    color: #68758a;
    font-size: 12px;

    strong {
      color: #2563eb;
    }

    &::before,
    i {
      position: absolute;
      right: 0;
      bottom: 0;
      left: 0;
      height: 5px;
      border-radius: 999px;
      content: '';
    }

    &::before {
      background: #edf2f8;
    }

    i {
      right: auto;
      display: block;
      background: linear-gradient(90deg, #3677f7, #64c8a2);
    }
  }

  .app-runtime {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin-bottom: 14px;

    div {
      min-width: 0;
      padding: 10px;
      border: 1px solid #e6edf7;
      border-radius: 12px;
      background: #f8fbff;
    }

    span,
    strong {
      display: block;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: #7d899c;
      font-size: 11px;
    }

    strong {
      margin-top: 5px;
      color: #172033;
      font-size: 13px;
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
        background: #4468f2;
        box-shadow: 0 10px 20px rgba(68, 104, 242, 0.18);
      }
    }
  }

  .panel-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;

    strong {
      color: #172033;
      font-size: 15px;
    }

    span {
      flex-shrink: 0;
      padding: 3px 8px;
      border-radius: 999px;
      color: #2f68df;
      background: #eef4ff;
      font-size: 11px;
      font-weight: 800;
    }
  }

  .context-stack {
    display: grid;
    gap: 9px;

    article {
      min-width: 0;
      padding: 12px;
      border: 1px solid #e8eef7;
      border-radius: 13px;
      background:
        linear-gradient(135deg, rgba(239, 246, 255, 0.86), rgba(255, 255, 255, 0.94)),
        #fff;
    }

    span,
    strong,
    p {
      display: block;
      min-width: 0;
    }

    span {
      color: #6f7b8f;
      font-size: 11px;
      font-weight: 800;
    }

    strong {
      margin-top: 5px;
      overflow: hidden;
      color: #172033;
      font-size: 14px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    p {
      margin: 6px 0 0;
      color: #68758a;
      font-size: 12px;
      line-height: 1.55;
    }
  }

  .reference-package {
    border-color: #d6e4f8 !important;
    background:
      linear-gradient(135deg, rgba(237, 246, 255, 0.96), #fff 58%),
      #fff !important;
  }

  .reference-card {
    position: relative;
    padding: 14px;
    border: 1px solid #d9e7fb;
    border-radius: 16px;
    background: #fbfdff;

    h3 {
      margin: 9px 0 7px;
      color: #14223b;
      font-size: 16px;
      line-height: 1.35;
    }

    p {
      margin: 0;
      color: #65758d;
      font-size: 12px;
    }
  }

  .reference-type {
    display: inline-flex;
    align-items: center;
    height: 24px;
    padding: 0 9px;
    border-radius: 999px;
    color: #1d5fd7;
    background: #eaf2ff;
    font-size: 11px;
    font-weight: 900;
  }

  .reference-id {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 8px;
    align-items: center;
    margin-top: 12px;
    padding: 9px 10px;
    border-radius: 11px;
    background: #eef5ff;

    span {
      color: #55708f;
      font-size: 11px;
      font-weight: 800;
    }

    strong {
      min-width: 0;
      overflow: hidden;
      color: #1f3b6d;
      font-size: 11px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .reference-evidence {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin-top: 12px;

    span {
      max-width: 100%;
      padding: 5px 8px;
      overflow: hidden;
      border: 1px solid #dbe7f7;
      border-radius: 999px;
      color: #4a607c;
      background: #fff;
      font-size: 11px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .reference-prompts {
    display: grid;
    gap: 7px;
    margin-top: 10px;

    button {
      min-height: 34px;
      padding: 7px 10px;
      border: 1px solid #d7e5fa;
      border-radius: 11px;
      color: #24456f;
      background: #fff;
      font-size: 12px;
      line-height: 1.35;
      text-align: left;
      cursor: pointer;

      &:hover {
        border-color: #9ec0ff;
        color: #1d5fd7;
        background: #f5f9ff;
      }
    }
  }

  .deliverable-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 9px;

    article {
      min-width: 0;
      min-height: 104px;
      padding: 12px;
      border: 1px solid #e4efe9;
      border-radius: 13px;
      background: #f7fcf9;
    }

    strong {
      display: block;
      color: #206a49;
      font-size: 13px;
    }

    p {
      margin: 8px 0 0;
      color: #667789;
      font-size: 12px;
      line-height: 1.55;
    }
  }

  .preflight-checks {
    ul {
      display: grid;
      gap: 9px;
      margin: 0;
      padding: 0;
      list-style: none;
    }

    li {
      display: grid;
      grid-template-columns: 42px minmax(0, 1fr);
      gap: 10px;
      align-items: start;
      padding: 11px;
      border: 1px solid #edf0f5;
      border-radius: 13px;
      background: #fbfcff;
    }

    li > span {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      height: 24px;
      border-radius: 999px;
      color: #8a5a12;
      background: #fff7e8;
      font-size: 11px;
      font-weight: 900;
    }

    li.ready > span {
      color: #1f7a4d;
      background: #eaf8f0;
    }

    strong,
    p {
      display: block;
      min-width: 0;
    }

    strong {
      color: #172033;
      font-size: 13px;
    }

    p {
      margin: 5px 0 0;
      color: #68758a;
      font-size: 12px;
      line-height: 1.55;
    }
  }

  .agent-flow {
    strong {
      color: #172033;
      font-size: 15px;
    }

    ol {
      display: grid;
      gap: 10px;
      margin: 12px 0 0;
      padding: 0;
      list-style: none;
    }

    li {
      display: grid;
      grid-template-columns: 26px minmax(0, 1fr);
      gap: 9px;
      align-items: start;
    }

    li span {
      width: 24px;
      height: 24px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      color: #2f68df;
      background: #eef4ff;
      font-size: 11px;
      font-weight: 900;
    }

    p {
      margin: 2px 0 0;
      color: #68758a;
      font-size: 12px;
      line-height: 1.55;
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
    .hub-overview {
      grid-template-columns: repeat(3, minmax(0, 1fr));

      .spotlight-strip {
        grid-column: 1 / -1;
      }
    }

    .hub-layout {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 760px) {
    .hub-shell {
      padding: 14px;
      border-radius: 22px;
    }

    .hub-top,
    .category-tabs {
      align-items: stretch;
      flex-direction: column;
    }

    .hub-search {
      width: 100%;
    }

    .category-tabs {
      display: flex;
      gap: 6px;
      padding: 10px;
      border-radius: 18px 18px 0 0;

      button {
        min-height: 52px;
        border-right: 0;
      }
    }

    .hub-overview,
    .agent-grid {
      grid-template-columns: 1fr;
    }

    .hub-layout {
      padding: 12px;
    }
  }
</style>
