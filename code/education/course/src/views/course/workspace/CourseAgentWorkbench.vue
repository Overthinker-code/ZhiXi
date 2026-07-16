<script setup lang="ts">
  import { computed, nextTick, ref, watch, type Component } from 'vue';
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
  import {
    fetchCourseAgents,
    type CourseAgentContractSummary,
  } from '@/api/ai-chat';
  import AgentRealtimeChat from '@/components/float-ai/AgentRealtimeChat.vue';
  import {
    createCourseAgentWindowSession,
    type CourseAgentWindowSession,
  } from '@/components/float-ai/courseAgentWindowSession';
  import { getClassroomCourse } from '@/data/classroomCourses';
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';
  import { resolveCourseResourceReference } from '@/utils/courseResourceReference';

  type AgentCategory = '全部智能体' | '自学中心' | '效率工具' | '学习助手' | '资料科研';
  type CourseAgentView = CourseAgentContractSummary & {
    title: string;
    desc: string;
    category: Exclude<AgentCategory, '全部智能体'>;
    icon: Component;
    workflow: string[];
    status: string;
  };

  const categoryTabs: AgentCategory[] = ['全部智能体', '自学中心', '效率工具', '学习助手', '资料科研'];
  const categoryCopy: Record<AgentCategory, string> = {
    全部智能体: '覆盖资料、陪练、阅读、图谱和科研任务',
    自学中心: '面向预习、复习和课程理解',
    效率工具: '面向写作、公式和产物整理',
    学习助手: '面向答疑、陪练和作业反馈',
    资料科研: '面向资料检索、阅读和研究问题',
  };
  const agentPresentation: Record<string, { icon: Component; workflow: string[] }> = {
    resource: { icon: IconStorage, workflow: ['确认课程范围与学习目标', '规划资料结构', '生成并检查内容', '保存可下载产物'] },
    research: { icon: IconExperiment, workflow: ['界定研究问题', '组织课程与外部检索', '核验证据边界', '整理阅读清单'] },
    practice: { icon: IconBulb, workflow: ['定位练习范围', '逐题发起练习', '等待学生作答', '反馈并安排追练'] },
    reader: { icon: IconBook, workflow: ['确认阅读材料', '提取论证结构', '定位引用依据', '形成阅读路径'] },
    writer: { icon: IconEdit, workflow: ['确认写作目标', '组织课程证据', '生成结构化正文', '输出可编辑文档'] },
    graph: { icon: IconMindMapping, workflow: ['读取课程节点', '呈现知识关系', '定位前置路径', '从节点启动学习任务'] },
    video: { icon: IconVideoCamera, workflow: ['读取媒体线索', '整理讲解结构', '标记关键节点', '形成复习清单'] },
    formula: { icon: IconCode, workflow: ['识别公式结构', '转换标准 LaTeX', '解释符号与条件', '关联课程例题'] },
    grade: { icon: IconFile, workflow: ['读取题目与答案', '匹配评分点', '解释错因', '给出订正与追练'] },
    planner: { icon: IconStar, workflow: ['读取真实学习进度', '确认时间与目标', '安排任务优先级', '设置复盘检查点'] },
    checker: { icon: IconSearch, workflow: ['读取作业材料', '核对课程证据', '标记结构与引用问题', '给出可验证修改建议'] },
    translator: { icon: IconBook, workflow: ['识别课程术语', '匹配专业语境', '生成双语解释', '补充例句与易混提醒'] },
  };

  const route = useRoute();
  const router = useRouter();
  const course = computed(() => getClassroomCourse(String(route.params.courseId || '')));
  const activeCategory = ref<AgentCategory>('全部智能体');
  const keyword = ref('');
  const selectedAgentKey = ref('');
  const favoriteKeys = ref(new Set<string>(['resource', 'practice', 'reader']));
  const detailDrawerOpen = ref(false);
  const agentContracts = ref<CourseAgentContractSummary[]>([]);
  const agentCatalogLoading = ref(false);
  const agentCatalogError = ref('');
  const chatSession = ref<CourseAgentWindowSession | null>(null);
  const chatDialogRef = ref<HTMLElement | null>(null);
  const chatCloseButtonRef = ref<HTMLButtonElement | null>(null);
  let lastChatTrigger: HTMLElement | null = null;
  let catalogRequestId = 0;

  function executionLabel(kind: CourseAgentContractSummary['executionKind']) {
    if (kind === 'resource_workflow') return '资料工作流';
    if (kind === 'knowledge_graph') return '课程图谱';
    return '页内执行';
  }

  function normalizedCategory(value: string): CourseAgentView['category'] {
    return categoryTabs.includes(value as AgentCategory) && value !== '全部智能体'
      ? (value as CourseAgentView['category'])
      : '学习助手';
  }

  const agentCatalog = computed<CourseAgentView[]>(() =>
    agentContracts.value.map((contract) => {
      const presentation = agentPresentation[contract.key];
      return {
        ...contract,
        title: contract.label,
        desc: contract.description,
        category: normalizedCategory(contract.category),
        icon: presentation?.icon || IconRobot,
        workflow: presentation?.workflow || [
          '确认课程范围与任务目标',
          '执行专用能力',
          '核验输出边界',
          '交付并给出下一步',
        ],
        status: executionLabel(contract.executionKind),
      };
    })
  );

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
  const incomingTopic = computed(() => routeQueryText(route.query.topic));
  const incomingPackageId = computed(() => routeQueryText(route.query.packageId));
  const incomingUpstreamSource = computed(() => routeQueryText(route.query.upstreamSource));
  const incomingNodeId = computed(() => routeQueryText(route.query.nodeId));
  const incomingNodeLabel = computed(() => routeQueryText(route.query.nodeLabel) || incomingTopic.value);
  const incomingMapType = computed(() => routeQueryText(route.query.mapType));
  const incomingAudit = computed(() => routeQueryText(route.query.audit));
  const incomingResourceId = computed(() => routeQueryText(route.query.resourceId));
  const incomingResourceTitle = computed(() => routeQueryText(route.query.resourceTitle));
  const incomingResourceChapter = computed(() => routeQueryText(route.query.resourceChapter));
  const incomingResourceType = computed(() => routeQueryText(route.query.resourceType));
  const incomingFileId = computed(
    () =>
      routeQueryText(route.query.currentFileId) ||
      routeQueryText(route.query.fileId) ||
      routeQueryText(route.query.current_file_id)
  );
  const incomingFileName = computed(() => routeQueryText(route.query.fileName));
  const incomingArtifactKind = computed(() => routeQueryText(route.query.artifactKind));
  const incomingArtifactList = computed(() => routeQueryText(route.query.artifactList));
  const incomingArtifactPreview = computed(() => routeQueryText(route.query.artifactPreview));
  const incomingResource = computed(() =>
    course.value && incomingResourceId.value
      ? resolveCourseResourceReference(course.value.id, incomingResourceId.value)
      : null
  );
  const incomingNodeContext = computed(() => {
    if (!incomingNodeId.value && !incomingNodeLabel.value && !incomingMapType.value) return null;
    return {
      nodeId: incomingNodeId.value,
      nodeLabel: incomingNodeLabel.value || incomingTopic.value || '课程图谱节点',
      mapType: incomingMapType.value || 'knowledge',
      source: incomingSource.value || 'knowledge-map',
    };
  });
  const incomingResourceContext = computed(() => {
    if (incomingResource.value) {
      return {
        resourceId: incomingResource.value.resourceId,
        title: incomingResource.value.title,
        chapter: incomingResource.value.chapter,
        type: incomingResource.value.type,
        fileId: incomingResource.value.file_id,
        sizeLabel: incomingResource.value.sizeLabel,
        downloads: incomingResource.value.downloads,
        evidence: incomingResource.value.evidence,
        prompts: incomingResource.value.prompts,
        resolved: true,
      };
    }
    if (!incomingResourceId.value && !incomingResourceTitle.value && !incomingResourceChapter.value) return null;
    return {
      resourceId: incomingResourceId.value,
      title: incomingResourceTitle.value || incomingResourceId.value || '课程资料',
      chapter: incomingResourceChapter.value || '待匹配章节',
      type: incomingResourceType.value || '资料',
      fileId: incomingResourceId.value || 'query-resource',
      sizeLabel: '待解析',
      downloads: 0,
      evidence: [] as string[],
      prompts: [] as string[],
      resolved: false,
    };
  });
  const incomingPackageContext = computed(() => {
    const packageSources = new Set([
      'resource-generation',
      'knowledge-map-package-audit',
      'knowledge-map-audit',
      'course-agent-package-audit',
    ]);
    const source = incomingSource.value || 'course-agent';
    if (!incomingPackageId.value && !incomingAudit.value && !packageSources.has(source)) return null;
    return {
      topic: incomingTopic.value || incomingResourceContext.value?.title || incomingNodeContext.value?.nodeLabel || selectedAgent.value?.title || '课程资源包',
      packageId: incomingPackageId.value || 'local-package',
      source,
      sourceLabel: sourceLabel(source),
      upstreamSource: incomingUpstreamSource.value,
      nodeId: incomingNodeId.value,
      nodeLabel: incomingNodeLabel.value,
      mapType: incomingMapType.value,
      audit: incomingAudit.value,
    };
  });

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

  const highlightedAgents = computed(() => {
    const preferred = ['resource', 'practice', 'reader'];
    return preferred
      .map((key) => agentCatalog.value.find((agent) => agent.key === key))
      .filter((agent): agent is CourseAgentView => Boolean(agent));
  });

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

  const launchLabel = computed(() => {
    if (incomingPackageContext.value && selectedAgent.value?.executionKind === 'chat') return '带核验上下文执行';
    if (incomingResourceContext.value && selectedAgent.value?.executionKind === 'chat') return '带着这份资料提问';
    if (selectedAgent.value?.executionKind === 'resource_workflow') return '生成学习资料';
    if (selectedAgent.value?.executionKind === 'knowledge_graph') return '进入课程图谱';
    return '开始对话执行';
  });

  const launchTarget = computed(() => {
    if (selectedAgent.value?.executionKind === 'resource_workflow') return '资料生成器';
    if (selectedAgent.value?.executionKind === 'knowledge_graph') return '课程知识图谱';
    return '页内实时窗口';
  });

  function readableLaunchTarget(target = launchTarget.value) {
    const map: Record<string, string> = {
      资料生成器: '资料生成',
      课程知识图谱: '课程图谱',
      页内实时窗口: '页内实时执行',
    };
    return map[target] || target || '课程助手';
  }

  const displayLaunchTarget = computed(() => readableLaunchTarget());
  const processingLabel = computed(() => {
    if (selectedAgent.value?.executionKind === 'resource_workflow') return '可追踪生成';
    if (selectedAgent.value?.executionKind === 'knowledge_graph') return '交互探索';
    return '实时流式';
  });

  const inputContextCards = computed(() => {
    if (!course.value || !selectedAgent.value) return [];
    const concepts = activeConcepts.value.map((concept) => concept.title).join('、') || '课程核心概念';
    return [
      {
        label: '课程学习情况',
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
      ...(incomingNodeContext.value
        ? [
            {
              label: '图谱节点上下文',
              value: incomingNodeContext.value.nodeLabel,
              detail: `${incomingNodeContext.value.mapType} · ${incomingNodeContext.value.nodeId || '按标题定位'}`,
            },
          ]
        : []),
      ...(incomingResourceContext.value
        ? [
            {
              label: '当前引用资料',
              value: incomingResourceContext.value.title,
              detail: `${incomingResourceContext.value.chapter} · ${incomingResourceContext.value.type} · ${incomingResourceContext.value.fileId}`,
            },
          ]
        : []),
      ...(incomingPackageContext.value
        ? [
            {
              label: '关联学习资料',
              value: incomingPackageContext.value.topic,
              detail: `${incomingPackageContext.value.sourceLabel} · ${incomingPackageContext.value.packageId}`,
            },
            incomingPackageContext.value.audit
              ? {
                  label: '核验摘要',
                  value: incomingPackageContext.value.nodeId || '已绑定图谱节点',
                  detail: incomingPackageContext.value.audit,
                }
              : null,
          ].filter(Boolean) as Array<{ label: string; value: string; detail: string }>
        : []),
      ...(incomingPrompt.value
        ? [
            {
              label: incomingSource.value === 'resource' ? '资料指令' : '外部任务',
              value: incomingResourceContext.value?.title || incomingResourceId.value || incomingSource.value || '来自课程入口',
              detail: incomingPrompt.value,
            },
          ]
        : []),
    ];
  });

  const deliverablePreview = computed(() =>
    (selectedAgent.value?.outputs || []).map((output, index) => ({
      title: output,
      detail: `${index + 1}. 结合课程资料生成，可继续复制、下载或进入下一步任务。`,
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
      detail: `将启动到 ${displayLaunchTarget.value}`,
      ready: Boolean(selectedAgent.value),
    },
    {
      label: '上下文约束',
      detail: incomingPrompt.value || selectedAgent.value?.starterActions?.[0] || '使用智能体默认任务说明',
      ready: Boolean(selectedAgent.value),
    },
    {
      label: '知识点检查',
      detail: incomingPackageContext.value
        ? `已接入 ${incomingPackageContext.value.packageId}，主题 ${incomingPackageContext.value.topic}`
        : '未指定知识点，将根据课程整体内容执行',
      ready: Boolean(incomingPackageContext.value || course.value),
    },
    {
      label: '资料引用',
      detail: incomingResourceContext.value
        ? `已带入《${incomingResourceContext.value.title}》的章节、类型和知识点线索`
        : '未从资料卡进入，将使用课程整体上下文',
      ready: Boolean(incomingResourceContext.value || course.value),
    },
    {
      label: '依据要求',
      detail: incomingResourceContext.value
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

  function sourceLabel(source: string) {
    const map: Record<string, string> = {
      'resource-generation': '资源生成中心',
      'knowledge-map-package-audit': '图谱核验',
      'knowledge-map-audit': '图谱回炉',
      'knowledge-map': '课程图谱',
      'knowledge-path': '图谱路径',
      'course-agent': '课程助手',
      'course-agent-graph': '课程图谱',
      'course-agent-package-audit': '图谱核验',
      resource: '课程资料',
    };
    return map[source] || source || '课程入口';
  }

  function categoryDisplayName(category: AgentCategory) {
    return category === '全部智能体' ? '全部任务' : category;
  }

  function packageQueryPayload() {
    const context = incomingPackageContext.value;
    if (!context) return {};
    return {
      topic: context.topic,
      packageId: context.packageId,
      packageTopic: context.topic,
      packageSource: context.source,
      upstreamSource: context.upstreamSource || context.source,
      nodeId: context.nodeId,
      nodeLabel: context.nodeLabel,
      mapType: context.mapType,
      audit: context.audit,
    };
  }

  function compactQuery(payload: Record<string, string | number | undefined>) {
    return Object.fromEntries(
      Object.entries(payload).filter(([, value]) => value !== undefined && String(value).trim())
    ) as Record<string, string | number>;
  }

  function nodeQueryPayload() {
    const context = incomingNodeContext.value;
    if (!context) return {};
    return {
      nodeId: context.nodeId,
      nodeLabel: context.nodeLabel,
      mapType: context.mapType,
      topic: context.nodeLabel,
      upstreamSource: incomingUpstreamSource.value || context.source,
    };
  }

  function resourceQueryPayload() {
    const context = incomingResourceContext.value;
    if (!context) return {};
    return {
      resourceId: context.resourceId,
      resourceTitle: context.title,
      resourceChapter: context.chapter,
      resourceType: context.type,
      topic: incomingTopic.value || context.title,
      upstreamSource: incomingUpstreamSource.value || incomingSource.value || 'resource',
    };
  }

  function fileQueryPayload() {
    if (!incomingFileId.value && !incomingFileName.value && !incomingArtifactList.value) return {};
    return {
      currentFileId: incomingFileId.value,
      fileId: incomingFileId.value,
      fileName: incomingFileName.value,
      artifactKind: incomingArtifactKind.value,
      artifactList: incomingArtifactList.value,
      artifactPreview: incomingArtifactPreview.value,
    };
  }

  function contextQueryPayload(extra: Record<string, string | number | undefined> = {}) {
    return compactQuery({
      ...packageQueryPayload(),
      ...nodeQueryPayload(),
      ...resourceQueryPayload(),
      ...fileQueryPayload(),
      ...extra,
    });
  }

  function packagePromptLines() {
    const context = incomingPackageContext.value;
    if (!context) return [];
    return [
      `图谱核验主题：${context.topic}`,
      `资源包编号：${context.packageId}`,
      `资源包来源：${context.sourceLabel}`,
      context.upstreamSource ? `上游来源：${sourceLabel(context.upstreamSource)}` : '',
      context.nodeId ? `图谱节点ID：${context.nodeId}` : '',
      context.nodeLabel ? `图谱节点：${context.nodeLabel}` : '',
      context.mapType ? `图谱类型：${context.mapType}` : '',
      context.audit ? `核验摘要：${context.audit}` : '',
      '执行时必须优先保持资源包、图谱节点、课堂证据和后续产物的一致性；如果证据不足，需要明确指出缺口并给出回炉生成建议。',
    ].filter(Boolean);
  }

  function nodePromptLines() {
    const context = incomingNodeContext.value;
    if (!context) return [];
    return [
      `图谱节点：${context.nodeLabel}`,
      context.nodeId ? `节点ID：${context.nodeId}` : '',
      `图谱类型：${context.mapType}`,
      '回答和产物必须回指这个节点，并说明它与课程章节、资料和练习的关系。',
    ].filter(Boolean);
  }

  function syncSelectedAgent() {
    const requested = normalizeAgentKey(route.query.task || 'resource');
    const matched = agentCatalog.value.find((agent) => agent.key === requested);
    const fallback =
      agentCatalog.value.find((agent) => agent.key === 'resource') || agentCatalog.value[0];
    const nextKey = matched?.key || fallback?.key || '';
    if (chatSession.value && chatSession.value.agent.key !== nextKey) {
      closeAgentWindow(false);
    }
    selectedAgentKey.value = nextKey;
  }

  async function loadAgentCatalog(courseId: string) {
    const requestId = ++catalogRequestId;
    agentCatalogLoading.value = true;
    agentCatalogError.value = '';
    try {
      const response = await fetchCourseAgents(courseId);
      if (requestId !== catalogRequestId) return;
      agentContracts.value = Array.isArray(response.agents) ? response.agents : [];
      syncSelectedAgent();
    } catch (error) {
      if (requestId !== catalogRequestId) return;
      agentContracts.value = [];
      selectedAgentKey.value = '';
      agentCatalogError.value = '课程助手暂时无法加载，请稍后重试。';
      console.error('[course-agent] failed to load server catalog', error);
    } finally {
      if (requestId === catalogRequestId) agentCatalogLoading.value = false;
    }
  }

  function closeAgentWindow(restoreFocus = true) {
    if (!chatSession.value) return;
    chatSession.value = null;
    void nextTick(() => {
      if (restoreFocus) lastChatTrigger?.focus();
    });
  }

  function selectAgent(key: string) {
    if (!agentCatalog.value.some((agent) => agent.key === key)) return;
    if (chatSession.value && chatSession.value.agent.key !== key) {
      closeAgentWindow(false);
    }
    selectedAgentKey.value = key;
    router.replace({ query: { ...route.query, task: key, forceAgent: undefined } });
  }

  function toggleFavorite(key: string) {
    const next = new Set(favoriteKeys.value);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    favoriteKeys.value = next;
  }

  function buildAgentPrompt(agent = selectedAgent.value) {
    if (!course.value || !agent) return '';
    const taskPrompt = agent.starterActions[0] || agent.desc;
    const reference = incomingResourceContext.value;
    const packageLines = packagePromptLines();
    const nodeLines = nodePromptLines();
    return [
      `当前课程：${course.value.title}`,
      `课程简介：${course.value.description}`,
      `学习进度：${course.value.progress}%（${course.value.learned}/${course.value.total} 节）`,
      `当前智能体：${agent.title}`,
      `智能体能力：${agent.desc}`,
      incomingPrompt.value ? `入口传入任务：${incomingPrompt.value}` : '',
      ...packageLines,
      ...nodeLines,
      reference
        ? [
            `当前引用资料：${reference.title}`,
            `资料ID：${reference.resourceId}`,
            `资料文件标识：${reference.fileId}`,
            `资料章节：${reference.chapter}`,
            `资料类型：${reference.type}`,
            reference.evidence.length ? `可用证据线索：${reference.evidence.join('；')}` : '当前资料仅由入口参数提供，引用证据不足时必须主动说明。',
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
    router.push(
      courseWorkspaceLocation(
        course.value.id,
        'knowledge',
        contextQueryPayload({
          source:
            incomingPackageContext.value?.upstreamSource ||
            incomingNodeContext.value?.source ||
            incomingSource.value ||
            'course-agent',
          topic:
            incomingPackageContext.value?.topic ||
            incomingNodeContext.value?.nodeLabel ||
            incomingResourceContext.value?.title,
        })
      )
    );
  }

  function openResourceGenerator(agent = selectedAgent.value) {
    if (!course.value || !agent) return;
    const normalizedDesc = agent.desc.replace(/[。.!！?？]+$/u, '');
    const topic =
      incomingPackageContext.value?.topic ||
      incomingNodeContext.value?.nodeLabel ||
      incomingResourceContext.value?.title ||
      incomingResourceContext.value?.resourceId ||
      agent.title;
    router.push({
      name: 'StudentCourseResourceGenerator',
      params: { courseId: course.value.id },
      query: contextQueryPayload({
        subject: course.value.title,
        topic,
        goal: [
          normalizedDesc,
          incomingPrompt.value || '请结合当前课程章节、课堂笔记、知识图谱和学习进度生成可下载资料。',
          incomingNodeContext.value ? `图谱节点：${incomingNodeContext.value.nodeLabel}` : '',
          incomingResourceContext.value ? `引用资料：${incomingResourceContext.value.title}` : '',
          incomingPackageContext.value?.audit
            ? `图谱核验摘要：${incomingPackageContext.value.audit}`
            : '',
        ].filter(Boolean).join('。'),
        source: incomingPackageContext.value ? 'course-agent-package-audit' : 'course-agent',
        task: agent.key,
      }),
    });
  }

  function openAgentWindow(agent: CourseAgentView) {
    if (!course.value || agent.executionKind !== 'chat') return;
    lastChatTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    chatSession.value = createCourseAgentWindowSession({
      agent,
      courseId: course.value.id,
      courseTitle: course.value.title,
      chapterId: activeChapter.value?.id,
      chapterLabel: activeChapter.value?.title,
      knowledgePointIds: [],
      initialPrompt: buildAgentPrompt(agent),
    });
    void nextTick(() => chatCloseButtonRef.value?.focus());
  }

  function focusableDialogElements() {
    const dialog = chatDialogRef.value;
    if (!dialog) return [];
    return Array.from(
      dialog.querySelectorAll<HTMLElement>(
        'button:not([disabled]), textarea:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
      )
    ).filter((element) => element.offsetParent !== null);
  }

  function handleChatDialogKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.preventDefault();
      closeAgentWindow();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = focusableDialogElements();
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function launchAgent(agent = selectedAgent.value) {
    if (!course.value || !agent) return;
    selectAgent(agent.key);
    if (agent.executionKind === 'resource_workflow') {
      openResourceGenerator(agent);
      return;
    }
    if (agent.executionKind === 'knowledge_graph') {
      openKnowledgeCenter();
      return;
    }
    openAgentWindow(agent);
  }

  function copyAgent(agent = selectedAgent.value) {
    if (!agent) return;
    const brief = [
      `${agent.title}：${agent.desc}`,
      `启动入口：${displayLaunchTarget.value}`,
      `输入上下文：${inputContextCards.value.map((item) => `${item.label}-${item.value}`).join('；')}`,
      incomingPrompt.value ? `入口任务：${incomingPrompt.value}` : '',
      incomingPackageContext.value
        ? `图谱核验包：${incomingPackageContext.value.topic}（${incomingPackageContext.value.packageId} / ${incomingPackageContext.value.sourceLabel}）`
        : '',
      incomingNodeContext.value
        ? `图谱节点：${incomingNodeContext.value.nodeLabel}（${incomingNodeContext.value.mapType} / ${incomingNodeContext.value.nodeId || '按标题定位'}）`
        : '',
      incomingResourceContext.value
        ? `引用资料：${incomingResourceContext.value.title}（${incomingResourceContext.value.chapter} / ${incomingResourceContext.value.type}）`
        : '',
      `预计交付：${agent.outputs.join('、')}`,
    ].filter(Boolean).join('\n');
    navigator.clipboard?.writeText(brief).catch(() => null);
    Message.success('已复制启动简报');
  }

  watch(
    () => route.query.task,
    syncSelectedAgent
  );

  watch(
    () => course.value?.id || '',
    (courseId) => {
      closeAgentWindow(false);
      agentContracts.value = [];
      if (courseId) void loadAgentCatalog(courseId);
    },
    { immediate: true }
  );

  watch([activeCategory, keyword], () => {
    const agents = filteredAgents.value;
    if (agents.length && !agents.some((agent) => agent.key === selectedAgentKey.value)) {
      selectAgent(agents[0].key);
    }
  });
</script>

<template>
  <section v-if="course" class="agent-hub">
    <div class="hub-shell">
      <header class="hub-top">
        <div class="hub-title">
          <span><icon-robot /> AI 课程助手</span>
          <h1>{{ course.shortTitle }} · 任务助手</h1>
          <p>在一个入口完成资料生成、课程问答、陪练批改和知识点检查。</p>
        </div>
        <label class="hub-search">
          <icon-search />
          <input
            v-model="keyword"
            type="search"
            aria-label="搜索课程助手任务、资料或知识点"
            placeholder="搜索任务、资料或知识点"
          />
        </label>
      </header>

      <section class="hub-overview compact-overview">
        <article>
          <span>课程进度</span>
          <strong>{{ course.progress }}%</strong>
        </article>
        <article>
          <span>已学章节</span>
          <strong>{{ course.learned }}/{{ course.total }}</strong>
        </article>
        <div class="spotlight-strip">
          <span>推荐任务</span>
          <button
            v-for="agent in highlightedAgents"
            :key="agent.key"
            type="button"
            @click="selectAgent(agent.key)"
          >
            <component :is="agent.icon" />
            {{ agent.title }}
          </button>
        </div>
      </section>

      <nav class="category-tabs compact-tabs" aria-label="课程助手分类">
        <button
          v-for="item in categoryStats"
          :key="item.category"
          type="button"
          :class="{ active: activeCategory === item.category }"
          @click="activeCategory = item.category"
        >
          <span>{{ categoryDisplayName(item.category) }}</span>
          <small>{{ item.count }} 个 · {{ item.desc }}</small>
        </button>
      </nav>

      <div class="hub-layout task-layout">
        <aside class="agent-rail">
          <section v-if="favoriteAgents.length" class="quick-row">
            <div class="section-heading">
              <strong><icon-star /> 我的收藏</strong>
              <span>常用任务</span>
            </div>
            <div class="quick-list">
              <button
                v-for="agent in favoriteAgents"
                :key="agent.key"
                type="button"
                :class="{ active: selectedAgent?.key === agent.key }"
                @click="selectAgent(agent.key)"
              >
                <component :is="agent.icon" />
                <span>{{ agent.title }}</span>
              </button>
            </div>
          </section>

          <section class="agent-section">
            <div class="section-heading">
              <strong>{{ categoryDisplayName(activeCategory) }}</strong>
              <span>{{ filteredAgents.length }} 个任务</span>
            </div>

            <div v-if="agentCatalogLoading" class="empty-agents" role="status">
              <icon-robot />
              <strong>正在加载课程助手</strong>
              <p>正在读取当前课程可用的专用智能体。</p>
            </div>
            <div v-else-if="agentCatalogError" class="empty-agents" role="alert">
              <icon-robot />
              <strong>课程助手暂时不可用</strong>
              <p>{{ agentCatalogError }}</p>
              <button type="button" @click="course && loadAgentCatalog(course.id)">重新加载</button>
            </div>
            <div v-else-if="filteredAgents.length" class="agent-list">
              <button
                v-for="agent in filteredAgents"
                :key="agent.key"
                type="button"
                class="agent-list-item"
                :class="{ active: selectedAgent?.key === agent.key }"
                @click="selectAgent(agent.key)"
              >
                <span class="agent-icon"><component :is="agent.icon" /></span>
                <span class="agent-copy">
                  <span class="agent-status">{{ agent.status }}</span>
                  <strong>{{ agent.title }}</strong>
                  <small>{{ agent.desc }}</small>
                </span>
              </button>
            </div>
            <div v-else class="empty-agents">
              <icon-search />
              <strong>没有匹配的任务</strong>
              <p>换一个关键词，或切回“全部任务”查看课程可用能力。</p>
              <button type="button" @click="activeCategory = '全部智能体'; keyword = ''">查看全部任务</button>
            </div>
          </section>
        </aside>

        <main class="task-workspace">
          <section class="selected-agent task-hero">
            <div class="panel-kicker">当前任务</div>
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
              <span>当前课程</span>
              <strong>已结合课程内容</strong>
              <i style="width: 100%"></i>
            </div>
            <div class="task-summary">
              <article>
                <span>执行方式</span>
                <strong>{{ displayLaunchTarget }}</strong>
              </article>
              <article>
                <span>处理方式</span>
                <strong>{{ processingLabel }}</strong>
              </article>
              <article>
                <span>输出数量</span>
                <strong>{{ selectedAgent?.outputs.length || 0 }} 项</strong>
              </article>
            </div>
            <div class="output-list output-list--large">
              <em v-for="item in selectedAgent?.outputs || []" :key="`selected-${item}`">
                {{ item }}
              </em>
            </div>
            <div class="selected-actions">
              <button type="button" class="primary" :disabled="!selectedAgent" @click="launchAgent()">
                <icon-robot /> {{ launchLabel }}
              </button>
              <button type="button" @click="openResourceGenerator()">
                <icon-storage /> 生成资料
              </button>
              <button type="button" @click="openKnowledgeCenter">
                <icon-mind-mapping /> 课程图谱
              </button>
              <button type="button" @click="copyAgent()">
                复制任务简报
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
        </main>

        <aside class="agent-panel task-inspector">
          <section class="context-package">
            <div class="panel-heading">
              <strong>本次任务会参考</strong>
              <span>已选择</span>
            </div>
            <div class="context-stack">
              <article v-for="item in inputContextCards" :key="item.label">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <p>{{ item.detail }}</p>
              </article>
            </div>
          </section>

          <section v-if="incomingPackageContext" class="package-audit-package">
            <div class="panel-heading">
              <strong>资源关联检查</strong>
              <span>{{ incomingPackageContext.sourceLabel }}</span>
            </div>
            <div class="package-audit-card">
              <span>当前主题</span>
              <strong>{{ incomingPackageContext.topic }}</strong>
              <div class="package-audit-meta">
                <em v-if="incomingPackageContext.nodeId">已关联课程知识点</em>
                <em v-if="incomingPackageContext.upstreamSource">
                  来源 {{ sourceLabel(incomingPackageContext.upstreamSource) }}
                </em>
              </div>
            </div>
            <div v-if="incomingPackageContext.audit" class="package-audit-summary">
              {{ incomingPackageContext.audit }}
            </div>
            <div class="package-audit-actions">
              <button type="button" @click="launchAgent()">检查内容</button>
              <button type="button" @click="openResourceGenerator()">按问题生成资料</button>
              <button type="button" @click="openKnowledgeCenter">查看关联知识点</button>
            </div>
          </section>

          <section v-if="incomingResourceContext" class="reference-package">
            <div class="panel-heading">
              <strong>当前引用资料</strong>
              <span>{{ incomingResourceContext.resolved ? '课程资料' : '当前选择' }}</span>
            </div>
            <div class="reference-card">
              <span class="reference-type">{{ incomingResourceContext.type }}</span>
              <h3>{{ incomingResourceContext.title }}</h3>
              <p>{{ incomingResourceContext.chapter }} · {{ incomingResourceContext.sizeLabel }} · {{ incomingResourceContext.downloads }} 次使用</p>
              <div class="reference-id">
                <span>资料来源</span>
                <strong>{{ incomingResourceContext.resolved ? '课程资料' : '当前选择' }}</strong>
              </div>
              <div v-if="incomingResourceContext.evidence.length" class="reference-evidence">
                <span v-for="item in incomingResourceContext.evidence" :key="item">
                  {{ item }}
                </span>
              </div>
            </div>
            <div v-if="incomingResourceContext.prompts.length" class="reference-prompts">
              <button
                v-for="prompt in incomingResourceContext.prompts"
                :key="prompt"
                type="button"
                @click="router.replace({ query: { ...route.query, prompt } })"
              >
                {{ prompt }}
              </button>
            </div>
          </section>

          <section class="course-context compact-context">
            <strong>课程范围</strong>
            <p>{{ course.description }}</p>
            <div class="context-tags">
              <span v-for="concept in course.concepts.slice(0, 5)" :key="concept.title">
                {{ concept.title }}
              </span>
            </div>
            <button type="button" @click="detailDrawerOpen = true">查看任务详情</button>
          </section>
        </aside>
      </div>

      <div
        v-if="detailDrawerOpen"
        class="detail-drawer-mask"
        role="presentation"
        @click.self="detailDrawerOpen = false"
      >
        <aside class="detail-drawer" aria-label="课程助手任务详情">
          <header>
            <div>
              <span>任务详情</span>
              <strong>{{ selectedAgent?.title }}</strong>
            </div>
            <button type="button" @click="detailDrawerOpen = false">关闭</button>
          </header>
          <section class="preflight-checks">
            <div class="panel-heading">
              <strong>任务准备情况</strong>
              <span>已就绪</span>
            </div>
            <ul>
              <li v-for="item in preflightChecks" :key="item.label" :class="{ ready: item.ready }">
                <span>{{ item.ready ? '已准备' : '需要补充' }}</span>
                <div>
                  <strong>{{ item.label }}</strong>
                  <p>{{ item.detail }}</p>
                </div>
              </li>
            </ul>
          </section>
          <section class="agent-flow">
            <strong>任务步骤</strong>
            <ol>
              <li v-for="(step, index) in selectedAgent?.workflow || []" :key="step">
                <span>{{ index + 1 }}</span>
                <p>{{ step }}</p>
              </li>
            </ol>
          </section>
        </aside>
      </div>

      <teleport to="body">
        <div
          v-if="chatSession"
          class="agent-chat-dialog-mask"
          @click.self="closeAgentWindow()"
        >
          <section
            ref="chatDialogRef"
            class="agent-chat-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="agent-chat-dialog-title"
            @keydown="handleChatDialogKeydown"
          >
            <header>
              <div>
                <span>当前课程任务</span>
                <strong id="agent-chat-dialog-title">{{ chatSession.agent.label }}</strong>
              </div>
              <button
                ref="chatCloseButtonRef"
                type="button"
                aria-label="关闭课程智能体实时窗口"
                @click="closeAgentWindow()"
              >
                关闭
              </button>
            </header>
            <AgentRealtimeChat
              :key="chatSession.token"
              :session-token="chatSession.token"
              :agent="chatSession.agent"
              :course-id="chatSession.courseId"
              :course-title="chatSession.courseTitle"
              :chapter-id="chatSession.chapterId"
              :chapter-label="chatSession.chapterLabel"
              :knowledge-point-ids="chatSession.knowledgePointIds"
              :initial-prompt="chatSession.initialPrompt"
            />
          </section>
        </div>
      </teleport>

      <teleport to="body">
        <section class="mobile-agent-dock" aria-label="当前课程任务快捷启动">
          <span class="agent-icon">
            <component :is="selectedAgent?.icon" />
          </span>
          <div class="mobile-agent-dock__copy">
            <strong>{{ selectedAgent?.title }}</strong>
            <small>{{ displayLaunchTarget }} · 实时生成</small>
          </div>
          <button type="button" class="primary" @click="launchAgent()">
            <icon-play-arrow-fill /> 启动
          </button>
          <button type="button" @click="openResourceGenerator()">
            <icon-storage /> 资料
          </button>
        </section>
      </teleport>
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
    transition: border-color 160ms ease, box-shadow 160ms ease;

    &:focus-within {
      border-color: #94a3b8;
      box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.07), 0 10px 28px rgba(37, 51, 91, 0.07);
    }

    input {
      min-width: 0;
      width: 100%;
      border: 0;
      outline: 0 !important;
      box-shadow: none !important;
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

  .task-layout {
    grid-template-columns: 300px minmax(0, 1fr) 330px;
    align-items: start;
    border-top: 1px solid #e8edf5;
    border-radius: 22px;
  }

  .compact-overview {
    grid-template-columns: repeat(2, 124px) minmax(0, 1fr);
  }

  .compact-tabs {
    margin-bottom: 14px;
    border-radius: 18px;

    button {
      min-height: 54px;
      font-size: 14px;

      small {
        display: none;
      }
    }
  }

  .agent-market {
    min-width: 0;
  }

  .agent-rail,
  .task-workspace,
  .task-inspector {
    min-width: 0;
  }

  .agent-rail {
    display: grid;
    gap: 14px;
  }

  .task-workspace {
    display: grid;
    gap: 14px;
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

      &.active,
      &:hover {
        border-color: #bcd0ff;
        color: #2f68df;
        background: #eef5ff;
      }
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

  .agent-list {
    display: grid;
    gap: 8px;
    max-height: 590px;
    overflow: auto;
    padding-right: 2px;
  }

  .agent-list-item {
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr);
    gap: 10px;
    align-items: center;
    width: 100%;
    min-height: 74px;
    padding: 10px;
    border: 1px solid transparent;
    border-radius: 14px;
    background: #f8fbff;
    text-align: left;
    cursor: pointer;
    transition: border-color 0.16s ease, background 0.16s ease, box-shadow 0.16s ease;

    .agent-icon {
      width: 42px;
      height: 42px;
      border-radius: 13px;
      font-size: 20px;
    }

    .agent-status {
      margin-bottom: 3px;
      font-size: 10px;
    }

    strong {
      margin-bottom: 3px;
      font-size: 14px;
    }

    small {
      display: -webkit-box;
      overflow: hidden;
      font-size: 12px;
      line-height: 1.45;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }

    &.active,
    &:hover {
      border-color: #bdd0ff;
      background: #fff;
      box-shadow: 0 10px 26px rgba(39, 65, 121, 0.08);
    }
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
  .package-audit-package,
  .reference-package,
  .deliverable-preview,
  .preflight-checks {
    padding: 16px;
  }

  .task-hero {
    padding: 22px;
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

  .task-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 14px;

    article {
      min-width: 0;
      padding: 12px;
      border: 1px solid #e6edf7;
      border-radius: 14px;
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
      font-weight: 700;
    }

    strong {
      margin-top: 6px;
      color: #172033;
      font-size: 15px;
    }
  }

  .selected-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
        grid-column: 1 / -1;
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

  .output-list--large {
    margin: 14px 0 16px;

    em {
      color: #315181;
      background: #eef5ff;
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

  .package-audit-package {
    border-color: #dce6ff !important;
    background:
      linear-gradient(135deg, rgba(241, 246, 255, 0.98), rgba(255, 255, 255, 0.96) 58%),
      radial-gradient(circle at 100% 0, rgba(92, 111, 207, 0.12), transparent 32%) !important;
  }

  .package-audit-card {
    padding: 14px;
    border: 1px solid #d8e4fb;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.82);

    span,
    strong,
    p {
      display: block;
      min-width: 0;
    }

    span {
      color: #5878f5;
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.08em;
    }

    strong {
      margin-top: 6px;
      overflow: hidden;
      color: #172033;
      font-size: 13px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    p {
      margin: 8px 0 0;
      color: #2b3854;
      font-size: 16px;
      font-weight: 900;
      line-height: 1.35;
    }
  }

  .package-audit-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin-top: 11px;

    em {
      max-width: 100%;
      overflow: hidden;
      padding: 5px 8px;
      border-radius: 999px;
      color: #2f68df;
      background: #eef4ff;
      font-size: 10px;
      font-style: normal;
      font-weight: 800;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .package-audit-summary {
    display: -webkit-box;
    margin-top: 10px;
    padding: 11px 12px;
    overflow: hidden;
    border: 1px dashed #cad8f5;
    border-radius: 13px;
    color: #5f6e85;
    background: rgba(255, 255, 255, 0.72);
    font-size: 12px;
    line-height: 1.6;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 4;
  }

  .package-audit-actions {
    display: grid;
    gap: 8px;
    margin-top: 10px;

    button {
      min-height: 34px;
      border: 1px solid #d7e3fb;
      border-radius: 11px;
      color: #30425f;
      background: #fff;
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;

      &:hover {
        border-color: #bfd2ff;
        color: #2f68df;
        background: #f4f8ff;
      }

      &:first-child {
        border-color: transparent;
        color: #fff;
        background: #4f6df5;
        box-shadow: 0 9px 18px rgba(79, 109, 245, 0.18);
      }
    }
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

  .compact-context {
    p {
      display: -webkit-box;
      overflow: hidden;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 3;
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

  .mobile-agent-dock {
    display: none;
  }

  .agent-chat-dialog-mask {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: grid;
    place-items: center;
    padding: 24px;
    background: rgba(15, 23, 42, 0.36);
    backdrop-filter: blur(4px);
    animation: drawer-fade 0.18s ease both;
  }

  .agent-chat-dialog {
    width: min(620px, calc(100vw - 48px));
    height: min(780px, calc(100vh - 48px));
    min-height: min(520px, calc(100vh - 48px));
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    overflow: hidden;
    border: 1px solid #dbe5f3;
    border-radius: 22px;
    background: #fff;
    box-shadow: 0 30px 90px rgba(15, 23, 42, 0.24);
    animation: dialog-enter 0.2s ease both;

    > header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 16px;
      border-bottom: 1px solid #e6edf6;
      background: #fff;

      span,
      strong {
        display: block;
      }

      span {
        color: #7b8799;
        font-size: 11px;
      }

      strong {
        margin-top: 3px;
        color: #172033;
        font-size: 17px;
      }

      button {
        min-width: 58px;
        height: 34px;
        border: 1px solid #dce5f1;
        border-radius: 999px;
        color: #475569;
        background: #fff;
        cursor: pointer;

        &:focus-visible {
          outline: 3px solid rgba(47, 104, 223, 0.28);
          outline-offset: 2px;
        }
      }
    }
  }

  .detail-drawer-mask {
    position: fixed;
    inset: 0;
    z-index: 80;
    display: flex;
    justify-content: flex-end;
    background: rgba(15, 23, 42, 0.22);
    animation: drawer-fade 0.18s ease both;
  }

  .detail-drawer {
    width: min(440px, calc(100vw - 32px));
    height: 100%;
    padding: 18px;
    overflow: auto;
    background: #fff;
    box-shadow: -18px 0 48px rgba(15, 23, 42, 0.16);
    animation: drawer-enter 0.2s ease both;

    > header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;

      span,
      strong {
        display: block;
      }

      span {
        color: #667085;
        font-size: 12px;
        font-weight: 700;
      }

      strong {
        margin-top: 4px;
        color: #101828;
        font-size: 19px;
      }

      button {
        height: 34px;
        padding: 0 12px;
        border: 1px solid #dfe6f2;
        border-radius: 999px;
        color: #344054;
        background: #fff;
        cursor: pointer;
      }
    }

    .preflight-checks,
    .agent-flow {
      margin-bottom: 14px;
      border: 1px solid #e7ecf4;
      border-radius: 16px;
      background: #fff;
    }
  }

  @keyframes drawer-fade {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  @keyframes drawer-enter {
    from {
      transform: translateX(16px);
    }
    to {
      transform: translateX(0);
    }
  }

  @keyframes dialog-enter {
    from {
      opacity: 0;
      transform: translateY(10px) scale(0.985);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
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
      padding: 14px 14px 96px;
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
      display: flex;
      flex-direction: column;
      padding: 12px;
    }

    .agent-panel {
      display: flex;
      flex-direction: column;
      order: -1;
    }

    .reference-package {
      order: -3;
    }

    .selected-agent {
      order: -2;
    }

    .context-package {
      order: -1;
    }

    .mobile-agent-dock {
      position: fixed;
      z-index: 30;
      right: 12px;
      bottom: 12px;
      left: 12px;
      display: grid;
      grid-template-columns: 38px minmax(0, 1fr) auto auto;
      gap: 8px;
      align-items: center;
      padding: 10px;
      border: 1px solid rgba(210, 219, 242, 0.94);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.96);
      box-shadow: 0 18px 48px rgba(35, 48, 95, 0.18);
      backdrop-filter: blur(16px);
    }

    .mobile-agent-dock__copy {
      min-width: 0;

      strong,
      small {
        display: block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      strong {
        color: #1f2a44;
        font-size: 13px;
      }

      small {
        margin-top: 2px;
        color: #7d879a;
        font-size: 11px;
      }
    }

    .mobile-agent-dock button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      min-width: 54px;
      height: 40px;
      border: 1px solid #dfe6f5;
      border-radius: 12px;
      color: #334155;
      background: #fff;
      font-size: 12px;
      font-weight: 700;
    }

    .mobile-agent-dock button.primary {
      border-color: transparent;
      color: #fff;
      background: #5367f8;
    }
  }
</style>
