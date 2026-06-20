<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    IconBulb,
    IconDownload,
    IconFile,
    IconMindMapping,
    IconRobot,
    IconSearch,
    IconTags,
  } from '@arco-design/web-vue/es/icon';
  import { getClassroomCourse } from '@/data/classroomCourses';
  import {
    buildCourseKnowledgeMaps,
    buildCourseStructureBranches,
    type CourseKnowledgeMap,
    type CourseKnowledgeMapType,
    type CourseKnowledgeNode,
  } from '@/data/courseWorkspace';
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';

  const route = useRoute();
  const router = useRouter();
  const keyword = ref('');
  const activeType = ref<CourseKnowledgeMapType>('knowledge');
  const viewMode = ref<'network' | 'structure'>('network');
  const activeRelation = ref<'全部' | '父子关系' | '前后置关系' | '关联关系' | '资料支撑' | '任务驱动'>('全部');
  const selectedNodeId = ref('course-root');
  const showResourceLinks = ref(true);
  const showLearningPath = ref(true);
  const canvasZoom = ref(1.08);
  const canvasPan = ref({ x: 0, y: 0 });
  const isPanning = ref(false);
  const panStart = ref({ pointerX: 0, pointerY: 0, x: 0, y: 0 });

  const course = computed(() => getClassroomCourse(String(route.params.courseId || '')));
  const maps = computed(() => (course.value ? buildCourseKnowledgeMaps(course.value) : []));
  const structureBranches = computed(() =>
    course.value ? buildCourseStructureBranches(course.value) : []
  );
  const activeMap = computed<CourseKnowledgeMap | undefined>(
    () => maps.value.find((item) => item.type === activeType.value) || maps.value[0]
  );
  const relationTypes = computed(() => [
    '全部' as const,
    ...Array.from(new Set(activeMap.value?.links.map((link) => link.relation) || [])),
  ]);
  const visibleNodes = computed(() => {
    const map = activeMap.value;
    const key = keyword.value.trim().toLowerCase();
    if (!map) return [];
    return map.nodes.filter((node) => !key || node.label.toLowerCase().includes(key));
  });
  const visibleNodeIds = computed(() => new Set(visibleNodes.value.map((node) => node.id)));
  const visibleLinks = computed(() => {
    const map = activeMap.value;
    if (!map) return [];
    return map.links.filter((link) => {
      const relationMatches = activeRelation.value === '全部' || link.relation === activeRelation.value;
      const resourceMatches = showResourceLinks.value || link.relation !== '资料支撑';
      const pathMatches = showLearningPath.value || link.relation !== '前后置关系';
      return relationMatches && resourceMatches && pathMatches && visibleNodeIds.value.has(link.source) && visibleNodeIds.value.has(link.target);
    });
  });
  const selectedNode = computed(() => {
    const map = activeMap.value;
    if (!map) return undefined;
    return map.nodes.find((node) => node.id === selectedNodeId.value) || map.nodes[0];
  });
  const selectedLinks = computed(() =>
    visibleLinks.value.filter(
      (link) => link.source === selectedNode.value?.id || link.target === selectedNode.value?.id
    )
  );
  const selectedNeighborIds = computed(
    () =>
      new Set(
        selectedLinks.value.flatMap((link) => [link.source, link.target])
      )
  );
  const selectedNeighbors = computed(() => {
    const map = activeMap.value;
    const node = selectedNode.value;
    if (!map || !node) return [];
    return selectedLinks.value
      .map((link) => {
        const neighborId = link.source === node.id ? link.target : link.source;
        const neighbor = map.nodes.find((item) => item.id === neighborId);
        return neighbor ? { link, neighbor } : null;
      })
      .filter(Boolean) as Array<{
        link: CourseKnowledgeMap['links'][number];
        neighbor: CourseKnowledgeNode;
      }>;
  });
  const selectedNodeMastery = computed(() => selectedNode.value?.mastery ?? course.value?.progress ?? 0);
  const selectedNodeEvidence = computed(() => selectedNode.value?.evidence?.slice(0, 5) || []);
  const selectedNodeChecks = computed(() => selectedNode.value?.checks?.slice(0, 4) || []);
  const selectedNodeActivities = computed(() => selectedNode.value?.activities?.slice(0, 4) || []);
  const selectedNodeOutcomes = computed(() => selectedNode.value?.outcomes?.slice(0, 3) || []);
  const selectedNodeMisconceptions = computed(() => selectedNode.value?.misconceptions?.slice(0, 3) || []);
  const selectedNodeResources = computed(() => selectedNode.value?.resources?.slice(0, 4) || []);
  const canvasTransform = computed(
    () => `translate(${canvasPan.value.x}px, ${canvasPan.value.y}px) scale(${canvasZoom.value})`
  );
  const graphStats = computed(() => [
    { label: '节点', value: String(visibleNodes.value.length) },
    { label: '关系', value: String(visibleLinks.value.length) },
    { label: '掌握度', value: `${course.value?.progress || 0}%` },
  ]);
  const lowMasteryNodes = computed(() =>
    [...visibleNodes.value]
      .filter((node) => node.weight < 4)
      .sort((a, b) => (a.mastery ?? course.value?.progress ?? 0) - (b.mastery ?? course.value?.progress ?? 0))
      .slice(0, 4)
  );
  const relationSummary = computed(() =>
    relationTypes.value.map((relation) => ({
      relation,
      count:
        relation === '全部'
          ? visibleLinks.value.length
          : visibleLinks.value.filter((link) => link.relation === relation).length,
    }))
  );
  const selectedRelationTags = computed(() =>
    selectedLinks.value.slice(0, 3).map((link) => {
      const neighborId = link.source === selectedNode.value?.id ? link.target : link.source;
      const neighbor = activeMap.value?.nodes.find((item) => item.id === neighborId);
      return `${link.relation} · ${neighbor?.label || '相邻节点'}`;
    })
  );
  const guidedLearningPath = computed(() => {
    const node = selectedNode.value;
    if (!node) return [];
    const related = selectedNeighbors.value.slice(0, 3);
    return [
      {
        label: '定位',
        title: `确认「${node.label}」的定义与边界`,
        desc: node.detail || activeMap.value?.description || '从当前图谱节点开始定位学习目标。',
      },
      {
        label: '证据',
        title: selectedNodeEvidence.value[0] || '绑定课堂资料和任务证据',
        desc: selectedNodeResources.value.length
          ? `优先检查：${selectedNodeResources.value.join('、')}`
          : '把课堂笔记、资料和任务记录挂到当前节点。',
      },
      {
        label: '练习',
        title: node.recommendedAction || '生成针对性练习并回收错因',
        desc: related.length
          ? `建议串联 ${related.map((item) => item.neighbor.label).join('、')}。`
          : '完成自测后把错因回写到图谱。',
      },
    ];
  });
  const graphCommandDeck = computed(() => {
    const node = selectedNode.value;
    const nodeLabel = node?.label || activeMap.value?.title || course.value?.shortTitle || '当前节点';
    return [
      {
        key: 'notes',
        kicker: '课堂笔记',
        title: `定位「${nodeLabel}」笔记证据`,
        desc: selectedNodeEvidence.value[0] || '回到课堂笔记，补齐定义、条件和边界。',
        metric: `${selectedNodeEvidence.value.length || 1} 条证据`,
      },
      {
        key: 'resources',
        kicker: '资料资源',
        title: '生成节点配套资料',
        desc: selectedNodeResources.value[0] || '生成讲义、导图、练习和审查清单。',
        metric: `${selectedNodeResources.value.length || 4} 项资源`,
      },
      {
        key: 'checks',
        kicker: '检查题',
        title: '用题目验证掌握度',
        desc: selectedNodeChecks.value[0] || '按定义、条件、步骤、证据四类错因检查。',
        metric: `${selectedNodeChecks.value.length || 3} 道检查`,
      },
      {
        key: 'agent',
        kicker: 'AI 伴学',
        title: '让 AI 解释关系与路径',
        desc: selectedRelationTags.value[0] || '基于相邻节点生成下一步学习动作。',
        metric: `${selectedLinks.value.length} 条关系`,
      },
    ];
  });
  const nodeStudyPack = computed(() => {
    const node = selectedNode.value;
    const map = activeMap.value;
    if (!node || !map || !course.value) return null;
    const neighbors = selectedNeighbors.value.slice(0, 4).map((item) => ({
      relation: item.link.relation,
      label: item.neighbor.label,
      mastery: item.neighbor.mastery ?? course.value?.progress ?? 0,
      strength: item.link.strength || 72,
    }));
    return {
      title: `${course.value.shortTitle}-${node.label}节点学习包`,
      courseTitle: course.value.title,
      mapTitle: map.title,
      nodeLabel: node.label,
      nodeType: nodeTypeLabel(node.type),
      mastery: selectedNodeMastery.value,
      objective: node.recommendedAction || '沿图谱完成证据复盘、关系理解和针对性练习。',
      evidence: selectedNodeEvidence.value.length
        ? selectedNodeEvidence.value
        : [node.detail || map.description],
      resources: selectedNodeResources.value.length
        ? selectedNodeResources.value
        : [`${node.label} 课堂讲义`, `${node.label} 自测题`, `${node.label} 复习卡片`],
      checks: selectedNodeChecks.value.length
        ? selectedNodeChecks.value
        : [`能否解释 ${node.label} 的定义、条件和边界？`, `能否把 ${node.label} 应用到新题目？`],
      neighbors,
      prompts: [
        `请解释「${node.label}」与相邻节点的前后置关系，并给出学习顺序。`,
        `围绕「${node.label}」生成 5 道检查题，标注考查的证据和误区。`,
        `把「${node.label}」整理成一页课堂笔记，包含定义、边界、例题和错因。`,
      ],
    };
  });
  const selectedNodeHealth = computed(() => {
    const mastery = selectedNodeMastery.value;
    return [
      {
        label: '掌握状态',
        value: `${mastery}%`,
        desc: mastery >= 80 ? '可进入迁移任务' : mastery >= 60 ? '需要补一轮自测' : '建议先补概念证据',
        tone: mastery >= 80 ? 'green' : mastery >= 60 ? 'blue' : 'orange',
      },
      {
        label: '证据覆盖',
        value: `${selectedNodeEvidence.value.length}`,
        desc: selectedNodeEvidence.value.length >= 3 ? '证据链完整' : '需要补课堂片段',
        tone: selectedNodeEvidence.value.length >= 3 ? 'green' : 'orange',
      },
      {
        label: '资源闭环',
        value: `${selectedNodeResources.value.length}`,
        desc: selectedNodeResources.value.length >= 3 ? '已连接资料包' : '建议生成节点资料',
        tone: selectedNodeResources.value.length >= 3 ? 'blue' : 'orange',
      },
      {
        label: '关系强度',
        value: `${Math.round(
          selectedLinks.value.reduce((sum, item) => sum + (item.strength || 72), 0) /
            Math.max(selectedLinks.value.length, 1)
        )}%`,
        desc: selectedLinks.value.length ? '可沿相邻节点学习' : '需要建立前后置关系',
        tone: selectedLinks.value.length ? 'blue' : 'orange',
      },
    ];
  });
  const evidenceMatrix = computed(() => {
    const node = selectedNode.value;
    return [
      {
        key: 'notes',
        title: '课堂证据',
        items: selectedNodeEvidence.value.length
          ? selectedNodeEvidence.value
          : [node?.detail || activeMap.value?.description || '暂无课堂证据'],
      },
      {
        key: 'resources',
        title: '资源文件',
        items: selectedNodeResources.value.length
          ? selectedNodeResources.value
          : [`${node?.label || course.value?.shortTitle || '当前节点'} 专属讲义待生成`],
      },
      {
        key: 'checks',
        title: '验证问题',
        items: selectedNodeChecks.value.length
          ? selectedNodeChecks.value
          : ['生成一组概念边界、条件识别和迁移应用检查题。'],
      },
    ];
  });
  const nodeActionTimeline = computed(() => [
    {
      step: '01',
      title: '读证据',
      desc: selectedNodeEvidence.value[0] || '回到课堂笔记确认定义、条件和边界。',
      state: selectedNodeEvidence.value.length ? 'ready' : 'todo',
    },
    {
      step: '02',
      title: '看关系',
      desc: selectedRelationTags.value[0] || '沿前后置关系找到相邻知识点。',
      state: selectedLinks.value.length ? 'ready' : 'todo',
    },
    {
      step: '03',
      title: '做检查',
      desc: selectedNodeChecks.value[0] || '用检查题验证是否真正掌握。',
      state: selectedNodeMastery.value >= 70 ? 'ready' : 'warning',
    },
    {
      step: '04',
      title: '产资料',
      desc: selectedNode.value?.recommendedAction || '把节点沉淀为讲义、练习和复习单。',
      state: selectedNodeResources.value.length >= 3 ? 'ready' : 'warning',
    },
  ]);
  const focusTagChips = computed(() =>
    (activeMap.value?.focusTags || []).map((tag, index) => ({
      tag,
      count: index === 0 ? visibleNodes.value.length : Math.max(1, Math.round(visibleLinks.value.length / (index + 1))),
    }))
  );
  const chapterCount = computed(() => course.value?.chapters.length || 0);
  const conceptCount = computed(() => course.value?.concepts.flatMap((item) => item.points).length || 0);
  const actionBadgeCount = computed(() =>
    structureBranches.value.reduce((sum, item) => sum + item.resourceBadges.length, 0)
  );

  function nodeClass(node: CourseKnowledgeNode) {
    const selected = selectedNode.value;
    const shouldDim = Boolean(
      selected && selected.weight < 4 && node.id !== selected.id && !selectedNeighborIds.value.has(node.id)
    );
    return [
      `node-${node.type}`,
      `node-weight-${node.weight}`,
      {
        selected: selected?.id === node.id,
        related: selectedNeighborIds.value.has(node.id),
        dimmed: shouldDim,
        weak: (node.mastery ?? course.value?.progress ?? 0) < 60,
        stable: (node.mastery ?? course.value?.progress ?? 0) >= 80,
      },
    ];
  }

  function linkClass(link: CourseKnowledgeMap['links'][number]) {
    const selected = selectedNode.value;
    const selectedId = selected?.id;
    return [
      `link-${link.relation}`,
      {
        selected: selectedId === link.source || selectedId === link.target,
        dimmed: Boolean(
          selectedId && selected?.weight !== 4 && selectedId !== link.source && selectedId !== link.target
        ),
      },
    ];
  }

  function nodeTypeLabel(type?: CourseKnowledgeNode['type']) {
    if (type === 'chapter') return '章节';
    if (type === 'concept') return '知识点';
    if (type === 'resource') return '资料';
    if (type === 'task') return '任务';
    if (type === 'ability') return '能力';
    return '图谱';
  }

  function nodeSubtitle(node: CourseKnowledgeNode) {
    const mastery = node.mastery ?? course.value?.progress ?? 0;
    return `${nodeTypeLabel(node.type)} · ${mastery}%`;
  }

  function nodeBoxWidth(node: CourseKnowledgeNode) {
    if (node.weight >= 4) return 190;
    if (node.weight >= 3) return 154;
    if (node.type === 'resource' || node.type === 'task') return 140;
    return 128;
  }

  function nodeBoxHeight(node: CourseKnowledgeNode) {
    return node.weight >= 4 ? 70 : node.weight >= 3 ? 52 : 42;
  }

  function nodeFill(node: CourseKnowledgeNode) {
    if (node.weight >= 4) return 'url(#graphRootFill)';
    if (node.type === 'chapter') return '#f5f8ff';
    if (node.type === 'resource') return '#f1fbf6';
    if (node.type === 'task') return '#fff7ec';
    if (node.type === 'ability') return '#f7f2ff';
    return '#ffffff';
  }

  function nodeStroke(node: CourseKnowledgeNode) {
    if (node.weight >= 4) return '#5c6df5';
    if (node.type === 'chapter') return '#79a9e8';
    if (node.type === 'resource') return '#75caa2';
    if (node.type === 'task') return '#eba85a';
    if (node.type === 'ability') return '#9b83db';
    return '#d9e2f3';
  }

  function nodeTextColor(node: CourseKnowledgeNode) {
    return node.weight >= 4 ? '#ffffff' : '#26334d';
  }

  function linkPath(link: CourseKnowledgeMap['links'][number]) {
    const source = activeMap.value?.nodes.find((node) => node.id === link.source);
    const target = activeMap.value?.nodes.find((node) => node.id === link.target);
    if (!source || !target) return '';
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const pull = Math.max(50, Math.min(118, Math.abs(dx) * 0.22 + Math.abs(dy) * 0.14));
    const c1x = source.x + dx * 0.34;
    const c2x = target.x - dx * 0.34;
    const c1y = source.y + dy * 0.16 - pull * Math.sign(dx || 1) * 0.12;
    const c2y = target.y - dy * 0.16 + pull * Math.sign(dx || 1) * 0.12;
    return `M ${source.x} ${source.y} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${target.x} ${target.y}`;
  }

  function shortNodeLabel(label: string, limit = 9) {
    return label.length > limit ? `${label.slice(0, limit - 1)}…` : label;
  }

  function selectNode(node: CourseKnowledgeNode) {
    selectedNodeId.value = node.id;
  }

  function selectMap(type: CourseKnowledgeMapType) {
    activeType.value = type;
    activeRelation.value = '全部';
    canvasPan.value = { x: 0, y: 0 };
  }

  function selectBranch(index: number) {
    selectedNodeId.value = `chapter-${index}`;
    if (activeType.value !== 'knowledge' && activeType.value !== 'target') {
      activeType.value = 'knowledge';
    }
  }

  function changeZoom(delta: number) {
    canvasZoom.value = Math.min(1.58, Math.max(0.78, Number((canvasZoom.value + delta).toFixed(2))));
  }

  function resetCanvas() {
    canvasZoom.value = 1.08;
    canvasPan.value = { x: 0, y: 0 };
  }

  function beginCanvasPan(event: PointerEvent) {
    if ((event.target as Element | null)?.closest?.('.graph-node')) return;
    isPanning.value = true;
    panStart.value = {
      pointerX: event.clientX,
      pointerY: event.clientY,
      x: canvasPan.value.x,
      y: canvasPan.value.y,
    };
    (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
  }

  function moveCanvasPan(event: PointerEvent) {
    if (!isPanning.value) return;
    canvasPan.value = {
      x: panStart.value.x + event.clientX - panStart.value.pointerX,
      y: panStart.value.y + event.clientY - panStart.value.pointerY,
    };
  }

  function endCanvasPan(event: PointerEvent) {
    if (!isPanning.value) return;
    isPanning.value = false;
    (event.currentTarget as HTMLElement).releasePointerCapture?.(event.pointerId);
  }

  function askGraphAgent(action: string) {
    if (!course.value || !activeMap.value) return;
    const node = selectedNode.value;
    router.push(
      courseWorkspaceLocation(course.value.id, 'agent', {
        task: 'graph',
        forceAgent: 'graph_agent',
        prompt: [
          `当前课程：${course.value.title}`,
          `当前图谱：${activeMap.value.title}`,
          node ? `当前节点：${node.label}（${node.type}，掌握度 ${selectedNodeMastery.value}%）` : '',
          node?.detail ? `节点说明：${node.detail}` : '',
          selectedNodeEvidence.value.length ? `证据资料：${selectedNodeEvidence.value.join('；')}` : '',
          `操作目标：${action}`,
          '请基于当前课程章节、任务、能力目标、资料证据和薄弱点，输出可执行的学习路径，并说明每一步的依据。',
        ].filter(Boolean).join('\n'),
      })
    );
  }

  function goResourceGenerator() {
    if (!course.value || !activeMap.value) return;
    const node = selectedNode.value;
    router.push({
      name: 'StudentCourseResourceGenerator',
      params: { courseId: course.value.id },
      query: {
        subject: course.value.title,
        topic: node?.label || activeMap.value.title,
        goal: node
          ? `围绕${node.label}生成带证据清单、误区纠正、检查题和学习路径的个性化资料。`
          : `围绕${activeMap.value.title}生成课程图谱配套资料。`,
        source: 'knowledge-map',
      },
    });
  }

  function goCourseContent() {
    if (!course.value) return;
    router.push(courseWorkspaceLocation(course.value.id, 'content'));
  }

  function runGraphCommand(key: string) {
    if (key === 'notes') {
      goCourseContent();
      return;
    }
    if (key === 'resources') {
      goResourceGenerator();
      return;
    }
    if (key === 'checks') {
      askGraphAgent('基于当前节点生成一组分层检查题，并说明每道题对应的图谱关系');
      return;
    }
    askGraphAgent('解释当前节点、相邻节点和学习路径，并给出下一步可执行动作');
  }

  function safeFilename(value: string) {
    return value.replace(/[\\/:*?"<>|]/g, '-').replace(/\s+/g, '').slice(0, 80);
  }

  function nodeStudyPackMarkdown() {
    const pack = nodeStudyPack.value;
    if (!pack) return '';
    return [
      `# ${pack.title}`,
      '',
      `课程：${pack.courseTitle}`,
      `图谱：${pack.mapTitle}`,
      `节点：${pack.nodeLabel}`,
      `类型：${pack.nodeType}`,
      `掌握度：${pack.mastery}%`,
      '',
      '## 学习目标',
      `- ${pack.objective}`,
      '',
      '## 证据矩阵',
      ...pack.evidence.map((item, index) => `${index + 1}. ${item}`),
      '',
      '## 相邻关系',
      ...(pack.neighbors.length
        ? pack.neighbors.map(
            (item, index) =>
              `${index + 1}. ${item.relation}：${item.label}（掌握度 ${item.mastery}% / 关系强度 ${item.strength}%）`
          )
        : ['1. 暂无相邻节点，需要先补充图谱关系。']),
      '',
      '## 配套资源',
      ...pack.resources.map((item) => `- ${item}`),
      '',
      '## 检查题',
      ...pack.checks.map((item, index) => `${index + 1}. ${item}`),
      '',
      '## AI 追问提示',
      ...pack.prompts.map((item, index) => `${index + 1}. ${item}`),
      '',
      '## 完成标准',
      '- [ ] 已能复述节点定义、适用条件和边界。',
      '- [ ] 已用至少一条课堂证据支撑理解。',
      '- [ ] 已完成检查题并记录错因。',
      '- [ ] 已把错因或资料需求同步到 AI 伴学或资源生成中心。',
    ].join('\n');
  }

  function downloadNodeStudyPack() {
    const pack = nodeStudyPack.value;
    if (!pack) return;
    const blob = new Blob([`${nodeStudyPackMarkdown()}\n`], {
      type: 'text/markdown;charset=utf-8',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${safeFilename(pack.title)}.md`;
    link.click();
    URL.revokeObjectURL(url);
    Message.success('节点学习包已生成');
  }

  watch(activeMap, (map) => {
    if (!map) return;
    if (!map.nodes.some((node) => node.id === selectedNodeId.value)) {
      selectedNodeId.value = map.nodes[0]?.id || 'course-root';
    }
  });

  watch([visibleNodes, visibleLinks], ([nodes]) => {
    if (!nodes.length) return;
    if (!nodes.some((node) => node.id === selectedNodeId.value)) {
      selectedNodeId.value = nodes[0].id;
    }
  });
</script>

<template>
  <section v-if="course && activeMap" class="knowledge-page">
    <div class="graph-lab-shell">
      <header class="graph-topbar">
        <div class="graph-brand">
          <span class="graph-pill">
            <icon-mind-mapping /> AI 课程图谱
          </span>
          <div>
            <h1>{{ course.title }}知识图谱</h1>
            <p>{{ activeMap.description }}</p>
          </div>
        </div>
        <div class="graph-top-actions">
          <label class="graph-search">
            <icon-search />
            <input v-model="keyword" type="search" placeholder="搜索知识点、资料、任务" />
          </label>
          <button type="button" class="ghost-action" @click="goCourseContent">课堂笔记</button>
          <button type="button" class="primary-action" @click="goResourceGenerator">
            <icon-file /> 生成资源
          </button>
        </div>
      </header>

      <div class="graph-workbench-grid">
        <aside class="map-catalog">
          <section class="catalog-card catalog-intro">
            <span>KNOWLEDGE MAP</span>
            <strong>课程图谱目录</strong>
            <p>选择图谱后，中间画布会同步切换节点、关系和右侧学习动作。</p>
          </section>

          <section class="catalog-card focus-chip-board">
            <strong>当前图谱焦点</strong>
            <button
              v-for="item in focusTagChips"
              :key="item.tag"
              type="button"
              @click="askGraphAgent(`围绕${item.tag}梳理当前图谱中的关键节点和学习动作`)"
            >
              <span>{{ item.tag }}</span>
              <em>{{ item.count }}</em>
            </button>
          </section>

          <nav class="graph-tabs" aria-label="图谱分类">
            <button
              v-for="item in maps"
              :key="item.type"
              type="button"
              :class="{ active: activeType === item.type }"
              @click="selectMap(item.type)"
            >
              <span>{{ item.title }}</span>
              <em>{{ item.nodes.length }} 节点 · {{ item.links.length }} 关系</em>
            </button>
          </nav>

          <section class="catalog-card">
            <strong>薄弱节点</strong>
            <button
              v-for="node in lowMasteryNodes"
              :key="node.id"
              type="button"
              class="weak-node"
              :class="{ active: selectedNode?.id === node.id }"
              @click="selectNode(node)"
            >
              <span>{{ node.label }}</span>
              <em>{{ node.mastery ?? course.progress }}%</em>
            </button>
          </section>
        </aside>

        <div class="graph-work-area">
          <div class="graph-filter-row">
            <div class="relation-filter">
              <button
                v-for="item in relationSummary"
                :key="item.relation"
                type="button"
                :class="{ active: activeRelation === item.relation }"
                @click="activeRelation = item.relation"
              >
                {{ item.relation }}
                <em>{{ item.count }}</em>
              </button>
            </div>
            <div class="graph-switches">
              <label><input v-model="showLearningPath" type="checkbox" /> 学习路径</label>
              <label><input v-model="showResourceLinks" type="checkbox" /> 资料关系</label>
              <div class="view-switch" aria-label="图谱视图">
                <button
                  type="button"
                  :class="{ active: viewMode === 'network' }"
                  @click="viewMode = 'network'"
                >
                  图谱
                </button>
                <button
                  type="button"
                  :class="{ active: viewMode === 'structure' }"
                  @click="viewMode = 'structure'"
                >
                  脉络
                </button>
              </div>
            </div>
          </div>

          <div class="graph-command-deck">
            <article v-for="item in graphCommandDeck" :key="item.key">
              <div>
                <span>{{ item.kicker }}</span>
                <strong>{{ item.title }}</strong>
                <p>{{ item.desc }}</p>
              </div>
              <button type="button" @click="runGraphCommand(item.key)">
                {{ item.metric }}
              </button>
            </article>
          </div>

          <main class="graph-stage">
            <section class="graph-canvas-panel">
              <div class="graph-canvas-head">
                <div>
                  <span class="canvas-eyebrow">{{ activeMap.title }}</span>
                  <strong>{{ selectedNode?.label || course.shortTitle }}</strong>
                  <p>{{ visibleNodes.length }} 个节点 · {{ visibleLinks.length }} 条关系 · 当前聚焦 {{ nodeTypeLabel(selectedNode?.type) }}</p>
                </div>
                <div class="canvas-head-right">
                  <div class="stat-strip">
                    <span v-for="item in graphStats" :key="item.label">
                      <b>{{ item.value }}</b>
                      {{ item.label }}
                    </span>
                  </div>
                  <div class="zoom-control">
                    <button type="button" @click="changeZoom(-0.08)">-</button>
                    <span>{{ Math.round(canvasZoom * 100) }}%</span>
                    <button type="button" @click="changeZoom(0.08)">+</button>
                    <button type="button" @click="resetCanvas">复位</button>
                  </div>
                </div>
              </div>

              <div v-if="viewMode === 'structure'" class="structure-map">
                <div class="structure-root">
                  <span>2026春</span>
                  <strong>{{ course.shortTitle }}</strong>
                </div>
                <div class="structure-trunk" aria-hidden="true"></div>
                <div class="structure-branches">
                  <article
                    v-for="(branch, index) in structureBranches"
                    :key="branch.id"
                    class="structure-branch"
                    :class="{ active: selectedNodeId === `chapter-${index}` }"
                    :style="{ '--branch-offset': `${index * 4}px` }"
                    tabindex="0"
                    @click="selectBranch(index)"
                    @keydown.enter="selectBranch(index)"
                  >
                    <div class="branch-title">
                      <span>{{ String(index + 1).padStart(2, '0') }}</span>
                      <strong>{{ branch.title }}</strong>
                    </div>
                    <div class="branch-badges">
                      <em
                        v-for="(badge, badgeIndex) in branch.resourceBadges"
                        :key="`${branch.id}-${badge}-${badgeIndex}`"
                        :class="`badge-${badge}`"
                      >
                        {{ badge }}
                      </em>
                    </div>
                    <div class="branch-meta">
                      <span>任务 {{ branch.taskCount }}</span>
                      <span>薄弱点：{{ branch.weakPoint }}</span>
                      <strong>{{ branch.progress }}%</strong>
                    </div>
                  </article>
                </div>
              </div>

              <div
                v-else
                class="map-canvas-viewport"
                :class="{ panning: isPanning }"
                @pointerdown="beginCanvasPan"
                @pointermove="moveCanvasPan"
                @pointerup="endCanvasPan"
                @pointerleave="endCanvasPan"
              >
                <svg
                  class="map-canvas"
                  :style="{ transform: canvasTransform }"
                  viewBox="40 0 880 460"
                  role="img"
                  :aria-label="activeMap.title"
                >
                  <defs>
                    <linearGradient id="graphRootFill" x1="0" x2="1" y1="0" y2="1">
                      <stop offset="0%" stop-color="#5379ff" />
                      <stop offset="100%" stop-color="#7660d8" />
                    </linearGradient>
                    <filter id="graphNodeShadow" x="-24%" y="-80%" width="148%" height="240%">
                      <feDropShadow dx="0" dy="8" stdDeviation="7" flood-color="#20305c" flood-opacity=".14" />
                    </filter>
                    <filter id="graphRootShadow" x="-24%" y="-80%" width="148%" height="240%">
                      <feDropShadow dx="0" dy="16" stdDeviation="12" flood-color="#4054cf" flood-opacity=".34" />
                    </filter>
                  </defs>

                  <g class="graph-links">
                    <path
                      v-for="link in visibleLinks"
                      :key="`${link.source}-${link.target}-${link.relation}`"
                      :d="linkPath(link)"
                      :class="linkClass(link)"
                    />
                  </g>

                  <g
                    v-for="node in visibleNodes"
                    :key="node.id"
                    :transform="`translate(${node.x - nodeBoxWidth(node) / 2} ${node.y - nodeBoxHeight(node) / 2})`"
                    :class="nodeClass(node)"
                    class="graph-node"
                    tabindex="0"
                    role="button"
                    @click="selectNode(node)"
                    @keydown.enter="selectNode(node)"
                  >
                    <title>{{ node.label }} · {{ nodeSubtitle(node) }}</title>
                    <rect
                      class="node-body"
                      :width="nodeBoxWidth(node)"
                      :height="nodeBoxHeight(node)"
                      :rx="node.weight >= 4 ? 18 : 12"
                      :fill="nodeFill(node)"
                      :stroke="nodeStroke(node)"
                      :filter="node.weight >= 4 ? 'url(#graphRootShadow)' : 'url(#graphNodeShadow)'"
                    />
                    <rect
                      v-if="node.weight < 4"
                      class="node-track"
                      x="16"
                      :y="nodeBoxHeight(node) - 8"
                      :width="nodeBoxWidth(node) - 32"
                      height="3"
                      rx="1.5"
                    />
                    <rect
                      v-if="node.weight < 4"
                      class="node-progress"
                      x="16"
                      :y="nodeBoxHeight(node) - 8"
                      :width="(nodeBoxWidth(node) - 32) * ((node.mastery ?? course.progress) / 100)"
                      height="3"
                      rx="1.5"
                      :fill="nodeStroke(node)"
                    />
                    <g
                      v-if="node.weight < 4"
                      class="node-mastery-badge"
                      :class="{
                        hot: (node.mastery ?? course.progress) < 60,
                        done: (node.mastery ?? course.progress) >= 80,
                      }"
                    >
                      <rect
                        :x="nodeBoxWidth(node) - 48"
                        y="-10"
                        width="42"
                        height="20"
                        rx="10"
                      />
                      <text
                        :x="nodeBoxWidth(node) - 27"
                        y="4"
                        text-anchor="middle"
                      >
                        {{ node.mastery ?? course.progress }}%
                      </text>
                    </g>
                    <circle
                      v-if="node.weight < 4"
                      cx="17"
                      :cy="nodeBoxHeight(node) / 2"
                      r="4"
                      :fill="nodeStroke(node)"
                    />
                    <text
                      :x="nodeBoxWidth(node) / 2 + (node.weight >= 4 ? 0 : 8)"
                      :y="node.weight >= 4 ? 26 : nodeBoxHeight(node) / 2 - 1"
                      text-anchor="middle"
                      :fill="nodeTextColor(node)"
                    >
                      {{ shortNodeLabel(node.label, node.weight >= 4 ? 10 : 8) }}
                    </text>
                    <text
                      v-if="node.weight >= 4"
                      :x="nodeBoxWidth(node) / 2"
                      y="46"
                      text-anchor="middle"
                      class="node-subtitle"
                    >
                      {{ nodeSubtitle(node) }}
                    </text>
                  </g>
                </svg>

                <div v-if="!visibleNodes.length" class="graph-empty">
                  <strong>没有匹配节点</strong>
                  <span>换一个关键词或切回全部关系后继续查看图谱。</span>
                </div>
              </div>

              <div v-if="viewMode === 'network'" class="map-canvas-tools">
                <div class="graph-legend">
                  <span class="legend-primary">核心路径</span>
                  <span class="legend-resource">资料支撑</span>
                  <span class="legend-task">任务驱动</span>
                </div>
                <div class="graph-quick-actions">
                  <button type="button" @click="askGraphAgent('沿当前节点展开前置和后置知识路径')">展开路径</button>
                  <button type="button" @click="askGraphAgent('解释当前节点连接的资料、任务和能力证据')">AI 解读</button>
                  <button type="button" @click="downloadNodeStudyPack">节点学习包</button>
                  <button type="button" @click="goResourceGenerator">生成资料</button>
                </div>
              </div>
            </section>

            <aside class="map-insights">
              <section class="node-detail-section">
                <div class="node-detail-head">
                  <div>
                    <strong>{{ nodeTypeLabel(selectedNode?.type) }}</strong>
                    <h3>{{ selectedNode?.label || activeMap.title }}</h3>
                  </div>
                  <div class="mastery-ring" :style="{ '--mastery': `${selectedNodeMastery * 3.6}deg` }">
                    <span>{{ selectedNodeMastery }}%</span>
                  </div>
                </div>
                <p>{{ selectedNode?.detail || activeMap.description }}</p>
                <div class="node-meta">
                  <span>关联 {{ selectedLinks.length }} 条</span>
                  <span>{{ selectedNode?.recommendedAction || '生成学习路径' }}</span>
                </div>
                <div v-if="selectedRelationTags.length" class="relation-tags">
                  <em v-for="item in selectedRelationTags" :key="item">{{ item }}</em>
                </div>
              </section>

              <section class="node-health-panel">
                <strong>节点状态</strong>
                <div class="node-health-grid">
                  <article
                    v-for="item in selectedNodeHealth"
                    :key="item.label"
                    :class="`tone-${item.tone}`"
                  >
                    <span>{{ item.label }}</span>
                    <b>{{ item.value }}</b>
                    <p>{{ item.desc }}</p>
                  </article>
                </div>
              </section>

              <section class="node-timeline-panel">
                <strong>学习路径</strong>
                <div class="node-timeline">
                  <article
                    v-for="item in nodeActionTimeline"
                    :key="item.step"
                    :class="`state-${item.state}`"
                  >
                    <span>{{ item.step }}</span>
                    <div>
                      <b>{{ item.title }}</b>
                      <p>{{ item.desc }}</p>
                    </div>
                  </article>
                </div>
              </section>

              <section v-if="nodeStudyPack" class="study-pack-panel">
                <div class="study-pack-head">
                  <div>
                    <strong>节点学习包</strong>
                    <span>{{ nodeStudyPack.nodeType }} · {{ nodeStudyPack.mastery }}%</span>
                  </div>
                  <button type="button" @click="downloadNodeStudyPack">
                    <icon-download /> 下载
                  </button>
                </div>
                <p>{{ nodeStudyPack.objective }}</p>
                <div class="study-pack-grid">
                  <article>
                    <span>证据</span>
                    <b>{{ nodeStudyPack.evidence.length }}</b>
                    <small>{{ nodeStudyPack.evidence[0] }}</small>
                  </article>
                  <article>
                    <span>资源</span>
                    <b>{{ nodeStudyPack.resources.length }}</b>
                    <small>{{ nodeStudyPack.resources[0] }}</small>
                  </article>
                  <article>
                    <span>检查</span>
                    <b>{{ nodeStudyPack.checks.length }}</b>
                    <small>{{ nodeStudyPack.checks[0] }}</small>
                  </article>
                </div>
              </section>

              <section class="evidence-matrix-panel">
                <strong>证据矩阵</strong>
                <article v-for="column in evidenceMatrix" :key="column.key" class="evidence-column">
                  <span>{{ column.title }}</span>
                  <p v-for="item in column.items.slice(0, 3)" :key="item">{{ item }}</p>
                </article>
              </section>

              <section v-if="selectedNodeOutcomes.length || selectedNodeMisconceptions.length">
                <strong>掌握标准</strong>
                <div class="insight-columns">
                  <div>
                    <span>学习产出</span>
                    <p v-for="item in selectedNodeOutcomes" :key="item">{{ item }}</p>
                  </div>
                  <div>
                    <span>常见误区</span>
                    <p v-for="item in selectedNodeMisconceptions" :key="item">{{ item }}</p>
                  </div>
                </div>
              </section>

              <section v-if="selectedNodeChecks.length">
                <strong>检查题</strong>
                <ul class="check-list">
                  <li v-for="item in selectedNodeChecks" :key="item">{{ item }}</li>
                </ul>
              </section>

              <section v-if="selectedNodeActivities.length">
                <strong>课堂动作</strong>
                <div class="activity-list">
                  <p v-for="item in selectedNodeActivities" :key="item">{{ item }}</p>
                </div>
              </section>

              <section v-if="selectedNeighbors.length">
                <strong>相邻节点</strong>
                <button
                  v-for="item in selectedNeighbors.slice(0, 5)"
                  :key="`${item.link.source}-${item.link.target}`"
                  type="button"
                  class="neighbor-button"
                  @click="selectNode(item.neighbor)"
                >
                  <span>{{ item.link.relation }}</span>
                  <b>{{ item.neighbor.label }}</b>
                  <em>{{ item.link.strength || 72 }}%</em>
                </button>
              </section>

              <section>
                <strong>AI 动作</strong>
                <button type="button" @click="askGraphAgent('解释当前节点和先修关系')">解释当前节点</button>
                <button type="button" @click="askGraphAgent('基于当前节点生成一组自测题')">生成图谱自测</button>
                <button type="button" @click="downloadNodeStudyPack">下载节点学习包</button>
                <button type="button" @click="goResourceGenerator">生成配套资料</button>
              </section>
            </aside>
          </main>
        </div>
      </div>

      <div class="guided-path">
        <article v-for="step in guidedLearningPath" :key="step.label">
          <span>{{ step.label }}</span>
          <strong>{{ step.title }}</strong>
          <p>{{ step.desc }}</p>
        </article>
        <article class="path-action">
          <span>伴学</span>
          <strong>让 AI 基于图谱制定下一步</strong>
          <button type="button" @click="askGraphAgent('围绕薄弱节点生成 20 分钟复习路径')">
            <icon-robot /> 生成复习路径
          </button>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped lang="less">
  .knowledge-page {
    color: #151e33;
  }

  .graph-lab-shell {
    position: relative;
    overflow: hidden;
    padding: 24px;
    border: 1px solid #e7ecf6;
    border-radius: 28px;
    background:
      radial-gradient(circle at 12% 0%, rgba(58, 130, 214, 0.12), transparent 30%),
      radial-gradient(circle at 100% 0%, rgba(121, 92, 207, 0.11), transparent 26%),
      linear-gradient(180deg, #fbfdff, #f4f8fc);
    box-shadow: 0 22px 58px rgba(31, 45, 83, 0.08);
  }

  .graph-topbar,
  .graph-filter-row,
  .graph-stage,
  .guided-path {
    position: relative;
    z-index: 1;
  }

  .graph-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 18px;
  }

  .graph-brand {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 16px;
    min-width: 0;

    h1 {
      margin: 0;
      color: #141d31;
      font-size: 25px;
      font-weight: 800;
      letter-spacing: 0;
      white-space: nowrap;
    }

    p {
      margin: 5px 0 0;
      color: #6f7d93;
      font-size: 13px;
      line-height: 1.5;
    }
  }

  .graph-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    height: 44px;
    padding: 0 18px;
    border: 4px solid rgba(255, 255, 255, 0.9);
    border-radius: 999px;
    color: #fff;
    background: linear-gradient(135deg, #3477f6, #5d55eb);
    box-shadow: 0 10px 22px rgba(68, 97, 225, 0.24);
    font-size: 17px;
    font-weight: 800;
    white-space: nowrap;
  }

  .graph-top-actions {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    min-width: 360px;
  }

  .graph-search {
    width: 290px;
    height: 42px;
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 0 15px;
    border: 1px solid #e8edf6;
    border-radius: 999px;
    color: #a6afbe;
    background: rgba(255, 255, 255, 0.88);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);

    input {
      width: 100%;
      min-width: 0;
      border: 0;
      outline: 0;
      color: #24304a;
      background: transparent;
      font-size: 13px;
    }
  }

  .ghost-action,
  .primary-action {
    height: 38px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 0 15px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }

  .ghost-action {
    border: 1px solid #e2e8f4;
    color: #536079;
    background: rgba(255, 255, 255, 0.84);
  }

  .primary-action {
    border: 0;
    color: #fff;
    background: #4468f2;
    box-shadow: 0 10px 18px rgba(68, 104, 242, 0.18);
  }

  .graph-tabs {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0;
    margin-bottom: 0;
    border: 1px solid #e8edf6;
    border-radius: 22px 22px 0 0;
    background: rgba(255, 255, 255, 0.92);
    overflow: hidden;

    button {
      min-width: 0;
      height: 62px;
      display: grid;
      place-items: center;
      gap: 2px;
      border: 0;
      border-right: 1px solid #eef2f8;
      color: #606b81;
      background: transparent;
      cursor: pointer;
      position: relative;

      &:last-child {
        border-right: 0;
      }

      &::after {
        position: absolute;
        bottom: 0;
        width: 34px;
        height: 4px;
        border-radius: 999px 999px 0 0;
        content: '';
        background: transparent;
      }

      &.active {
        color: #17213a;
        background: #fff;
      }

      &.active::after {
        background: #3778f6;
      }
    }

    span {
      font-size: 15px;
      font-weight: 800;
    }

    em {
      color: #95a0b3;
      font-size: 11px;
      font-style: normal;
    }
  }

  .graph-filter-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    padding: 14px 18px;
    border: 1px solid #e8edf6;
    border-top: 0;
    background: rgba(255, 255, 255, 0.94);
  }

  .relation-filter,
  .graph-switches {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }

  .relation-filter button,
  .view-switch button {
    height: 30px;
    padding: 0 12px;
    border: 1px solid #e4e9f3;
    border-radius: 999px;
    color: #707b91;
    background: #fff;
    font-size: 12px;
    cursor: pointer;

    &.active {
      border-color: #bfd2ff;
      color: #2f68df;
      background: #edf4ff;
    }
  }

  .graph-switches label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #68748a;
    font-size: 12px;
    white-space: nowrap;

    input {
      accent-color: #3778f6;
    }
  }

  .view-switch {
    display: inline-flex;
    gap: 4px;
    padding: 3px;
    border: 1px solid #e7edf8;
    border-radius: 999px;
    background: #f7f9fd;
  }

  .graph-stage {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 316px;
    gap: 18px;
    min-height: 590px;
    padding: 18px;
    border: 1px solid #e8edf6;
    border-top: 0;
    border-radius: 0 0 22px 22px;
    background: rgba(255, 255, 255, 0.96);
  }

  .graph-canvas-panel,
  .map-insights {
    border: 1px solid #e7edf6;
    border-radius: 20px;
    background: #fff;
    box-shadow: 0 14px 32px rgba(42, 56, 90, 0.06);
  }

  .graph-canvas-panel {
    position: relative;
    min-width: 0;
    overflow: hidden;
  }

  .graph-canvas-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    padding: 15px 18px;
    border-bottom: 1px solid #edf2f8;

    strong,
    span {
      display: block;
    }

    strong {
      color: #17213a;
      font-size: 16px;
    }

    span {
      margin-top: 3px;
      color: #7e899a;
      font-size: 12px;
    }
  }

  .zoom-control {
    display: grid;
    grid-template-columns: 30px 48px 30px;
    align-items: center;
    gap: 6px;

    button {
      height: 28px;
      border: 1px solid #dfe6f1;
      border-radius: 10px;
      color: #5f6b80;
      background: #fff;
      cursor: pointer;
    }

    span {
      color: #3970e7;
      font-size: 12px;
      font-weight: 800;
      text-align: center;
    }
  }

  .map-canvas {
    width: 100%;
    height: 528px;
    display: block;
    transform-origin: center;
    transition: transform 0.18s ease;
    background:
      radial-gradient(circle at 50% 50%, rgba(75, 101, 239, 0.08), transparent 32%),
      radial-gradient(circle, #dbe3f1 1.1px, transparent 1.2px);
    background-color: #fbfdff;
    background-size: auto, 24px 24px;
  }

  .graph-links path {
    fill: none;
    stroke: #cfd8e7;
    stroke-width: 1.8;
    stroke-linecap: round;
    opacity: 0.82;
    transition: opacity 0.16s ease, stroke 0.16s ease, stroke-width 0.16s ease;
  }

  .graph-links .link-父子关系,
  .graph-links .link-前后置关系 {
    stroke: #6fa4de;
    stroke-width: 2.6;
  }

  .graph-links .link-资料支撑 {
    stroke: #6fba92;
    stroke-dasharray: 6 6;
  }

  .graph-links .link-任务驱动 {
    stroke: #e5a156;
    stroke-dasharray: 5 5;
  }

  .graph-links .selected {
    stroke: #3d70f2;
    stroke-width: 3.4;
    opacity: 1;
  }

  .graph-links .dimmed {
    opacity: 0.2;
  }

  .graph-node {
    cursor: pointer;
    outline: none;
    transition: opacity 0.16s ease;

    .node-body {
      transition: transform 0.16s ease, filter 0.16s ease, stroke-width 0.16s ease;
      transform-box: fill-box;
      transform-origin: center;
    }

    .node-track {
      fill: rgba(158, 171, 195, 0.22);
      stroke: none;
      pointer-events: none;
    }

    .node-progress {
      stroke: none;
      pointer-events: none;
    }

    .node-mastery-badge {
      pointer-events: none;

      rect {
        fill: #edf4ff;
        stroke: #c8d8ff;
      }

      text {
        fill: #2f68df;
        font-size: 9px;
        font-weight: 900;
      }

      &.hot {
        rect {
          fill: #fff4e6;
          stroke: #ffd6a1;
        }

        text {
          fill: #d46f1d;
        }
      }

      &.done {
        rect {
          fill: #ecfff4;
          stroke: #b8e9cc;
        }

        text {
          fill: #237c4c;
        }
      }
    }

    text {
      font-size: 13px;
      font-weight: 800;
      pointer-events: none;
    }

    .node-subtitle {
      fill: rgba(255, 255, 255, 0.78);
      font-size: 11px;
      font-weight: 600;
    }

    &:hover .node-body,
    &:focus-visible .node-body {
      transform: translateY(-2px);
      stroke-width: 2.4;
    }

    &.selected .node-body {
      stroke: #255fe8;
      stroke-width: 3;
    }

    &.related:not(.selected) {
      opacity: 0.92;
    }

    &.dimmed {
      opacity: 0.38;
    }
  }

  .map-canvas-tools {
    position: absolute;
    right: 16px;
    bottom: 16px;
    left: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 12px;
    border: 1px solid rgba(214, 224, 241, 0.92);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.86);
    box-shadow: 0 12px 30px rgba(35, 48, 82, 0.08);
    backdrop-filter: blur(10px);
  }

  .graph-legend,
  .graph-quick-actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }

  .graph-legend span {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #6f7a90;
    font-size: 11px;
    white-space: nowrap;

    &::before {
      width: 22px;
      height: 3px;
      border-radius: 999px;
      content: '';
      background: #6fa4de;
    }
  }

  .graph-legend .legend-resource::before {
    background: repeating-linear-gradient(90deg, #6fba92 0 6px, transparent 6px 10px);
  }

  .graph-legend .legend-task::before {
    background: repeating-linear-gradient(90deg, #e5a156 0 5px, transparent 5px 9px);
  }

  .graph-quick-actions button {
    height: 30px;
    padding: 0 11px;
    border: 1px solid #dfe7f3;
    border-radius: 10px;
    color: #3d4b64;
    background: #fff;
    font-size: 11px;
    font-weight: 800;
    cursor: pointer;

    &:hover {
      border-color: #bfd2ff;
      color: #2f68df;
      background: #eff4ff;
    }
  }

  .structure-map {
    position: relative;
    min-height: 528px;
    display: grid;
    grid-template-columns: minmax(140px, 0.23fr) 20px minmax(0, 1fr);
    gap: 22px;
    align-items: center;
    padding: 34px;
    overflow: hidden;
    background:
      radial-gradient(circle at 22% 50%, rgba(59, 126, 226, 0.11), transparent 28%),
      radial-gradient(circle, #dbe3f1 1.1px, transparent 1.2px);
    background-color: #fbfdff;
    background-size: auto, 24px 24px;
  }

  .structure-root {
    justify-self: end;
    display: grid;
    gap: 9px;
    text-align: right;

    span,
    strong {
      display: inline-flex;
      justify-content: flex-end;
      padding: 9px 14px;
      border: 1px solid #bfe7ce;
      border-radius: 999px;
      color: #237c4c;
      background: #effbf5;
      font-size: 13px;
      font-weight: 800;
    }

    strong {
      color: #fff;
      background: #58ba77;
    }
  }

  .structure-trunk {
    width: 5px;
    height: min(420px, 100%);
    border-radius: 999px;
    background: linear-gradient(180deg, #58bd78, #83d89f);
    box-shadow: 0 0 0 7px rgba(89, 189, 120, 0.08);
  }

  .structure-branches {
    display: grid;
    gap: 11px;
    min-width: 0;
  }

  .structure-branch {
    position: relative;
    display: grid;
    grid-template-columns: minmax(120px, 0.34fr) minmax(0, 1fr) minmax(150px, 0.34fr);
    align-items: center;
    gap: 10px;
    min-height: 46px;
    padding-left: var(--branch-offset);
    border-radius: 12px;
    cursor: pointer;
    outline: none;

    &:hover,
    &:focus-visible,
    &.active {
      background: rgba(55, 120, 246, 0.07);
    }

    &.active {
      box-shadow: inset 0 0 0 1px rgba(55, 120, 246, 0.24);
    }

    &::before {
      position: absolute;
      left: -23px;
      width: 22px;
      height: 2px;
      content: '';
      background: #85d4a2;
    }

    &::after {
      position: absolute;
      left: -28px;
      width: 9px;
      height: 9px;
      border-radius: 50%;
      content: '';
      background: #64c681;
      box-shadow: 0 0 0 5px #e8f8ee;
    }
  }

  .branch-title {
    display: flex;
    align-items: center;
    gap: 8px;

    span {
      color: #8b96aa;
      font-size: 10px;
      font-weight: 900;
    }

    strong {
      min-width: 0;
      overflow: hidden;
      color: #2d3950;
      font-size: 13px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .branch-badges,
  .resource-pills,
  .node-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }

  .branch-badges em {
    min-width: 34px;
    padding: 4px 6px;
    border-radius: 7px;
    color: #fff;
    background: #d86f76;
    font-size: 9px;
    font-style: normal;
    text-align: center;
  }

  .branch-badges .badge-讲义,
  .branch-badges .badge-讨论 {
    background: #6fa4de;
  }

  .branch-badges .badge-自测 {
    background: #76c79a;
  }

  .branch-badges .badge-导图 {
    background: #9277d8;
  }

  .branch-meta {
    display: grid;
    grid-template-columns: minmax(0, 0.5fr) minmax(0, 1fr) 44px;
    gap: 6px;
    align-items: center;
    color: #8792a6;
    font-size: 10px;

    span {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      color: #3970e7;
      font-size: 12px;
      text-align: right;
    }
  }

  .map-insights {
    max-height: 592px;
    padding: 16px;
    overflow: auto;

    section + section {
      margin-top: 13px;
      padding-top: 13px;
      border-top: 1px solid #edf2f8;
    }

    strong {
      display: block;
      margin-bottom: 7px;
      color: #334059;
      font-size: 13px;
    }

    h3 {
      margin: 2px 0 7px;
      color: #172033;
      font-size: 20px;
      line-height: 1.25;
    }

    p {
      margin: 0;
      color: #68748a;
      font-size: 12px;
      line-height: 1.72;
    }

    button {
      width: 100%;
      min-height: 34px;
      margin-top: 7px;
      border: 1px solid #e1e7f1;
      border-radius: 11px;
      color: #536079;
      background: #fbfcff;
      font-size: 12px;
      cursor: pointer;

      &:hover {
        border-color: #c8d8ff;
        color: #2f68df;
        background: #f0f5ff;
      }
    }
  }

  .node-detail-head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 58px;
    gap: 10px;
    align-items: center;
  }

  .mastery-ring {
    width: 52px;
    height: 52px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    background:
      radial-gradient(circle, #fff 56%, transparent 58%),
      conic-gradient(#3778f6 var(--mastery), #edf2f8 0);

    span {
      color: #2f68df;
      font-size: 12px;
      font-weight: 900;
    }
  }

  .node-meta {
    margin-top: 10px;

    span {
      padding: 5px 8px;
      border-radius: 999px;
      color: #2f68df;
      background: #eef4ff;
      font-size: 10px;
    }
  }

  .evidence-list {
    display: grid;
    gap: 7px;
    margin: 0;
    padding-left: 17px;
    color: #657287;
    font-size: 11px;
    line-height: 1.55;
  }

  .resource-pills {
    margin-top: 9px;

    em {
      padding: 5px 8px;
      border-radius: 8px;
      color: #25744d;
      background: #effaf4;
      font-size: 10px;
      font-style: normal;
      line-height: 1.35;
    }
  }

  .node-health-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;

    article {
      min-width: 0;
      padding: 10px;
      border: 1px solid #e7edf7;
      border-radius: 13px;
      background: #fbfcff;
    }

    span,
    b,
    p {
      display: block;
      min-width: 0;
    }

    span {
      color: #8b96aa;
      font-size: 10px;
      font-weight: 800;
    }

    b {
      margin: 4px 0 3px;
      color: #25304a;
      font-size: 17px;
      line-height: 1;
    }

    p {
      color: #778299;
      font-size: 10px;
      line-height: 1.45;
    }

    .tone-green {
      border-color: #ccefd9;
      background: #f3fff7;

      b {
        color: #237c4c;
      }
    }

    .tone-blue {
      border-color: #cfe0ff;
      background: #f5f8ff;

      b {
        color: #2f68df;
      }
    }

    .tone-orange {
      border-color: #ffe1b8;
      background: #fff8ee;

      b {
        color: #cf731e;
      }
    }
  }

  .node-timeline {
    position: relative;
    display: grid;
    gap: 9px;

    &::before {
      position: absolute;
      top: 14px;
      bottom: 14px;
      left: 13px;
      width: 2px;
      border-radius: 999px;
      background: #dfe7f4;
      content: '';
    }

    article {
      position: relative;
      z-index: 1;
      display: grid;
      grid-template-columns: 28px minmax(0, 1fr);
      gap: 9px;
      align-items: start;
    }

    span {
      width: 28px;
      height: 28px;
      display: grid;
      place-items: center;
      border: 1px solid #dfe7f4;
      border-radius: 50%;
      color: #7a8799;
      background: #fff;
      font-size: 9px;
      font-weight: 900;
    }

    b {
      display: block;
      color: #28354e;
      font-size: 12px;
    }

    p {
      display: -webkit-box;
      margin-top: 3px;
      overflow: hidden;
      color: #738096;
      font-size: 11px;
      line-height: 1.55;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }

    .state-ready span {
      border-color: #b8e9cc;
      color: #237c4c;
      background: #ecfff4;
    }

    .state-warning span {
      border-color: #ffd6a1;
      color: #d46f1d;
      background: #fff4e6;
    }
  }

  .study-pack-panel {
    display: grid;
    gap: 10px;
    border-color: #d8e5ff !important;
    background:
      linear-gradient(135deg, rgba(47, 104, 223, 0.08), rgba(37, 116, 77, 0.05)),
      #ffffff !important;

    > p {
      margin: 0;
      color: #5e6b81;
      font-size: 11px;
      line-height: 1.65;
    }
  }

  .study-pack-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;

    > div {
      min-width: 0;
      display: grid;
      gap: 3px;
    }

    strong,
    span {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: #6c7890;
      font-size: 10px;
      font-weight: 800;
    }

    button {
      width: auto !important;
      height: 30px !important;
      flex: 0 0 auto;
      display: inline-flex !important;
      align-items: center;
      gap: 5px;
      padding: 0 10px !important;
      border-color: #cfe0ff !important;
      color: #2f68df !important;
      background: #f4f7ff !important;
      font-size: 10px !important;
    }
  }

  .study-pack-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 7px;

    article {
      min-width: 0;
      padding: 9px;
      border: 1px solid rgba(207, 224, 255, 0.86);
      border-radius: 11px;
      background: rgba(255, 255, 255, 0.78);
    }

    span,
    b,
    small {
      display: block;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: #7c879b;
      font-size: 9px;
      font-weight: 900;
    }

    b {
      margin-top: 3px;
      color: #24324a;
      font-size: 18px;
      line-height: 1;
    }

    small {
      margin-top: 5px;
      color: #6b778e;
      font-size: 9px;
    }
  }

  .evidence-matrix-panel {
    display: grid;
    gap: 8px;
  }

  .evidence-column {
    padding: 10px;
    border: 1px solid #e7edf7;
    border-radius: 13px;
    background: #fbfcff;

    span {
      display: block;
      margin-bottom: 6px;
      color: #2f68df;
      font-size: 11px;
      font-weight: 900;
    }

    p {
      position: relative;
      padding-left: 12px;

      &::before {
        position: absolute;
        top: 8px;
        left: 0;
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: #9eb2d0;
        content: '';
      }
    }

    p + p {
      margin-top: 5px;
    }
  }

  .activity-list {
    display: grid;
    gap: 7px;

    p {
      padding: 8px 10px;
      border: 1px dashed #dce5f2;
      border-radius: 11px;
      background: #fbfcff;
    }
  }

  .insight-columns {
    display: grid;
    gap: 9px;

    > div {
      padding: 10px;
      border: 1px solid #e8edf5;
      border-radius: 12px;
      background: #fbfcff;
    }

    span {
      display: block;
      margin-bottom: 6px;
      color: #2f68df;
      font-size: 11px;
      font-weight: 900;
    }

    p + p {
      margin-top: 6px;
    }
  }

  .neighbor-button {
    display: grid !important;
    grid-template-columns: 62px minmax(0, 1fr) 42px;
    gap: 7px;
    align-items: center;
    height: auto !important;
    min-height: 38px;
    padding: 8px 9px !important;
    text-align: left;

    span,
    b,
    em {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: #8792a6;
      font-size: 10px;
    }

    b {
      color: #344057;
      font-size: 12px;
      font-weight: 800;
    }

    em {
      color: #2f68df;
      font-size: 10px;
      font-style: normal;
      text-align: right;
    }
  }

  .guided-path {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-top: 16px;

    article {
      min-width: 0;
      padding: 14px;
      border: 1px solid #e7edf6;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.92);
      box-shadow: 0 10px 24px rgba(35, 48, 82, 0.05);
    }

    span {
      display: inline-flex;
      margin-bottom: 8px;
      padding: 4px 9px;
      border-radius: 999px;
      color: #237c4c;
      background: #ecfff4;
      font-size: 11px;
      font-weight: 800;
    }

    strong {
      display: block;
      color: #253148;
      font-size: 13px;
      line-height: 1.45;
    }

    p {
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      min-height: 38px;
      margin: 7px 0 0;
      overflow: hidden;
      color: #778299;
      font-size: 11px;
      line-height: 1.7;
    }
  }

  .path-action button {
    height: 34px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    margin-top: 10px;
    padding: 0 12px;
    border: 0;
    border-radius: 11px;
    color: #fff;
    background: #4468f2;
    font-size: 12px;
    font-weight: 800;
    cursor: pointer;
  }

  @media (max-width: 1180px) {
    .graph-topbar,
    .graph-filter-row {
      align-items: flex-start;
      flex-direction: column;
    }

    .graph-top-actions,
    .graph-search {
      width: 100%;
      min-width: 0;
    }

    .graph-stage {
      grid-template-columns: 1fr;
    }

    .map-insights {
      max-height: none;
    }

    .guided-path {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 820px) {
    .graph-lab-shell {
      padding: 14px;
      border-radius: 20px;
    }

    .graph-brand,
    .graph-top-actions {
      align-items: stretch;
      flex-direction: column;
    }

    .graph-brand h1 {
      white-space: normal;
    }

    .graph-tabs,
    .guided-path,
    .structure-map {
      grid-template-columns: 1fr;
    }

    .graph-tabs {
      border-radius: 18px 18px 0 0;
    }

    .graph-stage {
      padding: 12px;
    }

    .map-canvas {
      height: 430px;
      min-width: 720px;
    }

    .graph-canvas-panel {
      overflow: auto;
    }

    .map-canvas-tools {
      position: static;
      align-items: flex-start;
      flex-direction: column;
      margin: 10px 12px 12px;
    }

    .structure-map {
      gap: 14px;
      padding: 18px;
    }

    .structure-root {
      justify-self: start;
      text-align: left;
    }

    .structure-trunk {
      display: none;
    }

    .structure-branch {
      grid-template-columns: 1fr;
      padding: 10px;
      border: 1px solid #e4eaf4;
      border-radius: 12px;
      background: #fff;

      &::before,
      &::after {
        display: none;
      }
    }
  }

  .graph-workbench-grid {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: 246px minmax(0, 1fr);
    gap: 16px;
    align-items: start;
  }

  .graph-lab-shell .graph-topbar {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(430px, 0.42fr);
    align-items: center;
  }

  .graph-lab-shell .graph-brand > div {
    min-width: 0;
  }

  .graph-lab-shell .graph-brand h1 {
    max-width: 100%;
    overflow: hidden;
    font-size: 23px;
    line-height: 1.24;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .graph-lab-shell .graph-brand p {
    max-width: 760px;
    display: -webkit-box;
    overflow: hidden;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .graph-lab-shell .graph-top-actions {
    min-width: 0;
  }

  .graph-lab-shell .graph-search {
    flex: 1 1 260px;
    min-width: 210px;
  }

  .map-catalog {
    display: grid;
    gap: 12px;
    min-width: 0;
  }

  .catalog-card {
    min-width: 0;
    padding: 16px;
    border: 1px solid #e7edf7;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.94);
    box-shadow: 0 14px 32px rgba(31, 45, 83, 0.06);

    > span {
      display: block;
      margin-bottom: 7px;
      color: #5b78f3;
      font-size: 10px;
      font-weight: 900;
      letter-spacing: 0.14em;
    }

    > strong {
      display: block;
      color: #18223a;
      font-size: 16px;
      font-weight: 900;
    }

    p {
      margin: 8px 0 0;
      color: #748197;
      font-size: 12px;
      line-height: 1.7;
    }
  }

  .catalog-intro {
    background:
      linear-gradient(135deg, rgba(237, 244, 255, 0.98), rgba(255, 255, 255, 0.94)),
      radial-gradient(circle at 90% 10%, rgba(118, 96, 216, 0.14), transparent 34%);
  }

  .focus-chip-board {
    display: grid;
    gap: 8px;

    button {
      width: 100%;
      min-height: 36px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 32px;
      gap: 8px;
      align-items: center;
      padding: 8px 10px;
      border: 1px solid #e7edf8;
      border-radius: 12px;
      color: #4d5b73;
      background: #fbfcff;
      cursor: pointer;

      &:hover {
        border-color: #c8d8ff;
        color: #2f68df;
        background: #f1f6ff;
      }
    }

    span,
    em {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      font-size: 12px;
      font-weight: 800;
      text-align: left;
    }

    em {
      height: 22px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      color: #2f68df;
      background: #edf4ff;
      font-size: 10px;
      font-style: normal;
      font-weight: 900;
    }
  }

  .graph-workbench-grid .graph-tabs {
    display: grid;
    grid-template-columns: 1fr;
    gap: 9px;
    margin: 0;
    border: 0;
    border-radius: 0;
    background: transparent;
    overflow: visible;

    button {
      position: relative;
      min-height: 66px;
      display: grid;
      place-items: initial;
      align-content: center;
      gap: 5px;
      padding: 12px 14px 12px 18px;
      border: 1px solid #e6edf8;
      border-radius: 16px;
      color: #5d6a80;
      background: rgba(255, 255, 255, 0.88);
      box-shadow: 0 10px 24px rgba(31, 45, 83, 0.045);
      text-align: left;

      &::before {
        position: absolute;
        top: 15px;
        bottom: 15px;
        left: 0;
        width: 4px;
        border-radius: 0 999px 999px 0;
        content: '';
        background: transparent;
      }

      &::after {
        display: none;
      }

      &.active {
        border-color: #c9d8ff;
        color: #17213a;
        background: #fff;
        box-shadow: 0 16px 32px rgba(71, 103, 223, 0.13);
      }

      &.active::before {
        background: #4774ff;
      }
    }

    span {
      font-size: 14px;
      line-height: 1.2;
      font-weight: 900;
    }

    em {
      color: #98a4b7;
      font-size: 11px;
      font-style: normal;
    }
  }

  .weak-node {
    width: 100%;
    min-height: 38px;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 42px;
    gap: 8px;
    align-items: center;
    margin-top: 8px;
    padding: 8px 10px;
    border: 1px solid #ebeff7;
    border-radius: 12px;
    color: #516078;
    background: #fbfcff;
    cursor: pointer;

    span,
    em {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      font-size: 12px;
      font-weight: 800;
      text-align: left;
    }

    em {
      color: #e58b35;
      font-size: 11px;
      font-style: normal;
      font-weight: 900;
      text-align: right;
    }

    &.active,
    &:hover {
      border-color: #ffd9a7;
      background: #fff8ef;
    }
  }

  .graph-work-area {
    min-width: 0;
    border: 1px solid #e7edf7;
    border-radius: 24px;
    background: rgba(255, 255, 255, 0.96);
    box-shadow: 0 18px 42px rgba(31, 45, 83, 0.07);
    overflow: hidden;
  }

  .graph-work-area .graph-filter-row {
    border: 0;
    border-bottom: 1px solid #edf2f8;
    padding: 14px 16px;
    background: #fff;
  }

  .graph-command-deck {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    padding: 12px 16px 14px;
    border-bottom: 1px solid #edf2f8;
    background:
      linear-gradient(180deg, #fff, #f8fbff),
      radial-gradient(circle at 8% 0%, rgba(71, 116, 255, 0.08), transparent 24%);
  }

  .graph-command-deck article {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    align-items: center;
    min-width: 0;
    min-height: 94px;
    padding: 12px;
    border: 1px solid #e4ebf8;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.92);
  }

  .graph-command-deck span,
  .graph-command-deck strong,
  .graph-command-deck p {
    display: block;
    min-width: 0;
  }

  .graph-command-deck span {
    color: #5878f5;
    font-size: 10px;
    font-weight: 900;
  }

  .graph-command-deck strong {
    margin-top: 4px;
    overflow: hidden;
    color: #17213a;
    font-size: 13px;
    line-height: 1.35;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .graph-command-deck p {
    display: -webkit-box;
    margin: 6px 0 0;
    overflow: hidden;
    color: #748197;
    font-size: 11px;
    line-height: 1.55;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .graph-command-deck button {
    width: 72px;
    min-height: 34px;
    padding: 0 8px;
    border: 0;
    border-radius: 10px;
    color: #fff;
    background: #4f6df5;
    box-shadow: 0 9px 18px rgba(79, 109, 245, 0.18);
    font-size: 11px;
    font-weight: 900;
    cursor: pointer;
  }

  .graph-work-area .relation-filter button {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    height: 32px;
    padding: 0 12px;

    em {
      min-width: 20px;
      padding: 1px 6px;
      border-radius: 999px;
      color: #7a879b;
      background: #f1f4f9;
      font-size: 10px;
      font-style: normal;
      font-weight: 900;
    }

    &.active em {
      color: #2f68df;
      background: #fff;
    }
  }

  .graph-work-area .graph-stage {
    grid-template-columns: minmax(0, 1fr) 332px;
    gap: 16px;
    min-height: 650px;
    padding: 16px;
    border: 0;
    border-radius: 0;
    background: #f7faff;
  }

  .graph-work-area .graph-canvas-panel,
  .graph-work-area .map-insights {
    border-radius: 18px;
    box-shadow: none;
  }

  .graph-work-area .graph-canvas-head {
    min-height: 78px;
    align-items: flex-start;
    padding: 16px 18px;

    strong {
      color: #131c30;
      font-size: 21px;
      line-height: 1.25;
    }

    p {
      margin: 5px 0 0;
      color: #7c889b;
      font-size: 12px;
    }
  }

  .canvas-eyebrow {
    margin: 0 0 4px !important;
    color: #5878f5 !important;
    font-size: 10px !important;
    font-weight: 900;
    letter-spacing: 0.14em;
  }

  .canvas-head-right {
    display: grid;
    justify-items: end;
    gap: 10px;
  }

  .stat-strip {
    display: flex;
    gap: 8px;

    span {
      min-width: 54px;
      display: grid !important;
      gap: 1px;
      margin: 0 !important;
      padding: 6px 9px;
      border: 1px solid #edf2fa;
      border-radius: 11px;
      color: #98a3b5 !important;
      background: #fbfcff;
      font-size: 10px !important;
      text-align: center;
    }

    b {
      color: #25304a;
      font-size: 14px;
      line-height: 1;
    }
  }

  .graph-work-area .zoom-control {
    grid-template-columns: 30px 48px 30px 46px;
  }

  .map-canvas-viewport {
    position: relative;
    height: 558px;
    overflow: hidden;
    cursor: grab;
    background:
      radial-gradient(circle at 48% 48%, rgba(83, 121, 255, 0.09), transparent 30%),
      radial-gradient(circle, #dce4f1 1px, transparent 1.2px);
    background-color: #fbfdff;
    background-size: auto, 24px 24px;
    user-select: none;

    &.panning {
      cursor: grabbing;
    }
  }

  .graph-work-area .map-canvas {
    height: 100%;
    min-width: 0;
    background: transparent;
    transform-origin: center;
    will-change: transform;
  }

  .graph-empty {
    position: absolute;
    inset: 0;
    display: grid;
    place-content: center;
    gap: 6px;
    color: #7a8799;
    text-align: center;
    background: rgba(251, 253, 255, 0.72);

    strong {
      color: #26334d;
      font-size: 16px;
    }

    span {
      font-size: 12px;
    }
  }

  .graph-work-area .graph-links path {
    stroke-width: 2.2;
  }

  .graph-work-area .graph-links .link-父子关系,
  .graph-work-area .graph-links .link-前后置关系 {
    stroke: #6d9fe8;
    stroke-width: 3;
  }

  .graph-work-area .graph-links .link-关联关系 {
    stroke: #aab7c9;
  }

  .graph-work-area .graph-links .link-资料支撑 {
    stroke: #68bd91;
    stroke-width: 2.6;
  }

  .graph-work-area .graph-links .link-任务驱动 {
    stroke: #e8a453;
    stroke-width: 2.6;
  }

  .graph-work-area .graph-links .selected {
    stroke: #416df4;
    stroke-width: 4;
  }

  .graph-work-area .graph-node.selected .node-body {
    stroke: #355ff2;
    stroke-width: 3.4;
  }

  .graph-work-area .map-canvas-tools {
    left: 18px;
    right: 18px;
    bottom: 18px;
    padding: 11px 13px;
  }

  .graph-work-area .map-insights {
    max-height: 652px;
    background: #fff;
  }

  .relation-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;

    em {
      max-width: 100%;
      overflow: hidden;
      padding: 5px 8px;
      border-radius: 999px;
      color: #5a6b85;
      background: #f3f6fb;
      font-size: 10px;
      font-style: normal;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .check-list {
    display: grid;
    gap: 7px;
    margin: 0;
    padding-left: 17px;
    color: #647186;
    font-size: 11px;
    line-height: 1.58;
  }

  @media (max-width: 1320px) {
    .graph-lab-shell .graph-topbar {
      grid-template-columns: 1fr;
    }

    .graph-lab-shell .graph-top-actions {
      width: 100%;
    }

    .graph-workbench-grid {
      grid-template-columns: 220px minmax(0, 1fr);
    }

    .graph-work-area .graph-stage {
      grid-template-columns: 1fr;
    }

    .graph-work-area .map-insights {
      max-height: none;
    }

    .graph-command-deck {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 980px) {
    .graph-workbench-grid {
      grid-template-columns: 1fr;
    }

    .graph-workbench-grid .graph-tabs {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .canvas-head-right {
      justify-items: start;
    }

    .graph-work-area .graph-canvas-head {
      flex-direction: column;
    }
  }

  @media (max-width: 640px) {
    .graph-workbench-grid .graph-tabs {
      grid-template-columns: 1fr;
    }

    .stat-strip {
      flex-wrap: wrap;
    }

    .graph-command-deck {
      grid-template-columns: 1fr;
    }

    .map-canvas-viewport {
      height: 430px;
      overflow: auto;
    }
  }
</style>
