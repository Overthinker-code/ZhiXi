<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { useRoute, useRouter } from 'vue-router';
  import type { LocationQueryRaw } from 'vue-router';
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
    type CourseKnowledgeMap,
    type CourseKnowledgeMapType,
    type CourseKnowledgeNode,
    type CourseStructureBranch,
  } from '@/data/courseWorkspace';
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';
  import {
    fetchCourseKnowledgeGraph,
    fetchCourseKnowledgeNeighbors,
    fetchCourseKnowledgeNodeActions,
    setCourseKnowledgeNodeAction,
    type CourseKnowledgeNodeActionState,
    type CourseKnowledgeNodeActionType,
  } from '@/api/knowledge-graph';

  type PackageMatch = {
    map: CourseKnowledgeMap;
    node: CourseKnowledgeNode;
    score: number;
  };
  type NodeStudyStatus = {
    reviewed?: boolean;
    practice?: boolean;
    resource?: boolean;
    pending?: ClosureActionKey;
    updatedAt?: string;
  };
  type ClosureActionKey = 'reviewed' | 'practice' | 'resource';
  type GraphNodePosition = {
    x: number;
    y: number;
  };
  const GRAPH_CANVAS = {
    width: 960,
    height: 620,
    centerX: 480,
    centerY: 310,
  };

  const route = useRoute();
  const router = useRouter();
  const keyword = ref('');
  const activeType = ref<CourseKnowledgeMapType>('knowledge');
  const viewMode = ref<'network' | 'structure'>('network');
  const activeRelation = ref<'全部' | '父子关系' | '前后置关系' | '关联关系' | '资料支撑' | '任务驱动'>('全部');
  const selectedNodeId = ref('');
  const showResourceLinks = ref(true);
  const showLearningPath = ref(true);
  const isolateSearchResults = ref(false);
  const canvasZoom = ref(1);
  const canvasPan = ref({ x: 0, y: 0 });
  const isPanning = ref(false);
  const panStart = ref({ pointerX: 0, pointerY: 0, x: 0, y: 0 });
  const selectedLinkKey = ref('');
  const inspectorTab = ref<'evidence' | 'resources' | 'next'>('evidence');
  const nodeStatuses = ref<Record<string, NodeStudyStatus>>({});
  const maps = ref<CourseKnowledgeMap[]>([]);
  const graphLoading = ref(false);
  const graphError = ref('');
  const actionsAvailable = ref(false);
  let graphRequestSequence = 0;
  let neighborRequestSequence = 0;

  const course = computed(() => getClassroomCourse(String(route.params.courseId || '')));
  const structureBranches = computed<CourseStructureBranch[]>(() => {
    const map = activeMap.value;
    if (!map) return [];
    return map.nodes
      .filter((node) => node.type === 'chapter' && node.weight < 4)
      .map((node) => {
        const relatedLinks = map.links.filter(
          (link) => link.source === node.id || link.target === node.id
        );
        const relatedNodes = relatedLinks
          .map((link) => (link.source === node.id ? link.target : link.source))
          .map((id) => map.nodes.find((item) => item.id === id))
          .filter(Boolean) as CourseKnowledgeNode[];
        return {
          id: node.id,
          title: node.label,
          resourceBadges: [] as CourseStructureBranch['resourceBadges'],
          taskCount: relatedNodes.filter((item) => item.type === 'task').length,
          weakPoint:
            relatedNodes
              .filter((item) => item.type === 'concept' && item.mastery !== undefined)
              .sort((left, right) => (left.mastery || 0) - (right.mastery || 0))[0]
              ?.label || '暂无评测数据',
          progress: node.mastery ?? 0,
        };
      });
  });
  const activeMap = computed<CourseKnowledgeMap | undefined>(
    () => maps.value.find((item) => item.type === activeType.value) || maps.value[0]
  );
  const relationTypes = computed(() => [
    '全部' as const,
    ...Array.from(new Set(activeMap.value?.links.map((link) => link.relation) || [])),
  ]);
  const relationPriority = (relation: string) => {
    if (relation === '父子关系') return 5;
    if (relation === '前后置关系') return 4;
    if (relation === '关联关系') return 3;
    if (relation === '资料支撑') return 2;
    if (relation === '任务驱动') return 1;
    return 0;
  };
  const visibleNodes = computed(() => {
    const map = activeMap.value;
    const key = keyword.value.trim().toLowerCase();
    if (!map) return [];
    if (!key || !isolateSearchResults.value) {
      const ids = new Set<string>();
      const root = map.nodes.find((node) => node.weight >= 4) || map.nodes[0];
      if (root) ids.add(root.id);
      const selectedId = selectedNodeId.value || root?.id;
      const isRootFocus = !selectedId || selectedId === root?.id;
      if (isRootFocus) {
        map.nodes.forEach((node) => {
          if (node.weight >= 3) ids.add(node.id);
        });
      } else if (selectedId) {
        ids.add(selectedId);
        map.links
          .filter((link) => link.source === selectedId || link.target === selectedId)
          .sort(
            (a, b) =>
              relationPriority(b.relation) - relationPriority(a.relation) ||
              (b.strength || 0) - (a.strength || 0)
          )
          .slice(0, 9)
          .forEach((link) => {
            ids.add(link.source);
            ids.add(link.target);
          });
        if (ids.size < 7) {
          map.nodes
            .filter((node) => node.weight >= 3)
            .slice(0, 7 - ids.size)
            .forEach((node) => ids.add(node.id));
        }
      }
      return map.nodes.filter((node) => ids.has(node.id));
    }
    const matchIds = searchMatchNodeIds.value;
    const relatedIds = new Set<string>(matchIds);
    map.links.forEach((link) => {
      if (matchIds.has(link.source)) relatedIds.add(link.target);
      if (matchIds.has(link.target)) relatedIds.add(link.source);
    });
    return map.nodes.filter((node) => relatedIds.has(node.id));
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
  const selectedAllLinks = computed(() => {
    const map = activeMap.value;
    const selectedId = selectedNode.value?.id;
    if (!map || !selectedId) return [];
    return map.links.filter((link) => link.source === selectedId || link.target === selectedId);
  });
  const selectedLinks = computed(() =>
    visibleLinks.value.filter(
      (link) => link.source === selectedNode.value?.id || link.target === selectedNode.value?.id
    )
  );
  const selectedNeighborIds = computed(
    () =>
      new Set(
        selectedAllLinks.value.flatMap((link) => [link.source, link.target])
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
  const selectedLink = computed(() => {
    const map = activeMap.value;
    if (!map || !selectedLinkKey.value) return null;
    return visibleLinks.value.find((link) => linkKey(link) === selectedLinkKey.value) || null;
  });
  const selectedLinkNodes = computed(() => {
    const map = activeMap.value;
    const link = selectedLink.value;
    if (!map || !link) return null;
    const source = map.nodes.find((node) => node.id === link.source);
    const target = map.nodes.find((node) => node.id === link.target);
    if (!source || !target) return null;
    return { source, target };
  });
  const graphPathSteps = computed(() => {
    const map = activeMap.value;
    const node = selectedNode.value;
    if (!map || !node || !course.value) return [];
    const findNode = (id: string) => map.nodes.find((item) => item.id === id);
    const incoming = visibleLinks.value
      .filter((link) => link.target === node.id)
      .map((link) => ({ link, node: findNode(link.source) }))
      .filter((item): item is { link: CourseKnowledgeMap['links'][number]; node: CourseKnowledgeNode } => Boolean(item.node))
      .sort((a, b) => {
        const relationWeight = (link: CourseKnowledgeMap['links'][number]) =>
          link.relation === '前后置关系' ? 3 : link.relation === '父子关系' ? 2 : 1;
        return relationWeight(b.link) - relationWeight(a.link) || (b.link.strength || 0) - (a.link.strength || 0);
      });
    const outgoing = visibleLinks.value
      .filter((link) => link.source === node.id)
      .map((link) => ({ link, node: findNode(link.target) }))
      .filter((item): item is { link: CourseKnowledgeMap['links'][number]; node: CourseKnowledgeNode } => Boolean(item.node))
      .sort((a, b) => {
        const relationWeight = (link: CourseKnowledgeMap['links'][number]) =>
          link.relation === '前后置关系' ? 3 : link.relation === '任务驱动' ? 2 : 1;
        return relationWeight(b.link) - relationWeight(a.link) || (b.link.strength || 0) - (a.link.strength || 0);
      });
    const weakestRelated = [...incoming, ...outgoing].sort(
      (a, b) => (a.node.mastery ?? 101) - (b.node.mastery ?? 101)
    )[0];
    const selectedEvidence = node.evidence?.[0] || node.detail || map.description;
    const selectedResource = node.resources?.[0] || `${node.label} 节点讲义`;
    const selectedCheck = node.checks?.[0] || `能否说明「${node.label}」的定义、条件和边界？`;
    const steps = [
      incoming[0]
        ? {
            key: 'before',
            phase: '前置',
            title: incoming[0].node.label,
            relation: incoming[0].link.relation,
            strength: incoming[0].link.strength || 72,
            mastery: incoming[0].node.mastery ?? 0,
            masteryKnown: incoming[0].node.mastery !== undefined,
            desc: `先确认「${incoming[0].node.label}」与当前节点的${incoming[0].link.relation}，避免直接跳到结论。`,
            evidence: incoming[0].node.evidence?.[0] || incoming[0].node.detail || '需要补齐前置节点课堂证据。',
            resource: incoming[0].node.resources?.[0] || `${incoming[0].node.label} 前置讲义`,
            check: incoming[0].node.checks?.[0] || `能否解释「${incoming[0].node.label}」如何支撑当前节点？`,
            nodeId: incoming[0].node.id,
          }
        : {
            key: 'before',
            phase: '前置',
            title: '课程总览',
            relation: '父子关系',
            strength: 68,
            mastery: 0,
            masteryKnown: false,
            desc: '从课程总览确认当前节点在课程主线中的位置。',
            evidence: `${course.value.shortTitle} 总览结构`,
            resource: `${course.value.shortTitle} 章节脉络`,
            check: '能否说明当前节点属于哪条课程主线？',
            nodeId: node.id,
          },
      {
        key: 'current',
        phase: '当前',
        title: node.label,
        relation: nodeTypeLabel(node.type),
        strength: Math.round(
          selectedLinks.value.reduce((sum, item) => sum + (item.strength || 72), 0) /
            Math.max(selectedLinks.value.length, 1)
        ),
        mastery: selectedNodeMastery.value,
        masteryKnown: node.mastery !== undefined,
        desc: node.recommendedAction || '围绕当前节点完成定义、边界、例题和错因复盘。',
        evidence: selectedEvidence,
        resource: selectedResource,
        check: selectedCheck,
        nodeId: node.id,
      },
      outgoing[0]
        ? {
            key: 'after',
            phase: '后续',
            title: outgoing[0].node.label,
            relation: outgoing[0].link.relation,
            strength: outgoing[0].link.strength || 72,
            mastery: outgoing[0].node.mastery ?? 0,
            masteryKnown: outgoing[0].node.mastery !== undefined,
            desc: `掌握当前节点后，沿${outgoing[0].link.relation}进入「${outgoing[0].node.label}」。`,
            evidence: outgoing[0].node.evidence?.[0] || outgoing[0].node.detail || '需要补齐后续节点课堂证据。',
            resource: outgoing[0].node.resources?.[0] || `${outgoing[0].node.label} 拓展练习`,
            check: outgoing[0].node.checks?.[0] || `能否把「${node.label}」迁移到「${outgoing[0].node.label}」？`,
            nodeId: outgoing[0].node.id,
          }
        : weakestRelated
          ? {
              key: 'after',
              phase: '补强',
              title: weakestRelated.node.label,
              relation: weakestRelated.link.relation,
              strength: weakestRelated.link.strength || 72,
              mastery: weakestRelated.node.mastery ?? 0,
              masteryKnown: weakestRelated.node.mastery !== undefined,
              desc: `当前没有明确后继，建议先补强相邻薄弱点「${weakestRelated.node.label}」。`,
              evidence: weakestRelated.node.evidence?.[0] || weakestRelated.node.detail || '需要补充相邻节点证据。',
              resource: weakestRelated.node.resources?.[0] || `${weakestRelated.node.label} 补强练习`,
              check: weakestRelated.node.checks?.[0] || `能否说清「${weakestRelated.node.label}」与当前节点的关系？`,
              nodeId: weakestRelated.node.id,
            }
          : {
              key: 'after',
              phase: '后续',
              title: '生成迁移任务',
              relation: '任务驱动',
              strength: 64,
              mastery: selectedNodeMastery.value,
              masteryKnown: node.mastery !== undefined,
              desc: '当前节点暂无后续关系，建议生成迁移题来补齐图谱边。',
              evidence: selectedEvidence,
              resource: `${node.label} 迁移练习`,
              check: `能否用「${node.label}」解决一个新场景问题？`,
              nodeId: node.id,
            },
    ];
    return steps;
  });
  const pathCoverageStats = computed(() => {
    const steps = graphPathSteps.value;
    const evidenceReady = steps.filter((item) => item.evidence && !item.evidence.includes('需要补')).length;
    const assessedSteps = steps.filter((item) => item.masteryKnown);
    const averageMastery = assessedSteps.length
      ? Math.round(
          assessedSteps.reduce((sum, item) => sum + item.mastery, 0) /
            assessedSteps.length
        )
      : null;
    const averageStrength = Math.round(
      steps.reduce((sum, item) => sum + item.strength, 0) / Math.max(steps.length, 1)
    );
    return [
      { label: '路径阶段', value: `${steps.length}` },
      { label: '证据覆盖', value: `${evidenceReady}/${steps.length}` },
      { label: '平均掌握', value: averageMastery === null ? '未评测' : `${averageMastery}%` },
      { label: '关系强度', value: `${averageStrength}%` },
    ];
  });
  const selectedNodeMastery = computed(() => selectedNode.value?.mastery ?? 0);
  const selectedNodeMasteryLabel = computed(() =>
    selectedNode.value?.mastery === undefined
      ? '未评测'
      : `${selectedNode.value.mastery}%`
  );
  const selectedNodeEvidence = computed(() => selectedNode.value?.evidence?.slice(0, 5) || []);
  const selectedNodeChecks = computed(() => selectedNode.value?.checks?.slice(0, 4) || []);
  const selectedNodeActivities = computed(() => selectedNode.value?.activities?.slice(0, 4) || []);
  const selectedNodeOutcomes = computed(() => selectedNode.value?.outcomes?.slice(0, 3) || []);
  const selectedNodeMisconceptions = computed(() => selectedNode.value?.misconceptions?.slice(0, 3) || []);
  const selectedNodeResources = computed(() => selectedNode.value?.resources?.slice(0, 4) || []);
  const canvasTransform = computed(
    () =>
      `translate(${GRAPH_CANVAS.centerX + canvasPan.value.x} ${GRAPH_CANVAS.centerY + canvasPan.value.y}) scale(${canvasZoom.value}) translate(-${GRAPH_CANVAS.centerX} -${GRAPH_CANVAS.centerY})`
  );
  const graphNodePositions = computed(() => {
    const map = activeMap.value;
    const selected = selectedNode.value;
    const positions = new Map<string, GraphNodePosition>();
    if (!map) return positions;
    const root = map.nodes.find((node) => node.weight >= 4) || map.nodes[0];
    const visible = visibleNodes.value;
    const rootId = root?.id;
    const selectedId = selected?.id || rootId;
    const isRootFocus = !selectedId || selectedId === rootId;
    const center = { x: 430, y: GRAPH_CANVAS.centerY };

    if (isRootFocus) {
      if (root) positions.set(root.id, center);
      const primaryNodes = visible.filter((node) => node.id !== rootId && node.weight >= 3);
      const secondaryNodes = visible.filter((node) => node.id !== rootId && node.weight < 3);
      primaryNodes.forEach((node, index) => {
        const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(primaryNodes.length, 1);
        positions.set(node.id, {
          x: center.x + Math.cos(angle) * 300,
          y: center.y + Math.sin(angle) * 214,
        });
      });
      secondaryNodes.forEach((node, index) => {
        const colCount = Math.min(Math.max(secondaryNodes.length, 1), 4);
        const col = index % colCount;
        const row = Math.floor(index / colCount);
        positions.set(node.id, {
          x: 210 + col * 180,
          y: 548 - row * 64,
        });
      });
      return positions;
    }

    if (selected) positions.set(selected.id, center);
    if (root && root.id !== selectedId) positions.set(root.id, { x: 430, y: 78 });

    const selectedLinksInMap = map.links.filter(
      (link) =>
        visibleNodeIds.value.has(link.source) &&
        visibleNodeIds.value.has(link.target) &&
        (link.source === selectedId || link.target === selectedId)
    );
    const nodeById = (id: string) => map.nodes.find((node) => node.id === id);
    const nodesFromLinks = (
      predicate: (link: CourseKnowledgeMap['links'][number]) => boolean,
      side: 'source' | 'target'
    ) =>
      selectedLinksInMap
        .filter(predicate)
        .sort(
          (a, b) =>
            relationPriority(b.relation) - relationPriority(a.relation) ||
            (b.strength || 0) - (a.strength || 0)
        )
        .map((link) => nodeById(link[side]))
        .filter(Boolean) as CourseKnowledgeNode[];

    const incoming = nodesFromLinks((link) => link.target === selectedId, 'source');
    const outgoing = nodesFromLinks((link) => link.source === selectedId, 'target');
    const support = Array.from(
      new Map(
        [...incoming, ...outgoing]
          .filter(
            (node) =>
              node.type === 'resource' ||
              node.type === 'task' ||
              node.type === 'ability' ||
              selectedLinksInMap.some(
                (link) =>
                  (link.source === node.id || link.target === node.id) &&
                  (link.relation === '资料支撑' || link.relation === '任务驱动')
              )
          )
          .map((node) => [node.id, node])
      ).values()
    );
    const supportIds = new Set(support.map((node) => node.id));
    const leftNodes = incoming.filter((node) => !supportIds.has(node.id) && node.id !== rootId);
    const rightNodes = outgoing.filter((node) => !supportIds.has(node.id) && node.id !== rootId);

    const distribute = (count: number, start: number, end: number) => {
      if (count <= 1) return [(start + end) / 2];
      const step = (end - start) / (count - 1);
      return Array.from({ length: count }, (_, index) => start + index * step);
    };
    const placeColumn = (nodes: CourseKnowledgeNode[], x: number, startY = 142, endY = 470) => {
      const unique = Array.from(new Map(nodes.map((node) => [node.id, node])).values())
        .filter((node) => visible.some((item) => item.id === node.id) && !positions.has(node.id));
      const ySlots = distribute(unique.length, startY, endY);
      unique.forEach((node, index) => {
        positions.set(node.id, { x, y: ySlots[index] });
      });
    };
    const placeRail = (nodes: CourseKnowledgeNode[], y: number, startX = 250, endX = 710) => {
      const unique = Array.from(new Map(nodes.map((node) => [node.id, node])).values())
        .filter((node) => visible.some((item) => item.id === node.id) && !positions.has(node.id));
      const xSlots = distribute(unique.length, startX, endX);
      unique.forEach((node, index) => {
        positions.set(node.id, { x: xSlots[index], y });
      });
    };

    placeColumn(leftNodes, 135, 160, 458);
    placeColumn(rightNodes, 735, 150, 470);
    placeRail(support, 530, 270, 650);

    const contextNodes = visible.filter((node) => !positions.has(node.id));
    contextNodes.forEach((node, index) => {
      const slots = [
        { x: 120, y: 150 },
        { x: 745, y: 150 },
        { x: 120, y: 470 },
        { x: 745, y: 470 },
        { x: 430, y: 540 },
        { x: 430, y: 78 },
      ];
      positions.set(node.id, slots[index % slots.length]);
    });
    return positions;
  });
  const graphStats = computed(() => [
    { label: '节点', value: String(visibleNodes.value.length) },
    { label: '关系', value: String(visibleLinks.value.length) },
    {
      label: '已评测',
      value: `${visibleNodes.value.filter((node) => node.mastery !== undefined).length}/${visibleNodes.value.length}`,
    },
  ]);
  const selectedMasteryState = computed(() => {
    if (selectedNode.value?.mastery === undefined) {
      return { label: '未评测', tone: 'unstarted' };
    }
    const mastery = selectedNodeMastery.value;
    if (mastery >= 80) return { label: '已掌握', tone: 'mastered' };
    if (mastery >= 60) return { label: '掌握中', tone: 'learning' };
    if (mastery > 0) return { label: '薄弱', tone: 'weak' };
    return { label: '未学习', tone: 'unstarted' };
  });
  const evidenceRows = computed(() => {
    const node = selectedNode.value;
    const fallback = node?.detail || activeMap.value?.description || '等待补充课程证据';
    const rows = selectedNodeEvidence.value.length ? selectedNodeEvidence.value : [fallback];
    return rows.slice(0, 4).map((title, index) => ({
      id: index + 1,
      title,
      source: index === 0 ? '课程课件' : index === 1 ? '课堂练习' : '学习记录',
      relevance: Math.max(68, 92 - index * 9),
    }));
  });
  const lowMasteryNodes = computed(() =>
    [...visibleNodes.value]
      .filter((node) => node.weight < 4 && node.mastery !== undefined)
      .sort((a, b) => (a.mastery || 0) - (b.mastery || 0))
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
        kicker: '01',
        title: '课程资料',
        desc: '课件、习题与课堂笔记',
        metric: `${selectedNodeEvidence.value.length || 1} 份`,
      },
      {
        key: 'resources',
        kicker: '02',
        title: '知识节点',
        desc: `${nodeLabel} 与一阶关系`,
        metric: `${visibleNodes.value.length} 个`,
      },
      {
        key: 'checks',
        kicker: '03',
        title: '掌握核验',
        desc: '证据、练习与错因状态',
        metric: selectedNodeMasteryLabel.value,
      },
      {
        key: 'agent',
        kicker: '04',
        title: '学习路径',
        desc: '按薄弱点生成下一步',
        metric: '个性化',
      },
    ];
  });
  const recommendedNode = computed(() => {
    const map = activeMap.value;
    if (!map || !course.value) return null;
    const candidates = map.nodes
      .filter((node) => node.weight < 4)
      .map((node) => {
        const mastery = node.mastery;
        const evidenceGap = Math.max(0, 2 - (node.evidence?.length || 0));
        const resourceGap = Math.max(0, 2 - (node.resources?.length || 0));
        const checkGap = Math.max(0, 2 - (node.checks?.length || 0));
        const relationCount = map.links.filter(
          (link) => link.source === node.id || link.target === node.id
        ).length;
        const status = nodeStatuses.value[`${map.type}:${node.id}`] || {};
        const unfinishedBonus =
          Number(!status.reviewed) + Number(!status.practice) + Number(!status.resource);
        return {
          node,
          score:
            (mastery === undefined ? 45 : 100 - mastery) * 1.4 +
            evidenceGap * 16 +
            resourceGap * 12 +
            checkGap * 14 +
            relationCount * 2 +
            unfinishedBonus * 8,
          reasons: [
            mastery === undefined ? '尚无掌握评测' : mastery < 65 ? `掌握度 ${mastery}%` : '',
            evidenceGap ? `缺 ${evidenceGap} 条课堂证据` : '',
            checkGap ? `缺 ${checkGap} 道检查题` : '',
            resourceGap ? `缺 ${resourceGap} 项配套资料` : '',
          ].filter(Boolean),
        };
      })
      .sort((a, b) => b.score - a.score);
    return candidates[0] || null;
  });
  const recommendationReasons = computed(() =>
    recommendedNode.value?.reasons.length
      ? recommendedNode.value.reasons
      : ['可沿图谱完成一次证据、练习、资料闭环']
  );
  const recommendationActions = computed(() => [
    {
      key: 'evidence',
      label: '读证据',
      desc: selectedNodeEvidence.value[0] || '回到课堂笔记确认定义和边界',
      done: Boolean(selectedNodeStatus.value.reviewed),
    },
    {
      key: 'practice',
      label: '加入复习',
      desc: selectedNodeChecks.value[0] || '生成分层检查题并记录错因',
      done: Boolean(selectedNodeStatus.value.practice),
    },
    {
      key: 'resource',
      label: '申请资料',
      desc: selectedNodeResources.value[0] || '生成讲义、导图和复习单',
      done: Boolean(selectedNodeStatus.value.resource),
    },
  ]);
  const nodeStudyPack = computed(() => {
    const node = selectedNode.value;
    const map = activeMap.value;
    if (!node || !map || !course.value) return null;
    const neighbors = selectedNeighbors.value.slice(0, 4).map((item) => ({
      relation: item.link.relation,
      label: item.neighbor.label,
      mastery: item.neighbor.mastery ?? 0,
      masteryKnown: item.neighbor.mastery !== undefined,
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
    const hasMastery = selectedNode.value?.mastery !== undefined;
    return [
      {
        label: '掌握状态',
        value: selectedNodeMasteryLabel.value,
        desc: !hasMastery
          ? '完成一次练习后生成评测结果'
          : mastery >= 80
            ? '可进入迁移任务'
            : mastery >= 60
              ? '需要补一轮自测'
              : '建议先补概念证据',
        tone: hasMastery && mastery >= 80 ? 'green' : hasMastery && mastery >= 60 ? 'blue' : 'orange',
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
  const searchMatches = computed(() => {
    const key = normalizeMatchText(keyword.value);
    if (!key || !activeMap.value) return [];
    return activeMap.value.nodes
      .map((node) => {
        const fields = [
          { label: '名称', value: node.label, weight: 5 },
          { label: '说明', value: node.detail || '', weight: 3 },
          { label: '证据', value: node.evidence?.join(' ') || '', weight: 2 },
          { label: '资源', value: node.resources?.join(' ') || '', weight: 2 },
          { label: '检查', value: node.checks?.join(' ') || '', weight: 1 },
        ];
        const hit = fields.find((field) => normalizeMatchText(field.value).includes(key));
        const exact = normalizeMatchText(node.label) === key;
        return hit
          ? {
              node,
              hitLabel: hit.label,
              excerpt: hit.value || node.label,
              score: hit.weight + (exact ? 4 : 0) + (node.weight >= 4 ? 1 : 0),
            }
          : null;
      })
      .filter(Boolean)
      .sort((a, b) => b!.score - a!.score)
      .slice(0, 6) as Array<{
        node: CourseKnowledgeNode;
        hitLabel: string;
        excerpt: string;
        score: number;
      }>;
  });
  const searchMatchNodeIds = computed(
    () => new Set(searchMatches.value.map((item) => item.node.id))
  );
  const selectedNodeStatus = computed(() => {
    const key = nodeStudyStatusKey();
    return key ? nodeStatuses.value[key] || {} : {};
  });
  const nodeStatusActions = computed(() => [
    {
      key: 'reviewed' as const,
      label: '已读证据',
      active: Boolean(selectedNodeStatus.value.reviewed),
    },
    {
      key: 'practice' as const,
      label: '加入复习',
      active: Boolean(selectedNodeStatus.value.practice),
    },
    {
      key: 'resource' as const,
      label: '需要资料',
      active: Boolean(selectedNodeStatus.value.resource),
    },
  ]);
  const closureActionMeta: Record<ClosureActionKey, { label: string; short: string; desc: string }> = {
    reviewed: {
      label: '打开课程内容',
      short: '证据',
      desc: '先阅读课堂内容，返回后再手动标记已读。',
    },
    practice: {
      label: '加入复习',
      short: '检查',
      desc: '把分层检查题加入复习安排。',
    },
    resource: {
      label: '申请资料',
      short: '资料',
      desc: '记录讲义、导图、练习和阅读清单需求。',
    },
  };
  const nodeClosureStats = computed(() => {
    const map = activeMap.value;
    if (!map) {
      return {
        total: 0,
        reviewed: 0,
        practice: 0,
        resource: 0,
        complete: 0,
        progress: 0,
      };
    }
    const summary = map.nodes.reduce(
      (acc, node) => {
        const status = nodeStatuses.value[`${map.type}:${node.id}`] || {};
        const doneCount =
          Number(Boolean(status.reviewed)) +
          Number(Boolean(status.practice)) +
          Number(Boolean(status.resource));
        acc.reviewed += Number(Boolean(status.reviewed));
        acc.practice += Number(Boolean(status.practice));
        acc.resource += Number(Boolean(status.resource));
        acc.complete += Number(doneCount === 3);
        return acc;
      },
      {
        total: map.nodes.length,
        reviewed: 0,
        practice: 0,
        resource: 0,
        complete: 0,
      }
    );
    return {
      ...summary,
      progress: Math.round(
        ((summary.reviewed + summary.practice + summary.resource) /
          Math.max(summary.total * 3, 1)) *
          100
      ),
    };
  });
  const selectedNodeClosure = computed(() => {
    const status = selectedNodeStatus.value;
    const actions = (Object.keys(closureActionMeta) as ClosureActionKey[]).map((key) => ({
      key,
      ...closureActionMeta[key],
      done: Boolean(status[key]),
      pending: status.pending === key && !status[key],
    }));
    const done = actions.filter((item) => item.done).length;
    return {
      actions,
      done,
      total: actions.length,
      progress: Math.round((done / Math.max(actions.length, 1)) * 100),
      missing: actions.filter((item) => !item.done),
    };
  });
  const nodeClosureQueue = computed(() => {
    const map = activeMap.value;
    if (!map || !course.value) return [];
    const actionOrder: ClosureActionKey[] = ['reviewed', 'practice', 'resource'];
    return map.nodes
      .map((node) => {
        const status = nodeStatuses.value[`${map.type}:${node.id}`] || {};
        const missingKey =
          actionOrder.find((key) => !status[key]) || null;
        const doneCount = actionOrder.filter((key) => status[key]).length;
        const mastery = node.mastery ?? 0;
        const relationCount = map.links.filter(
          (link) => link.source === node.id || link.target === node.id
        ).length;
        return {
          node,
          missingKey,
          doneCount,
          pendingKey: status.pending || '',
          mastery,
          masteryKnown: node.mastery !== undefined,
          relationCount,
          priority:
            Number(Boolean(missingKey)) * 100 +
            (100 - mastery) +
            relationCount * 2 +
            (node.weight < 4 ? 8 : 0),
        };
      })
      .filter((item) => item.missingKey)
      .sort((a, b) => b.priority - a.priority)
      .slice(0, 5)
      .map((item) => ({
        ...item,
        actionKey: item.missingKey as ClosureActionKey,
        action: closureActionMeta[item.missingKey as ClosureActionKey],
      }));
  });
  const selectedNodePopoverStyle = computed(() => {
    const node = selectedNode.value;
    if (!node) return {};
    const position = nodePosition(node);
    const baseLeft = (position.x / GRAPH_CANVAS.width) * 100;
    const baseTop = (position.y / GRAPH_CANVAS.height) * 100;
    const left = Math.max(8, Math.min(92, 50 + (baseLeft - 50) * canvasZoom.value));
    const top = Math.max(14, Math.min(88, 50 + (baseTop - 50) * canvasZoom.value));
    return {
      left: `calc(${left}% + ${canvasPan.value.x}px)`,
      top: `calc(${top}% + ${canvasPan.value.y}px)`,
    };
  });
  const chapterCount = computed(
    () => activeMap.value?.nodes.filter((node) => node.type === 'chapter').length || 0
  );
  const conceptCount = computed(
    () => activeMap.value?.nodes.filter((node) => node.type === 'concept').length || 0
  );
  const actionBadgeCount = computed(() =>
    structureBranches.value.reduce((sum, item) => sum + item.resourceBadges.length, 0)
  );
  const packageContext = computed(() => {
    const topic = queryText(route.query.topic);
    const packageId = queryText(route.query.packageId);
    const source = queryText(route.query.source);
    const packageSources = new Set([
      'resource-generation',
      'knowledge-map-audit',
      'course-agent-package-audit',
    ]);
    if (!packageId && !packageSources.has(source)) return null;
    return {
      topic: topic || selectedNode.value?.label || activeMap.value?.title || '课程资源包',
      packageId: packageId || 'local-preview',
      source,
      sourceLabel: source === 'resource-generation' ? '资源生成中心' : '课程图谱入口',
      nodeId: queryText(route.query.nodeId),
      nodeLabel: queryText(route.query.nodeLabel),
      mapType: queryText(route.query.mapType) as CourseKnowledgeMapType,
      resourceId: queryText(route.query.resourceId),
    };
  });
  const packageTarget = computed<PackageMatch | null>(() => {
    const context = packageContext.value;
    if (!context) return null;
    if (context.nodeId) {
      const exactMap = context.mapType
        ? maps.value.find((map) => map.type === context.mapType)
        : null;
      const candidates = exactMap ? [exactMap] : maps.value;
      const exact = candidates
        .flatMap((map) => map.nodes.map((node) => ({ map, node })))
        .find(({ node }) => node.id === context.nodeId);
      if (exact) return { ...exact, score: 99 };
    }
    if (context.nodeLabel) {
      const labelKey = normalizeMatchText(context.nodeLabel);
      const exact = maps.value
        .flatMap((map) => map.nodes.map((node) => ({ map, node })))
        .find(({ map, node }) => {
          const mapMatches = context.mapType ? map.type === context.mapType : true;
          return mapMatches && normalizeMatchText(node.label) === labelKey;
        });
      if (exact) return { ...exact, score: 88 };
    }
    const topicKey = normalizeMatchText(context.topic);
    let best: PackageMatch | null = null;
    maps.value.forEach((map: CourseKnowledgeMap) => {
      map.nodes.forEach((node) => {
        const labelKey = normalizeMatchText(node.label);
        const nodeText = normalizeMatchText(
          [
            node.label,
            node.detail,
            node.evidence?.join(' '),
            node.resources?.join(' '),
            node.checks?.join(' '),
            node.activities?.join(' '),
            node.outcomes?.join(' '),
            node.misconceptions?.join(' '),
            node.recommendedAction,
          ]
            .filter(Boolean)
            .join(' ')
        );
        let score = 0;
        if (labelKey && topicKey && labelKey === topicKey) score += 9;
        if (labelKey && topicKey && (labelKey.includes(topicKey) || topicKey.includes(labelKey))) score += 5;
        if (nodeText && topicKey && nodeText.includes(topicKey)) score += 3;
        score += Math.min(node.evidence?.length || 0, 3) * 0.35;
        score += Math.min(node.resources?.length || 0, 3) * 0.3;
        if (!best || score > best.score) best = { map, node, score };
      });
    });
    return best;
  });
  const packageConfidence = computed(() => {
    const score = packageTarget.value?.score || 0;
    if (score >= 8) return '高';
    if (score >= 4) return '中';
    return '待确认';
  });
  const packageVerificationCards = computed(() => {
    const targetNode = packageTarget.value?.node || selectedNode.value;
    const targetMap = packageTarget.value?.map || activeMap.value;
    if (!packageContext.value || !targetNode || !targetMap) return [];
    const evidenceCount = targetNode.evidence?.length || 0;
    const resourceCount = targetNode.resources?.length || 0;
    const checkCount = targetNode.checks?.length || 0;
    const neighborCount =
      targetMap.links.filter(
        (link: CourseKnowledgeMap['links'][number]) =>
          link.source === targetNode.id || link.target === targetNode.id
      ).length || 0;
    return [
      {
        key: 'node',
        label: '节点定位',
        value: targetNode.label,
        desc: `${targetMap.title} · 已关联到当前主题`,
        state: packageConfidence.value === '待确认' ? 'warning' : 'ready',
      },
      {
        key: 'evidence',
        label: '学习记录',
        value: evidenceCount ? '已找到' : '待补充',
        desc: evidenceCount ? targetNode.evidence?.[0] || '已关联学习记录' : '可以补充课堂片段或学习笔记',
        state: evidenceCount >= 2 ? 'ready' : 'warning',
      },
      {
        key: 'resources',
        label: '资源支撑',
        value: `${resourceCount} 项`,
        desc: resourceCount ? targetNode.resources?.[0] || '已连接资料资源' : '建议重新生成讲义、练习和导图',
        state: resourceCount >= 2 ? 'ready' : 'warning',
      },
      {
        key: 'checks',
        label: '检查闭环',
        value: `${checkCount || neighborCount} 个`,
        desc: checkCount
          ? targetNode.checks?.[0] || '已配置检查题'
          : `可沿 ${neighborCount} 条相邻关系生成分层自测`,
        state: checkCount ? 'ready' : 'warning',
      },
    ];
  });
  const packageAuditSteps = computed(() => {
    const targetNode = packageTarget.value?.node || selectedNode.value;
    if (!packageContext.value || !targetNode) return [];
    return [
      {
        step: '01',
        title: '锁定知识节点',
        desc: `资源包主题「${packageContext.value.topic}」已指向「${targetNode.label}」。`,
        state: packageConfidence.value === '待确认' ? 'warning' : 'ready',
      },
      {
        step: '02',
        title: '核对课堂依据',
        desc: selectedNodeEvidence.value[0] || targetNode.detail || '需要回到课堂笔记补齐定义、边界和例题。',
        state: (targetNode.evidence?.length || 0) >= 2 ? 'ready' : 'warning',
      },
      {
        step: '03',
        title: '验证资料产物',
        desc: targetNode.resources?.[0] || '检查生成包是否包含讲义、练习、导图和阅读清单。',
        state: (targetNode.resources?.length || 0) >= 2 ? 'ready' : 'warning',
      },
      {
        step: '04',
        title: '生成个性化下一步',
        desc: targetNode.recommendedAction || '把薄弱点、检查题和相邻路径同步给 AI 伴学。',
        state: 'ready',
      },
    ];
  });

  function nodeClass(node: CourseKnowledgeNode) {
    const selected = selectedNode.value;
    const packageNode = packageTarget.value?.node;
    const status = nodeStatuses.value[nodeStudyStatusKey(node)];
    const hasSearch = Boolean(keyword.value.trim());
    const isSearchHit = searchMatchNodeIds.value.has(node.id);
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
        weak: node.mastery !== undefined && node.mastery < 60,
        stable: node.mastery !== undefined && node.mastery >= 80,
        'package-target': packageContext.value && packageNode?.id === node.id,
        'search-hit': isSearchHit,
        'search-muted': hasSearch && !isSearchHit && !selectedNeighborIds.value.has(node.id),
        'status-reviewed': Boolean(status?.reviewed),
        'status-practice': Boolean(status?.practice),
        'status-resource': Boolean(status?.resource),
      },
    ];
  }

  function nodeAppearIndex(node: CourseKnowledgeNode) {
    if (selectedNode.value?.id === node.id) return 0;
    const index = visibleNodes.value.findIndex((item) => item.id === node.id);
    return Math.max(index, 0);
  }

  function linkClass(link: CourseKnowledgeMap['links'][number]) {
    const selected = selectedNode.value;
    const selectedId = selected?.id;
    const isSelectedLink = selectedLinkKey.value === linkKey(link);
    const hasSearch = Boolean(keyword.value.trim());
    const touchesSearchHit =
      searchMatchNodeIds.value.has(link.source) || searchMatchNodeIds.value.has(link.target);
    return [
      `link-${link.relation}`,
      {
        selected: isSelectedLink || selectedId === link.source || selectedId === link.target,
        'link-selected': isSelectedLink,
        'search-muted': hasSearch && !touchesSearchHit,
        dimmed: Boolean(
          selectedId && selected?.weight !== 4 && !isSelectedLink && selectedId !== link.source && selectedId !== link.target
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

  function masteryDisplay(value: number, known: boolean) {
    return known ? `${value}%` : '未评测';
  }

  function branchMasteryDisplay(branch: CourseStructureBranch) {
    const node = activeMap.value?.nodes.find((item) => item.id === branch.id);
    return node?.mastery === undefined ? '未评测' : `${node.mastery}%`;
  }

  function nodeSubtitle(node: CourseKnowledgeNode) {
    return `${nodeTypeLabel(node.type)} · ${node.mastery === undefined ? '未评测' : `${node.mastery}%`}`;
  }

  function nodeBoxWidth(node: CourseKnowledgeNode) {
    if (selectedNode.value?.id === node.id) return 196;
    if (node.weight >= 4) return 164;
    if (node.weight >= 3) return 152;
    return 140;
  }

  function nodeBoxHeight(node: CourseKnowledgeNode) {
    if (selectedNode.value?.id === node.id) return 76;
    return node.weight >= 4 ? 62 : 56;
  }

  function nodeFill(node: CourseKnowledgeNode) {
    if (selectedNode.value?.id === node.id) return '#ffffff';
    if (node.weight >= 4) return '#f7f8ff';
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
    return '#172033';
  }

  function hiddenNeighborCount(node: CourseKnowledgeNode) {
    const map = activeMap.value;
    if (!map) return 0;
    const relatedIds = new Set(
      map.links
        .filter((link) => link.source === node.id || link.target === node.id)
        .map((link) => (link.source === node.id ? link.target : link.source))
    );
    return Array.from(relatedIds).filter((id) => !visibleNodeIds.value.has(id)).length;
  }

  function relationShortLabel(relation: string) {
    if (relation === '前后置关系') return '前置';
    if (relation === '父子关系') return '归属';
    if (relation === '资料支撑') return '证据';
    if (relation === '任务驱动') return '任务';
    return '关联';
  }

  function graphLinkLabel(link: CourseKnowledgeMap['links'][number]) {
    const map = activeMap.value;
    const source = map?.nodes.find((node) => node.id === link.source)?.label || link.source;
    const target = map?.nodes.find((node) => node.id === link.target)?.label || link.target;
    return `${source}到${target}的${link.relation}`;
  }

  function linkLabelPosition(link: CourseKnowledgeMap['links'][number]) {
    const source = activeMap.value?.nodes.find((node) => node.id === link.source);
    const target = activeMap.value?.nodes.find((node) => node.id === link.target);
    if (!source || !target) return { x: 0, y: 0 };
    const sourcePosition = nodePosition(source);
    const targetPosition = nodePosition(target);
    return {
      x: (sourcePosition.x + targetPosition.x) / 2,
      y: (sourcePosition.y + targetPosition.y) / 2 - 8,
    };
  }

  function nodePosition(node: CourseKnowledgeNode): GraphNodePosition {
    return graphNodePositions.value.get(node.id) || { x: node.x, y: node.y };
  }

  function nodeEdgeAnchor(
    node: CourseKnowledgeNode,
    toward: GraphNodePosition
  ): GraphNodePosition {
    const position = nodePosition(node);
    const dx = toward.x - position.x;
    const dy = toward.y - position.y;
    if (!dx && !dy) return position;
    const halfWidth = nodeBoxWidth(node) / 2 + 7;
    const halfHeight = nodeBoxHeight(node) / 2 + 7;
    const scale = Math.min(
      Math.abs(dx) > 0 ? halfWidth / Math.abs(dx) : Number.POSITIVE_INFINITY,
      Math.abs(dy) > 0 ? halfHeight / Math.abs(dy) : Number.POSITIVE_INFINITY
    );
    return {
      x: position.x + dx * scale,
      y: position.y + dy * scale,
    };
  }

  function linkPath(link: CourseKnowledgeMap['links'][number]) {
    const source = activeMap.value?.nodes.find((node) => node.id === link.source);
    const target = activeMap.value?.nodes.find((node) => node.id === link.target);
    if (!source || !target) return '';
    const sourceCenter = nodePosition(source);
    const targetCenter = nodePosition(target);
    const sourcePosition = nodeEdgeAnchor(source, targetCenter);
    const targetPosition = nodeEdgeAnchor(target, sourceCenter);
    const dx = targetPosition.x - sourcePosition.x;
    const dy = targetPosition.y - sourcePosition.y;
    const pull = Math.max(50, Math.min(118, Math.abs(dx) * 0.22 + Math.abs(dy) * 0.14));
    const c1x = sourcePosition.x + dx * 0.34;
    const c2x = targetPosition.x - dx * 0.34;
    const c1y = sourcePosition.y + dy * 0.16 - pull * Math.sign(dx || 1) * 0.12;
    const c2y = targetPosition.y - dy * 0.16 + pull * Math.sign(dx || 1) * 0.12;
    return `M ${sourcePosition.x} ${sourcePosition.y} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${targetPosition.x} ${targetPosition.y}`;
  }

  function linkKey(link: CourseKnowledgeMap['links'][number]) {
    return `${link.source}::${link.target}::${link.relation}`;
  }

  function shortNodeLabel(label: string, limit = 9) {
    return label.length > limit ? `${label.slice(0, limit - 1)}…` : label;
  }

  function selectNode(node: CourseKnowledgeNode) {
    selectedNodeId.value = node.id;
    selectedLinkKey.value = '';
    canvasZoom.value = Math.min(canvasZoom.value, 1.08);
    canvasPan.value = { x: 0, y: 0 };
    persistSelectedNode();
    void expandNodeNeighbors(node);
  }

  function selectLink(link: CourseKnowledgeMap['links'][number]) {
    selectedLinkKey.value = linkKey(link);
    const source = activeMap.value?.nodes.find((node) => node.id === link.source);
    const target = activeMap.value?.nodes.find((node) => node.id === link.target);
    if (source && target && selectedNode.value?.id !== source.id && selectedNode.value?.id !== target.id) {
      selectedNodeId.value = target.id;
    }
  }

  function selectMap(type: CourseKnowledgeMapType) {
    if (!maps.value.some((item) => item.type === type)) {
      Message.warning('当前课程暂不支持该图谱类型');
      return;
    }
    activeType.value = type;
    activeRelation.value = '全部';
    selectedLinkKey.value = '';
    canvasPan.value = { x: 0, y: 0 };
  }

  function selectBranch(index: number) {
    const branch = structureBranches.value[index];
    const node = activeMap.value?.nodes.find((item) => item.id === branch?.id);
    if (node) selectNode(node);
  }

  function queryText(value: unknown) {
    if (Array.isArray(value)) return String(value[0] || '').trim();
    return typeof value === 'string' ? value.trim() : '';
  }

  function normalizeMatchText(value: string) {
    return value.toLowerCase().replace(/\s+/g, '').replace(/[「」《》、，。；：:：\-_/|()[\]{}]/g, '');
  }

  type CourseQueryValue = string | number | null | undefined;

  function compactQuery(query: Record<string, CourseQueryValue>): LocationQueryRaw {
    return Object.fromEntries(
      Object.entries(query).filter(([, value]) => value !== undefined && value !== null && value !== '')
    ) as LocationQueryRaw;
  }

  function nodeContextQuery(extra: Record<string, CourseQueryValue> = {}) {
    const node = selectedNode.value;
    return compactQuery({
      topic: node?.label || activeMap.value?.title,
      nodeId: node?.id,
      nodeLabel: node?.label,
      mapType: activeMap.value?.type,
      source: 'knowledge-map',
      ...extra,
    });
  }

  const actionTypeByClosureKey: Record<ClosureActionKey, CourseKnowledgeNodeActionType> = {
    reviewed: 'evidence_read',
    practice: 'review_queued',
    resource: 'resource_requested',
  };

  function studyStatusFromApi(
    state: CourseKnowledgeNodeActionState | undefined
  ): NodeStudyStatus {
    return {
      reviewed: Boolean(state?.evidenceRead),
      practice: Boolean(state?.reviewQueued),
      resource: Boolean(state?.resourceRequested),
      updatedAt: state?.updatedAt,
    };
  }

  function applyNodeActionStates(
    mapType: CourseKnowledgeMapType,
    states: Record<string, CourseKnowledgeNodeActionState>,
    replaceMap = false
  ) {
    const retained = replaceMap
      ? Object.fromEntries(
          Object.entries(nodeStatuses.value).filter(
            ([key]) => !key.startsWith(`${mapType}:`)
          )
        )
      : { ...nodeStatuses.value };
    Object.entries(states).forEach(([nodeId, state]) => {
      retained[`${mapType}:${nodeId}`] = studyStatusFromApi(state);
    });
    nodeStatuses.value = retained;
  }

  async function loadNodeActionStates(map = activeMap.value) {
    if (!course.value || !map) return;
    try {
      const response = await fetchCourseKnowledgeNodeActions(course.value.id, map.type);
      if (response.courseId !== course.value.id || response.mapType !== map.type) {
        throw new Error('节点动作范围与当前课程不一致');
      }
      applyNodeActionStates(map.type, response.states, true);
      actionsAvailable.value = true;
    } catch {
      applyNodeActionStates(map.type, {}, true);
      actionsAvailable.value = false;
      Message.error('节点学习状态暂时无法读取，请稍后重试');
    }
  }

  async function expandNodeNeighbors(node: CourseKnowledgeNode) {
    if (!course.value || !activeMap.value) return;
    const requestId = ++neighborRequestSequence;
    const courseId = course.value.id;
    const mapType = activeMap.value.type;
    try {
      const response = await fetchCourseKnowledgeNeighbors(courseId, node.id, mapType, 1);
      if (
        requestId !== neighborRequestSequence ||
        response.courseId !== courseId ||
        response.centerNodeId !== node.id ||
        activeMap.value?.type !== mapType
      ) {
        return;
      }
      const current = activeMap.value;
      const nodeById = new Map(current.nodes.map((item) => [item.id, item]));
      response.nodes.forEach((item) => nodeById.set(item.id, item));
      const linkByKey = new Map(
        current.links.map((item) => [linkKey(item), item])
      );
      response.links.forEach((item) => linkByKey.set(linkKey(item), item));
      maps.value = maps.value.map((item) =>
        item.type === mapType
          ? {
              ...item,
              nodes: Array.from(nodeById.values()),
              links: Array.from(linkByKey.values()),
            }
          : item
      );
    } catch {
      Message.warning(`暂时无法展开「${node.label}」的相邻知识点`);
    }
  }

  async function loadCourseGraph() {
    const courseId = String(route.params.courseId || '');
    const requestId = ++graphRequestSequence;
    graphLoading.value = true;
    graphError.value = '';
    actionsAvailable.value = false;
    nodeStatuses.value = {};
    try {
      const response = await fetchCourseKnowledgeGraph(courseId);
      if (requestId !== graphRequestSequence) return;
      if (response.courseId !== courseId) {
        throw new Error('课程图谱范围与当前课程不一致');
      }
      if (!response.maps.length) {
        throw new Error('当前课程还没有可用的知识图谱');
      }
      maps.value = response.maps;
      if (!response.maps.some((item) => item.type === activeType.value)) {
        activeType.value = response.maps[0].type;
      }
      applyIncomingNodeFromRoute();
      loadSelectedNodeForMap();
      if (!selectedNodeId.value || !activeMap.value?.nodes.some((node) => node.id === selectedNodeId.value)) {
        selectedNodeId.value =
          activeMap.value?.nodes.find((node) => node.weight >= 4)?.id ||
          activeMap.value?.nodes[0]?.id ||
          '';
      }
      await loadNodeActionStates(activeMap.value);
      if (selectedNode.value) await expandNodeNeighbors(selectedNode.value);
    } catch (error) {
      if (requestId !== graphRequestSequence) return;
      maps.value = [];
      nodeStatuses.value = {};
      const status = Number(
        (error as { response?: { status?: number } } | null)?.response?.status || 0
      );
      graphError.value =
        status === 404
          ? '未找到可访问的课程图谱，请确认你已加入这门课程。'
          : status === 422
            ? '课程标识或图谱类型无效，请返回课程列表后重新进入。'
            : error instanceof Error && error.message.startsWith('当前课程')
              ? error.message
              : '课程图谱加载失败，请稍后重试。';
    } finally {
      if (requestId === graphRequestSequence) graphLoading.value = false;
    }
  }

  function selectedNodeStorageKey() {
    if (!course.value || !activeMap.value) return '';
    return `zhixi:knowledge-selected-node:${course.value.id}:${activeMap.value.type}`;
  }

  function nodeStudyStatusKey(node = selectedNode.value) {
    if (!activeMap.value || !node) return '';
    return `${activeMap.value.type}:${node.id}`;
  }

  function persistSelectedNode() {
    const key = selectedNodeStorageKey();
    if (!key || typeof window === 'undefined') return;
    window.localStorage.setItem(key, selectedNodeId.value);
  }

  function loadSelectedNodeForMap() {
    const key = selectedNodeStorageKey();
    if (!key || typeof window === 'undefined' || !activeMap.value) return;
    const savedNodeId = window.localStorage.getItem(key);
    const recommended = recommendedNode.value?.node;
    if (
      savedNodeId &&
      activeMap.value.nodes.some((node) => node.id === savedNodeId)
    ) {
      selectedNodeId.value = savedNodeId;
      return;
    }
    if (!queryText(route.query.nodeId) && !queryText(route.query.nodeLabel) && !queryText(route.query.topic)) {
      if (recommended) selectedNodeId.value = recommended.id;
    }
  }

  async function updateNodeStatus(
    node: CourseKnowledgeNode,
    key: ClosureActionKey,
    value: boolean
  ) {
    const map = activeMap.value;
    if (!map || !course.value) return false;
    if (!actionsAvailable.value) {
      Message.error('节点学习状态服务暂时不可用，请刷新后重试');
      return false;
    }
    const statusKey = `${map.type}:${node.id}`;
    const current = nodeStatuses.value[statusKey] || {};
    if (current.pending) return false;
    nodeStatuses.value = {
      ...nodeStatuses.value,
      [statusKey]: {
        ...current,
        [key]: value,
        pending: key,
      },
    };
    try {
      const response = await setCourseKnowledgeNodeAction(
        course.value.id,
        node.id,
        map.type,
        actionTypeByClosureKey[key],
        value
      );
      if (response.courseId !== course.value.id || response.mapType !== map.type) {
        throw new Error('节点动作范围与当前课程不一致');
      }
      applyNodeActionStates(map.type, response.states);
      return true;
    } catch {
      nodeStatuses.value = {
        ...nodeStatuses.value,
        [statusKey]: current,
      };
      Message.error(`「${node.label}」学习状态保存失败，已恢复原状态`);
      return false;
    }
  }

  async function toggleNodeStatus(key: ClosureActionKey) {
    const node = selectedNode.value;
    if (!node) return;
    const current = nodeStatuses.value[nodeStudyStatusKey(node)] || {};
    const saved = await updateNodeStatus(node, key, !current[key]);
    if (saved) Message.success(`「${node.label}」学习状态已更新`);
  }

  async function runClosureAction(key: ClosureActionKey, node = selectedNode.value) {
    if (!node) return;
    if (selectedNode.value?.id !== node.id) {
      selectNode(node);
    }
    if (key === 'reviewed') {
      goCourseContent();
      return;
    }
    if (!(await updateNodeStatus(node, key, true))) return;
    if (key === 'practice') {
      askGraphAgent(`围绕「${node.label}」生成分层检查题、判分标准和错因回写模板`);
      return;
    }
    goResourceGenerator();
  }

  function continueClosureQueue() {
    const next = nodeClosureQueue.value[0];
    if (!next?.missingKey) {
      Message.success('当前图谱节点闭环已完成，可以切换其他图谱继续检查');
      return;
    }
    void runClosureAction(next.missingKey as ClosureActionKey, next.node);
  }

  function selectSearchMatch(node: CourseKnowledgeNode) {
    selectNode(node);
    centerNodeInCanvas(node, 0.48);
  }

  function centerNodeInCanvas(node = selectedNode.value, pull = 0.46) {
    if (!node) return;
    const position = nodePosition(node);
    canvasPan.value = {
      x: Math.round((GRAPH_CANVAS.centerX - position.x) * pull),
      y: Math.round((GRAPH_CANVAS.centerY - position.y) * pull),
    };
  }

  function packageAuditContextLines() {
    const context = packageContext.value;
    if (!context) return [];
    const target = packageTarget.value;
    return [
      `资源包主题：${context.topic}`,
      `资源包编号：${context.packageId}`,
      `资源包来源：${context.sourceLabel}`,
      target ? `匹配节点：${target.node.label}（${target.map.title}，置信度 ${packageConfidence.value}）` : '',
      packageVerificationCards.value.length
        ? `核验项：${packageVerificationCards.value
            .map((item) => `${item.label}${item.value}，${item.state === 'ready' ? '已具备依据' : '需复核'}`)
            .join('；')}`
        : '',
    ].filter(Boolean);
  }

  function focusPackageNode() {
    const target = packageTarget.value;
    if (!target) {
      Message.warning('当前资源包还没有匹配到图谱节点，请换关键词或回炉生成时补充主题');
      return;
    }
    activeType.value = target.map.type;
    activeRelation.value = '全部';
    keyword.value = '';
    selectedNodeId.value = target.node.id;
    Message.success(`已定位到「${target.node.label}」`);
  }

  function applyIncomingNodeFromRoute() {
    const requestedNodeId = queryText(route.query.nodeId);
    const requestedLabel = queryText(route.query.nodeLabel) || queryText(route.query.topic);
    const requestedMap = queryText(route.query.mapType) as CourseKnowledgeMapType;
    if (!requestedNodeId && !requestedLabel && !requestedMap) return;
    const candidateMaps = requestedMap
      ? maps.value.filter((map) => map.type === requestedMap)
      : maps.value;
    const match = candidateMaps
      .flatMap((map) => map.nodes.map((node) => ({ map, node })))
      .find(({ node }) => {
        if (requestedNodeId && node.id === requestedNodeId) return true;
        return requestedLabel && normalizeMatchText(node.label) === normalizeMatchText(requestedLabel);
      });
    if (!match) {
      if (requestedMap && maps.value.some((map) => map.type === requestedMap)) {
        activeType.value = requestedMap;
      }
      return;
    }
    activeType.value = match.map.type;
    selectedNodeId.value = match.node.id;
  }

  function askPackageAudit() {
    const context = packageContext.value;
    if (!context) return;
    askGraphAgent(
      `核验资源包「${context.topic}」是否覆盖当前节点的定义、边界、关系、练习和资料证据，并列出需要回炉生成的具体项`
    );
  }

  function generatePackageChecks() {
    const context = packageContext.value;
    if (!context) return;
    askGraphAgent(
      `基于资源包「${context.topic}」和当前节点生成 8 道分层核验题，标注每道题对应的证据、关系和常见误区`
    );
  }

  function goPackageBackfillGenerator() {
    if (!course.value) return;
    const context = packageContext.value;
    const target = packageTarget.value?.node || selectedNode.value;
    const auditItems = packageVerificationCards.value.filter((item) => item.state !== 'ready');
    const auditSummary = (auditItems.length ? auditItems : packageVerificationCards.value)
      .map((item) => `${item.label}:${item.desc}`)
      .join('；');
    router.push({
      name: 'StudentCourseResourceGenerator',
      params: { courseId: course.value.id },
      query: {
        subject: course.value.title,
        topic: context?.topic || target?.label || activeMap.value?.title,
        goal: [
          `围绕${target?.label || context?.topic || '当前知识点'}重新生成可核验资料包。`,
          `必须补齐课堂证据、图谱关系、检查题、误区纠正和回炉说明。`,
          context?.packageId ? `原资源包编号：${context.packageId}` : '',
        ]
          .filter(Boolean)
          .join(''),
        source: 'knowledge-map-audit',
        upstreamSource: context?.source,
        packageId: context?.packageId,
        nodeId: target?.id,
        nodeLabel: target?.label,
        mapType: packageTarget.value?.map.type || activeMap.value?.type,
        audit: auditSummary || '图谱节点已完成基础匹配，继续复核资料包的证据、关系、练习和误区覆盖。',
      },
    });
  }

  function changeZoom(delta: number) {
    canvasZoom.value = Math.min(1.34, Math.max(0.74, Number((canvasZoom.value + delta).toFixed(2))));
  }

  function resetCanvas() {
    canvasZoom.value = 1;
    canvasPan.value = { x: 0, y: 0 };
  }

  function centerSelectedNode() {
    centerNodeInCanvas(selectedNode.value, 0.5);
  }

  function handleCanvasWheel(event: WheelEvent) {
    const delta = event.deltaY > 0 ? -0.06 : 0.06;
    changeZoom(delta);
  }

  function beginCanvasPan(event: PointerEvent) {
    if (
      (event.target as Element | null)?.closest?.(
        '.graph-node, .graph-links path, .node-canvas-popover, button, input, a'
      )
    ) return;
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
    const packageLines = packageAuditContextLines();
    router.push(
      courseWorkspaceLocation(course.value.id, 'agent', {
        task: 'graph',
        forceAgent: 'retrieval_agent',
        source: packageContext.value ? 'knowledge-map-package-audit' : 'knowledge-map',
        topic: packageContext.value?.topic || node?.label || activeMap.value.title,
        nodeId: node?.id,
        nodeLabel: node?.label,
        mapType: activeMap.value.type,
        packageId: packageContext.value?.packageId,
        prompt: [
          `当前课程：${course.value.title}`,
          `当前图谱：${activeMap.value.title}`,
          node ? `当前节点：${node.label}（${node.type}，${selectedNodeMasteryLabel.value}）` : '',
          node?.detail ? `节点说明：${node.detail}` : '',
          selectedNodeEvidence.value.length ? `证据资料：${selectedNodeEvidence.value.join('；')}` : '',
          ...packageLines,
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
      query: nodeContextQuery({
        subject: course.value.title,
        goal: node
          ? `围绕${node.label}生成带证据清单、误区纠正、检查题和学习路径的个性化资料。`
          : `围绕${activeMap.value.title}生成课程图谱配套资料。`,
        source: packageContext.value ? 'knowledge-map-package-audit' : 'knowledge-map',
        upstreamSource: packageContext.value?.source,
        packageId: packageContext.value?.packageId,
      }),
    });
  }

  function goCourseContent() {
    if (!course.value) return;
    router.push(
      courseWorkspaceLocation(
        course.value.id,
        'content',
        nodeContextQuery({
          open: 'mind',
          source: 'knowledge-map',
        })
      )
    );
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

  function startRecommendedNode() {
    const node = recommendedNode.value?.node;
    if (!node) return;
    selectNode(node);
    centerNodeInCanvas(node, 0.5);
  }

  async function runRecommendationAction(key: string) {
    if (recommendedNode.value?.node && selectedNode.value?.id !== recommendedNode.value.node.id) {
      selectNode(recommendedNode.value.node);
    }
    if (key === 'evidence') {
      goCourseContent();
      return;
    }
    if (key === 'practice') {
      if (!(await updateNodeStatus(selectedNode.value!, 'practice', true))) return;
      askGraphAgent('基于当前推荐节点生成分层检查题，并给出判分标准和错因记录模板');
      return;
    }
    if (!(await updateNodeStatus(selectedNode.value!, 'resource', true))) return;
    goResourceGenerator();
  }

  function selectPathStep(nodeId: string) {
    const node = activeMap.value?.nodes.find((item) => item.id === nodeId);
    if (!node) return;
    selectNode(node);
  }

  function askPathTutor() {
    const node = selectedNode.value;
    if (!node) return;
    const pathLines = graphPathSteps.value.map(
      (item, index) =>
        `${index + 1}. ${item.phase}：${item.title}（${item.relation}，掌握状态 ${masteryDisplay(item.mastery, item.masteryKnown)}，证据：${item.evidence}，检查：${item.check}）`
    );
    askGraphAgent(
      [
        `沿当前节点「${node.label}」解释前置、当前、后续学习路径。`,
        '请把每个阶段拆成：先看什么证据、补什么资料、做哪道检查题、完成后如何判断通过。',
        `路径阶段：${pathLines.join('；')}`,
      ].join('\n')
    );
  }

  function generatePathResources() {
    if (!course.value || !selectedNode.value) return;
    router.push({
      name: 'StudentCourseResourceGenerator',
      params: { courseId: course.value.id },
      query: nodeContextQuery({
        subject: course.value.title,
        topic: `${selectedNode.value.label}学习路径`,
        goal: [
          `基于课程图谱节点「${selectedNode.value.label}」生成前置-当前-后续三段式学习包。`,
          `必须包含每段的课堂证据、资料讲义、检查题、误区提醒和通过标准。`,
          `路径阶段：${graphPathSteps.value
            .map((item) => `${item.phase}:${item.title}/${item.relation}/${masteryDisplay(item.mastery, item.masteryKnown)}`)
            .join('；')}`,
        ].join(''),
        source: 'knowledge-path',
        path: graphPathSteps.value.map((item) => `${item.phase}:${item.title}`).join('>'),
      }),
    });
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
      `掌握状态：${selectedNodeMasteryLabel.value}`,
      packageContext.value
        ? `资源包：${packageContext.value.topic}（${packageContext.value.packageId} / ${packageContext.value.sourceLabel}）`
        : '',
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
              `${index + 1}. ${item.relation}：${item.label}（掌握状态 ${masteryDisplay(item.mastery, item.masteryKnown)} / 关系强度 ${item.strength}%）`
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
      ...(packageContext.value
        ? [
            '',
            '## 资源包核验',
            ...packageVerificationCards.value.map(
              (item, index) =>
                `${index + 1}. ${item.label}：${item.value} - ${item.desc}（${item.state === 'ready' ? '通过' : '需复核'}）`
            ),
          ]
        : []),
      '',
      '## 完成标准',
      '- [ ] 已能复述节点定义、适用条件和边界。',
      '- [ ] 已用至少一条课堂证据支撑理解。',
      '- [ ] 已完成检查题并记录错因。',
      '- [ ] 已把错因或资料需求同步到 AI 伴学或资源生成中心。',
    ].join('\n');
  }

  function graphPathMarkdown() {
    if (!course.value || !selectedNode.value) return '';
    return [
      `# ${course.value.shortTitle}-${selectedNode.value.label}图谱学习路径`,
      '',
      `课程：${course.value.title}`,
      `图谱：${activeMap.value?.title || ''}`,
      `节点：${selectedNode.value.label}`,
      `掌握状态：${selectedNodeMasteryLabel.value}`,
      '',
      '## 路径概览',
      ...pathCoverageStats.value.map((item) => `- ${item.label}：${item.value}`),
      '',
      '## 分阶段学习动作',
      ...graphPathSteps.value.flatMap((item, index) => [
        `### ${index + 1}. ${item.phase}：${item.title}`,
        `- 关系：${item.relation} / 强度 ${item.strength}% / 掌握状态 ${masteryDisplay(item.mastery, item.masteryKnown)}`,
        `- 目标：${item.desc}`,
        `- 证据：${item.evidence}`,
        `- 资料：${item.resource}`,
        `- 检查：${item.check}`,
        '',
      ]),
      '## 闭环要求',
      '- [ ] 已按顺序完成每个阶段的证据阅读。',
      '- [ ] 已为薄弱阶段生成或补齐资料。',
      '- [ ] 已完成每个阶段的检查题并记录错因。',
      '- [ ] 已把仍未掌握的节点回到图谱继续追踪。',
    ].join('\n');
  }

  function downloadGraphPathPack() {
    if (!course.value || !selectedNode.value) return;
    const blob = new Blob([`${graphPathMarkdown()}\n`], {
      type: 'text/markdown;charset=utf-8',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${safeFilename(`${course.value.shortTitle}-${selectedNode.value.label}图谱学习路径`)}.md`;
    link.click();
    URL.revokeObjectURL(url);
    Message.success('图谱学习路径已下载');
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
      selectedNodeId.value =
        recommendedNode.value?.node.id ||
        map.nodes.find((node) => node.weight >= 4)?.id ||
        map.nodes[0]?.id ||
        '';
    }
    selectedLinkKey.value = '';
  });

  watch(activeRelation, () => {
    selectedLinkKey.value = '';
  });

  watch(
    () => route.params.courseId,
    () => {
      void loadCourseGraph();
    },
    { immediate: true }
  );

  watch(
    () => [route.query.nodeId, route.query.nodeLabel, route.query.mapType, route.query.topic],
    applyIncomingNodeFromRoute,
    { immediate: true }
  );

  watch(
    packageTarget,
    (target) => {
      if (!packageContext.value || !target) return;
      if (activeType.value !== target.map.type) {
        activeType.value = target.map.type;
      }
      selectedNodeId.value = target.node.id;
    },
    { immediate: true }
  );

  watch([visibleNodes, visibleLinks], ([nodes]) => {
    if (!nodes.length) return;
    if (!nodes.some((node) => node.id === selectedNodeId.value)) {
      selectedNodeId.value = nodes[0].id;
    }
  });
</script>

<template>
  <section v-if="graphLoading" class="knowledge-page graph-page-state" aria-live="polite">
    <strong>正在读取课程知识图谱</strong>
    <p>正在同步课程计划、资料关系和你的节点学习状态。</p>
  </section>
  <section v-else-if="graphError" class="knowledge-page graph-page-state graph-page-state--error" role="alert">
    <strong>课程图谱暂时无法显示</strong>
    <p>{{ graphError }}</p>
    <button type="button" @click="loadCourseGraph">重新加载</button>
  </section>
  <section v-else-if="course && activeMap" class="knowledge-page">
    <div class="graph-lab-shell">
      <header class="graph-topbar">
        <div class="graph-brand">
          <span class="graph-pill">
            <icon-mind-mapping /> 课程图谱
          </span>
          <div>
            <h1>{{ course.title }} · 知识图谱</h1>
            <p>{{ activeMap.description }}</p>
          </div>
        </div>
        <div class="graph-top-actions">
          <label class="graph-search">
            <icon-search />
            <input
              v-model="keyword"
              type="search"
              aria-label="搜索图谱节点或资料"
              placeholder="搜索节点或资料"
            />
          </label>
          <button type="button" class="ghost-action" @click="goCourseContent">课堂笔记</button>
          <button type="button" class="primary-action" @click="goResourceGenerator">
            <icon-file /> 生成资料
          </button>
        </div>
      </header>

      <section v-if="packageContext" class="package-audit-banner">
        <div class="package-audit-title">
          <span>资源关联检查</span>
          <strong>{{ packageContext.topic }}</strong>
          <p>
            {{ packageContext.sourceLabel }} ·
            {{ packageTarget ? `已关联 ${packageTarget.node.label}` : '请选择对应知识点' }}
          </p>
        </div>
        <div class="package-audit-cards">
          <article
            v-for="item in packageVerificationCards"
            :key="item.key"
            :class="`state-${item.state}`"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.desc }}</p>
          </article>
        </div>
        <div class="package-audit-actions">
          <button type="button" @click="focusPackageNode">定位节点</button>
          <button type="button" @click="askPackageAudit">检查内容</button>
          <button type="button" @click="goPackageBackfillGenerator">按问题重新生成</button>
        </div>
      </section>

      <div class="graph-workbench-grid">
        <aside class="map-catalog">
          <section class="catalog-card catalog-intro">
            <span>图谱目录</span>
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
              <em>{{ node.mastery === undefined ? '未评测' : `${node.mastery}%` }}</em>
            </button>
          </section>
        </aside>

        <div class="graph-work-area">
          <section v-if="selectedNode" class="mobile-node-summary" aria-label="当前节点快捷操作">
            <div class="mobile-node-summary__head">
              <span>{{ nodeTypeLabel(selectedNode.type) }} · {{ selectedNodeMasteryLabel }}</span>
              <strong>{{ selectedNode.label }}</strong>
              <p>{{ selectedNode.detail || activeMap.description }}</p>
            </div>
            <div class="mobile-node-summary__metrics">
              <em>{{ selectedNodeEvidence.length }} 条学习记录</em>
              <em>{{ selectedNodeResources.length }} 份学习资料</em>
              <em>{{ selectedLinks.length }} 个关联知识点</em>
            </div>
            <div class="mobile-node-summary__actions">
              <button type="button" @click="askGraphAgent('解释当前知识点的定义、前后置关系和参考资料')">问小智</button>
              <button type="button" @click="goResourceGenerator">生成资料</button>
              <button type="button" @click="downloadNodeStudyPack">学习包</button>
            </div>
          </section>

          <section class="mobile-path-strip" aria-label="移动端图谱路径推演">
            <div class="mobile-path-strip__head">
              <span>三段路径</span>
              <button type="button" @click="generatePathResources">生成路径资料</button>
            </div>
            <div class="mobile-path-strip__steps">
              <button
                v-for="item in graphPathSteps"
                :key="`mobile-path-${item.key}-${item.nodeId}`"
                type="button"
                :class="{ active: item.nodeId === selectedNode?.id }"
                @click="selectPathStep(item.nodeId)"
              >
                <span>{{ item.phase }}</span>
                <strong>{{ item.title }}</strong>
                <small>{{ item.relation }} · {{ masteryDisplay(item.mastery, item.masteryKnown) }}</small>
              </button>
            </div>
          </section>

          <section class="closure-command-center" aria-label="本次学习计划">
            <div class="closure-command-head">
              <div>
                <span>学习计划</span>
                <strong>本次学习安排</strong>
                <p>
                  记录“已读资料、加入复习、申请资料”三类下一步动作。
                </p>
              </div>
              <button type="button" @click="continueClosureQueue">继续下一步</button>
            </div>
            <div class="closure-progress-row">
              <div class="closure-progress-card">
                <span>安排进度</span>
                <strong>{{ nodeClosureStats.progress }}%</strong>
                <div class="closure-progress-track">
                  <i :style="{ width: `${nodeClosureStats.progress}%` }"></i>
                </div>
                <small>{{ nodeClosureStats.complete }}/{{ nodeClosureStats.total }} 个知识点已记录三类安排</small>
              </div>
              <div class="closure-stat-grid">
                <article>
                  <span>已读资料</span>
                  <b>{{ nodeClosureStats.reviewed }}</b>
                </article>
                <article>
                  <span>加入复习</span>
                  <b>{{ nodeClosureStats.practice }}</b>
                </article>
                <article>
                  <span>申请资料</span>
                  <b>{{ nodeClosureStats.resource }}</b>
                </article>
              </div>
              <div class="selected-closure-card">
                <span>当前节点</span>
                <strong>{{ selectedNode?.label || activeMap.title }}</strong>
                <div class="selected-closure-actions">
                  <button
                    v-for="item in selectedNodeClosure.actions"
                    :key="item.key"
                    type="button"
                    :class="{ done: item.done, pending: item.pending }"
                    :disabled="item.pending"
                    @click="runClosureAction(item.key)"
                  >
                    {{ item.done ? '已记录' : item.pending ? '保存中' : item.short }}
                  </button>
                </div>
              </div>
            </div>
            <div class="closure-queue-list">
              <button
                v-for="item in nodeClosureQueue"
                :key="`${item.node.id}-${item.missingKey}`"
                type="button"
                :class="{ active: item.node.id === selectedNode?.id, pending: item.pendingKey === item.missingKey }"
                :disabled="item.pendingKey === item.missingKey"
                @click="runClosureAction(item.actionKey, item.node)"
              >
                <span>{{ item.pendingKey === item.missingKey ? '保存中' : item.action.label }}</span>
                <strong>{{ item.node.label }}</strong>
                <small>
                  {{ masteryDisplay(item.mastery, item.masteryKnown) }} · 已记录 {{ item.doneCount }}/3 ·
                  {{ item.pendingKey === item.missingKey ? '正在保存状态' : item.action.desc }}
                </small>
              </button>
              <div v-if="!nodeClosureQueue.length" class="closure-queue-empty">
                当前图谱各知识点均已记录学习安排，可继续查看图谱或下载路径包。
              </div>
            </div>
          </section>

          <div class="graph-filter-row">
            <div class="relation-filter">
              <button
                v-for="item in relationSummary"
                :key="item.relation"
                type="button"
                :class="{ active: activeRelation === item.relation }"
                :aria-pressed="activeRelation === item.relation"
                @click="activeRelation = item.relation"
              >
                {{ item.relation }}
                <em>{{ item.count }}</em>
              </button>
            </div>
            <div class="graph-switches">
              <label>
                <input
                  v-model="showLearningPath"
                  type="checkbox"
                  aria-label="显示学习路径"
                />
                学习路径
              </label>
              <label>
                <input
                  v-model="showResourceLinks"
                  type="checkbox"
                  aria-label="显示资料关系"
                />
                资料关系
              </label>
              <div class="view-switch" aria-label="图谱视图">
                <button
                  type="button"
                  :class="{ active: viewMode === 'network' }"
                  :aria-pressed="viewMode === 'network'"
                  @click="viewMode = 'network'"
                >
                  图谱
                </button>
                <button
                  type="button"
                  :class="{ active: viewMode === 'structure' }"
                  :aria-pressed="viewMode === 'structure'"
                  @click="viewMode = 'structure'"
                >
                  脉络
                </button>
              </div>
            </div>
          </div>

          <section v-if="recommendedNode" class="today-recommendation">
            <div class="today-recommendation__main">
              <span>今日重点</span>
              <strong>建议先攻克「{{ recommendedNode.node.label }}」</strong>
              <p>
                {{ recommendedNode.node.recommendedAction || recommendedNode.node.detail || '沿图谱完成一次证据、检查、资料闭环。' }}
              </p>
              <div class="recommend-reasons">
                <em v-for="item in recommendationReasons" :key="item">{{ item }}</em>
              </div>
            </div>
            <div class="recommend-flow">
              <button
                v-for="item in recommendationActions"
                :key="item.key"
                type="button"
                :class="{ done: item.done }"
                @click="runRecommendationAction(item.key)"
              >
                <span>{{ item.label }}</span>
                <b>{{ item.done ? '已完成' : '开始' }}</b>
                <small>{{ item.desc }}</small>
              </button>
            </div>
            <button type="button" class="recommend-start" @click="startRecommendedNode">
              定位推荐节点
            </button>
          </section>

          <section v-if="keyword.trim()" class="graph-search-results" aria-label="图谱搜索结果">
            <div>
              <strong>搜索定位</strong>
              <span>{{ searchMatches.length ? `找到 ${searchMatches.length} 个相关节点` : '暂无命中节点' }}</span>
              <button type="button" @click="isolateSearchResults = !isolateSearchResults">
                {{ isolateSearchResults ? '显示全图' : '仅看相关' }}
              </button>
            </div>
            <button
              v-for="item in searchMatches"
              :key="item.node.id"
              type="button"
              :class="{ active: item.node.id === selectedNode?.id }"
              @click="selectSearchMatch(item.node)"
            >
              <b>{{ item.node.label }}</b>
              <em>{{ item.hitLabel }}</em>
              <small>{{ item.excerpt }}</small>
            </button>
          </section>

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

          <section class="graph-stage" aria-label="图谱工作区">
            <section class="graph-canvas-panel">
              <div class="graph-canvas-head">
                <div>
                  <span class="canvas-eyebrow">{{ activeMap.title }}</span>
                  <strong>{{ selectedNode?.label || course.shortTitle }}</strong>
                  <p>{{ visibleNodes.length }} 个节点 · {{ visibleLinks.length }} 条关系 · 点击节点展开关联知识点</p>
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
                  <span>课程</span>
                  <strong>{{ course.shortTitle }}</strong>
                </div>
                <div class="structure-trunk" aria-hidden="true"></div>
                <div class="structure-branches">
                  <article
                    v-for="(branch, index) in structureBranches"
                    :key="branch.id"
                  class="structure-branch"
                  :class="{ active: selectedNodeId === branch.id }"
                  :style="{ '--branch-offset': `${index * 4}px` }"
                  tabindex="0"
                  @click="selectBranch(index)"
                  @keydown.enter="selectBranch(index)"
                  @keydown.space.prevent="selectBranch(index)"
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
                      <strong>{{ branchMasteryDisplay(branch) }}</strong>
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
                @wheel.prevent="handleCanvasWheel"
                @dblclick="centerSelectedNode"
              >
                <svg
                  class="map-canvas"
                  :viewBox="`0 0 ${GRAPH_CANVAS.width} ${GRAPH_CANVAS.height}`"
                  preserveAspectRatio="xMidYMin meet"
                  role="group"
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

                  <g class="map-canvas-content" :transform="canvasTransform">
                    <g class="graph-links">
                      <g
                        v-for="link in visibleLinks"
                        :key="`${link.source}-${link.target}-${link.relation}`"
                      >
                        <path
                          class="graph-link-hit"
                          :d="linkPath(link)"
                          aria-hidden="true"
                          @click.stop="selectLink(link)"
                        />
                        <path
                          :d="linkPath(link)"
                          :class="linkClass(link)"
                          role="button"
                          tabindex="0"
                          :aria-label="graphLinkLabel(link)"
                          @click.stop="selectLink(link)"
                          @keydown.enter.stop="selectLink(link)"
                          @keydown.space.prevent.stop="selectLink(link)"
                        >
                          <title>{{ graphLinkLabel(link) }}</title>
                        </path>
                      </g>
                      <g
                        v-for="link in selectedLinks.slice(0, 4)"
                        :key="`label-${linkKey(link)}`"
                        class="graph-link-label"
                        :transform="`translate(${linkLabelPosition(link).x} ${linkLabelPosition(link).y})`"
                      >
                        <rect x="-20" y="-10" width="40" height="20" rx="10" />
                        <text text-anchor="middle" y="4">{{ relationShortLabel(link.relation) }}</text>
                      </g>
                    </g>

                    <g
                      v-for="node in visibleNodes"
                      :key="node.id"
                      :transform="`translate(${nodePosition(node).x - nodeBoxWidth(node) / 2} ${nodePosition(node).y - nodeBoxHeight(node) / 2})`"
                      :class="nodeClass(node)"
                      :style="{ '--node-delay': `${nodeAppearIndex(node) * 22}ms` }"
                      class="graph-node"
                      tabindex="0"
                      role="button"
                      :aria-label="`${node.label}，${nodeSubtitle(node)}`"
                      @click="selectNode(node)"
                      @keydown.enter="selectNode(node)"
                      @keydown.space.prevent="selectNode(node)"
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
                        v-if="node.weight < 4 && node.mastery !== undefined"
                        class="node-track"
                        x="16"
                        :y="nodeBoxHeight(node) - 8"
                        :width="nodeBoxWidth(node) - 32"
                        height="3"
                        rx="1.5"
                      />
                      <rect
                        v-if="node.weight < 4 && node.mastery !== undefined"
                        class="node-progress"
                        x="16"
                        :y="nodeBoxHeight(node) - 8"
                        :width="(nodeBoxWidth(node) - 32) * ((node.mastery || 0) / 100)"
                        height="3"
                        rx="1.5"
                        :fill="nodeStroke(node)"
                      />
                      <g
                        v-if="node.weight < 4 && node.mastery !== undefined"
                        class="node-mastery-badge"
                        :class="{
                          hot: (node.mastery || 0) < 60,
                          done: (node.mastery || 0) >= 80,
                        }"
                      >
                        <rect
                          :x="nodeBoxWidth(node) - 40"
                          y="-8"
                          width="34"
                          height="16"
                          rx="8"
                        />
                        <text
                          :x="nodeBoxWidth(node) - 23"
                          y="3"
                          text-anchor="middle"
                        >
                          {{ node.mastery }}%
                        </text>
                      </g>
                      <g
                        v-if="packageContext && packageTarget?.node.id === node.id"
                        class="node-package-badge"
                        :transform="`translate(${nodeBoxWidth(node) - 25} ${nodeBoxHeight(node) + 6})`"
                      >
                        <rect x="-30" y="-11" width="60" height="22" rx="11" />
                        <text x="0" y="4" text-anchor="middle">资源包</text>
                      </g>
                      <g
                        v-if="nodeStatuses[nodeStudyStatusKey(node)]"
                        class="node-status-badges"
                        :transform="`translate(14 ${nodeBoxHeight(node) + 10})`"
                      >
                        <circle
                          v-if="nodeStatuses[nodeStudyStatusKey(node)]?.reviewed"
                          cx="0"
                          cy="0"
                          r="5"
                        />
                        <circle
                          v-if="nodeStatuses[nodeStudyStatusKey(node)]?.practice"
                          cx="14"
                          cy="0"
                          r="5"
                        />
                        <circle
                          v-if="nodeStatuses[nodeStudyStatusKey(node)]?.resource"
                          cx="28"
                          cy="0"
                          r="5"
                        />
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
                        :y="selectedNode?.id === node.id || node.weight >= 4 ? 27 : 23"
                        text-anchor="middle"
                        :fill="nodeTextColor(node)"
                      >
                        {{ shortNodeLabel(node.label, selectedNode?.id === node.id ? 12 : 9) }}
                      </text>
                      <text
                        v-if="node.weight >= 4 || selectedNode?.id === node.id"
                        :x="nodeBoxWidth(node) / 2"
                        :y="selectedNode?.id === node.id ? 49 : 44"
                        text-anchor="middle"
                        class="node-subtitle"
                      >
                        {{ nodeSubtitle(node) }}
                      </text>
                      <text
                        v-else
                        :x="nodeBoxWidth(node) / 2 + 8"
                        y="40"
                        text-anchor="middle"
                        class="node-subtitle node-subtitle--compact"
                      >
                        {{ nodeSubtitle(node) }}
                      </text>
                      <g
                        v-if="hiddenNeighborCount(node)"
                        class="node-expand-count"
                        :transform="`translate(${nodeBoxWidth(node) + 12} ${nodeBoxHeight(node) / 2})`"
                      >
                        <circle r="14" />
                        <text text-anchor="middle" y="4">+{{ hiddenNeighborCount(node) }}</text>
                      </g>
                    </g>
                  </g>
                </svg>

                <div class="graph-minimap" aria-hidden="true">
                  <svg :viewBox="`0 0 ${GRAPH_CANVAS.width} ${GRAPH_CANVAS.height}`">
                    <path
                      v-for="link in visibleLinks"
                      :key="`mini-${linkKey(link)}`"
                      :d="linkPath(link)"
                    />
                    <circle
                      v-for="node in visibleNodes"
                      :key="`mini-${node.id}`"
                      :cx="nodePosition(node).x"
                      :cy="nodePosition(node).y"
                      :r="selectedNode?.id === node.id ? 18 : 10"
                      :class="{ selected: selectedNode?.id === node.id }"
                    />
                  </svg>
                </div>

                <div class="canvas-orbit-tools" aria-label="图谱画布工具">
                  <button type="button" @click.stop="changeZoom(0.08)">放大</button>
                  <button type="button" @click.stop="changeZoom(-0.08)">缩小</button>
                  <button type="button" @click.stop="centerSelectedNode">居中</button>
                  <button type="button" @click.stop="resetCanvas">复位</button>
                  <button
                    type="button"
                    :class="{ active: isolateSearchResults }"
                    @click.stop="isolateSearchResults = !isolateSearchResults"
                  >
                    命中
                  </button>
                </div>

                <div v-if="!visibleNodes.length" class="graph-empty">
                  <strong>没有匹配节点</strong>
                  <span>换一个关键词或切回全部关系后继续查看图谱。</span>
                </div>

                <div
                  v-if="selectedNode"
                  class="node-canvas-popover"
                  :style="selectedNodePopoverStyle"
                >
                  <div>
                    <span>{{ nodeTypeLabel(selectedNode.type) }} · {{ selectedNodeMasteryLabel }}</span>
                    <strong>{{ selectedNode.label }}</strong>
                  </div>
                  <div class="popover-metrics">
                    <em>{{ selectedNodeEvidence.length }} 条学习记录</em>
                    <em>{{ selectedNodeResources.length }} 份学习资料</em>
                    <em>{{ selectedLinks.length }} 个关联知识点</em>
                  </div>
                  <div class="popover-actions">
                    <button type="button" @click.stop="askGraphAgent('解释当前知识点的定义、前后置关系和参考资料')">问小智</button>
                    <button type="button" @click.stop="goResourceGenerator">生成资料</button>
                    <button type="button" @click.stop="downloadNodeStudyPack">学习包</button>
                  </div>
                </div>
              </div>

              <div v-if="viewMode === 'network'" class="map-canvas-tools">
                <div class="graph-legend">
                  <span class="legend-mastered">已掌握</span>
                  <span class="legend-learning">掌握中</span>
                  <span class="legend-weak">薄弱</span>
                  <span class="legend-unstarted">未学习</span>
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
              <section v-if="packageContext" class="package-insight-panel">
                <div class="package-insight-head">
                  <div>
                    <strong>资源关联检查</strong>
                    <span>{{ packageContext.topic }}</span>
                  </div>
                  <button type="button" @click="askPackageAudit">查看检查结果</button>
                </div>
                <div class="package-audit-timeline">
                  <article
                    v-for="item in packageAuditSteps"
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
                <div class="package-insight-actions">
                  <button type="button" @click="focusPackageNode">查看匹配节点</button>
                  <button type="button" @click="generatePackageChecks">生成理解检查题</button>
                  <button type="button" @click="goPackageBackfillGenerator">按问题重新生成</button>
                </div>
              </section>

              <section class="node-detail-section">
                <div class="node-detail-head">
                  <div>
                    <strong :class="`mastery-state mastery-state--${selectedMasteryState.tone}`">
                      {{ selectedMasteryState.label }}<template v-if="selectedNode?.mastery !== undefined"> · {{ selectedNodeMastery }}%</template>
                    </strong>
                    <h3>{{ selectedNode?.label || activeMap.title }}</h3>
                  </div>
                  <div class="mastery-ring" :style="{ '--mastery': `${selectedNodeMastery * 3.6}deg` }">
                    <span>{{ selectedNodeMasteryLabel }}</span>
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
                <div class="inspector-tabs" role="tablist" aria-label="节点详情">
                  <button
                    type="button"
                    role="tab"
                    :class="{ active: inspectorTab === 'evidence' }"
                    :aria-selected="inspectorTab === 'evidence'"
                    @click="inspectorTab = 'evidence'"
                  >
                    学习证据
                  </button>
                  <button
                    type="button"
                    role="tab"
                    :class="{ active: inspectorTab === 'resources' }"
                    :aria-selected="inspectorTab === 'resources'"
                    @click="inspectorTab = 'resources'"
                  >
                    关联资源
                  </button>
                  <button
                    type="button"
                    role="tab"
                    :class="{ active: inspectorTab === 'next' }"
                    :aria-selected="inspectorTab === 'next'"
                    @click="inspectorTab = 'next'"
                  >
                    下一步
                  </button>
                </div>
              </section>

              <section v-show="inspectorTab === 'next'" class="node-health-panel">
                <strong>节点状态</strong>
                <div class="node-status-toggles" aria-label="节点学习状态">
                  <button
                    v-for="item in nodeStatusActions"
                    :key="item.key"
                    type="button"
                    :class="{ active: item.active }"
                    :aria-pressed="item.active"
                    :disabled="selectedNodeStatus.pending === item.key"
                    @click="toggleNodeStatus(item.key)"
                  >
                    {{ item.label }}
                  </button>
                </div>
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

              <section v-if="inspectorTab === 'evidence' && selectedLink && selectedLinkNodes" class="link-audit-panel">
                <strong>关系详情</strong>
                <div class="link-audit-main">
                  <span>{{ selectedLink.relation }}</span>
                  <b>{{ selectedLinkNodes.source.label }} → {{ selectedLinkNodes.target.label }}</b>
                  <em>强度 {{ selectedLink.strength || 72 }}%</em>
                </div>
                <div class="link-audit-grid">
                  <article>
                    <span>前置资料</span>
                    <p>{{ selectedLinkNodes.source.evidence?.[0] || selectedLinkNodes.source.detail || '还没有可用的前置学习资料。' }}</p>
                  </article>
                  <article>
                    <span>理解检查</span>
                    <p>{{ selectedLinkNodes.target.checks?.[0] || selectedLinkNodes.target.recommendedAction || '可以生成一道理解检查题。' }}</p>
                  </article>
                </div>
                <button type="button" @click="askGraphAgent(`审计${selectedLink.relation}：${selectedLinkNodes.source.label}到${selectedLinkNodes.target.label}的证据是否充分`)">
                  请小智解释这条关系
                </button>
              </section>

              <section v-show="inspectorTab === 'next'" class="node-timeline-panel">
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

              <section v-show="inspectorTab === 'next'" class="path-decision-panel">
                <div class="path-decision-head">
                  <strong>学习路径</strong>
                  <button type="button" @click="generatePathResources">生成资料</button>
                </div>
                <button
                  v-for="item in graphPathSteps"
                  :key="`decision-${item.key}-${item.nodeId}`"
                  type="button"
                  class="path-decision-item"
                  :class="{ active: item.nodeId === selectedNode?.id }"
                  @click="selectPathStep(item.nodeId)"
                >
                  <span>{{ item.phase }}</span>
                  <b>{{ item.title }}</b>
                  <em>{{ item.relation }} · {{ masteryDisplay(item.mastery, item.masteryKnown) }}</em>
                </button>
              </section>

              <section v-if="inspectorTab === 'resources' && nodeStudyPack" class="study-pack-panel">
                <div class="study-pack-head">
                  <div>
                    <strong>节点学习包</strong>
                    <span>{{ nodeStudyPack.nodeType }} · {{ selectedNodeMasteryLabel }}</span>
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

              <section v-show="inspectorTab === 'evidence'" class="evidence-matrix-panel">
                <strong>参考资料</strong>
                <article v-for="item in evidenceRows" :key="item.id" class="evidence-row">
                  <span>{{ item.id }}</span>
                  <div>
                    <b>{{ item.title }}</b>
                    <small>{{ item.source }}</small>
                  </div>
                </article>
              </section>

              <section
                v-if="selectedNodeOutcomes.length || selectedNodeMisconceptions.length"
                class="node-mastery-panel"
              >
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

              <section v-if="selectedNodeChecks.length" class="node-check-panel">
                <strong>检查题</strong>
                <ul class="check-list">
                  <li v-for="item in selectedNodeChecks" :key="item">{{ item }}</li>
                </ul>
              </section>

              <section v-if="selectedNodeActivities.length" class="node-activity-panel">
                <strong>课堂动作</strong>
                <div class="activity-list">
                  <p v-for="item in selectedNodeActivities" :key="item">{{ item }}</p>
                </div>
              </section>

              <section v-if="inspectorTab === 'next' && selectedNeighbors.length" class="node-neighbor-panel">
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

              <section class="node-action-panel">
                <button
                  type="button"
                  class="node-action-primary"
                  @click="askGraphAgent('围绕当前薄弱点开始针对性学习，先解释证据，再给一道检查题')"
                >
                  开始针对性学习
                </button>
                <button type="button" class="node-action-secondary" @click="askGraphAgent('解释当前节点和先修关系')">
                  <icon-robot /> 问小智
                </button>
              </section>
            </aside>
          </section>

          <section class="path-inspector-panel" aria-label="图谱学习路径推演">
            <div class="path-inspector-head">
              <div>
                <span>路径推演</span>
                <strong>{{ selectedNode?.label || activeMap.title }} 学习路径推演</strong>
                <p>把当前知识点拆成前置确认、当前攻克、后续迁移三段，并绑定证据、资料和检查题。</p>
              </div>
              <div class="path-stats">
                <article v-for="item in pathCoverageStats" :key="item.label">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </article>
              </div>
            </div>

            <div class="path-step-grid">
              <article
                v-for="(item, index) in graphPathSteps"
                :key="`${item.key}-${item.nodeId}-${index}`"
                class="path-step-card"
                :class="[`path-step-card--${item.key}`, { active: item.nodeId === selectedNode?.id }]"
              >
                <button type="button" class="path-step-node" @click="selectPathStep(item.nodeId)">
                  <span>{{ item.phase }}</span>
                  <strong>{{ item.title }}</strong>
                  <small>{{ item.relation }} · {{ item.strength }}%</small>
                </button>
                <div class="path-step-body">
                  <p>{{ item.desc }}</p>
                  <div class="path-step-meta">
                    <span>{{ masteryDisplay(item.mastery, item.masteryKnown) }}</span>
                    <span>{{ item.resource }}</span>
                  </div>
                  <div class="path-step-evidence">
                    <b>证据</b>
                    <span>{{ item.evidence }}</span>
                  </div>
                  <div class="path-step-check">
                    <b>检查</b>
                    <span>{{ item.check }}</span>
                  </div>
                </div>
              </article>
            </div>

            <div class="path-inspector-actions">
              <button type="button" @click="askPathTutor">AI 解释路径</button>
              <button type="button" @click="generatePathResources">生成路径资料</button>
              <button type="button" @click="downloadGraphPathPack">下载路径包</button>
            </div>
          </section>
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

  .graph-page-state {
    display: grid;
    min-height: 420px;
    place-content: center;
    justify-items: center;
    gap: 10px;
    border: 1px solid #e7ecf6;
    border-radius: 28px;
    background: #fff;
    text-align: center;

    strong {
      font-size: 22px;
    }

    p {
      margin: 0;
      color: #65718a;
    }

    button {
      margin-top: 8px;
      padding: 9px 18px;
      border: 0;
      border-radius: 10px;
      background: #5367f8;
      color: #fff;
      cursor: pointer;
    }
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
  .package-audit-banner,
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
    transition: border-color 160ms ease, box-shadow 160ms ease;

    &:focus-within {
      border-color: #94a3b8;
      box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.08);
    }

    input {
      width: 100%;
      min-width: 0;
      border: 0;
      outline: 0 !important;
      box-shadow: none !important;
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

  .package-audit-banner {
    display: grid;
    grid-template-columns: minmax(220px, 0.32fr) minmax(0, 1fr) 104px;
    gap: 14px;
    align-items: stretch;
    margin: -4px 0 16px;
    padding: 16px;
    border: 1px solid #dce7ff;
    border-radius: 22px;
    background:
      linear-gradient(135deg, rgba(244, 248, 255, 0.96), rgba(255, 255, 255, 0.98)),
      radial-gradient(circle at 0 0, rgba(67, 111, 245, 0.14), transparent 34%);
    box-shadow: 0 16px 36px rgba(45, 73, 160, 0.09);
  }

  .package-audit-title {
    min-width: 0;
    display: grid;
    align-content: center;
    gap: 5px;

    span {
      color: #5878f5;
      font-size: 10px;
      font-weight: 900;
      letter-spacing: 0.13em;
    }

    strong {
      overflow: hidden;
      color: #16213a;
      font-size: 20px;
      line-height: 1.25;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    p {
      margin: 0;
      overflow: hidden;
      color: #6f7d93;
      font-size: 12px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .package-audit-cards {
    min-width: 0;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 9px;
  }

  .package-audit-cards article {
    min-width: 0;
    padding: 10px 11px;
    border: 1px solid #e5ecf8;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.86);

    span,
    strong,
    p {
      display: block;
      min-width: 0;
    }

    span {
      color: #8190a7;
      font-size: 10px;
      font-weight: 900;
    }

    strong {
      margin-top: 4px;
      overflow: hidden;
      color: #24304a;
      font-size: 15px;
      line-height: 1.2;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    p {
      display: -webkit-box;
      margin: 5px 0 0;
      overflow: hidden;
      color: #728097;
      font-size: 10px;
      line-height: 1.45;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }

    &.state-ready {
      border-color: #ccefd9;
      background: #f4fff8;

      strong {
        color: #237c4c;
      }
    }

    &.state-warning {
      border-color: #ffe1b8;
      background: #fff8ef;

      strong {
        color: #cf731e;
      }
    }
  }

  .package-audit-actions {
    display: grid;
    gap: 8px;
    align-content: center;

    button {
      height: 32px;
      border: 1px solid #d6e2ff;
      border-radius: 11px;
      color: #2f68df;
      background: #fff;
      font-size: 11px;
      font-weight: 900;
      cursor: pointer;

      &:hover {
        color: #fff;
        background: #4468f2;
      }
    }
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
    transition: opacity 0.18s ease, stroke 0.18s ease, stroke-width 0.18s ease;
  }

  .graph-links path.graph-link-hit {
    stroke: transparent;
    stroke-width: 16;
    opacity: 1;
    pointer-events: stroke;
  }

  .graph-links path:not(.graph-link-hit):focus-visible {
    stroke: #1d4ed8;
    stroke-width: 4;
    opacity: 1;
    outline: none;
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
    stroke-width: 3;
    opacity: 1;
  }

  .graph-links .dimmed {
    opacity: 0.2;
  }

  .graph-node {
    cursor: pointer;
    outline: none;
    transition: opacity 0.18s ease;
    animation: graph-node-pop 180ms ease both;
    animation-delay: var(--node-delay, 0ms);

    .node-body {
      transition: filter 0.18s ease, stroke-width 0.18s ease, transform 0.18s ease;
      transform-box: fill-box;
      transform-origin: center;
      animation: graph-node-body-in 220ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
      animation-delay: var(--node-delay, 0ms);
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
      font-size: 12px;
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
      filter: drop-shadow(0 12px 14px rgba(65, 109, 244, 0.18));
    }

    &.package-target .node-body {
      stroke: #7d5cf2;
      stroke-width: 3.6;
    }

    &.related:not(.selected) {
      opacity: 0.92;
    }

    &.dimmed {
      opacity: 0.38;
    }
  }

  .graph-node:focus-visible .node-body {
    stroke: #1d4ed8;
    stroke-width: 3;
  }

  .node-package-badge {
    pointer-events: none;

    rect {
      fill: #f3efff;
      stroke: #cbbdff;
      stroke-width: 1.2;
    }

    text {
      fill: #6e50d8;
      font-size: 10px;
      font-weight: 900;
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

  .package-insight-panel {
    padding: 12px;
    border: 1px solid #dce7ff !important;
    border-radius: 16px;
    background:
      linear-gradient(135deg, rgba(241, 246, 255, 0.96), rgba(255, 255, 255, 0.96)),
      radial-gradient(circle at 100% 0, rgba(118, 96, 216, 0.12), transparent 28%);
  }

  .package-insight-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 10px;

    div {
      min-width: 0;
    }

    strong {
      margin: 0 !important;
      color: #24304a !important;
    }

    span {
      display: block;
      margin-top: 3px;
      overflow: hidden;
      color: #7c889b;
      font-size: 10px;
      font-weight: 800;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    button {
      width: auto !important;
      min-height: 30px !important;
      margin: 0 !important;
      padding: 0 10px !important;
      border-color: #cfe0ff !important;
      color: #2f68df !important;
      background: #fff !important;
      font-size: 10px !important;
      font-weight: 900;
    }
  }

  .package-audit-timeline {
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
      background: #dce6fb;
      content: '';
    }

    article {
      position: relative;
      z-index: 1;
      display: grid;
      grid-template-columns: 28px minmax(0, 1fr);
      gap: 9px;
    }

    span {
      width: 28px;
      height: 28px;
      display: grid;
      place-items: center;
      border: 1px solid #cfe0ff;
      border-radius: 50%;
      color: #2f68df;
      background: #fff;
      font-size: 9px;
      font-weight: 900;
    }

    b {
      display: block;
      color: #26334d;
      font-size: 12px;
    }

    p {
      display: -webkit-box;
      margin-top: 3px !important;
      overflow: hidden;
      color: #738096 !important;
      font-size: 11px !important;
      line-height: 1.55 !important;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }

    .state-warning span {
      border-color: #ffd6a1;
      color: #d46f1d;
      background: #fff8ef;
    }
  }

  .package-insight-actions {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 7px;
    margin-top: 10px;

    button {
      min-height: 32px !important;
      margin: 0 !important;
      padding: 0 7px !important;
      font-size: 10px !important;
      font-weight: 900;
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

  .path-decision-panel {
    display: grid;
    gap: 8px;
  }

  .path-decision-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;

    strong {
      margin-bottom: 0;
    }

    button {
      width: auto;
      min-height: 28px;
      margin: 0;
      padding: 0 10px;
      border-color: #cfe0ff;
      color: #2f68df;
      background: #fff;
      font-size: 10px;
      font-weight: 900;
      white-space: nowrap;
    }
  }

  .path-decision-item {
    min-width: 0;
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr);
    gap: 5px 8px;
    align-items: center;
    padding: 9px 10px;
    text-align: left;

    &.active {
      border-color: #b9c9ff;
      background: #f4f7ff;
    }

    span {
      grid-row: span 2;
      width: 36px;
      height: 36px;
      display: grid;
      place-items: center;
      border-radius: 12px;
      color: #2c7a62;
      background: #eef9f4;
      font-size: 10px;
      font-weight: 900;
    }

    b,
    em {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    b {
      color: #24304a;
      font-size: 12px;
    }

    em {
      color: #7b879b;
      font-size: 10px;
      font-style: normal;
      font-weight: 800;
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

  .today-recommendation {
    display: grid;
    grid-template-columns: minmax(240px, 0.9fr) minmax(360px, 1.1fr) auto;
    gap: 12px;
    align-items: stretch;
    padding: 14px 16px;
    border-bottom: 1px solid #e5edf8;
    background:
      linear-gradient(135deg, rgba(244, 249, 255, 0.98), rgba(255, 255, 255, 0.96)),
      radial-gradient(circle at 0 0, rgba(67, 116, 255, 0.12), transparent 28%);
  }

  .today-recommendation__main {
    min-width: 0;
    display: grid;
    align-content: center;
    gap: 6px;
    padding: 14px;
    border: 1px solid #dfe9fa;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.9);

    span {
      color: #4774ff;
      font-size: 10px;
      font-weight: 900;
      letter-spacing: 0.14em;
    }

    strong {
      overflow: hidden;
      color: #14203a;
      font-size: 18px;
      line-height: 1.25;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    p {
      display: -webkit-box;
      margin: 0;
      overflow: hidden;
      color: #63718a;
      font-size: 12px;
      line-height: 1.55;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }
  }

  .recommend-reasons {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;

    em {
      padding: 4px 8px;
      border-radius: 999px;
      color: #d07120;
      background: #fff6ea;
      font-size: 10px;
      font-style: normal;
      font-weight: 900;
    }
  }

  .recommend-flow {
    min-width: 0;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 9px;
  }

  .recommend-flow button {
    min-width: 0;
    display: grid;
    gap: 5px;
    padding: 12px;
    border: 1px solid #dfe8f8;
    border-radius: 15px;
    color: #34435f;
    background: #fff;
    cursor: pointer;
    text-align: left;

    &:hover {
      border-color: #b7c9ff;
      background: #f4f7ff;
    }

    &.done {
      border-color: #bfe8d1;
      background: #f3fff8;

      b {
        color: #278052;
      }
    }

    span,
    b,
    small {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: #6b7890;
      font-size: 10px;
      font-weight: 900;
    }

    b {
      color: #2f68df;
      font-size: 14px;
    }

    small {
      color: #758299;
      font-size: 10px;
      line-height: 1.4;
    }
  }

  .recommend-start {
    align-self: stretch;
    min-width: 94px;
    border: 0;
    border-radius: 15px;
    color: #fff;
    background: #425fe8;
    box-shadow: 0 12px 24px rgba(66, 95, 232, 0.2);
    font-size: 12px;
    font-weight: 900;
    cursor: pointer;
  }

  .closure-command-center {
    display: grid;
    gap: 12px;
    padding: 14px 16px;
    border-bottom: 1px solid #e5edf8;
    background:
      linear-gradient(135deg, rgba(250, 252, 255, 0.98), rgba(245, 250, 255, 0.94)),
      radial-gradient(circle at 100% 0, rgba(42, 132, 116, 0.12), transparent 30%);
  }

  .closure-command-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;

    > div {
      min-width: 0;
    }

    span {
      display: block;
      color: #1f8a7a;
      font-size: 10px;
      font-weight: 900;
      letter-spacing: 0.14em;
    }

    strong {
      display: block;
      margin-top: 4px;
      color: #14203a;
      font-size: 17px;
      font-weight: 900;
    }

    p {
      margin: 4px 0 0;
      color: #66758d;
      font-size: 12px;
      line-height: 1.55;
    }

    button {
      flex: 0 0 auto;
      height: 38px;
      padding: 0 15px;
      border: 0;
      border-radius: 13px;
      color: #fff;
      background: #178b78;
      box-shadow: 0 10px 20px rgba(23, 139, 120, 0.18);
      font-size: 12px;
      font-weight: 900;
      cursor: pointer;
    }
  }

  .closure-progress-row {
    display: grid;
    grid-template-columns: minmax(220px, 0.8fr) minmax(260px, 0.8fr) minmax(260px, 1fr);
    gap: 10px;
    align-items: stretch;
  }

  .closure-progress-card,
  .selected-closure-card,
  .closure-stat-grid article {
    min-width: 0;
    border: 1px solid #dde9f4;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 10px 24px rgba(33, 48, 75, 0.05);
  }

  .closure-progress-card {
    display: grid;
    gap: 7px;
    padding: 12px;

    span,
    small {
      color: #718098;
      font-size: 11px;
      font-weight: 800;
    }

    strong {
      color: #14203a;
      font-size: 24px;
      line-height: 1;
    }
  }

  .closure-progress-track {
    height: 7px;
    overflow: hidden;
    border-radius: 999px;
    background: #e8eef6;

    i {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #178b78, #4f7df3);
    }
  }

  .closure-stat-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;

    article {
      display: grid;
      align-content: center;
      gap: 5px;
      padding: 12px;
      text-align: center;
    }

    span {
      color: #718098;
      font-size: 10px;
      font-weight: 900;
    }

    b {
      color: #1f8a7a;
      font-size: 22px;
    }
  }

  .selected-closure-card {
    display: grid;
    gap: 9px;
    padding: 12px;

    span {
      color: #718098;
      font-size: 10px;
      font-weight: 900;
    }

    strong {
      overflow: hidden;
      color: #14203a;
      font-size: 15px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .selected-closure-actions {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 7px;

    button {
      height: 32px;
      border: 1px solid #dfe8f4;
      border-radius: 11px;
      color: #4b5d78;
      background: #fff;
      font-size: 11px;
      font-weight: 900;
      cursor: pointer;

      &.pending {
        border-color: #ffd7a3;
        color: #bd671d;
        background: #fff8ef;
      }

      &.done {
        border-color: #bfe8d1;
        color: #247b51;
        background: #f2fff7;
      }
    }
  }

  .closure-queue-list {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 8px;

    button,
    .closure-queue-empty {
      min-width: 0;
      min-height: 86px;
      padding: 11px;
      border: 1px solid #dfe8f4;
      border-radius: 15px;
      background: rgba(255, 255, 255, 0.9);
      text-align: left;
    }

    button {
      display: grid;
      gap: 5px;
      cursor: pointer;

      &:hover,
      &.active {
        border-color: #bcd2ff;
        background: #f4f8ff;
      }

      &.pending {
        border-color: #ffd7a3;
        background: #fff8ef;
      }
    }

    span,
    strong,
    small {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    span {
      color: #1f8a7a;
      font-size: 10px;
      font-weight: 900;
      white-space: nowrap;
    }

    strong {
      color: #14203a;
      font-size: 13px;
      white-space: nowrap;
    }

    small {
      display: -webkit-box;
      color: #718098;
      font-size: 10px;
      line-height: 1.45;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }
  }

  .closure-queue-empty {
    display: grid;
    place-items: center;
    color: #607089;
    font-size: 12px;
    font-weight: 800;
    text-align: center;
  }

  .mobile-node-summary,
  .mobile-path-strip {
    display: none;
  }

  .graph-search-results {
    display: grid;
    grid-template-columns: 150px repeat(6, minmax(0, 1fr));
    gap: 8px;
    align-items: stretch;
    padding: 12px 16px;
    border-bottom: 1px solid #edf2f8;
    background: #fbfdff;

    > div,
    button {
      min-width: 0;
      border: 1px solid #e5ecf8;
      border-radius: 13px;
      background: #fff;
    }

    > div {
      display: grid;
      align-content: center;
      gap: 4px;
      padding: 10px 12px;

      strong {
        color: #1f2b45;
        font-size: 13px;
      }

      span {
        color: #7a879b;
        font-size: 11px;
      }

      button {
        justify-self: start;
        min-height: 24px;
        padding: 0 9px;
        border-radius: 999px;
        color: #2f68df;
        background: #edf4ff;
        font-size: 10px;
        font-weight: 900;
      }
    }

    button {
      display: grid;
      gap: 4px;
      padding: 10px;
      color: #56647b;
      cursor: pointer;
      text-align: left;

      &.active,
      &:hover {
        border-color: #b9ccff;
        background: #f3f7ff;
      }
    }

    b,
    em,
    small {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    b {
      color: #24304a;
      font-size: 12px;
    }

    em {
      color: #2f68df;
      font-size: 10px;
      font-style: normal;
      font-weight: 900;
    }

    small {
      color: #7f8ba0;
      font-size: 10px;
    }
  }

  .graph-command-deck {
    display: grid !important;
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

  .path-inspector-panel {
    padding: 16px;
    border-bottom: 1px solid #e5edf8;
    background:
      linear-gradient(180deg, #f8fbff 0%, #f3f8ff 100%),
      radial-gradient(circle at 8% 4%, rgba(44, 142, 111, 0.12), transparent 26%),
      radial-gradient(circle at 94% 6%, rgba(224, 144, 59, 0.1), transparent 24%);
  }

  .path-inspector-head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(360px, 0.46fr);
    gap: 14px;
    align-items: stretch;
    margin-bottom: 12px;

    > div:first-child {
      min-width: 0;
      padding: 15px;
      border: 1px solid #e3ebf6;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.9);
    }

    span,
    strong,
    p {
      display: block;
      min-width: 0;
    }

    span {
      color: #2c7a62;
      font-size: 10px;
      font-weight: 900;
      letter-spacing: 0.13em;
    }

    strong {
      margin-top: 5px;
      overflow: hidden;
      color: #15203a;
      font-size: 19px;
      line-height: 1.28;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    p {
      display: -webkit-box;
      margin: 8px 0 0;
      overflow: hidden;
      color: #64728a;
      font-size: 12px;
      line-height: 1.65;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }
  }

  .path-stats {
    min-width: 0;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;

    article {
      min-width: 0;
      display: grid;
      align-content: center;
      gap: 5px;
      padding: 12px 10px;
      border: 1px solid #e4ebf6;
      border-radius: 15px;
      background: rgba(255, 255, 255, 0.9);
    }

    span {
      overflow: hidden;
      color: #7d8aa1;
      font-size: 10px;
      font-weight: 900;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      color: #1f2b45;
      font-size: 17px;
      line-height: 1.1;
      white-space: nowrap;
    }
  }

  .path-step-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .path-step-card {
    min-width: 0;
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    overflow: hidden;
    border: 1px solid #e1e9f5;
    border-radius: 16px;
    background: #fff;
    box-shadow: 0 12px 28px rgba(36, 53, 92, 0.06);

    &.active {
      border-color: #b7c8ff;
      box-shadow: 0 16px 30px rgba(66, 104, 214, 0.12);
    }
  }

  .path-step-card--before .path-step-node {
    background: #f3fbf6;
  }

  .path-step-card--current .path-step-node {
    background: #f5f7ff;
  }

  .path-step-card--after .path-step-node {
    background: #fff8ef;
  }

  .path-step-node {
    width: 100%;
    min-height: 82px;
    display: grid;
    gap: 4px;
    align-content: center;
    justify-items: start;
    margin: 0;
    padding: 14px;
    border: 0;
    border-radius: 0;
    color: #17213a;
    cursor: pointer;
    text-align: left;

    span,
    strong,
    small {
      display: block;
      max-width: 100%;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: #62728d;
      font-size: 10px;
      font-weight: 900;
    }

    strong {
      color: #17213a;
      font-size: 15px;
      line-height: 1.3;
    }

    small {
      color: #6d7b92;
      font-size: 11px;
      font-weight: 800;
    }
  }

  .path-step-body {
    min-width: 0;
    display: grid;
    gap: 10px;
    padding: 13px 14px 14px;

    p {
      display: -webkit-box;
      margin: 0;
      overflow: hidden;
      color: #5e6c83;
      font-size: 12px;
      line-height: 1.6;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }
  }

  .path-step-meta {
    display: grid;
    grid-template-columns: 76px minmax(0, 1fr);
    gap: 7px;

    span {
      min-width: 0;
      overflow: hidden;
      padding: 6px 8px;
      border-radius: 10px;
      color: #52617b;
      background: #f6f8fc;
      font-size: 10px;
      font-weight: 900;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .path-step-evidence,
  .path-step-check {
    min-width: 0;
    display: grid;
    grid-template-columns: 36px minmax(0, 1fr);
    gap: 8px;
    align-items: start;
    padding: 9px;
    border: 1px solid #eef2f8;
    border-radius: 12px;
    background: #fbfcff;

    b {
      color: #2c7a62;
      font-size: 10px;
      font-weight: 900;
    }

    span {
      display: -webkit-box;
      overflow: hidden;
      color: #627086;
      font-size: 11px;
      line-height: 1.55;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }
  }

  .path-step-check b {
    color: #c27026;
  }

  .path-inspector-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
    justify-content: flex-end;
    margin-top: 12px;

    button {
      min-height: 34px;
      padding: 0 14px;
      border: 1px solid #dce6f6;
      border-radius: 11px;
      color: #394761;
      background: rgba(255, 255, 255, 0.94);
      font-size: 12px;
      font-weight: 900;
      cursor: pointer;

      &:first-child {
        border-color: #3f67e7;
        color: #fff;
        background: #4f6df5;
        box-shadow: 0 10px 18px rgba(79, 109, 245, 0.18);
      }
    }
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
    height: clamp(620px, calc(100vh - 260px), 820px);
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
    stroke-width: 1.8;
    cursor: pointer;
    pointer-events: stroke;
  }

  .graph-work-area .graph-links .link-父子关系,
  .graph-work-area .graph-links .link-前后置关系 {
    stroke: #6d9fe8;
    stroke-width: 2.4;
  }

  .graph-work-area .graph-links .link-关联关系 {
    stroke: #aab7c9;
  }

  .graph-work-area .graph-links .link-资料支撑 {
    stroke: #68bd91;
    stroke-width: 2.2;
  }

  .graph-work-area .graph-links .link-任务驱动 {
    stroke: #e8a453;
    stroke-width: 2.2;
  }

  .graph-work-area .graph-links .selected {
    stroke: #416df4;
    stroke-width: 3.2;
  }

  .graph-work-area .graph-links .link-selected {
    stroke: #255fe8;
    stroke-width: 4;
    filter: drop-shadow(0 4px 6px rgba(47, 104, 223, 0.18));
  }

  .graph-work-area .graph-links .search-muted {
    opacity: 0.12;
  }

  .graph-work-area .graph-node.selected .node-body {
    stroke: #355ff2;
    stroke-width: 2.6;
  }

  .graph-work-area .graph-node.search-hit .node-body {
    stroke: #2f68df;
    stroke-dasharray: 5 4;
  }

  .graph-work-area .graph-node.search-muted {
    opacity: 0.22;
  }

  .graph-work-area .graph-node.status-practice .node-body {
    filter: drop-shadow(0 10px 11px rgba(226, 132, 45, 0.18));
  }

  .node-status-badges {
    pointer-events: none;

    circle {
      fill: #2f68df;
      stroke: #fff;
      stroke-width: 2;

      &:nth-child(2) {
        fill: #e88d32;
      }

      &:nth-child(3) {
        fill: #2c9a66;
      }
    }
  }

  .graph-work-area .canvas-orbit-tools {
    display: none !important;
    position: absolute;
    top: 18px;
    right: 18px;
    z-index: 3;
    gap: 7px;
    padding: 8px;
    border: 1px solid rgba(205, 218, 240, 0.92);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.9);
    box-shadow: 0 14px 32px rgba(30, 44, 78, 0.12);
    backdrop-filter: blur(12px);

    button {
      width: 52px;
      height: 30px;
      border: 1px solid #e0e7f3;
      border-radius: 10px;
      color: #4b5a74;
      background: #fff;
      font-size: 11px;
      font-weight: 900;
      cursor: pointer;

      &:hover,
      &.active {
        border-color: #b7c9ff;
        color: #2f68df;
        background: #edf4ff;
      }
    }
  }

  .node-canvas-popover {
    position: absolute;
    z-index: 2;
    width: min(282px, calc(100% - 24px));
    display: none;
    gap: 10px;
    padding: 12px;
    border: 1px solid rgba(195, 209, 241, 0.92);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.94);
    box-shadow: 0 16px 34px rgba(28, 42, 79, 0.14);
    transform: translate(-50%, calc(-100% - 16px));
    backdrop-filter: blur(12px);
    pointer-events: auto;

    span,
    strong {
      display: block;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: #5878f5;
      font-size: 10px;
      font-weight: 900;
    }

    strong {
      margin-top: 3px;
      color: #17213a;
      font-size: 15px;
    }
  }

  .popover-metrics,
  .popover-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .popover-metrics em {
    padding: 4px 7px;
    border-radius: 999px;
    color: #60708a;
    background: #f2f6fc;
    font-size: 10px;
    font-style: normal;
    font-weight: 800;
  }

  .popover-actions button {
    height: 28px;
    padding: 0 9px;
    border: 1px solid #dbe5f5;
    border-radius: 9px;
    color: #35435c;
    background: #fff;
    font-size: 11px;
    font-weight: 900;
    cursor: pointer;

    &:hover {
      border-color: #c3d4ff;
      color: #2f68df;
      background: #f2f6ff;
    }
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

  .node-status-toggles {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 7px;
    margin-bottom: 9px;

    button {
      min-height: 30px !important;
      margin: 0 !important;
      padding: 0 6px !important;
      border-color: #e2e9f5 !important;
      color: #69778e !important;
      background: #fbfcff !important;
      font-size: 10px !important;
      font-weight: 900;

      &.active {
        border-color: #b9ccff !important;
        color: #2f68df !important;
        background: #f1f6ff !important;
      }
    }
  }

  .link-audit-panel {
    padding: 12px;
    border: 1px solid #dce7ff !important;
    border-radius: 16px;
    background:
      linear-gradient(135deg, rgba(241, 246, 255, 0.96), rgba(255, 255, 255, 0.96)),
      radial-gradient(circle at 0 0, rgba(47, 104, 223, 0.11), transparent 30%);
  }

  .link-audit-main {
    display: grid;
    gap: 5px;
    margin-bottom: 9px;

    span,
    b,
    em {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: #2f68df;
      font-size: 10px;
      font-weight: 900;
    }

    b {
      color: #1f2b45;
      font-size: 13px;
    }

    em {
      color: #65748c;
      font-size: 10px;
      font-style: normal;
      font-weight: 800;
    }
  }

  .link-audit-grid {
    display: grid;
    gap: 7px;

    article {
      padding: 9px;
      border: 1px solid #e4ebf8;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.86);
    }

    span {
      display: block;
      margin-bottom: 4px;
      color: #2c7a62;
      font-size: 10px;
      font-weight: 900;
    }

    p {
      display: -webkit-box;
      overflow: hidden;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
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

    .today-recommendation {
      grid-template-columns: 1fr;
    }

    .graph-search-results {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .path-inspector-head,
    .path-step-grid {
      grid-template-columns: 1fr;
    }

    .package-audit-banner {
      grid-template-columns: 1fr;
    }

    .package-audit-actions {
      grid-template-columns: repeat(3, minmax(0, 1fr));
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

    .package-audit-cards {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .path-inspector-head {
      grid-template-columns: 1fr;
    }

    .path-stats {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .closure-progress-row,
    .closure-queue-list {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 640px) {
    .graph-work-area {
      order: -1;
    }

    .map-catalog {
      order: 2;
    }

    .graph-workbench-grid .graph-tabs {
      grid-template-columns: 1fr;
    }

    .stat-strip {
      flex-wrap: wrap;
    }

    .graph-command-deck {
      grid-template-columns: 1fr;
    }

    .graph-search-results {
      grid-template-columns: 1fr;
    }

    .today-recommendation {
      padding: 12px;
    }

    .recommend-flow {
      grid-template-columns: 1fr;
    }

    .recommend-start {
      min-height: 40px;
    }

    .closure-command-head {
      align-items: stretch;
      flex-direction: column;

      button {
        width: 100%;
      }
    }

    .closure-progress-row,
    .closure-stat-grid,
    .selected-closure-actions,
    .closure-queue-list {
      grid-template-columns: 1fr;
    }

    .mobile-node-summary,
    .mobile-path-strip {
      display: grid;
      gap: 10px;
      padding: 12px;
      border-bottom: 1px solid #e7edf7;
      background: #fff;
    }

    .mobile-node-summary {
      border-top: 1px solid #e7edf7;
    }

    .mobile-node-summary__head {
      display: grid;
      gap: 5px;

      span {
        color: #2f68df;
        font-size: 11px;
        font-weight: 900;
      }

      strong {
        color: #14203a;
        font-size: 18px;
        line-height: 1.25;
      }

      p {
        display: -webkit-box;
        margin: 0;
        overflow: hidden;
        color: #66758d;
        font-size: 12px;
        line-height: 1.55;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 2;
      }
    }

    .mobile-node-summary__metrics,
    .mobile-node-summary__actions,
    .mobile-path-strip__steps {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 7px;
    }

    .mobile-node-summary__metrics em {
      min-width: 0;
      padding: 7px 8px;
      border-radius: 11px;
      color: #607089;
      background: #f5f8fc;
      font-size: 11px;
      font-style: normal;
      font-weight: 900;
      text-align: center;
    }

    .mobile-node-summary__actions button,
    .mobile-path-strip__head button,
    .mobile-path-strip__steps button {
      border: 1px solid #dfe8f4;
      border-radius: 12px;
      background: #fff;
      cursor: pointer;
    }

    .mobile-node-summary__actions button {
      height: 36px;
      color: #2f68df;
      font-size: 12px;
      font-weight: 900;
    }

    .mobile-path-strip__head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;

      span {
        color: #14203a;
        font-size: 14px;
        font-weight: 900;
      }

      button {
        height: 34px;
        padding: 0 12px;
        color: #fff;
        background: #178b78;
        font-size: 12px;
        font-weight: 900;
      }
    }

    .mobile-path-strip__steps button {
      min-width: 0;
      display: grid;
      gap: 3px;
      padding: 9px;
      text-align: left;

      &.active {
        border-color: #bcd2ff;
        background: #f4f8ff;
      }

      span,
      strong,
      small {
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      span {
        color: #2f68df;
        font-size: 10px;
        font-weight: 900;
      }

      strong {
        color: #14203a;
        font-size: 12px;
      }

      small {
        color: #718098;
        font-size: 10px;
      }
    }

    .node-canvas-popover {
      left: 12px !important;
      right: 12px;
      top: auto !important;
      bottom: 12px;
      transform: none;
    }

    .path-inspector-panel {
      padding: 12px;
    }

    .path-inspector-head strong {
      white-space: normal;
    }

    .path-stats,
    .path-step-meta {
      grid-template-columns: 1fr;
    }

    .path-inspector-actions {
      justify-content: stretch;

      button {
        flex: 1 1 100%;
      }
    }

    .package-audit-cards,
    .package-audit-actions,
    .package-insight-actions {
      grid-template-columns: 1fr;
    }

    .map-canvas-viewport {
      height: 430px;
      overflow: auto;
    }

    .graph-work-area .map-canvas {
      min-width: 720px;
    }

    .canvas-orbit-tools {
      position: sticky;
      top: 10px;
      right: auto;
      left: 10px;
      width: max-content;
      grid-auto-flow: column;
      grid-template-columns: none;
    }
  }

  /* Page refinement: keep the graph as the primary product surface. */
  .knowledge-page {
    --zy-brand: #4f46e5;
    --zy-brand-soft: rgba(99, 102, 241, 0.1);
    --zy-text: #101828;
    --zy-muted: #667085;
    --zy-border: rgba(15, 23, 42, 0.08);
    animation: knowledge-page-enter 180ms ease both;
  }

  .graph-lab-shell {
    overflow: visible;
    padding: 16px;
    border-color: var(--zy-border);
    border-radius: 20px;
    background: #f7f9ff;
    box-shadow: none;
  }

  .graph-topbar {
    margin-bottom: 12px;
  }

  .graph-lab-shell .graph-brand {
    align-items: flex-start;
    gap: 12px;
  }

  .graph-pill {
    height: 34px;
    padding: 0 12px;
    border: 1px solid rgba(99, 102, 241, 0.14);
    color: var(--zy-brand);
    background: #ffffff;
    box-shadow: none;
    font-size: 13px;
  }

  .graph-lab-shell .graph-brand h1 {
    color: var(--zy-text);
    font-size: 23px;
    font-weight: 800;
  }

  .graph-lab-shell .graph-brand p {
    max-width: 820px;
    color: var(--zy-muted);
    font-size: 13px;
    line-height: 1.6;
  }

  .graph-lab-shell .graph-top-actions {
    gap: 8px;
  }

  .graph-search {
    height: 38px;
    border-color: var(--zy-border);
    background: #ffffff;
    box-shadow: none;
  }

  .graph-lab-shell .graph-search {
    flex: 1 1 190px;
    min-width: 180px;
  }

  .ghost-action,
  .primary-action {
    height: 36px;
    border-radius: 999px;
    transition: border-color 160ms ease, background 160ms ease, color 160ms ease, transform 160ms ease;
  }

  .ghost-action:hover,
  .primary-action:hover {
    transform: translateY(-1px);
  }

  .primary-action {
    background: var(--zy-brand);
    box-shadow: 0 10px 22px rgba(79, 70, 229, 0.14);
  }

  .catalog-intro,
  .focus-chip-board,
  .mobile-path-strip,
  .closure-command-center,
  .today-recommendation,
  .path-inspector-panel,
  .guided-path,
  .node-canvas-popover,
  .node-mastery-panel,
  .node-check-panel,
  .node-activity-panel {
    display: none !important;
  }

  .graph-workbench-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .map-catalog {
    position: static;
    display: block;
  }

  .map-catalog .catalog-card {
    display: none;
  }

  .graph-workbench-grid .graph-tabs {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 8px;
    border: 0;
    border-radius: 0;
    background: transparent;
    overflow: visible;
  }

  .graph-workbench-grid .graph-tabs button {
    min-height: 50px;
    height: auto;
    justify-items: start;
    padding: 10px 12px;
    border-color: var(--zy-border);
    border-radius: 14px;
    border-right: 1px solid var(--zy-border);
    background: #ffffff;
    box-shadow: none;
    transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
  }

  .graph-workbench-grid .graph-tabs button:hover {
    transform: translateY(-1px);
  }

  .graph-workbench-grid .graph-tabs button.active {
    border-color: rgba(99, 102, 241, 0.24);
    background: #f6f7ff;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  }

  .graph-workbench-grid .graph-tabs button.active::after {
    background: var(--zy-brand);
  }

  .graph-workbench-grid .graph-tabs span {
    font-size: 13px;
  }

  .graph-workbench-grid .graph-tabs em {
    font-size: 10px;
  }

  .catalog-card {
    padding: 14px;
    border-color: var(--zy-border);
    border-radius: 16px;
    box-shadow: none;
  }

  .catalog-card > strong {
    color: var(--zy-text);
    font-size: 14px;
  }

  .weak-node {
    min-height: 34px;
    margin-top: 7px;
    border-color: var(--zy-border);
    background: #ffffff;
  }

  .graph-work-area {
    border-color: var(--zy-border);
    border-radius: 18px;
    box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05);
  }

  .graph-work-area .graph-filter-row {
    align-items: center;
    padding: 10px 12px;
  }

  .relation-filter {
    max-width: 100%;
    overflow-x: auto;
    flex-wrap: nowrap;
    scrollbar-width: none;
  }

  .relation-filter::-webkit-scrollbar {
    display: none;
  }

  .relation-filter button,
  .view-switch button {
    flex: 0 0 auto;
    height: 28px;
    border-color: var(--zy-border);
    background: #ffffff;
  }

  .relation-filter button.active,
  .view-switch button.active {
    border-color: rgba(99, 102, 241, 0.2);
    color: var(--zy-brand);
    background: #f4f6ff;
  }

  .graph-work-area .graph-stage {
    grid-template-columns: minmax(0, 1fr) 294px;
    min-height: 0;
    padding: 10px;
    background: #f7f9ff;
  }

  .graph-work-area .graph-canvas-panel,
  .graph-work-area .map-insights {
    border: 1px solid var(--zy-border);
    border-radius: 16px;
    box-shadow: none;
  }

  .graph-work-area .graph-canvas-head {
    min-height: 56px;
    padding: 10px 14px;
  }

  .graph-work-area .graph-canvas-head strong {
    color: var(--zy-text);
    font-size: 19px;
  }

  .canvas-eyebrow {
    color: var(--zy-brand) !important;
    letter-spacing: 0 !important;
  }

  .stat-strip span {
    border-color: var(--zy-border);
    background: #ffffff;
  }

  .map-canvas-viewport {
    height: clamp(480px, calc(100vh - 330px), 570px);
    background:
      linear-gradient(rgba(79, 70, 229, 0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(79, 70, 229, 0.04) 1px, transparent 1px),
      #fbfdff;
    background-size: 28px 28px;
  }

  .graph-work-area .canvas-orbit-tools {
    top: 14px;
    right: 14px;
    gap: 6px;
    border-color: var(--zy-border);
    border-radius: 14px;
    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.07);
  }

  .canvas-orbit-tools button {
    width: 48px;
    height: 28px;
    border-color: var(--zy-border);
    border-radius: 9px;
  }

  .graph-work-area .map-canvas-tools {
    left: 14px;
    right: 14px;
    bottom: 14px;
    padding: 9px 10px;
    border-color: var(--zy-border);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
    backdrop-filter: blur(8px);
  }

  .graph-quick-actions button {
    border-radius: 999px;
  }

  .graph-work-area .map-insights {
    max-height: clamp(500px, calc(100vh - 300px), 620px);
    padding: 12px;
    overflow: auto;
    background: #ffffff;
  }

  .map-insights section + section {
    margin-top: 12px;
    padding-top: 12px;
  }

  .node-detail-head {
    grid-template-columns: minmax(0, 1fr) 54px;
  }

  .mastery-ring {
    width: 50px;
    height: 50px;
  }

  .node-health-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
  }

  .node-health-grid article {
    padding: 8px;
    border-color: var(--zy-border);
    background: #fbfdff;
  }

  .path-decision-item,
  .neighbor-button,
  .map-insights button {
    border-color: var(--zy-border);
    transition: border-color 160ms ease, background 160ms ease, color 160ms ease;
  }

  .node-action-panel {
    display: grid;
    gap: 7px;
  }

  .node-action-panel button:first-of-type {
    border-color: rgba(99, 102, 241, 0.22);
    color: #ffffff;
    background: var(--zy-brand);
  }

  .graph-search-results {
    grid-template-columns: 130px repeat(4, minmax(0, 1fr));
    padding: 10px 14px;
  }

  @keyframes knowledge-page-enter {
    from {
      opacity: 0;
      transform: translateY(8px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes graph-node-pop {
    from {
      opacity: 0;
    }

    to {
      opacity: 1;
    }
  }

  @keyframes graph-node-body-in {
    from {
      transform: translateY(5px);
    }

    to {
      transform: translateY(0);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .knowledge-page,
    .graph-node,
    .graph-node .node-body,
    .graph-workbench-grid .graph-tabs button,
    .ghost-action,
    .primary-action {
      animation: none;
      transition: none;
    }
  }

  @media (max-width: 1320px) {
    .graph-lab-shell .graph-topbar {
      grid-template-columns: minmax(0, 1fr) minmax(390px, 0.42fr);
      gap: 14px;
    }

    .graph-lab-shell .graph-top-actions {
      width: auto;
      min-width: 0;
    }
  }

  @media (max-width: 1180px) {
    .graph-lab-shell .graph-topbar {
      grid-template-columns: 1fr;
    }

    .graph-lab-shell .graph-top-actions {
      width: 100%;
    }

    .graph-workbench-grid {
      grid-template-columns: 1fr;
    }

    .graph-workbench-grid .graph-tabs {
      display: flex;
      overflow-x: auto;
      padding-bottom: 2px;
      scrollbar-width: none;
    }

    .graph-workbench-grid .graph-tabs::-webkit-scrollbar {
      display: none;
    }

    .graph-workbench-grid .graph-tabs button {
      flex: 0 0 168px;
    }

    .graph-work-area .graph-stage {
      grid-template-columns: minmax(0, 1fr) 270px;
      gap: 10px;
    }

    .graph-work-area .map-insights {
      max-height: clamp(460px, calc(100vh - 292px), 560px);
    }
  }

  @media (max-width: 980px) {
    .map-catalog {
      position: static;
    }

    .graph-workbench-grid {
      grid-template-columns: 1fr;
    }

    .graph-work-area .graph-stage {
      grid-template-columns: 1fr;
    }

    .graph-work-area .map-insights {
      max-height: none;
    }
  }

  /* 2026 demo pass: move the graph itself higher in the first viewport. */
  .graph-lab-shell .graph-topbar {
    gap: 10px;
    margin-bottom: 8px;
    padding: 11px 14px 10px;
  }

  .graph-lab-shell .graph-brand {
    gap: 12px;
  }

  .graph-pill {
    height: 30px;
    padding: 0 11px;
    border-width: 0;
    font-size: 12px;
    box-shadow: 0 6px 14px rgba(68, 97, 225, 0.14);
  }

  .graph-lab-shell .graph-brand h1 {
    margin-bottom: 2px;
    font-size: 20px;
    line-height: 1.2;
  }

  .graph-lab-shell .graph-brand p {
    max-width: 720px;
    font-size: 12px;
    line-height: 1.45;
    -webkit-line-clamp: 1;
  }

  .graph-lab-shell .graph-search {
    height: 34px;
  }

  .graph-top-actions .ghost-action {
    display: none;
  }

  .primary-action {
    height: 34px;
    padding: 0 12px;
  }

  .graph-workbench-grid {
    gap: 8px;
  }

  .graph-workbench-grid .graph-tabs {
    gap: 6px;
  }

  .graph-workbench-grid .graph-tabs button {
    min-height: 34px;
    padding: 6px 10px;
    border-radius: 12px;
  }

  .graph-workbench-grid .graph-tabs span {
    font-size: 12px;
  }

  .graph-workbench-grid .graph-tabs em {
    display: none;
  }

  .graph-work-area .graph-filter-row {
    min-height: 36px;
    padding: 5px 8px;
  }

  .relation-filter button,
  .view-switch button {
    height: 26px;
    padding: 0 10px;
    font-size: 12px;
  }

  .graph-switches label {
    font-size: 12px;
  }

  .graph-work-area .graph-stage {
    gap: 8px;
    padding: 6px;
  }

  .graph-work-area .graph-canvas-head {
    min-height: 38px;
    padding: 6px 10px;
  }

  .graph-work-area .graph-canvas-head strong {
    font-size: 16px;
  }

  .graph-work-area .graph-canvas-head p {
    display: none;
  }

  .stat-strip {
    gap: 6px;
  }

  .stat-strip span {
    min-width: 50px;
    padding: 5px 7px;
  }

  .stat-strip strong {
    font-size: 15px;
  }

  .stat-strip small {
    display: none;
  }

  .map-canvas-viewport {
    height: clamp(520px, calc(100vh - 230px), 650px);
  }

  .canvas-orbit-tools {
    top: 10px;
    right: 10px;
  }

  .canvas-orbit-tools button {
    width: 44px;
    height: 26px;
    font-size: 12px;
  }

  .graph-work-area .map-insights {
    max-height: clamp(520px, calc(100vh - 225px), 660px);
  }

  .graph-work-area .map-canvas-tools {
    left: 10px;
    right: 10px;
    bottom: 10px;
    padding: 7px 8px;
  }

  .graph-work-area .graph-quick-actions button {
    min-height: 28px;
    padding: 0 10px;
    font-size: 12px;
  }

  /* Graph workspace v2: selected-node focus with progressive disclosure. */
  .graph-lab-shell {
    padding: 16px 18px 28px;
    background: #f7f9ff;
  }

  .graph-topbar {
    padding: 12px 14px 14px;
    border: 0;
    background: transparent;
    box-shadow: none;
  }

  .graph-brand {
    gap: 14px;
  }

  .graph-brand h1 {
    margin: 0 0 5px;
    font-size: 24px;
    letter-spacing: 0;
  }

  .graph-brand p {
    max-width: 620px;
    color: #667085;
  }

  .graph-pill {
    padding: 6px 10px;
    border: 1px solid #e3e7ff;
    color: #4f46e5;
    background: #f7f7ff;
    border-radius: 8px;
  }

  .graph-search {
    width: min(300px, 27vw);
    border-color: rgba(15, 23, 42, 0.08);
    background: #fff;
  }

  .ghost-action {
    display: none;
  }

  .primary-action {
    min-height: 38px;
    border-radius: 8px;
    box-shadow: 0 8px 20px rgba(79, 70, 229, 0.18);
  }

  .graph-workbench-grid {
    display: block;
  }

  .map-catalog {
    display: block;
    width: auto;
    margin: 0 0 10px;
    padding: 0;
    border: 0;
    background: transparent;
    box-shadow: none;
  }

  .map-catalog > :not(.graph-tabs) {
    display: none;
  }

  .graph-tabs {
    display: flex !important;
    gap: 6px;
    padding: 0 2px;
  }

  .graph-tabs button {
    min-width: 0;
    flex: 1;
    min-height: 42px;
    padding: 7px 12px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    background: #fff;
    border-radius: 8px;
    text-align: left;
    box-shadow: none;
  }

  .graph-tabs button span {
    font-size: 13px;
    font-weight: 650;
  }

  .graph-tabs button em {
    display: none;
  }

  .graph-tabs button.active {
    border-color: #c9ceff;
    color: #4338ca;
    background: #f7f7ff;
    box-shadow: inset 2px 0 0 #6366f1;
  }

  .graph-work-area {
    min-width: 0;
  }

  .mobile-node-summary,
  .mobile-path-strip,
  .closure-command-center,
  .today-recommendation,
  .path-inspector-panel {
    display: none !important;
  }

  .graph-filter-row {
    min-height: 44px;
    margin: 0;
    padding: 6px 10px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-bottom: 0;
    background: #fff;
    border-radius: 10px 10px 0 0;
  }

  .relation-filter {
    gap: 4px;
  }

  .relation-filter button {
    min-height: 30px;
    padding: 0 10px;
    border: 0;
    color: #667085;
    background: transparent;
    border-radius: 7px;
  }

  .relation-filter button.active {
    color: #4338ca;
    background: #f0f1ff;
  }

  .relation-filter button em {
    min-width: 18px;
    color: inherit;
    background: rgba(99, 102, 241, 0.08);
  }

  .graph-switches {
    color: #667085;
  }

  .view-switch {
    padding: 2px;
    border-color: rgba(15, 23, 42, 0.08);
    background: #f8fafc;
  }

  .view-switch button {
    min-height: 28px;
    padding: 0 11px;
    border-radius: 6px;
  }

  .graph-command-deck {
    display: grid !important;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0;
    margin: 0;
    padding: 10px 14px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-bottom: 0;
    background: #fff;
  }

  .graph-command-deck article {
    position: relative;
    min-height: 58px;
    padding: 6px 46px 6px 42px;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
  }

  .graph-command-deck article:not(:last-child)::after {
    position: absolute;
    top: 28px;
    right: -5px;
    width: 18px;
    height: 1px;
    content: '';
    background: #d6dbea;
  }

  .graph-command-deck article > div > span {
    position: absolute;
    top: 8px;
    left: 6px;
    display: grid;
    width: 28px;
    height: 28px;
    border: 1px solid #dfe3ff;
    color: #4f46e5;
    background: #f7f7ff;
    border-radius: 8px;
    place-items: center;
    font-size: 11px;
  }

  .graph-command-deck strong {
    display: block;
    margin-bottom: 2px;
    color: #27324a;
    font-size: 13px;
  }

  .graph-command-deck p {
    overflow: hidden;
    margin: 0;
    color: #98a2b3;
    font-size: 11px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .graph-command-deck article > button {
    position: absolute;
    top: 18px;
    right: 14px;
    min-height: 22px;
    padding: 0;
    border: 0;
    color: #6366f1;
    background: transparent;
    font-size: 11px;
  }

  .graph-stage {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 318px;
    gap: 0;
    align-items: stretch;
    margin: 0;
    border: 1px solid rgba(15, 23, 42, 0.08);
    background: #fff;
    border-radius: 0 0 12px 12px;
    overflow: hidden;
  }

  .graph-canvas-panel {
    min-width: 0;
    border: 0;
    border-right: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 0;
    background: #fff;
    box-shadow: none;
  }

  .graph-canvas-head {
    min-height: 62px;
    padding: 10px 16px;
    border-bottom: 1px solid rgba(15, 23, 42, 0.08);
    background: #fff;
  }

  .graph-canvas-head > div:first-child {
    min-width: 0;
  }

  .canvas-eyebrow {
    color: #6366f1;
    font-size: 11px;
  }

  .graph-canvas-head strong {
    font-size: 17px;
  }

  .graph-canvas-head p {
    margin-top: 2px;
    color: #98a2b3;
    font-size: 11px;
  }

  .stat-strip {
    display: none;
  }

  .zoom-control {
    padding: 2px;
    border-color: rgba(15, 23, 42, 0.08);
    background: #f8fafc;
  }

  .graph-work-area .map-canvas-viewport {
    height: clamp(430px, calc(100vh - 450px), 560px);
    min-height: 430px;
    background-color: #fbfcff;
    background-image: radial-gradient(circle, rgba(99, 102, 241, 0.12) 1px, transparent 1px);
    background-size: 20px 20px;
    cursor: grab;
  }

  .map-canvas-viewport.panning {
    cursor: grabbing;
  }

  .map-canvas {
    width: 100%;
    height: 100%;
  }

  .graph-links path {
    fill: none;
    stroke: #aeb8cc;
    stroke-width: 1.5;
    opacity: 0.52;
    transition: opacity 180ms ease, stroke 180ms ease, stroke-width 180ms ease;
  }

  .graph-links path.selected {
    stroke: #4f60e8;
    stroke-width: 2.2;
    opacity: 0.95;
  }

  .graph-links path.link-前后置关系,
  .graph-links path.link-父子关系 {
    stroke: #6476ef;
  }

  .graph-links path.link-关联关系 {
    stroke: #94a3b8;
    stroke-dasharray: 6 6;
  }

  .graph-links path.link-资料支撑 {
    stroke: #20a779;
    stroke-dasharray: 5 5;
  }

  .graph-link-label {
    pointer-events: none;
  }

  .graph-link-label rect {
    fill: rgba(255, 255, 255, 0.96);
    stroke: #e5e8f0;
  }

  .graph-link-label text {
    fill: #667085;
    font-size: 9px;
  }

  .graph-node {
    outline: none;
    cursor: pointer;
  }

  .graph-node .node-body {
    stroke-width: 1.2;
    filter: url(#graphNodeShadow);
    transition: stroke 180ms ease, stroke-width 180ms ease, filter 180ms ease;
  }

  .graph-node:hover .node-body {
    stroke: #9aa7ff;
    stroke-width: 1.8;
  }

  .graph-node.selected .node-body {
    stroke: #4f5ff0 !important;
    stroke-width: 2.5;
    filter: url(#graphRootShadow);
  }

  .graph-node.selected::before {
    opacity: 1;
  }

  .graph-node > text:not(.node-subtitle) {
    font-size: 13px;
    font-weight: 680;
  }

  .node-subtitle {
    fill: #667085 !important;
    font-size: 10px;
    font-weight: 500;
  }

  .node-subtitle--compact {
    fill: #98a2b3 !important;
    font-size: 9px;
  }

  .node-track {
    fill: #edf0f6;
  }

  .node-mastery-badge {
    display: none;
  }

  .node-expand-count circle {
    fill: #fff;
    stroke: #d6dbea;
    stroke-width: 1.2;
    transition: fill 160ms ease, stroke 160ms ease;
  }

  .node-expand-count text {
    fill: #475467;
    font-size: 10px;
    font-weight: 650;
  }

  .graph-node:hover .node-expand-count circle {
    fill: #f0f1ff;
    stroke: #818cf8;
  }

  .node-canvas-popover {
    display: none;
  }

  .graph-work-area .canvas-orbit-tools {
    top: auto;
    right: 50%;
    bottom: 16px;
    display: flex !important;
    flex-direction: row;
    padding: 4px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    background: rgba(255, 255, 255, 0.96);
    border-radius: 9px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    transform: translateX(50%);
  }

  .canvas-orbit-tools button {
    width: auto;
    min-width: 42px;
    height: 28px;
    padding: 0 8px;
    border: 0;
    border-radius: 6px;
  }

  .graph-work-area .map-canvas-tools {
    pointer-events: none;
    top: auto;
    right: 14px;
    bottom: 14px;
    left: auto;
    width: auto;
    display: flex;
    justify-content: flex-end;
    padding: 0;
    border: 0;
    background: transparent;
    box-shadow: none;
  }

  .graph-legend {
    pointer-events: auto;
    display: grid;
    gap: 6px;
    padding: 9px 11px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    background: rgba(255, 255, 255, 0.96);
    border-radius: 8px;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
  }

  .graph-legend span {
    position: relative;
    padding-left: 14px;
    font-size: 10px;
  }

  .graph-legend span::before {
    position: absolute;
    top: 50%;
    left: 0;
    width: 7px;
    height: 7px;
    content: '';
    border-radius: 50%;
    transform: translateY(-50%);
  }

  .legend-mastered::before {
    background: #12a270;
  }

  .legend-learning::before {
    background: #5267ed;
  }

  .legend-weak::before {
    background: #f28b32;
  }

  .legend-unstarted::before {
    background: #98a2b3;
  }

  .graph-quick-actions {
    display: none;
  }

  .graph-work-area .map-insights {
    position: static;
    width: auto;
    max-height: clamp(492px, calc(100vh - 388px), 622px);
    padding: 0;
    overflow: auto;
    border: 0;
    border-radius: 0;
    background: #fff;
    box-shadow: none;
    scrollbar-width: thin;
  }

  .map-insights > section {
    margin: 0;
    padding: 16px;
    border: 0;
    border-bottom: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 0;
    background: #fff;
    box-shadow: none;
  }

  .node-detail-section {
    padding-bottom: 0 !important;
  }

  .node-detail-head h3 {
    margin: 5px 0 0;
    color: #101828;
    font-size: 22px;
  }

  .mastery-state {
    display: inline-flex;
    padding: 4px 7px;
    border-radius: 6px;
    font-size: 11px !important;
  }

  .mastery-state--mastered {
    color: #087a55;
    background: #ecfdf3;
  }

  .mastery-state--learning {
    color: #334fd7;
    background: #eef2ff;
  }

  .mastery-state--weak {
    color: #c25c12;
    background: #fff5e8;
  }

  .mastery-state--unstarted {
    color: #667085;
    background: #f2f4f7;
  }

  .mastery-ring {
    width: 58px;
    height: 58px;
    background: conic-gradient(#5267ed var(--mastery), #edf0f6 0);
  }

  .node-detail-section > p {
    margin: 12px 0;
    color: #667085;
    font-size: 12px;
    line-height: 1.65;
  }

  .node-meta {
    display: none;
  }

  .relation-tags {
    display: flex;
    gap: 5px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }

  .relation-tags em {
    padding: 4px 7px;
    color: #667085;
    background: #f6f7fa;
    border-radius: 6px;
    font-size: 10px;
  }

  .inspector-tabs {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    margin: 0 -16px;
    border-top: 1px solid rgba(15, 23, 42, 0.08);
  }

  .inspector-tabs button {
    position: relative;
    min-height: 42px;
    border: 0;
    color: #667085;
    background: #fff;
    font-size: 12px;
  }

  .inspector-tabs button.active {
    color: #4f46e5;
    font-weight: 650;
  }

  .inspector-tabs button.active::after {
    position: absolute;
    right: 14px;
    bottom: 0;
    left: 14px;
    height: 2px;
    content: '';
    background: #6366f1;
    border-radius: 2px 2px 0 0;
  }

  .evidence-matrix-panel > strong {
    display: block;
    margin-bottom: 10px;
    color: #344054;
    font-size: 13px;
  }

  .evidence-column {
    display: none;
  }

  .evidence-row {
    display: grid;
    grid-template-columns: 26px minmax(0, 1fr);
    gap: 9px;
    align-items: center;
    padding: 9px 0;
    border-bottom: 1px solid #f0f2f6;
  }

  .evidence-row:last-child {
    border-bottom: 0;
  }

  .evidence-row > span {
    display: grid;
    width: 24px;
    height: 24px;
    color: #4f46e5;
    background: #eef0ff;
    border-radius: 6px;
    place-items: center;
    font-size: 11px;
    font-weight: 700;
  }

  .evidence-row b,
  .evidence-row small {
    display: block;
  }

  .evidence-row b {
    overflow: hidden;
    color: #344054;
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .evidence-row small {
    margin-top: 3px;
    color: #12a270;
    font-size: 10px;
  }

  .node-mastery-panel,
  .node-check-panel,
  .node-activity-panel {
    display: none !important;
  }

  .node-health-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .node-health-grid article {
    min-height: 92px;
    padding: 10px;
    border-radius: 8px;
  }

  .node-timeline-panel {
    display: none !important;
  }

  .path-decision-item {
    min-height: 52px;
    border-radius: 8px;
  }

  .study-pack-grid {
    grid-template-columns: 1fr;
  }

  .node-neighbor-panel .neighbor-button {
    border-radius: 8px;
  }

  .node-action-panel {
    position: sticky;
    bottom: 0;
    z-index: 2;
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 14px 16px 16px !important;
    border-top: 1px solid rgba(15, 23, 42, 0.08) !important;
    background: rgba(255, 255, 255, 0.98) !important;
  }

  .node-action-panel > strong {
    display: none;
  }

  .node-action-panel button {
    min-height: 38px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 650;
  }

  .node-action-primary {
    border: 1px solid #4f5ff0 !important;
    color: #fff !important;
    background: #4f5ff0 !important;
  }

  .node-action-secondary {
    border: 1px solid #d8dcff !important;
    color: #4f46e5 !important;
    background: #fff !important;
  }

  .graph-minimap {
    position: absolute;
    bottom: 14px;
    left: 14px;
    width: 112px;
    height: 76px;
    padding: 6px;
    border: 1px solid rgba(99, 102, 241, 0.18);
    background: rgba(255, 255, 255, 0.94);
    border-radius: 8px;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
  }

  .graph-minimap svg {
    width: 100%;
    height: 100%;
  }

  .graph-minimap path {
    fill: none;
    stroke: #c6ccda;
    stroke-width: 7;
  }

  .graph-minimap circle {
    fill: #cbd2e4;
  }

  .graph-minimap circle.selected {
    fill: #4f5ff0;
  }

  .graph-search-results {
    margin: 0 0 10px;
    border-radius: 8px;
  }

  @media (max-width: 1180px) {
    .graph-stage {
      grid-template-columns: minmax(0, 1fr) 286px;
    }

    .graph-command-deck article {
      padding-right: 12px;
    }

    .graph-command-deck article > button {
      display: none;
    }

    .graph-switches label {
      display: none;
    }
  }

  @media (max-width: 980px) {
    .graph-topbar {
      align-items: flex-start;
    }

    .graph-top-actions {
      width: auto;
    }

    .graph-search {
      width: 230px;
    }

    .graph-stage {
      grid-template-columns: 1fr;
    }

    .graph-canvas-panel {
      border-right: 0;
    }

    .map-insights {
      max-height: none;
      border-top: 1px solid rgba(15, 23, 42, 0.08);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .graph-node,
    .graph-node .node-body,
    .graph-links path {
      animation: none !important;
      transition: none !important;
    }
  }
</style>
