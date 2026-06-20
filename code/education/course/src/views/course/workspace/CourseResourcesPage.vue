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
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';
  import {
    fetchRecentGeneratedPackages,
    type RecentGeneratedPackage,
    type ResourceKind,
  } from '@/api/resource-generation';
  import { getToken } from '@/utils/auth';
  import axios from 'axios';

  const route = useRoute();
  const router = useRouter();
  const query = ref('');
  const activeType = ref<'全部' | CourseResourceItem['type']>('全部');
  const recentPackages = ref<RecentGeneratedPackage[]>([]);
  const loadingRecentPackages = ref(false);
  const activeMissionResourceId = ref('');
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
  const resources = computed(() =>
    course.value ? buildCourseResources(course.value) : []
  );
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
  const aiTrialPercent = computed(() =>
    Math.min((aiTrialUsed.value / aiTrialLimit) * 100, 100)
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
  const aiGenerationValue = computed(() => [
    {
      label: '生成内容',
      value: '讲义 + 练习 + 导图',
      desc: '生成成功后写入课程资料页和图谱核验入口',
    },
    {
      label: '课程绑定',
      value: `${course.value?.chapters.length || 0} 章上下文`,
      desc: '自动带入章节、知识点和交付标准',
    },
    {
      label: '节省时间',
      value: '约 30 分钟 / 次',
      desc: '减少重复整理，把时间留给讲评和追问',
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
        label: '图谱节点线索',
        value: `${graphNodeTotal} 个`,
        desc: '每份资料可回跳到课程图谱核验',
      },
      {
        label: '待完成动作',
        value: `${taskTotal} 项`,
        desc: '阅读、练习、追问和复盘连成闭环',
      },
      {
        label: '生成回流',
        value: `${generatedPackagesForCourse.value.length} 包`,
        desc: '保留下载、复核和图谱校验入口',
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

  function resourceMissionScore(item: CourseResourceItem) {
    const lesson = relatedLesson(item);
    const concept = relatedConcept(item);
    return (
      (lesson?.status === 'done' ? 8 : 24) +
      (concept?.misconceptions?.length || 0) * 5 +
      (item.type.includes('练习') ? 10 : 0) +
      Math.max(0, 80 - item.downloads) / 10
    );
  }

  const recommendedResource = computed(() => {
    const candidates = visibleResources.value.length
      ? visibleResources.value
      : resources.value;
    return [...candidates].sort(
      (a, b) => resourceMissionScore(b) - resourceMissionScore(a)
    )[0];
  });

  const activeMissionResource = computed(() => {
    const active = resources.value.find(
      (item) => item.id === activeMissionResourceId.value
    );
    return active || recommendedResource.value;
  });

  const activeMissionPlan = computed(() =>
    activeMissionResource.value
      ? resourcePlan(activeMissionResource.value)
      : undefined
  );

  const missionReasons = computed(() => {
    const item = activeMissionResource.value;
    const plan = activeMissionPlan.value;
    if (!item || !plan) return [];
    const concept = plan.concept;
    return [
      resourceLearningStatus(item),
      concept?.misconceptions?.[0]
        ? `需要澄清：${concept.misconceptions[0]}`
        : `重点补齐：${plan.graphNodes[0]}`,
      `已绑定 ${plan.graphNodes.length} 个图谱节点`,
    ];
  });

  const missionSteps = computed(() => {
    const item = activeMissionResource.value;
    const plan = activeMissionPlan.value;
    if (!item || !plan) return [];
    return [
      {
        key: 'read',
        title: '阅读定位',
        desc: plan.tasks[0],
        action: '生成学习包',
        handler: () => downloadResourceBrief(item),
      },
      {
        key: 'practice',
        title: '配套练习',
        desc: plan.tasks[2] || '完成自测题并记录错因。',
        action: aiTrialRemaining.value ? '生成追练包' : '查看额度',
        handler: () => generateResourceMaterials(item),
      },
      {
        key: 'ask',
        title: 'AI 追问',
        desc: plan.prompts[0],
        action: '打开资料助手',
        handler: () => askAboutResource(item),
      },
      {
        key: 'graph',
        title: '图谱核验',
        desc: `回到课程图谱确认 ${plan.graphNodes.slice(0, 2).join('、')} 的关系。`,
        action: '定位图谱',
        handler: () => locateResourceInGraph(item),
      },
    ];
  });

  const materialReviewPreview = computed(() => {
    const item = activeMissionResource.value;
    const plan = activeMissionPlan.value;
    if (!item || !plan) return [];
    return [
      {
        title: '讲义结构',
        value: `${item.chapter} / ${plan.concept?.title || plan.lesson?.title || item.title}`,
        desc: '先讲定义边界，再放课堂证据和误区订正。',
      },
      {
        title: '练习设计',
        value: `${plan.tasks.length} 项任务`,
        desc: '阅读标注、自测、错因追问和二次复盘都有明确交付。',
      },
      {
        title: '图谱回流',
        value: plan.graphNodes.slice(0, 3).join(' / '),
        desc: '生成后可携带资源 ID、节点 ID 和主题回到图谱核验。',
      },
      {
        title: '文件审查',
        value: 'Markdown / PDF / 导图',
        desc: '下载包内置质量清单，便于检查排版、证据和下一步行动。',
      },
    ];
  });

  function activateResourceMission(item: CourseResourceItem) {
    activeMissionResourceId.value = item.id;
    const board = document.querySelector('.resource-mission-board');
    board?.scrollIntoView({ behavior: 'smooth', block: 'start' });
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

  function formatFileSize(size: number) {
    if (!Number.isFinite(size) || size <= 0) return '0 KB';
    if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
    return `${(size / 1024 / 1024).toFixed(1)} MB`;
  }

  function artifactKindLabel(kind?: ResourceKind) {
    const map: Record<ResourceKind, string> = {
      lecture_markdown: '讲义',
      lecture_pdf: '讲义 PDF',
      practice_markdown: '练习',
      practice_pdf: '练习 PDF',
      mind_map: '思维导图',
      reading_list: '阅读清单',
      case_project: '案例项目',
      video_script: '数字人脚本',
      quality_checklist: '审查清单',
    };
    return kind ? map[kind] || kind : '资料';
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
    router.push(
      courseWorkspaceLocation(course.value.id, 'agent', {
        task: 'reader',
        prompt: `当前课程是《${course.value.title}》。请围绕最近生成的资源包「${pkg.topic}」做资料复核：先列出已生成文件，再指出适合预习、练习、图谱核验和 AI 追问的使用顺序。`,
        packageId: pkg.package_id,
        nodeId: pkg.node_id,
        nodeLabel: pkg.node_label,
        mapType: pkg.map_type,
        resourceId: pkg.resource_id,
        topic: pkg.topic,
        source: 'resource-generation',
      })
    );
  }

  function auditGeneratedPackageInGraph(pkg: RecentGeneratedPackage) {
    if (!course.value) return;
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

  onMounted(loadRecentPackages);
</script>

<template>
  <section v-if="course" class="course-resources">
    <header class="resource-heading">
      <div>
        <span>COURSE LIBRARY</span>
        <h1>课程资料</h1>
        <p>按章节组织课件、讲义、案例和练习，所有资料都保留课程上下文。</p>
      </div>
      <button type="button" @click="openGenerator()">
        <icon-robot />
        <span>AI 生成课程资源</span>
        <small>{{
          aiTrialRemaining ? `剩余 ${aiTrialRemaining} 次` : '升级解锁'
        }}</small>
      </button>
    </header>

    <section class="ai-credit-panel" aria-label="AI 生成试用额度">
      <div class="ai-credit-panel__main">
        <span class="ai-credit-panel__eyebrow">AI GENERATION TRIAL</span>
        <h2>
          {{
            aiTrialRemaining
              ? `剩余 ${aiTrialRemaining} 次试用生成`
              : '试用额度已用完'
          }}
        </h2>
        <p
          >优先把高价值资料生成动作交给
          AI：讲义、练习、笔记骨架和知识卡会带上当前课程上下文。</p
        >
        <div class="ai-credit-meter" aria-hidden="true">
          <i :style="{ width: `${aiTrialPercent}%` }" />
        </div>
        <small
          >已生成 {{ aiTrialUsed }}/{{
            aiTrialLimit
          }}，生成成功后计入本地历史。</small
        >
      </div>
      <div class="ai-credit-panel__value">
        <article v-for="item in aiGenerationValue" :key="item.label">
          <strong>{{ item.value }}</strong>
          <span>{{ item.label }}</span>
          <small>{{ item.desc }}</small>
        </article>
      </div>
      <div class="ai-credit-panel__actions">
        <button type="button" @click="openGenerator('课程资源生成')">
          <icon-robot />
          {{ aiTrialRemaining ? '进入生成工坊' : '查看升级提示' }}
        </button>
        <button type="button" @click="showUpgradePrompt">升级后批量生成</button>
      </div>
    </section>

    <section
      v-if="activeMissionResource && activeMissionPlan"
      class="resource-mission-board"
      aria-label="今日个性化学习闭环"
    >
      <div class="mission-brief">
        <span class="mission-brief__eyebrow">PERSONAL STUDY LOOP</span>
        <div class="mission-brief__title">
          <div>
            <h2>今日个性化学习闭环</h2>
            <p
              >根据当前筛选、课节进度和资料图谱关系，优先完成一份能产生真实交付的学习资料。</p
            >
          </div>
          <strong>{{ resourceLearningStatus(activeMissionResource) }}</strong>
        </div>
        <div class="mission-resource-card">
          <div>
            <small>推荐资料</small>
            <h3>{{ activeMissionResource.title }}</h3>
            <p>{{ activeMissionResource.chapter }} · {{ activeMissionResource.type }}</p>
          </div>
          <button type="button" @click="generateResourceMaterials(activeMissionResource)">
            <icon-robot />
            {{ aiTrialRemaining ? '生成配套资料' : '查看生成额度' }}
          </button>
        </div>
        <div class="mission-reasons">
          <span v-for="reason in missionReasons" :key="reason">{{ reason }}</span>
        </div>
        <div class="mission-stats">
          <article v-for="item in resourceCoverageStats" :key="item.label">
            <strong>{{ item.value }}</strong>
            <span>{{ item.label }}</span>
            <small>{{ item.desc }}</small>
          </article>
        </div>
      </div>

      <div class="mission-workflow">
        <div class="mission-workflow__head">
          <div>
            <span>4-STEP EXECUTION</span>
            <h3>读资料、做练习、问 AI、回图谱</h3>
          </div>
          <button type="button" @click="downloadResourceBrief(activeMissionResource)">
            <icon-download />
            下载学习包
          </button>
        </div>
        <div class="mission-steps">
          <article v-for="(step, index) in missionSteps" :key="step.key">
            <b>{{ String(index + 1).padStart(2, '0') }}</b>
            <div>
              <strong>{{ step.title }}</strong>
              <p>{{ step.desc }}</p>
            </div>
            <button type="button" @click="step.handler()">{{ step.action }}</button>
          </article>
        </div>
      </div>

      <div class="material-review-preview">
        <div class="material-review-preview__head">
          <span>MATERIAL REVIEW</span>
          <h3>资料审查预览</h3>
          <p>生成或下载前先确认目标、内容结构、图谱回流和文件形态。</p>
        </div>
        <div class="review-preview-grid">
          <article v-for="item in materialReviewPreview" :key="item.title">
            <span>{{ item.title }}</span>
            <strong>{{ item.value }}</strong>
            <small>{{ item.desc }}</small>
          </article>
        </div>
      </div>
    </section>

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
          ><small>AI 生成包</small
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

    <section class="resource-flow">
      <div>
        <span>RESOURCE TO GRAPH</span>
        <h2>把资料接入课程图谱</h2>
        <p
          >把章节资料、作业任务和讨论节点统一放进学习路径里，下载、追问、生成和图谱复盘形成同一条闭环。</p
        >
      </div>
      <div class="flow-steps">
        <button type="button" @click="openKnowledgeMap">
          <icon-mind-mapping />
          <strong>查看课程图谱</strong>
          <small>知识 / 问题 / 能力 / 目标</small>
        </button>
        <button type="button" @click="openGenerator('图谱资源生成')">
          <icon-robot />
          <strong>{{
            aiTrialRemaining ? '生成图谱资源' : '升级生成资源'
          }}</strong>
          <small>{{
            aiTrialRemaining ? '生成成功后回流资料页' : '额度用完，查看升级提示'
          }}</small>
        </button>
        <button
          type="button"
          @click="askAboutResource(resources[0])"
          :disabled="!resources[0]"
        >
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

    <section class="generated-package-panel" aria-label="最近生成资源包">
      <div class="generated-package-head">
        <div>
          <span>GENERATED ASSETS</span>
          <h2>最近生成资源包</h2>
          <p
            >真实生成的讲义、练习、导图和审查清单会沉淀到这里，并可回到图谱核验。</p
          >
        </div>
        <button type="button" :disabled="loadingRecentPackages" @click="loadRecentPackages">
          {{ loadingRecentPackages ? '同步中...' : '刷新生成记录' }}
        </button>
      </div>

      <div v-if="generatedPackagesForCourse.length" class="generated-package-grid">
        <article
          v-for="pkg in generatedPackagesForCourse.slice(0, 4)"
          :key="pkg.package_id"
          class="generated-package-card"
        >
          <div class="generated-package-top">
            <span>AI 生成包</span>
            <small>{{ generatedPackageLabel(pkg) }}</small>
          </div>
          <h3>{{ pkg.topic }}</h3>
          <p>{{ pkg.subject }} · {{ pkg.node_label || pkg.resource_id || pkg.package_id }}</p>
          <div class="generated-trust-tags">
            <span>本地生成</span>
            <span>质量清单</span>
            <span>{{ pkg.node_id ? '图谱已绑定' : '待图谱核验' }}</span>
          </div>
          <div class="generated-package-stats">
            <article>
              <strong>{{ pkg.artifacts.length }}</strong>
              <span>文件</span>
            </article>
            <article>
              <strong>{{
                formatFileSize(
                  pkg.artifacts.reduce((sum, artifact) => sum + artifact.file_size, 0)
                )
              }}</strong>
              <span>总大小</span>
            </article>
            <article>
              <strong>闭环</strong>
              <span>资料 + 图谱</span>
            </article>
          </div>
          <div class="generated-artifact-list">
            <button
              v-for="artifact in pkg.artifacts.slice(0, 4)"
              :key="`${pkg.package_id}-${artifact.file_name}`"
              type="button"
              @click="downloadGeneratedArtifact(pkg, artifact)"
            >
              <span>{{ artifactKindLabel(artifact.kind) }}</span>
              <b>{{ artifact.title || artifact.file_name }}</b>
              <small>{{ formatFileSize(artifact.file_size) }}</small>
            </button>
          </div>
          <div class="generated-package-actions">
            <button type="button" @click="downloadGeneratedArtifact(pkg)">
              <icon-download /> 下载首个文件
            </button>
            <button type="button" @click="askAboutGeneratedPackage(pkg)">
              <icon-robot /> 资料复核
            </button>
            <button type="button" @click="auditGeneratedPackageInGraph(pkg)">
              <icon-mind-mapping /> 图谱核验
            </button>
          </div>
        </article>
      </div>
      <div v-else class="generated-package-empty">
        <span><icon-storage /></span>
        <div>
          <strong>还没有生成资源包回流</strong>
          <p>建议先围绕“{{ activeMissionResource?.title || course.title }}”生成第一份讲义、练习和图谱核验包。</p>
        </div>
        <button type="button" @click="openGenerator('课程资料回流生成')">现在生成</button>
      </div>
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
      <article
        v-for="item in visibleResources"
        :key="item.id"
        class="resource-card"
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
        <div class="resource-trust-row">
          <span>课程组审核</span>
          <span>v{{ resourceIndex(item) + 1 }}.{{ item.downloads % 10 }}</span>
          <span>{{ resourceLearningStatus(item) }}</span>
        </div>
        <div class="resource-actions">
          <button type="button" class="primary" @click="activateResourceMission(item)">
            <icon-check-circle /> 开始闭环
          </button>
          <button type="button" @click="downloadResourceBrief(item)">
            <icon-download /> 学习包
          </button>
          <button type="button" @click="locateResourceInGraph(item)">
            <icon-mind-mapping /> 图谱定位
          </button>
          <button type="button" @click="askAboutResource(item)">
            <icon-robot /> 围绕资料提问
          </button>
          <button type="button" @click="generateResourceMaterials(item)">
            <icon-bulb /> 生成配套
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

    > button {
      display: flex;
      gap: 6px;
      align-items: center;
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
</style>
