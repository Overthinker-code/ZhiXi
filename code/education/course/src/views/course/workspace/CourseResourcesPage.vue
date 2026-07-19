<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { Message, Modal } from '@arco-design/web-vue';
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
  import { fetchCourseWorkspace } from '@/api/course';
  import {
    downloadResource,
    type ResourceRecord,
  } from '@/api/resources';
  import {
    fetchResourceRecommendations,
  } from '@/api/resource-hub';
  import ResourcePreviewDialog from '@/components/resource/ResourcePreviewDialog.vue';
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';
  import {
    fetchRecentGeneratedPackages,
    type RecentGeneratedPackage,
  } from '@/api/resource-generation';
  import { getToken } from '@/utils/auth';
  import axios from 'axios';

  const route = useRoute();
  const router = useRouter();
  const query = ref('');
  const activeType = ref<'全部' | CourseResourceItem['type']>('全部');
  const recentPackages = ref<RecentGeneratedPackage[]>([]);
  const loadingRecentPackages = ref(false);
  const selectedResourceId = ref('');
  const resourceDrawerVisible = ref(false);
  const resourceToolDrawerVisible = ref(false);
  const generatedPackagePreviewVisible = ref(false);
  const previewedGeneratedPackage = ref<RecentGeneratedPackage | null>(null);
  const showAllResources = ref(false);
  const backendResources = ref<ResourceRecord[]>([]);
  const previewResourceRecord = ref<ResourceRecord | null>(null);
  const profileSignals = ref<string[]>([]);
  const defaultResourcePreviewCount = 6;
  const aiTrialLimit = 3;
  const aiTrialStorageKey = 'zhixi-course-resource-ai-trial-v1';
  type AiTrialUsage = Record<string, number>;

  function readAiTrialUsage(): AiTrialUsage {
    if (typeof window === 'undefined') return {};
    try {
      return JSON.parse(window.localStorage.getItem(aiTrialStorageKey) || '{}');
    } catch {
      return {};
    }
  }

  const aiTrialUsage = ref<AiTrialUsage>(readAiTrialUsage());
  const course = computed(() =>
    getClassroomCourse(String(route.params.courseId || ''))
  );
  const resources = computed(() => {
    if (!course.value) return [];
    const serverItems = backendResources.value.map(mapBackendResource);
    return serverItems.length ? serverItems : buildCourseResources(course.value);
  });
  const networkResources = computed(() => {
    const signals = profileSignals.value.map((item) => item.toLowerCase());
    return resources.value
      .filter((item) => ['视频', '笔记'].includes(item.type) && item.backendResource?.url)
      .sort((left, right) => networkMatchScore(right, signals) - networkMatchScore(left, signals));
  });
  const generatedPackagesForCourse = computed(() => {
    const activeCourse = course.value;
    if (!activeCourse) return [] as RecentGeneratedPackage[];
    return recentPackages.value.filter((pkg) => {
      if (pkg.course_id) return pkg.course_id === activeCourse.id;
      return [activeCourse.title, activeCourse.shortTitle].includes(pkg.subject);
    });
  });
  const generatedArtifactCount = computed(() =>
    generatedPackagesForCourse.value.reduce(
      (sum, item) => sum + item.artifacts.length,
      0
    )
  );
  const aiTrialUsed = computed(() =>
    course.value
      ? Math.max(
          aiTrialUsage.value[course.value.id] || 0,
          generatedPackagesForCourse.value.length
        )
      : 0
  );
  const aiTrialRemaining = computed(() =>
    Math.max(aiTrialLimit - aiTrialUsed.value, 0)
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
      const typeMatches =
        activeType.value === '全部' || item.type === activeType.value;
      const searchMatches =
        !keyword ||
        item.title.toLowerCase().includes(keyword) ||
        item.chapter.toLowerCase().includes(keyword);
      return typeMatches && searchMatches;
    });
  });
  const displayedResources = computed(() =>
    showAllResources.value
      ? visibleResources.value
      : visibleResources.value.slice(0, defaultResourcePreviewCount)
  );
  const hiddenResourceCount = computed(() =>
    Math.max(visibleResources.value.length - displayedResources.value.length, 0)
  );

  function resourceTypeLabel(resource: ResourceRecord): CourseResourceItem['type'] {
    if (resource.type === 'ppt' || /课件|ppt/i.test(resource.title)) return '课件';
    if (resource.type === 'lecture_markdown') return '讲义';
    if (resource.type === 'practice_markdown' || resource.type === 'question') return '练习';
    if (resource.type === 'external_video') return '视频';
    if (resource.type === 'external_note') return '笔记';
    if (resource.type === 'knowledge_graph' || resource.type === 'mind_map') return '导图';
    return '资料' as CourseResourceItem['type'];
  }

  function mapBackendResource(resource: ResourceRecord): CourseResourceItem {
    const metadata = resource.content || {};
    const chapter = typeof metadata.chapter === 'string'
      ? metadata.chapter
      : resource.knowledge_point || '课程拓展';
    return {
      id: resource.id,
      title: resource.title,
      type: resourceTypeLabel(resource),
      chapter,
      size: resource.file_size
        ? `${(resource.file_size / 1024 / 1024).toFixed(resource.file_size > 1024 * 1024 ? 1 : 2)} MB`
        : '在线资源',
      updatedAt: resource.upload_time
        ? new Date(resource.upload_time).toLocaleDateString('zh-CN')
        : '持续更新',
      downloads: 0,
      backendResource: { ...resource, favorite: false, top: false },
    };
  }

  function networkMatchScore(item: CourseResourceItem, signals: string[]) {
    const metadata = item.backendResource?.content || {};
    const tags = Array.isArray(metadata.profile_tags)
      ? metadata.profile_tags.map((tag) => String(tag).toLowerCase())
      : [];
    const text = `${item.title} ${item.chapter} ${tags.join(' ')}`.toLowerCase();
    return signals.reduce((score, signal) => score + (signal && text.includes(signal) ? 1 : 0), 0);
  }

  function networkReason(item: CourseResourceItem) {
    const metadata = item.backendResource?.content || {};
    const matched = profileSignals.value.find((signal) =>
      `${item.title} ${item.chapter} ${(metadata.profile_tags || []).join?.(' ') || ''}`.includes(signal)
    );
    if (matched) return `画像信号“${matched}”与该资源匹配，建议作为当前课程的补充学习。`;
    return typeof metadata.summary === 'string'
      ? metadata.summary
      : '根据当前课程进度与资源偏好推荐。';
  }

  function openNetworkResource(item: CourseResourceItem) {
    const url = item.backendResource?.url;
    if (!url) return;
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  function openOnlinePreview(item: CourseResourceItem) {
    const resource = item.backendResource;
    if (!resource) {
      Message.info('该演示资料暂无原文件，请选择已入库的课程资料。');
      return;
    }
    if (resource.url) {
      openNetworkResource(item);
      return;
    }
    previewResourceRecord.value = resource;
  }

  async function downloadOriginalResource(resource: ResourceRecord) {
    try {
      const response = await downloadResource(resource.id);
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = resource.file_name || resource.title;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      Message.warning('原始资料暂时无法下载，请检查后端是否已启动。');
    }
  }

  async function loadCourseResources() {
    if (!course.value) return;
    try {
      const workspace = await fetchCourseWorkspace(course.value.id);
      backendResources.value = workspace.resources.map((resource) => ({
        ...resource,
        favorite: false,
        top: false,
      }));
    } catch {
      // Keep the deterministic local course shell available when the backend is offline.
    }
    try {
      const recommendations = await fetchResourceRecommendations(12, false);
      profileSignals.value = recommendations.data.profile_signals || [];
    } catch {
      profileSignals.value = [];
    }
  }
  const resourceQuality = computed(() => [
    {
      label: '资料关联',
      value: '章节 / 知识点 / 任务',
      desc: '关联章节和知识点，方便继续学习',
    },
    {
      label: '使用建议',
      value: '预习 / 练习 / 追问',
      desc: '下载后可继续提问、练习或查看知识点',
    },
    {
      label: '内容检查',
      value: '目标 / 内容 / 练习',
      desc: '导出文件包含明确的学习目标和练习要求',
    },
  ]);
  const resourceCoverageStats = computed(() => {
    const graphNodeTotal = resources.value.reduce(
      (sum, item) => sum + resourcePlan(item).graphNodes.length,
      0
    );
    const taskTotal = resources.value.reduce(
      (sum, item) => sum + resourcePlan(item).tasks.length,
      0
    );
    return [
      {
        label: '可执行资料',
        value: `${resources.value.length} 份`,
        desc: '含章节、类型、版本和学习任务',
      },
      {
        label: '关联知识点',
        value: `${graphNodeTotal} 个`,
        desc: '每份资料可在课程图谱中继续查看',
      },
      {
        label: '待完成动作',
        value: `${taskTotal} 项`,
        desc: '包含阅读、练习、提问和复盘建议',
      },
      {
        label: '最近生成',
        value: `${generatedPackagesForCourse.value.length} 包`,
        desc: '可继续下载、检查内容或查看知识点',
      },
    ];
  });

  function resourceIndex(item: CourseResourceItem) {
    return Math.max(
      resources.value.findIndex((resource) => resource.id === item.id),
      0
    );
  }

  function relatedConcept(item: CourseResourceItem) {
    if (!course.value) return undefined;
    return course.value.concepts[
      resourceIndex(item) % Math.max(course.value.concepts.length, 1)
    ];
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

  function resourceLearningStatus(item: CourseResourceItem) {
    const lesson = relatedLesson(item);
    if (lesson?.status === 'done') return '已完成课节复盘';
    if (item.type.includes('练习') || item.type.includes('作业')) return '建议优先追练';
    if (item.downloads < 40) return '低频资料待补齐';
    return '本周复习推荐';
  }

  const selectedResource = computed(() => {
    const active = resources.value.find((item) => item.id === selectedResourceId.value);
    return active || visibleResources.value[0] || resources.value[0] || undefined;
  });
  const selectedResourcePlan = computed(() =>
    selectedResource.value ? resourcePlan(selectedResource.value) : undefined
  );

  function selectResource(item: CourseResourceItem, openDrawer = false) {
    selectedResourceId.value = item.id;
    if (
      openDrawer &&
      typeof window !== 'undefined' &&
      window.matchMedia('(max-width: 1180px)').matches
    ) {
      resourceDrawerVisible.value = true;
    }
  }

  function openResourceDetails(item: CourseResourceItem) {
    selectResource(item);
    resourceDrawerVisible.value = true;
  }

  type RouteQueryPayload = Record<string, string | number | undefined>;

  function compactRouteQuery(payload: RouteQueryPayload) {
    return Object.fromEntries(
      Object.entries(payload).filter(([, value]) => value !== undefined && String(value).trim())
    ) as Record<string, string | number>;
  }

  function resourceGraphNodeId(item: CourseResourceItem) {
    const index = resourceIndex(item);
    return index >= 0 && index < 6 ? `resource-${index}` : undefined;
  }

  function resourceRouteQuery(item: CourseResourceItem, extra: RouteQueryPayload = {}) {
    const plan = resourcePlan(item);
    const graphLabel = item.title.replace(course.value?.shortTitle || '', '') || item.title;
    const focusTopic = plan.concept?.title || plan.lesson?.title || item.title;
    return compactRouteQuery({
      resourceId: item.id,
      resourceTitle: item.title,
      resourceChapter: item.chapter,
      resourceType: item.type,
      topic: focusTopic,
      nodeId: resourceGraphNodeId(item),
      nodeLabel: graphLabel,
      mapType: 'problem',
      source: 'resource',
      ...extra,
    });
  }

  function buildResourceMarkdown(item: CourseResourceItem) {
    const plan = resourcePlan(item);
    const { concept } = plan;
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
      `前置关系：先复盘 ${item.chapter} 的基本定义，再进入 ${
        concept?.title || lessonTitle
      } 的应用边界。`,
      `后续动作：把本资料生成的错题、摘要和追问同步到课程图谱。`,
      '',
      '## 课堂笔记骨架',
      `- 关键概念：${concept?.title || lessonTitle}`,
      `- 证据材料：${
        concept?.resources?.slice(0, 3).join('；') ||
        `${item.title}、课堂讲义、例题卡片`
      }`,
      `- 易错点：${
        concept?.misconceptions?.slice(0, 2).join('；') ||
        '定义边界不清；只背结论不写条件'
      }`,
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
      '- [ ] 已把薄弱点同步到课程图谱或 AI 伴学。',
    ];
    return `${lines.join('\n')}\n`;
  }

  function askAboutResource(item: CourseResourceItem) {
    if (!course.value) return;
    router.push(
      courseWorkspaceLocation(course.value.id, 'agent', {
        task: 'reader',
        prompt: `当前课程是《${course.value.title}》。我想围绕资料《${item.title}》提问，请先告诉我可以从哪些角度阅读这份资料。`,
        ...resourceRouteQuery(item),
      })
    );
  }

  function showUpgradePrompt() {
    Modal.info({
      title: aiTrialRemaining.value ? '专业版批量生成能力' : '升级后继续生成课程资源',
      content: aiTrialRemaining.value
        ? '当前仍可继续使用本地试用生成。专业版适合批量生成整章讲义、分层练习、图谱节点资源和班级级生成历史。'
        : '当前课程的本地试用额度已用完。升级后适合批量生成讲义、练习、知识卡和图谱节点资源，并保留更多生成历史。',
      okText: '知道了',
    });
  }

  function hasAiTrialCredit() {
    if (aiTrialRemaining.value <= 0) {
      showUpgradePrompt();
      return false;
    }
    return true;
  }

  function openGenerator(actionLabel = 'AI 生成课程资源') {
    if (!course.value) return;
    if (!hasAiTrialCredit()) return;
    router.push({
      name: 'StudentCourseResourceGenerator',
      params: { courseId: course.value.id },
      query: {
        subject: course.value.title,
        topic: course.value.chapters[0]?.title || course.value.title,
        source: 'course-workspace',
        entry: actionLabel,
      },
    });
  }

  function openKnowledgeMap() {
    if (!course.value) return;
    router.push(courseWorkspaceLocation(course.value.id, 'knowledge'));
  }

  function locateResourceInGraph(item: CourseResourceItem) {
    if (!course.value) return;
    router.push(
      courseWorkspaceLocation(
        course.value.id,
        'knowledge',
        resourceRouteQuery(item, { source: 'resource' })
      )
    );
  }

  function generateResourceMaterials(item: CourseResourceItem) {
    if (!course.value) return;
    if (!hasAiTrialCredit()) return;
    const plan = resourcePlan(item);
    const graphNodes = plan.graphNodes.join(' / ');
    router.push({
      name: 'StudentCourseResourceGenerator',
      params: { courseId: course.value.id },
      query: resourceRouteQuery(item, {
        subject: course.value.title,
        topic: plan.concept?.title || item.title,
        goal: [
          `围绕资料《${item.title}》生成配套讲义、练习、思维导图、阅读清单和质量核查清单。`,
          `章节：${item.chapter}。`,
          graphNodes ? `图谱节点：${graphNodes}。` : '',
          '生成内容必须能直接服务课前预习、课堂复盘和错因追练。',
        ].filter(Boolean).join(''),
        entry: 'resource-card',
      }),
    });
  }

  function downloadResourceBrief(item: CourseResourceItem) {
    const content = buildResourceMarkdown(item);
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${course.value?.shortTitle || 'course'}-${
      item.title
    }-学习包.md`;
    link.click();
    URL.revokeObjectURL(url);
    Message.success('学习资源包已生成');
  }

  function generatedPackageLabel(pkg: RecentGeneratedPackage) {
    const date = new Date(pkg.generated_at);
    if (Number.isNaN(date.getTime())) return '刚刚生成';
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  type GeneratedPackageArtifact = RecentGeneratedPackage['artifacts'][number];

  function openGeneratedPackagePreview(pkg: RecentGeneratedPackage) {
    previewedGeneratedPackage.value = pkg;
    generatedPackagePreviewVisible.value = true;
  }

  function generatedArtifactFileId(
    pkg: RecentGeneratedPackage,
    artifact?: GeneratedPackageArtifact
  ) {
    if (!artifact?.file_name) return '';
    return `${pkg.package_id}/${artifact.file_name}`;
  }

  async function downloadGeneratedArtifact(
    pkg: RecentGeneratedPackage,
    artifact = pkg.artifacts[0]
  ) {
    if (!artifact) {
      Message.warning('这个资源包还没有可下载文件');
      return;
    }
    const token = getToken();
    const url =
      artifact.download_url ||
      `/api/v1/resource-generation/artifacts/${pkg.package_id}/${artifact.file_name}`;
    try {
      const response = await axios.get(url, {
        responseType: 'blob',
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      const blobUrl = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = artifact.file_name;
      link.click();
      URL.revokeObjectURL(blobUrl);
    } catch {
      Message.warning('资源文件暂时无法下载，请稍后重试或先进入资料复核。');
    }
  }

  function askAboutGeneratedPackage(pkg: RecentGeneratedPackage) {
    if (!course.value) return;
    generatedPackagePreviewVisible.value = false;
    const firstArtifact = pkg.artifacts[0];
    const artifactFileId = generatedArtifactFileId(pkg, firstArtifact);
    const artifactTitle = firstArtifact?.title || firstArtifact?.file_name || '';
    const artifactList = pkg.artifacts
      .slice(0, 6)
      .map((artifact, index) => `${index + 1}. ${artifact.title || artifact.file_name}（${artifact.file_name}）`)
      .join('\n');
    const artifactPreview = pkg.artifacts
      .slice(0, 4)
      .map((artifact) => `${artifact.title || artifact.file_name}：${artifact.preview || '暂无预览'}`)
      .join('\n');
    router.push(
      courseWorkspaceLocation(course.value.id, 'agent', {
        task: 'reader',
        prompt: [
          `当前课程是《${course.value.title}》。请围绕最近生成的资源包「${pkg.topic}」做资料复核。`,
          artifactList ? `已生成文件清单：\n${artifactList}` : '',
          firstArtifact
            ? `当前优先复核文件：${artifactTitle}，文件标识：${artifactFileId}。`
            : '',
          '请先说明你能看到的是资源包与文件线索还是完整原文；如果没有原文片段，不要假装已经读完文件。然后指出预习、练习、图谱核验和 AI 追问的使用顺序。',
        ]
          .filter(Boolean)
          .join('\n'),
        packageId: pkg.package_id,
        packageTopic: pkg.topic,
        packageSource: pkg.source || 'resource-generation',
        nodeId: pkg.node_id,
        nodeLabel: pkg.node_label,
        mapType: pkg.map_type,
        resourceId: pkg.resource_id,
        resourceTitle: artifactTitle || pkg.topic,
        resourceType: firstArtifact?.kind,
        currentFileId: artifactFileId,
        fileId: artifactFileId,
        fileName: firstArtifact?.file_name,
        artifactKind: firstArtifact?.kind,
        artifactList,
        artifactPreview,
        topic: pkg.topic,
        source: 'resource-generation',
      })
    );
  }

  function auditGeneratedPackageInGraph(pkg: RecentGeneratedPackage) {
    if (!course.value) return;
    generatedPackagePreviewVisible.value = false;
    router.push(
      courseWorkspaceLocation(course.value.id, 'knowledge', {
        topic: pkg.topic,
        packageId: pkg.package_id,
        nodeId: pkg.node_id,
        nodeLabel: pkg.node_label,
        mapType: pkg.map_type,
        resourceId: pkg.resource_id,
        source: 'resource-generation',
      })
    );
  }

  async function loadRecentPackages() {
    if (!course.value) return;
    loadingRecentPackages.value = true;
    try {
      recentPackages.value = await fetchRecentGeneratedPackages(course.value.id);
    } catch {
      Message.warning('生成记录暂不可用，已显示课程内置资料。');
    } finally {
      loadingRecentPackages.value = false;
    }
  }

  onMounted(() => {
    void loadRecentPackages();
    void loadCourseResources();
  });
</script>

<template>
  <section v-if="course" class="course-resources">
    <header class="resource-heading">
      <div>
        <h1>课程资料</h1>
        <p>按章节整理课件、讲义、案例和练习；查看详情后可下载学习包、生成配套或定位图谱。</p>
      </div>
      <div class="resource-heading__actions">
        <button type="button" class="ghost" @click="resourceToolDrawerVisible = true">
          <icon-storage />
          <span>资料工具</span>
        </button>
        <button type="button" @click="openGenerator()">
          <icon-robot />
          <span>生成资料</span>
        </button>
      </div>
    </header>

    <div class="resource-overview">
      <article>
        <span class="overview-icon"><icon-storage /></span>
        <div
          ><small>资料总数</small
          ><strong>{{ resources.length + generatedArtifactCount }}</strong></div
        >
      </article>
      <article>
        <span class="overview-icon"><icon-file /></span>
        <div
          ><small>覆盖章节</small
          ><strong>{{ course.chapters.length }}</strong></div
        >
      </article>
      <article>
        <span class="overview-icon"><icon-download /></span>
        <div
          ><small>最近生成</small
          ><strong>{{ generatedPackagesForCourse.length }}</strong></div
        >
      </article>
      <article>
        <span class="overview-icon"><icon-check-circle /></span>
        <div
          ><small>已学章节</small
          ><strong>{{ completedChapterCount }}</strong></div
        >
      </article>
    </div>

    <section v-if="networkResources.length" class="network-recommendations" aria-label="画像驱动的网络学习资源">
      <header>
        <div>
          <span>PROFILE × RESOURCE AGENT</span>
          <h2>根据个人画像推送</h2>
          <p>结合薄弱知识点、学习偏好与课程进度排序；外部内容将在原平台打开。</p>
        </div>
        <div class="network-recommendations__signals">
          <span v-for="signal in profileSignals.slice(0, 3)" :key="signal">{{ signal }}</span>
        </div>
      </header>
      <div class="network-recommendations__grid">
        <article v-for="item in networkResources.slice(0, 5)" :key="item.id">
          <div class="network-resource__meta">
            <span>{{ item.backendResource?.source }}</span>
            <small>{{ item.type }}</small>
          </div>
          <h3>{{ item.title }}</h3>
          <p>{{ networkReason(item) }}</p>
          <button type="button" @click="openNetworkResource(item)">
            前往原平台学习
          </button>
        </article>
      </div>
    </section>

    <section class="resource-library-shell" aria-label="课程资料库">
      <div class="resource-library-main">
        <div class="resource-toolbar">
          <label>
            <icon-search />
            <input
              v-model="query"
              type="search"
              aria-label="搜索课程资料或章节"
              placeholder="搜索资料或章节"
            />
          </label>
          <div>
            <button
              v-for="type in resourceTypes"
              :key="type"
              type="button"
              :class="{ active: activeType === type }"
              :aria-pressed="activeType === type"
              @click="activeType = type"
            >
              {{ type }}
            </button>
          </div>
        </div>

        <div class="resource-grid">
          <article
            v-for="item in displayedResources"
            :key="item.id"
            class="resource-card"
            :class="{ active: selectedResource?.id === item.id }"
            role="button"
            tabindex="0"
            :aria-label="`${item.title}，${item.type}，查看资料详情`"
            @click="openResourceDetails(item)"
            @keydown.enter="openResourceDetails(item)"
            @keydown.space.prevent="openResourceDetails(item)"
          >
            <div class="resource-card__top">
              <span class="resource-type">{{ item.type }}</span>
              <small>{{ item.updatedAt }}</small>
            </div>
            <span class="resource-file-icon"><icon-file /></span>
            <h2>{{ item.title }}</h2>
            <p>{{ item.chapter }}</p>
            <div class="resource-path">
              <span
                v-for="node in resourcePlan(item).graphNodes.slice(0, 3)"
                :key="node"
              >
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
            <span class="resource-card__cta">详情</span>
            <div class="resource-trust-row">
              <span>课程组审核</span>
              <span>v{{ resourceIndex(item) + 1 }}.{{ item.downloads % 10 }}</span>
              <span>{{ resourceLearningStatus(item) }}</span>
            </div>
          </article>
        </div>

        <div
          v-if="visibleResources.length > defaultResourcePreviewCount"
          class="resource-list-more"
        >
          <span>
            当前显示 {{ displayedResources.length }} / {{ visibleResources.length }} 份资料<span
              v-if="hiddenResourceCount"
            >，还有 {{ hiddenResourceCount }} 份未展开</span>
          </span>
          <button type="button" @click="showAllResources = !showAllResources">
            {{ showAllResources ? '收起资料列表' : `展开全部 ${visibleResources.length} 份` }}
          </button>
        </div>

        <a-empty v-if="!visibleResources.length" description="没有匹配的课程资料" />
      </div>
    </section>

    <a-drawer
      v-model:visible="resourceDrawerVisible"
      :width="440"
      :footer="false"
      placement="right"
      unmount-on-close
    >
      <template #title>资料详情</template>
      <div v-if="selectedResource && selectedResourcePlan" class="resource-inspector resource-inspector--drawer">
        <div class="resource-inspector__head">
          <span>{{ selectedResource.type }}</span>
          <h2>{{ selectedResource.title }}</h2>
          <p>{{ selectedResource.chapter }} · {{ selectedResource.size }} · {{ selectedResource.downloads }} 次使用</p>
        </div>
        <div class="resource-inspector__nodes">
          <strong>关联知识点</strong>
          <div>
            <span v-for="node in selectedResourcePlan.graphNodes.slice(0, 4)" :key="node">
              {{ node }}
            </span>
          </div>
        </div>
        <section>
          <strong>建议使用顺序</strong>
          <ol>
            <li v-for="task in selectedResourcePlan.tasks" :key="task">{{ task }}</li>
          </ol>
        </section>
        <section>
          <strong>可直接追问</strong>
          <button
            v-for="prompt in selectedResourcePlan.prompts"
            :key="prompt"
            type="button"
            @click="askAboutResource(selectedResource)"
          >
            {{ prompt }}
          </button>
        </section>
        <div class="resource-inspector__actions">
          <button
            v-if="selectedResource.backendResource"
            type="button"
            class="primary"
            @click="openOnlinePreview(selectedResource)"
          >
            <icon-file /> {{ selectedResource.type === '课件' ? 'PPT 放映' : '在线阅读' }}
          </button>
          <button
            v-if="selectedResource.backendResource && !selectedResource.backendResource.url"
            type="button"
            @click="downloadOriginalResource(selectedResource.backendResource)"
          >
            <icon-download /> 原始文件
          </button>
          <button type="button" class="primary" @click="downloadResourceBrief(selectedResource)">
            <icon-download /> 学习包
          </button>
          <button type="button" @click="generateResourceMaterials(selectedResource)">
            <icon-bulb /> 生成配套
          </button>
          <button type="button" @click="locateResourceInGraph(selectedResource)">
            <icon-mind-mapping /> 图谱定位
          </button>
          <button type="button" @click="askAboutResource(selectedResource)">
            <icon-robot /> 资料问答
          </button>
        </div>
      </div>
    </a-drawer>

    <a-drawer
      v-model:visible="resourceToolDrawerVisible"
      :width="420"
      :footer="false"
      placement="right"
      unmount-on-close
    >
      <template #title>资料工具</template>
      <div class="resource-tool-drawer">
        <section class="tool-section">
          <div class="tool-section__head">
          <span>学习工具</span>
          <p>围绕当前资料继续生成、提问或查看关联知识点。</p>
          </div>
          <div class="tool-action-grid">
            <button type="button" @click="openGenerator('课程资料生成')">
              <icon-robot />
              <strong>生成配套资料</strong>
              <small>讲义、练习、导图</small>
            </button>
            <button type="button" @click="openKnowledgeMap">
              <icon-mind-mapping />
              <strong>查看关联知识点</strong>
              <small>在课程图谱中定位</small>
            </button>
            <button
              type="button"
              :disabled="!selectedResource"
              @click="selectedResource && askAboutResource(selectedResource)"
            >
              <icon-file />
              <strong>资料问答</strong>
              <small>基于当前资料追问</small>
            </button>
            <button
              type="button"
              :disabled="!selectedResource"
              @click="selectedResource && locateResourceInGraph(selectedResource)"
            >
              <icon-check-circle />
              <strong>在图谱中查看</strong>
              <small>结合当前资料定位</small>
            </button>
          </div>
        </section>

        <section class="tool-section">
          <div class="tool-section__head">
            <span>资料状态</span>
            <p>帮助你快速了解资料覆盖范围和可用方式。</p>
          </div>
          <div class="tool-stat-grid">
            <article v-for="item in resourceCoverageStats" :key="item.label">
              <strong>{{ item.value }}</strong>
              <span>{{ item.label }}</span>
            </article>
          </div>
        </section>

        <section class="tool-section">
          <div class="tool-section__head">
            <span>质量标准</span>
            <p>资料进入学习路径前应满足这些条件。</p>
          </div>
          <div class="tool-quality-list">
            <article v-for="item in resourceQuality" :key="item.label">
              <icon-bulb />
              <div>
                <strong>{{ item.label }}</strong>
                <span>{{ item.value }}</span>
              </div>
            </article>
          </div>
        </section>

        <section class="tool-section">
          <div class="tool-section__head tool-section__head--row">
            <div>
              <span>生成记录</span>
              <p>生成的学习资料会保存在这里，并可查看关联知识点。</p>
            </div>
            <button type="button" :disabled="loadingRecentPackages" @click="loadRecentPackages">
              {{ loadingRecentPackages ? '同步中' : '刷新' }}
            </button>
          </div>
          <div v-if="generatedPackagesForCourse.length" class="tool-package-list">
            <article
              v-for="pkg in generatedPackagesForCourse.slice(0, 3)"
              :key="pkg.package_id"
            >
              <div>
                <button
                  type="button"
                  class="tool-package-topic"
                  @click="openGeneratedPackagePreview(pkg)"
                >
                  <strong>{{ pkg.topic }}</strong>
                </button>
                <span>{{ generatedPackageLabel(pkg) }} · {{ pkg.artifacts.length }} 个文件</span>
              </div>
              <div>
                <button type="button" @click="openGeneratedPackagePreview(pkg)">
                  <icon-file /> 预览
                </button>
                <button type="button" @click="askAboutGeneratedPackage(pkg)">
                  <icon-robot /> 检查内容
                </button>
                <button type="button" @click="auditGeneratedPackageInGraph(pkg)">
                  <icon-mind-mapping /> 关联知识点
                </button>
              </div>
            </article>
          </div>
          <div v-else class="tool-empty">
            <strong>还没有生成学习资料</strong>
            <p>可先围绕当前课程生成一份讲义、练习或思维导图。</p>
            <button type="button" @click="openGenerator('课程资料回流生成')">现在生成</button>
          </div>
        </section>
      </div>
    </a-drawer>

    <a-drawer
      v-model:visible="generatedPackagePreviewVisible"
      :width="520"
      :footer="false"
      unmount-on-close
      title="资源包预览"
    >
      <div v-if="previewedGeneratedPackage" class="generated-package-preview">
        <header>
          <span>课程生成记录</span>
          <h2>{{ previewedGeneratedPackage.topic }}</h2>
          <p>
            {{ generatedPackageLabel(previewedGeneratedPackage) }} ·
            {{ previewedGeneratedPackage.artifacts.length }} 个可下载文件
          </p>
        </header>

        <div class="generated-package-preview__files">
          <article
            v-for="artifact in previewedGeneratedPackage.artifacts"
            :key="artifact.file_name"
          >
            <div>
              <strong>{{ artifact.title || artifact.file_name }}</strong>
              <span>{{ artifact.file_name }}</span>
            </div>
            <p>{{ artifact.preview || '该文件可下载查看完整内容。' }}</p>
            <button
              type="button"
              @click="downloadGeneratedArtifact(previewedGeneratedPackage, artifact)"
            >
              <icon-download /> 下载文件
            </button>
          </article>
        </div>

        <footer>
          <button
            type="button"
            @click="askAboutGeneratedPackage(previewedGeneratedPackage)"
          >
            <icon-robot /> 检查内容
          </button>
          <button
            type="button"
            class="primary"
            @click="auditGeneratedPackageInGraph(previewedGeneratedPackage)"
          >
            <icon-mind-mapping /> 查看关联知识点
          </button>
        </footer>
      </div>
    </a-drawer>
    <ResourcePreviewDialog
      :resource="previewResourceRecord"
      @close="previewResourceRecord = null"
      @download="downloadOriginalResource"
    />
  </section>
</template>

<style scoped lang="less">
  .course-resources {
    color: #17213a;
  }

  .network-recommendations {
    margin: 0 0 16px;
    padding: 18px;
    border: 1px solid rgba(79, 70, 229, 0.16);
    border-radius: 16px;
    background: linear-gradient(135deg, #f7f7ff, #fff 62%);
  }

  .network-recommendations > header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 18px;
    margin-bottom: 14px;
  }

  .network-recommendations > header span {
    color: #4f46e5;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: .1em;
  }

  .network-recommendations h2 {
    margin: 4px 0;
    font-size: 18px;
  }

  .network-recommendations p {
    margin: 0;
    color: #667085;
    font-size: 11px;
    line-height: 1.6;
  }

  .network-recommendations__signals {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 6px;
  }

  .network-recommendations__signals span {
    padding: 5px 8px;
    border-radius: 999px;
    background: #eeecff;
    letter-spacing: 0;
  }

  .network-recommendations__grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
  }

  .network-recommendations__grid article {
    display: flex;
    min-width: 0;
    min-height: 174px;
    flex-direction: column;
    padding: 13px;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: #fff;
  }

  .network-resource__meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    color: #4f46e5;
    font-size: 10px;
    font-weight: 700;
  }

  .network-recommendations__grid h3 {
    margin: 10px 0 6px;
    font-size: 13px;
    line-height: 1.45;
  }

  .network-recommendations__grid article > p {
    display: -webkit-box;
    overflow: hidden;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
  }

  .network-recommendations__grid button {
    margin-top: auto;
    padding: 7px 9px;
    border: 1px solid #d9dcff;
    border-radius: 8px;
    color: #4338ca;
    background: #f7f7ff;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
  }

  @media (max-width: 1180px) {
    .network-recommendations__grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }

  @media (max-width: 640px) {
    .network-recommendations > header { align-items: flex-start; flex-direction: column; }
    .network-recommendations__signals { justify-content: flex-start; }
    .network-recommendations__grid { grid-template-columns: 1fr; }
  }

  .resource-heading {
    display: flex;
    gap: 20px;
    align-items: flex-end;
    justify-content: space-between;
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

    .resource-heading__actions {
      display: flex;
      flex: 0 0 auto;
      gap: 10px;
      align-items: center;
    }

    .resource-heading__actions button {
      display: inline-flex;
      gap: 6px;
      align-items: center;
      justify-content: center;
      height: 36px;
      padding: 0 14px;
      border: 0;
      border-radius: 9px;
      color: #fff;
      background: #5367f8;
      cursor: pointer;

      span {
        font-size: 12px;
        font-weight: 700;
      }

      small {
        padding-left: 8px;
        border-left: 1px solid rgba(255, 255, 255, 0.36);
        font-size: 10px;
        opacity: 0.88;
      }
    }

    .resource-heading__actions .ghost {
      border: 1px solid rgba(15, 23, 42, 0.08);
      color: #475467;
      background: #fff;
    }
  }

  .ai-credit-panel {
    display: grid;
    grid-template-columns: minmax(240px, 0.9fr) minmax(0, 1.25fr) 150px;
    gap: 12px;
    margin-bottom: 12px;
    padding: 16px;
    border: 1px solid #dbe5ec;
    border-radius: 12px;
    background: linear-gradient(
        135deg,
        rgba(46, 125, 106, 0.09),
        transparent 42%
      ),
      linear-gradient(90deg, #fff, #f8fbff);
    box-shadow: 0 10px 28px rgba(36, 55, 84, 0.05);
  }

  .ai-credit-panel__main {
    min-width: 0;

    h2 {
      margin: 6px 0 6px;
      color: #21304a;
      font-size: 18px;
    }

    p,
    small {
      margin: 0;
      color: #7e8a9f;
      font-size: 11px;
      line-height: 1.65;
    }

    > small {
      display: block;
      margin-top: 7px;
      color: #64748b;
    }
  }

  .ai-credit-panel__eyebrow {
    color: #2e7d6a;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.14em;
  }

  .ai-credit-meter {
    height: 7px;
    margin-top: 11px;
    overflow: hidden;
    border-radius: 999px;
    background: #e9eef6;

    i {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #2e7d6a, #5367f8);
      transition: width 180ms ease;
    }
  }

  .ai-credit-panel__value {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;

    article {
      min-width: 0;
      padding: 11px 10px;
      border: 1px solid rgba(218, 226, 239, 0.9);
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.74);
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
      color: #22314a;
      font-size: 13px;
    }

    span {
      margin-top: 5px;
      color: #5367f8;
      font-size: 10px;
      font-weight: 700;
    }

    small {
      margin-top: 5px;
      color: #8490a5;
      font-size: 9px;
    }
  }

  .ai-credit-panel__actions {
    display: grid;
    align-content: center;
    gap: 8px;

    button {
      height: 34px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      border: 1px solid #dbe2f0;
      border-radius: 9px;
      color: #60708b;
      background: #fff;
      font-size: 10px;
      font-weight: 700;
      cursor: pointer;
    }

    button:first-child {
      border-color: transparent;
      color: #fff;
      background: #2e7d6a;
    }
  }

  .mobile-resource-action-strip {
    display: none;
  }

  .resource-mission-board {
    display: grid;
    grid-template-columns: minmax(260px, 0.88fr) minmax(320px, 1.18fr) minmax(240px, 0.72fr);
    gap: 12px;
    margin-bottom: 12px;
    padding: 16px;
    border: 1px solid #dbe6f2;
    border-radius: 14px;
    background:
      linear-gradient(135deg, rgba(83, 103, 248, 0.08), transparent 32%),
      linear-gradient(180deg, #fff, #f8fbff);
    box-shadow: 0 16px 34px rgba(30, 49, 84, 0.07);
  }

  .mission-brief,
  .mission-workflow,
  .material-review-preview {
    min-width: 0;
  }

  .mission-brief__eyebrow,
  .mission-workflow__head span,
  .material-review-preview__head span {
    color: #5367f8;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.14em;
  }

  .mission-brief__title {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    justify-content: space-between;
    margin-top: 5px;

    h2 {
      margin: 0 0 6px;
      color: #1f2b45;
      font-size: 20px;
    }

    p {
      margin: 0;
      color: #7f8a9d;
      font-size: 11px;
      line-height: 1.65;
    }

    strong {
      flex: 0 0 auto;
      padding: 5px 8px;
      border-radius: 999px;
      color: #2e7d6a;
      background: #eaf8f2;
      font-size: 10px;
    }
  }

  .mission-resource-card {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    align-items: center;
    margin-top: 14px;
    padding: 12px;
    border: 1px solid #e1e7f1;
    border-radius: 12px;
    background: #fff;

    small,
    h3,
    p {
      display: block;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    small {
      color: #8a95a8;
      font-size: 10px;
    }

    h3 {
      margin: 4px 0;
      color: #24314a;
      font-size: 15px;
    }

    p {
      margin: 0;
      color: #718096;
      font-size: 10px;
    }

    button {
      height: 32px;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 0 11px;
      border: 0;
      border-radius: 9px;
      color: #fff;
      background: #5367f8;
      font-size: 10px;
      font-weight: 800;
      cursor: pointer;
      white-space: nowrap;
    }
  }

  .mission-reasons {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;

    span {
      max-width: 100%;
      padding: 5px 8px;
      overflow: hidden;
      border-radius: 999px;
      color: #50617f;
      background: #f2f5fb;
      font-size: 10px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .mission-stats {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    margin-top: 12px;

    article {
      min-width: 0;
      padding: 10px;
      border: 1px solid #edf1f6;
      border-radius: 10px;
      background: #fbfcff;
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
      color: #24314a;
      font-size: 15px;
    }

    span {
      margin-top: 4px;
      color: #5367f8;
      font-size: 10px;
      font-weight: 800;
    }

    small {
      margin-top: 4px;
      color: #8a95a8;
      font-size: 9px;
    }
  }

  .mission-workflow {
    padding: 13px;
    border: 1px solid #e1e8f1;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.78);
  }

  .mission-workflow__head {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    justify-content: space-between;

    h3 {
      margin: 5px 0 0;
      color: #24314a;
      font-size: 16px;
    }

    button {
      height: 30px;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 0 10px;
      border: 1px solid #dce2ff;
      border-radius: 9px;
      color: #5367f8;
      background: #f5f7ff;
      font-size: 10px;
      font-weight: 800;
      cursor: pointer;
      white-space: nowrap;
    }
  }

  .mission-steps {
    display: grid;
    gap: 8px;
    margin-top: 12px;

    article {
      min-width: 0;
      display: grid;
      grid-template-columns: 34px minmax(0, 1fr) auto;
      gap: 9px;
      align-items: center;
      padding: 10px;
      border: 1px solid #edf1f6;
      border-radius: 10px;
      background: #fff;
    }

    b {
      width: 34px;
      height: 34px;
      display: grid;
      border-radius: 9px;
      color: #fff;
      background: #2e7d6a;
      font-size: 10px;
      place-items: center;
    }

    strong,
    p {
      display: block;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    strong {
      color: #25324b;
      font-size: 12px;
      white-space: nowrap;
    }

    p {
      display: -webkit-box;
      margin: 3px 0 0;
      color: #7f899b;
      font-size: 10px;
      line-height: 1.45;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }

    button {
      height: 28px;
      padding: 0 9px;
      border: 1px solid #dbe2f0;
      border-radius: 8px;
      color: #60708b;
      background: #fafbfc;
      font-size: 9px;
      cursor: pointer;
      white-space: nowrap;
    }
  }

  .material-review-preview {
    padding: 13px;
    border: 1px solid #e1e8f1;
    border-radius: 12px;
    background: #fff;
  }

  .material-review-preview__head {
    h3 {
      margin: 5px 0 5px;
      color: #24314a;
      font-size: 16px;
    }

    p {
      margin: 0;
      color: #7f899b;
      font-size: 10px;
      line-height: 1.6;
    }
  }

  .review-preview-grid {
    display: grid;
    gap: 8px;
    margin-top: 12px;

    article {
      min-width: 0;
      padding: 10px;
      border: 1px solid #edf1f6;
      border-radius: 10px;
      background: #f8fafc;
    }

    span,
    strong,
    small {
      display: block;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: #5367f8;
      font-size: 9px;
      font-weight: 800;
    }

    strong {
      margin-top: 4px;
      color: #25324b;
      font-size: 11px;
    }

    small {
      margin-top: 4px;
      color: #8a95a8;
      font-size: 9px;
    }
  }

  .resource-overview {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 14px;

    article {
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 56px;
      padding: 10px 12px;
      border: 1px solid #e4e8f1;
      border-radius: 14px;
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
      margin-top: 2px;
      color: #29364d;
      font-size: 18px;
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

  .generated-package-panel {
    margin-top: 12px;
    padding: 16px;
    border: 1px solid #dde8ef;
    border-radius: 12px;
    background:
      linear-gradient(135deg, rgba(46, 125, 106, 0.08), transparent 36%),
      linear-gradient(180deg, #fff, #f8fbff);
    box-shadow: 0 10px 28px rgba(36, 55, 84, 0.05);
  }

  .generated-package-head {
    display: flex;
    gap: 16px;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 12px;

    span {
      color: #2e7d6a;
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.14em;
    }

    h2 {
      margin: 5px 0 4px;
      color: #25324b;
      font-size: 18px;
    }

    p {
      margin: 0;
      color: #7f899b;
      font-size: 11px;
      line-height: 1.65;
    }

    > button {
      height: 32px;
      padding: 0 11px;
      border: 1px solid #dbe2f0;
      border-radius: 9px;
      color: #60708b;
      background: #fff;
      font-size: 10px;
      font-weight: 700;
      cursor: pointer;

      &:disabled {
        cursor: wait;
        opacity: 0.68;
      }
    }
  }

  .generated-package-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .generated-package-card {
    min-width: 0;
    padding: 14px;
    border: 1px solid #e1e8f1;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.92);
  }

  .generated-package-top,
  .generated-package-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .generated-package-top {
    span {
      padding: 3px 7px;
      border-radius: 999px;
      color: #2e7d6a;
      background: #eaf8f2;
      font-size: 9px;
      font-weight: 800;
    }

    small {
      color: #98a1b1;
      font-size: 9px;
    }
  }

  .generated-package-card h3 {
    margin: 11px 0 5px;
    overflow: hidden;
    color: #27344c;
    font-size: 15px;
    line-height: 1.35;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .generated-package-card > p {
    margin: 0;
    overflow: hidden;
    color: #7f8a9d;
    font-size: 10px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .generated-trust-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 9px;

    span {
      padding: 4px 7px;
      border-radius: 999px;
      color: #50617f;
      background: #f2f5fb;
      font-size: 9px;
      font-weight: 700;
    }

    span:first-child {
      color: #2e7d6a;
      background: #eaf8f2;
    }
  }

  .generated-package-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin-top: 12px;

    article {
      min-width: 0;
      padding: 9px;
      border: 1px solid #edf1f6;
      border-radius: 9px;
      background: #f8fafc;
    }

    strong,
    span {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      color: #25324b;
      font-size: 13px;
    }

    span {
      margin-top: 3px;
      color: #8a95a8;
      font-size: 9px;
    }
  }

  .generated-artifact-list {
    display: grid;
    gap: 7px;
    margin-top: 12px;

    button {
      min-width: 0;
      display: grid;
      grid-template-columns: 64px minmax(0, 1fr) 48px;
      gap: 8px;
      align-items: center;
      min-height: 34px;
      padding: 7px 9px;
      border: 1px solid #edf1f6;
      border-radius: 9px;
      color: #61708a;
      background: #fbfcff;
      cursor: pointer;
      text-align: left;
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
      color: #5367f8;
      font-size: 9px;
      font-weight: 800;
    }

    b {
      color: #334059;
      font-size: 10px;
    }

    small {
      color: #98a1b1;
      font-size: 9px;
      text-align: right;
    }
  }

  .generated-package-actions {
    margin-top: 12px;

    button {
      min-width: 0;
      height: 30px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      flex: 1;
      padding: 0 8px;
      border: 1px solid #e0e5ee;
      border-radius: 8px;
      color: #687389;
      background: #fafbfc;
      font-size: 9px;
      cursor: pointer;

      &:last-child {
        border-color: #dce2ff;
        color: #5367f8;
        background: #f5f7ff;
      }
    }
  }

  .generated-package-empty {
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr) auto;
    gap: 12px;
    align-items: center;
    padding: 14px;
    border: 1px dashed #d7e1ef;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.72);

    > span {
      width: 42px;
      height: 42px;
      display: grid;
      border-radius: 12px;
      color: #2e7d6a;
      background: #eaf8f2;
      place-items: center;
    }

    strong,
    p {
      display: block;
      min-width: 0;
    }

    strong {
      color: #27344c;
      font-size: 13px;
    }

    p {
      margin: 4px 0 0;
      color: #7f899b;
      font-size: 11px;
      line-height: 1.6;
    }

    button {
      height: 32px;
      padding: 0 12px;
      border: 0;
      border-radius: 9px;
      color: #fff;
      background: #2e7d6a;
      font-size: 10px;
      font-weight: 800;
      cursor: pointer;
      white-space: nowrap;
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
    background: radial-gradient(
        circle at right top,
        rgba(83, 103, 248, 0.11),
        transparent 34%
      ),
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
      transition: border-color 160ms ease, box-shadow 160ms ease;

      &:focus-within {
        border-color: #94a3b8;
        box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.08);
      }
    }

    input {
      width: 100%;
      border: 0;
      outline: 0 !important;
      box-shadow: none !important;
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

  .resource-trust-row {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 10px;

    span {
      max-width: 100%;
      padding: 4px 7px;
      overflow: hidden;
      border-radius: 999px;
      color: #61708a;
      background: #f2f5fb;
      font-size: 9px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .resource-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
    margin-top: 12px;

    button {
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      min-width: 0;
      border: 1px solid #e0e5ee;
      border-radius: 8px;
      color: #687389;
      background: #fafbfc;
      font-size: 9px;
      cursor: pointer;
    }

    button.primary {
      grid-column: 1 / -1;
      border-color: transparent;
      color: #fff;
      background: #5367f8;
      font-weight: 800;
    }

    button:nth-child(3),
    button:last-child {
      border-color: #dce2ff;
      color: #5367f8;
      background: #f5f7ff;
    }
  }

  @media (max-width: 1080px) {
    .resource-grid,
    .generated-package-grid,
    .resource-mission-board {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .material-review-preview {
      grid-column: 1 / -1;
    }
  }

  @media (max-width: 720px) {
    .resource-heading,
    .resource-toolbar,
    .resource-flow,
    .generated-package-head {
      align-items: flex-start;
      flex-direction: column;
    }

    .resource-overview,
    .resource-grid,
    .generated-package-grid,
    .generated-package-empty,
    .resource-flow,
    .resource-mission-board,
    .ai-credit-panel,
    .ai-credit-panel__value,
    .quality-strip,
    .flow-steps {
      grid-template-columns: 1fr;
    }

    .generated-package-head > button,
    .generated-package-empty button {
      width: 100%;
    }

    .generated-package-actions {
      align-items: stretch;
      flex-direction: column;
    }

    .mobile-resource-action-strip {
      display: grid;
      gap: 10px;
      margin-bottom: 12px;
      padding: 12px;
      border: 1px solid #dbe6f2;
      border-radius: 12px;
      background: #fff;
      box-shadow: 0 10px 24px rgba(30, 49, 84, 0.06);

      > div:first-child {
        display: grid;
        gap: 3px;
        min-width: 0;
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
        color: #2e7d6a;
        font-size: 10px;
        font-weight: 900;
        letter-spacing: 0.08em;
      }

      strong {
        color: #21304a;
        font-size: 15px;
      }

      small {
        color: #7e8a9f;
        font-size: 11px;
      }

      > div:last-child {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 7px;
      }

      button {
        min-width: 0;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
        border: 1px solid #dbe2f0;
        border-radius: 10px;
        color: #5367f8;
        background: #f7f9ff;
        font-size: 11px;
        font-weight: 900;
        cursor: pointer;
      }
    }

    .mission-brief__title,
    .mission-workflow__head,
    .mission-resource-card,
    .mission-steps article {
      grid-template-columns: 1fr;
    }

    .mission-brief__title,
    .mission-workflow__head {
      flex-direction: column;
    }

    .mission-resource-card button,
    .mission-workflow__head button,
    .mission-steps button {
      width: 100%;
      justify-content: center;
    }

    .generated-artifact-list button {
      grid-template-columns: 56px minmax(0, 1fr);

      small {
        grid-column: 2;
        text-align: left;
      }
    }
  }

  .ai-credit-panel,
  .mobile-resource-action-strip,
  .resource-mission-board,
  .resource-flow,
  .quality-strip,
  .generated-package-panel {
    display: none;
  }

  .course-resources {
    animation: resource-enter 0.18s ease both;
  }

  .resource-heading {
    padding-bottom: 14px;

    h1 {
      margin: 0 0 6px;
      color: #101828;
      font-size: 26px;
      letter-spacing: 0;
    }

    p {
      max-width: 660px;
      color: #667085;
      font-size: 13px;
      line-height: 1.65;
    }

    .resource-heading__actions button {
      height: 38px;
      border-radius: 999px;
      background: #6366f1;
      box-shadow: 0 10px 22px rgba(99, 102, 241, 0.18);
      transition: transform 160ms ease, background 160ms ease;

      &:hover {
        background: #4f46e5;
        transform: translateY(-1px);
      }
    }

    .resource-heading__actions .ghost {
      color: #475467;
      background: #fff;
      box-shadow: none;

      &:hover {
        color: #4f46e5;
        background: #f8faff;
      }
    }
  }

  .resource-overview {
    margin: 0 0 14px;

    article {
      min-height: 58px;
      padding: 10px 14px;
      border-radius: 16px;
    }

    .overview-icon {
      width: 34px;
      height: 34px;
      border-radius: 12px;
    }

    small {
      font-size: 11px;
    }

    strong {
      margin-top: 2px;
      font-size: 18px;
    }
  }

  .generated-package-panel {
    margin: 0 0 14px;
    padding: 14px 16px;
    border-radius: 16px;
    background: #fff;
  }

  .generated-package-head {
    h2 {
      margin: 3px 0;
      font-size: 18px;
    }

    p {
      font-size: 12px;
      line-height: 1.5;
    }
  }

  .generated-package-empty {
    padding: 14px;
    border-radius: 13px;
    background: #f8fafc;
  }

  .resource-library-shell {
    display: block;
    align-items: start;
  }

  .resource-library-main,
  .resource-inspector {
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 16px;
    background: #fff;
    box-shadow: 0 10px 26px rgba(15, 23, 42, 0.035);
  }

  .resource-library-main {
    padding: 14px;
  }

  .resource-library-main .resource-toolbar {
    margin: 0 0 10px;
    gap: 10px;

    label {
      height: 38px;
      border-radius: 999px;
      background: #f8fafc;
    }

    > div {
      padding: 4px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 999px;
      background: #f8fafc;
    }

    > div button {
      height: 28px;
      border: 0;
      border-radius: 999px;
      background: transparent;
      font-size: 12px;

      &.active {
        color: #6366f1;
        background: #fff;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.06);
      }
    }
  }

  .resource-library-main .resource-grid {
    grid-template-columns: 1fr;
    gap: 7px;
  }

  .resource-library-main .resource-card {
    position: relative;
    display: grid;
    grid-template-columns: 40px minmax(0, 1fr) minmax(108px, auto) 46px;
    gap: 6px 12px;
    align-items: center;
    min-height: 66px;
    padding: 9px 12px;
    border-color: transparent;
    border-radius: 13px;
    background: #fbfcff;
    cursor: pointer;
    box-shadow: none;

    &:hover,
    &.active {
      border-color: rgba(99, 102, 241, 0.18);
      background: #fff;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
      transform: translateY(-1px);
    }
  }

  .resource-library-main .resource-card__top {
    grid-column: 2 / span 3;
    justify-content: flex-start;
    gap: 8px;
  }

  .resource-library-main .resource-file-icon {
    grid-column: 1;
    grid-row: 1 / span 4;
    margin-top: 0;
  }

  .resource-library-main .resource-card h2 {
    grid-column: 2;
    margin: 0;
    color: #101828;
    font-size: 14px;
    line-height: 1.25;
  }

  .resource-library-main .resource-card p {
    grid-column: 2;
    min-height: 0;
    overflow: hidden;
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .resource-library-main .resource-path,
  .resource-library-main .resource-trust-row {
    grid-column: 2 / span 2;
    margin-top: 0;
    padding-top: 0;
    border-top: 0;
  }

  .resource-library-main .resource-path {
    min-height: 0;
  }

  .resource-library-main .resource-trust-row {
    display: none;
  }

  .resource-library-main .resource-meta {
    grid-column: 3;
    grid-row: 2 / span 2;
    display: grid;
    gap: 4px;
    justify-items: end;
    margin-top: 0;
    padding-top: 0;
    border-top: 0;
    white-space: nowrap;
  }

  .resource-card__cta {
    grid-column: 4;
    grid-row: 2 / span 2;
    justify-self: end;
    padding: 5px 9px;
    border-radius: 999px;
    color: #4f46e5;
    background: rgba(79, 70, 229, 0.08);
    font-size: 12px;
    font-weight: 700;
  }

  .resource-library-main .resource-checks {
    display: none;
  }

  .resource-library-main .resource-actions {
    display: none;
  }

  .resource-list-more {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-top: 10px;
    padding: 10px;
    border: 1px dashed rgba(99, 102, 241, 0.22);
    border-radius: 14px;
    background: #f8faff;

    span {
      color: #667085;
      font-size: 12px;
    }

    button {
      height: 32px;
      padding: 0 13px;
      border: 1px solid rgba(99, 102, 241, 0.22);
      border-radius: 999px;
      color: #4f46e5;
      background: #fff;
      cursor: pointer;
      font-size: 12px;
      font-weight: 700;
      transition:
        transform 150ms ease,
        border-color 150ms ease,
        box-shadow 150ms ease;

      &:hover {
        border-color: rgba(99, 102, 241, 0.42);
        box-shadow: 0 8px 18px rgba(99, 102, 241, 0.1);
        transform: translateY(-1px);
      }
    }
  }

  .resource-inspector {
    position: sticky;
    top: 82px;
    display: grid;
    gap: 14px;
    padding: 18px;
  }

  .resource-inspector__head {
    span {
      color: #6366f1;
      font-size: 12px;
      font-weight: 700;
    }

    h2 {
      margin: 7px 0 6px;
      color: #101828;
      font-size: 18px;
      line-height: 1.35;
    }

    p {
      margin: 0;
      color: #667085;
      font-size: 13px;
      line-height: 1.55;
    }
  }

  .resource-inspector__nodes {
    strong {
      display: block;
      margin-bottom: 8px;
      color: #101828;
      font-size: 13px;
    }

    div {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    span {
      padding: 5px 8px;
      border-radius: 999px;
      color: #475467;
      background: #f2f4f7;
      font-size: 12px;
    }
  }

  .resource-inspector section {
    strong {
      display: block;
      margin-bottom: 8px;
      color: #101828;
      font-size: 13px;
    }

    ol {
      display: grid;
      gap: 7px;
      margin: 0;
      padding-left: 18px;
      color: #667085;
      font-size: 12px;
      line-height: 1.55;
    }

    button {
      width: 100%;
      margin-bottom: 7px;
      padding: 9px 10px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 12px;
      color: #475467;
      background: #f8fafc;
      text-align: left;
      cursor: pointer;
      font-size: 12px;
      line-height: 1.45;
    }
  }

  .resource-inspector__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    button {
      height: 34px;
      padding: 0 12px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 999px;
      color: #475467;
      background: #fff;
      cursor: pointer;
      font-size: 12px;
      font-weight: 650;

      &.primary {
        color: #fff;
        border-color: #6366f1;
        background: #6366f1;
      }
    }
  }

  .resource-inspector--drawer {
    border: 0;
    box-shadow: none;
    padding: 0;
  }

  .resource-tool-drawer {
    display: grid;
    gap: 14px;
    color: #101828;
  }

  .tool-section {
    padding: 14px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 16px;
    background: #fff;
  }

  .tool-section__head {
    margin-bottom: 12px;

    span {
      color: #4f46e5;
      font-size: 12px;
      font-weight: 750;
    }

    p {
      margin: 4px 0 0;
      color: #667085;
      font-size: 12px;
      line-height: 1.5;
    }
  }

  .tool-section__head--row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;

    button {
      height: 30px;
      padding: 0 11px;
      border: 1px solid rgba(99, 102, 241, 0.18);
      border-radius: 999px;
      color: #4f46e5;
      background: #f8faff;
      cursor: pointer;
      font-size: 12px;
      font-weight: 700;

      &:disabled {
        cursor: wait;
        opacity: 0.6;
      }
    }
  }

  .tool-action-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;

    button {
      min-width: 0;
      display: grid;
      grid-template-columns: 30px minmax(0, 1fr);
      gap: 8px;
      align-items: center;
      min-height: 64px;
      padding: 10px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 14px;
      color: #475467;
      background: #f8fafc;
      cursor: pointer;
      text-align: left;
      transition:
        transform 150ms ease,
        border-color 150ms ease,
        box-shadow 150ms ease;

      &:hover:not(:disabled) {
        border-color: rgba(99, 102, 241, 0.26);
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
      width: 30px;
      height: 30px;
      padding: 7px;
      border-radius: 10px;
      color: #4f46e5;
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
      color: #101828;
      font-size: 12px;
    }

    small {
      color: #667085;
      font-size: 11px;
    }
  }

  .tool-stat-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
      color: #101828;
      font-size: 17px;
    }

    span {
      margin-top: 3px;
      color: #667085;
      font-size: 12px;
    }
  }

  .tool-quality-list {
    display: grid;
    gap: 8px;

    article {
      display: grid;
      grid-template-columns: 32px minmax(0, 1fr);
      gap: 9px;
      align-items: center;
      padding: 9px 10px;
      border-radius: 13px;
      background: #f8fafc;
    }

    svg {
      width: 32px;
      height: 32px;
      padding: 8px;
      border-radius: 10px;
      color: #4f46e5;
      background: #eef2ff;
    }

    strong,
    span {
      display: block;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      color: #101828;
      font-size: 12px;
    }

    span {
      margin-top: 3px;
      color: #667085;
      font-size: 11px;
    }
  }

  .tool-package-list {
    display: grid;
    gap: 9px;

    article {
      display: grid;
      gap: 9px;
      padding: 11px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 14px;
      background: #f8fafc;
    }

    strong,
    span {
      display: block;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      color: #101828;
      font-size: 13px;
    }

    span {
      margin-top: 4px;
      color: #667085;
      font-size: 11px;
    }

    article > div:last-child {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    button {
      height: 30px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 0 10px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 999px;
      color: #475467;
      background: #fff;
      cursor: pointer;
      font-size: 11px;
    }

    .tool-package-topic {
      width: 100%;
      height: auto;
      padding: 0;
      border: 0;
      border-radius: 0;
      background: transparent;
      text-align: left;
    }
  }

  .generated-package-preview {
    display: grid;
    gap: 18px;
    color: #101828;

    > header span {
      color: #4f46e5;
      font-size: 11px;
      font-weight: 750;
    }

    > header h2 {
      margin: 7px 0 5px;
      font-size: 20px;
      line-height: 1.4;
    }

    > header p {
      margin: 0;
      color: #667085;
      font-size: 12px;
    }

    > footer {
      display: flex;
      justify-content: flex-end;
      gap: 8px;

      button {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        height: 36px;
        padding: 0 14px;
        border: 1px solid rgba(15, 23, 42, 0.08);
        border-radius: 10px;
        color: #475467;
        background: #fff;
        cursor: pointer;
        font-size: 12px;
        font-weight: 700;

        &.primary {
          border-color: #4f46e5;
          color: #fff;
          background: #4f46e5;
        }
      }
    }
  }

  .generated-package-preview__files {
    display: grid;
    gap: 10px;

    article {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 9px 12px;
      padding: 13px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 14px;
      background: #f8fafc;
    }

    strong,
    span {
      display: block;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      font-size: 13px;
    }

    span {
      margin-top: 3px;
      color: #667085;
      font-size: 11px;
    }

    p {
      grid-column: 1 / -1;
      max-height: 66px;
      margin: 0;
      overflow: hidden;
      color: #475467;
      font-size: 12px;
      line-height: 1.8;
    }

    button {
      grid-column: 2;
      grid-row: 1;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      align-self: center;
      height: 32px;
      padding: 0 10px;
      border: 1px solid rgba(99, 102, 241, 0.18);
      border-radius: 9px;
      color: #4f46e5;
      background: #fff;
      cursor: pointer;
      font-size: 11px;
      font-weight: 700;
    }
  }

  .tool-empty {
    padding: 12px;
    border-radius: 14px;
    background: #f8fafc;

    strong {
      color: #101828;
      font-size: 13px;
    }

    p {
      margin: 5px 0 11px;
      color: #667085;
      font-size: 12px;
      line-height: 1.55;
    }

    button {
      height: 32px;
      padding: 0 12px;
      border: 0;
      border-radius: 999px;
      color: #fff;
      background: #6366f1;
      cursor: pointer;
      font-size: 12px;
      font-weight: 700;
    }
  }

  @keyframes resource-enter {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 1180px) {
    .resource-library-shell {
      grid-template-columns: 1fr;
    }

    .resource-inspector {
      display: none;
    }
  }

  @media (max-width: 760px) {
    .resource-library-main .resource-card {
      grid-template-columns: 38px minmax(0, 1fr);
    }

    .resource-library-main .resource-meta,
    .resource-library-main .resource-actions {
      grid-column: 2;
      grid-row: auto;
      width: 100%;
    }

    .resource-list-more {
      align-items: stretch;
      flex-direction: column;

      button {
        width: 100%;
      }
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .course-resources {
      animation: none;
    }

    .resource-library-main .resource-card,
    .resource-heading__actions button,
    .resource-list-more button,
    .tool-action-grid button {
      transition: none;
    }

    .resource-library-main .resource-card:hover,
    .resource-library-main .resource-card.active,
    .resource-heading__actions button:hover,
    .resource-list-more button:hover,
    .tool-action-grid button:hover {
      transform: none;
    }
  }
</style>
