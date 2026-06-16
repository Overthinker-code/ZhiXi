<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    IconBulb,
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
  const viewMode = ref<'network' | 'structure'>('structure');
  const activeRelation = ref<'全部' | '父子关系' | '前后置关系' | '关联关系' | '资料支撑' | '任务驱动'>('全部');
  const selectedNodeId = ref('course-root');
  const showResourceLinks = ref(true);
  const showLearningPath = ref(true);
  const canvasZoom = ref(1);

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
  const chapterCount = computed(() => course.value?.chapters.length || 0);
  const conceptCount = computed(() => course.value?.concepts.flatMap((item) => item.points).length || 0);
  const actionBadgeCount = computed(() =>
    structureBranches.value.reduce((sum, item) => sum + item.resourceBadges.length, 0)
  );

  function nodeClass(node: CourseKnowledgeNode) {
    return [`node-${node.type}`, `node-weight-${node.weight}`, { selected: selectedNode.value?.id === node.id }];
  }

  function selectNode(node: CourseKnowledgeNode) {
    selectedNodeId.value = node.id;
  }

  function changeZoom(delta: number) {
    canvasZoom.value = Math.min(1.45, Math.max(0.72, Number((canvasZoom.value + delta).toFixed(2))));
  }

  function askGraphAgent(action: string) {
    if (!course.value || !activeMap.value) return;
    router.push(
      courseWorkspaceLocation(course.value.id, 'agent', {
        task: 'map',
        forceAgent: 'graph_agent',
        prompt: [
          `当前课程：${course.value.title}`,
          `当前图谱：${activeMap.value.title}`,
          `操作目标：${action}`,
          '请基于当前课程章节、任务、能力目标和薄弱点，输出可执行的学习路径，并说明每一步的依据。',
        ].join('\n'),
      })
    );
  }

  function goResourceGenerator() {
    if (!course.value || !activeMap.value) return;
    router.push({
      name: 'StudentCourseResourceGenerator',
      params: { courseId: course.value.id },
      query: {
        subject: course.value.title,
        topic: activeMap.value.title,
        source: 'knowledge-map',
      },
    });
  }

  function goCourseContent() {
    if (!course.value) return;
    router.push(courseWorkspaceLocation(course.value.id, 'content'));
  }
</script>

<template>
  <section v-if="course && activeMap" class="knowledge-page">
    <header class="knowledge-hero">
      <div>
        <span>COURSE KNOWLEDGE GRAPH</span>
        <h1>课程图谱中心</h1>
        <p>把章节、问题、能力目标与 AI 辅导入口组织成一张可操作的学习地图。</p>
      </div>
      <div class="hero-actions">
        <button type="button" @click="goResourceGenerator">
          <icon-file /> 从图谱生成资源
        </button>
        <button type="button" @click="askGraphAgent('解释当前图谱并生成下一步学习计划')">
          <icon-robot /> 让小智解读
        </button>
      </div>
    </header>

    <div class="knowledge-summary">
      <article>
        <small>章节节点</small>
        <strong>{{ chapterCount }}</strong>
        <span>覆盖整门课程结构</span>
      </article>
      <article>
        <small>知识点</small>
        <strong>{{ conceptCount }}</strong>
        <span>含重点、难点与先修关系</span>
      </article>
      <article>
        <small>图谱模式</small>
        <strong>{{ maps.length }}</strong>
        <span>知识 / 问题 / 能力 / 目标 / 辅导</span>
      </article>
      <article>
        <small>学习动作</small>
        <strong>{{ actionBadgeCount }}</strong>
        <span>讲义、自测、案例、导图与讨论统一编排</span>
      </article>
    </div>

    <div class="knowledge-shell">
      <aside class="map-sidebar">
        <label class="map-search">
          <icon-search />
          <input v-model="keyword" type="search" placeholder="检索分类或知识点" />
        </label>

        <div class="map-tabs">
          <button
            v-for="item in maps"
            :key="item.type"
            type="button"
            :class="{ active: activeType === item.type }"
            @click="activeType = item.type"
          >
            <icon-mind-mapping />
            <span>
              <strong>{{ item.title }}</strong>
              <small>{{ item.nodes.length }} 节点</small>
            </span>
          </button>
        </div>

        <div class="relation-filter">
          <strong>关系类型</strong>
          <button
            v-for="relation in relationTypes"
            :key="relation"
            type="button"
            :class="{ active: activeRelation === relation }"
            @click="activeRelation = relation"
          >
            {{ relation }}
          </button>
        </div>
      </aside>

      <main class="map-canvas-card">
        <div class="map-toolbar">
          <div>
            <span>{{ activeMap.title }}</span>
            <strong>{{ activeMap.description }}</strong>
          </div>
          <div class="view-switch" aria-label="图谱视图">
            <button
              type="button"
              :class="{ active: viewMode === 'structure' }"
              @click="viewMode = 'structure'"
            >
              结构图
            </button>
            <button
              type="button"
              :class="{ active: viewMode === 'network' }"
              @click="viewMode = 'network'"
            >
              多图谱
            </button>
          </div>
          <div class="focus-tags">
            <em v-for="tag in activeMap.focusTags" :key="tag">{{ tag }}</em>
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
              :style="{ '--branch-offset': `${index * 4}px` }"
              tabindex="0"
              @click="selectedNodeId = `chapter-${index}`"
              @keydown.enter="selectedNodeId = `chapter-${index}`"
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

        <svg
          v-else
          class="map-canvas"
          :style="{ transform: `scale(${canvasZoom})` }"
          viewBox="0 0 940 470"
          role="img"
          :aria-label="activeMap.title"
        >
          <defs>
            <linearGradient id="nodePrimary" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0%" stop-color="#6474ff" />
              <stop offset="100%" stop-color="#35b8e8" />
            </linearGradient>
          </defs>
          <line
            v-for="link in visibleLinks"
            :key="`${link.source}-${link.target}-${link.relation}`"
            :x1="activeMap.nodes.find((node) => node.id === link.source)?.x"
            :y1="activeMap.nodes.find((node) => node.id === link.source)?.y"
            :x2="activeMap.nodes.find((node) => node.id === link.target)?.x"
            :y2="activeMap.nodes.find((node) => node.id === link.target)?.y"
            :class="`link-${link.relation}`"
          />
          <g
            v-for="node in visibleNodes"
            :key="node.id"
            :transform="`translate(${node.x} ${node.y})`"
            :class="nodeClass(node)"
            tabindex="0"
            @click="selectNode(node)"
            @keydown.enter="selectNode(node)"
          >
            <circle :r="node.weight >= 4 ? 48 : node.weight >= 3 ? 38 : node.weight >= 2 ? 30 : 24" />
            <text text-anchor="middle" dominant-baseline="middle">
              {{ node.label.length > 9 ? `${node.label.slice(0, 8)}…` : node.label }}
            </text>
          </g>
        </svg>

        <div class="map-bottom">
          <div>
            <icon-tags />
            <span>当前显示 {{ visibleNodes.length }} 个节点、{{ visibleLinks.length }} 条关系</span>
          </div>
          <button type="button" @click="askGraphAgent('围绕薄弱节点生成 20 分钟复习路径')">
            <icon-bulb /> 生成复习路径
          </button>
        </div>
      </main>

      <aside class="map-insights">
        <section>
          <strong>节点详情</strong>
          <h3>{{ selectedNode?.label || activeMap.title }}</h3>
          <p>{{ selectedNode?.type === 'resource' ? '该节点代表可继续阅读或下载的课程资料。' : selectedNode?.type === 'task' ? '该节点代表可执行的作业、自测或 AI 学习任务。' : activeMap.description }}</p>
          <div class="node-meta">
            <span>类型：{{ selectedNode?.type || 'graph' }}</span>
            <span>关联：{{ selectedLinks.length }} 条</span>
          </div>
        </section>
        <section>
          <strong>图谱控制</strong>
          <label><input v-model="showLearningPath" type="checkbox" /> 学习路径</label>
          <label><input v-model="showResourceLinks" type="checkbox" /> 关联资源</label>
          <div class="zoom-control">
            <button type="button" @click="changeZoom(-0.08)">-</button>
            <span>{{ Math.round(canvasZoom * 100) }}%</span>
            <button type="button" @click="changeZoom(0.08)">+</button>
          </div>
        </section>
        <section>
          <strong>可执行动作</strong>
          <button type="button" @click="askGraphAgent('解释图谱中的先修关系')">解释先修关系</button>
          <button type="button" @click="askGraphAgent('找出最应该复习的三个知识点')">定位三处薄弱点</button>
          <button type="button" @click="askGraphAgent('基于图谱生成一组自测题')">生成图谱自测</button>
          <button type="button" @click="goCourseContent">回到课堂笔记</button>
        </section>
        <section>
          <strong>资源联动</strong>
          <p>资源中心可按当前图谱主题生成讲义、练习、课堂笔记和知识点卡片。</p>
          <button type="button" @click="goResourceGenerator">生成配套资料</button>
        </section>
      </aside>
    </div>
  </section>
</template>

<style scoped lang="less">
  .knowledge-page {
    color: #17213a;
  }

  .knowledge-hero {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 20px;
    padding: 2px 2px 18px;

    span {
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

  .hero-actions {
    display: flex;
    gap: 8px;

    button {
      height: 36px;
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 0 13px;
      border: 1px solid #dce2ff;
      border-radius: 9px;
      color: #5367f8;
      background: #f5f7ff;
      cursor: pointer;

      &:last-child {
        border-color: transparent;
        color: #fff;
        background: #5367f8;
      }
    }
  }

  .knowledge-summary {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 12px;

    article {
      padding: 15px 16px;
      border: 1px solid #e4e8f1;
      border-radius: 12px;
      background: #fff;
      box-shadow: 0 3px 12px rgba(34, 48, 88, 0.04);
    }

    small,
    strong,
    span {
      display: block;
    }

    small,
    span {
      color: #8e98a9;
      font-size: 10px;
    }

    strong {
      margin: 4px 0;
      color: #29364d;
      font-size: 22px;
    }
  }

  .knowledge-shell {
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr) 238px;
    gap: 12px;
    align-items: stretch;
  }

  .map-sidebar,
  .map-canvas-card,
  .map-insights {
    border: 1px solid #e4e8f1;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 3px 12px rgba(34, 48, 88, 0.04);
  }

  .map-sidebar {
    padding: 12px;
  }

  .map-search {
    height: 34px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 10px;
    border: 1px solid #e1e6ef;
    border-radius: 9px;
    color: #929cad;
    background: #fafbff;

    input {
      min-width: 0;
      width: 100%;
      border: 0;
      outline: 0;
      background: transparent;
      font-size: 10px;
    }
  }

  .map-tabs {
    display: grid;
    gap: 7px;
    margin-top: 12px;

    button {
      display: grid;
      grid-template-columns: 28px minmax(0, 1fr);
      gap: 8px;
      align-items: center;
      padding: 10px;
      border: 1px solid transparent;
      border-radius: 10px;
      color: #798397;
      background: #fafbfc;
      text-align: left;
      cursor: pointer;

      &.active {
        border-color: #dce2ff;
        color: #5367f8;
        background: #f3f5ff;
      }
    }

    strong,
    small {
      display: block;
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

  .relation-filter {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid #edf0f5;

    strong {
      display: block;
      margin-bottom: 8px;
      font-size: 11px;
    }

    button {
      margin: 0 5px 6px 0;
      padding: 5px 8px;
      border: 1px solid #e3e7ef;
      border-radius: 999px;
      color: #7b8598;
      background: #fff;
      font-size: 9px;
      cursor: pointer;

      &.active {
        border-color: #dce2ff;
        color: #5367f8;
        background: #f5f7ff;
      }
    }
  }

  .map-canvas-card {
    min-width: 0;
    overflow: hidden;
  }

  .map-toolbar,
  .map-bottom {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 14px;
    border-bottom: 1px solid #edf0f5;

    span,
    strong {
      display: block;
    }

    span {
      color: #5367f8;
      font-size: 10px;
      font-weight: 700;
    }

    strong {
      margin-top: 3px;
      color: #4c5870;
      font-size: 12px;
      font-weight: 500;
    }
  }

  .view-switch {
    display: inline-flex;
    padding: 3px;
    border: 1px solid #e1e6f4;
    border-radius: 9px;
    background: #f8faff;

    button {
      height: 24px;
      padding: 0 10px;
      border: 0;
      border-radius: 7px;
      color: #758098;
      background: transparent;
      font-size: 10px;
      cursor: pointer;

      &.active {
        color: #fff;
        background: #5367f8;
      }
    }
  }

  .focus-tags {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 5px;

    em {
      padding: 4px 7px;
      border-radius: 999px;
      color: #5367f8;
      background: #eef1ff;
      font-size: 9px;
      font-style: normal;
    }
  }

  .structure-map {
    position: relative;
    min-height: 470px;
    display: grid;
    grid-template-columns: minmax(130px, 0.24fr) 18px minmax(0, 1fr);
    gap: 20px;
    align-items: center;
    padding: 24px 26px;
    overflow: hidden;
    background:
      radial-gradient(circle at 22% 50%, rgba(83, 103, 248, 0.11), transparent 28%),
      linear-gradient(90deg, rgba(229, 234, 246, 0.6) 1px, transparent 1px),
      linear-gradient(rgba(229, 234, 246, 0.6) 1px, transparent 1px);
    background-color: #fbfcff;
    background-size: auto, 34px 34px, 34px 34px;
  }

  .structure-root {
    position: relative;
    z-index: 1;
    justify-self: end;
    display: grid;
    gap: 8px;
    text-align: right;

    span,
    strong {
      display: inline-flex;
      justify-content: flex-end;
      padding: 8px 12px;
      border: 1px solid #bfe5ce;
      border-radius: 999px;
      color: #227a45;
      background: #f0fff6;
      font-size: 13px;
    }

    strong {
      color: #fff;
      background: #4fb86b;
    }
  }

  .structure-trunk {
    width: 4px;
    height: min(410px, 100%);
    border-radius: 999px;
    background: linear-gradient(180deg, #55bf75, #82d7a0);
    box-shadow: 0 0 0 6px rgba(90, 191, 118, 0.08);
  }

  .structure-branches {
    display: grid;
    gap: 10px;
    min-width: 0;
  }

  .structure-branch {
    position: relative;
    display: grid;
    grid-template-columns: minmax(120px, 0.34fr) minmax(0, 1fr) minmax(150px, 0.34fr);
    align-items: center;
    gap: 10px;
    min-height: 42px;
    padding-left: var(--branch-offset);
    border-radius: 9px;
    cursor: pointer;
    outline: none;

    &:hover,
    &:focus-visible {
      background: rgba(83, 103, 248, 0.06);
    }

    &::before {
      position: absolute;
      left: -20px;
      width: 18px;
      height: 2px;
      content: '';
      background: #86d4a1;
    }

    &::after {
      position: absolute;
      left: -24px;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      content: '';
      background: #64c681;
      box-shadow: 0 0 0 4px #e8f8ee;
    }
  }

  .branch-title {
    display: flex;
    align-items: center;
    gap: 7px;

    span {
      color: #8b96aa;
      font-size: 10px;
      font-weight: 800;
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

  .branch-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;

    em {
      min-width: 34px;
      padding: 3px 5px;
      border-radius: 4px;
      color: #fff;
      background: #d84d55;
      font-size: 9px;
      font-style: normal;
      text-align: center;
    }

    .badge-讲义,
    .badge-讨论 {
      background: #7ba4c8;
    }

    .badge-自测 {
      background: #8bd0b0;
    }

    .badge-案例 {
      background: #d86f76;
    }

    .badge-导图 {
      background: #8d7ad9;
    }
  }

  .branch-meta {
    display: grid;
    grid-template-columns: minmax(0, 0.5fr) minmax(0, 1fr) 40px;
    gap: 6px;
    align-items: center;
    color: #8a94a7;
    font-size: 9px;

    span {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      color: #5367f8;
      font-size: 11px;
      text-align: right;
    }
  }

  .map-canvas {
    width: 100%;
    height: 470px;
    display: block;
    transform-origin: center;
    transition: transform 0.18s ease;
    background:
      radial-gradient(circle at center, rgba(83, 103, 248, 0.08), transparent 38%),
      linear-gradient(90deg, rgba(229, 234, 246, 0.55) 1px, transparent 1px),
      linear-gradient(rgba(229, 234, 246, 0.55) 1px, transparent 1px);
    background-color: #fbfcff;
    background-size: auto, 34px 34px, 34px 34px;

    line {
      stroke: #cfd6e8;
      stroke-width: 1.4;
      stroke-dasharray: 4 4;
    }

    .link-父子关系,
    .link-前后置关系 {
      stroke: #6575ff;
      stroke-width: 1.8;
      stroke-dasharray: none;
    }

    .link-资料支撑 {
      stroke: #31b88a;
    }

    .link-任务驱动 {
      stroke: #f6a23c;
    }

    g {
      cursor: pointer;
    }

    circle {
      fill: #fff;
      stroke: #dfe5f5;
      stroke-width: 1.5;
      filter: drop-shadow(0 8px 16px rgba(45, 57, 98, 0.12));
    }

    text {
      max-width: 80px;
      fill: #2c3952;
      font-size: 10px;
      font-weight: 700;
      pointer-events: none;
    }

    .node-chapter circle {
      fill: #f5f7ff;
      stroke: #bfc8ff;
    }

    .node-concept circle {
      fill: #fff;
      stroke: #dfe5f5;
    }

    .node-resource circle {
      fill: #f3fff9;
      stroke: #bcebd8;
    }

    .node-task circle {
      fill: #fff8ef;
      stroke: #f8d7a9;
    }

    .node-ability circle {
      fill: #f5f0ff;
      stroke: #d7c9ff;
    }

    .node-weight-4 circle {
      fill: url(#nodePrimary);
      stroke: transparent;
    }

    .node-weight-4 text {
      fill: #fff;
      font-size: 13px;
    }

    .selected circle {
      stroke: #2563eb;
      stroke-width: 3;
      filter: drop-shadow(0 10px 18px rgba(37, 99, 235, 0.26));
    }
  }

  .map-bottom {
    border-top: 1px solid #edf0f5;
    border-bottom: 0;
    color: #7d879a;
    font-size: 10px;

    > div {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    button {
      height: 30px;
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 0 11px;
      border: 1px solid #dce2ff;
      border-radius: 8px;
      color: #5367f8;
      background: #f5f7ff;
      cursor: pointer;
    }
  }

  .map-insights {
    padding: 12px;

    section + section {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid #edf0f5;
    }

    strong {
      display: block;
      margin-bottom: 6px;
      color: #334059;
      font-size: 12px;
    }

    p {
      margin: 0;
      color: #808a9c;
      font-size: 10px;
      line-height: 1.7;
    }

    h3 {
      margin: 2px 0 6px;
      color: #172033;
      font-size: 16px;
    }

    label {
      display: flex;
      align-items: center;
      gap: 7px;
      margin: 8px 0;
      color: #596579;
      font-size: 11px;
    }

    input {
      accent-color: #5367f8;
    }

    button {
      width: 100%;
      height: 30px;
      margin-top: 6px;
      border: 1px solid #e0e5ee;
      border-radius: 8px;
      color: #5f6b80;
      background: #fafbfc;
      font-size: 10px;
      cursor: pointer;

      &:hover {
        border-color: #dce2ff;
        color: #5367f8;
        background: #f5f7ff;
      }
    }
  }

  .node-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 9px;

    span {
      padding: 4px 7px;
      border-radius: 999px;
      color: #5367f8;
      background: #eef1ff;
      font-size: 9px;
    }
  }

  .zoom-control {
    display: grid;
    grid-template-columns: 30px minmax(0, 1fr) 30px;
    align-items: center;
    gap: 6px;
    margin-top: 8px;

    span {
      text-align: center;
      color: #5367f8;
      font-size: 11px;
      font-weight: 700;
    }

    button {
      margin-top: 0;
      padding: 0;
    }
  }

  @media (max-width: 1180px) {
    .knowledge-shell {
      grid-template-columns: 210px minmax(0, 1fr);
    }

    .map-insights {
      grid-column: 1 / -1;
    }
  }

  @media (max-width: 820px) {
    .knowledge-hero,
    .map-toolbar,
    .map-bottom {
      align-items: flex-start;
      flex-direction: column;
    }

    .hero-actions,
    .knowledge-summary,
    .structure-map,
    .knowledge-shell {
      grid-template-columns: 1fr;
    }

    .structure-map {
      gap: 14px;
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
      border: 1px solid #e4e8f1;
      border-radius: 10px;
      background: #fff;

      &::before,
      &::after {
        display: none;
      }
    }

    .knowledge-summary {
      display: grid;
    }

    .map-canvas {
      height: 390px;
    }
  }
</style>
