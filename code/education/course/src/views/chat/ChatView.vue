<script setup lang="ts">
  import { computed, h, onMounted, ref, resolveComponent } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { useUserStore } from '@/store';
  import { useChatStore } from '@/store/chat';
  import {
    deleteReferenceFile,
    fetchReferenceFiles,
    fetchLearningReport,
    type ReferenceFile,
    type ReferenceScopeFilter,
  } from '@/api/rag';
  import LegacyAssistantPanel from './LegacyAssistantPanel.vue';
  import ReferenceFileUploadDialog from './components/ReferenceFileUploadDialog.vue';

  type DrawerKey = 'profile' | 'resources' | 'agents';

  const showUploadModal = ref(false);
  const activeDrawer = ref<DrawerKey | null>(null);
  const files = ref<ReferenceFile[]>([]);
  const loadingFiles = ref(false);
  const filesLoaded = ref(false);
  const resourceLoadError = ref('');
  const learningReport = ref<any | null>(null);
  const loadingReport = ref(false);
  const scopeFilter = ref<ReferenceScopeFilter>('all');
  const scopeFilterOptions = [
    { label: '全部', value: 'all' },
    { label: '课程库', value: 'system' },
    { label: '我的资料', value: 'personal' },
  ];

  const userStore = useUserStore();
  const chatStore = useChatStore();
  const isAdmin = computed(() => userStore.role === 'teacher');
  const drawerVisible = computed({
    get: () => Boolean(activeDrawer.value),
    set: (value: boolean) => {
      if (!value) activeDrawer.value = null;
    },
  });
  const drawerTitle = computed(() => {
    if (activeDrawer.value === 'profile') return 'AI画像构建面板';
    if (activeDrawer.value === 'agents') return '多智能体协作';
    return '课程资料上下文';
  });

  const profileItems = computed(() => {
    const report = learningReport.value;
    const behavior = report?.classroom_behavior_summary || {};
    const weakPoints = Array.isArray(report?.weak_points) ? report.weak_points : [];
    const strengths = Array.isArray(report?.strengths) ? report.strengths : [];
    const insights = Array.isArray(report?.mastery_insights)
      ? report.mastery_insights
      : [];
    return [
      {
        label: '当前目标',
        value: report?.current_goal || '—',
        hint: report?.summary || '完成对话后将自动更新',
      },
      {
        label: '学习偏好',
        value: report?.learning_style || '—',
        hint: strengths[0] || '—',
      },
      {
        label: '薄弱点',
        value: weakPoints.length ? weakPoints.slice(0, 2).join(' / ') : '—',
        hint: insights[0] || '—',
      },
      {
        label: '风险等级',
        value:
          report?.risk_level === 'high'
            ? '较高'
            : report?.risk_level === 'low'
              ? '较低'
              : '中等',
        hint: Array.isArray(report?.recommended_actions)
          ? report.recommended_actions[0] || '—'
          : '—',
      },
      {
        label: '课堂投入',
        value:
          typeof behavior?.recent_avg_lei === 'number'
            ? `${Math.round(behavior.recent_avg_lei * 100)}%`
            : '—',
        hint: behavior?.teacher_note || '—',
      },
      {
        label: '推荐资源',
        value:
          Array.isArray(report?.recommended_resources) && report.recommended_resources.length
            ? report.recommended_resources.slice(0, 2).join(' / ')
            : '—',
        hint: Array.isArray(report?.follow_up_questions)
          ? report.follow_up_questions[0] || '—'
          : '—',
      },
    ];
  });

  const latestAssistantMessage = computed(() => {
    const messages = chatStore.currentMessages || [];
    return [...messages].reverse().find((item: any) => item.role === 'assistant') || null;
  });

  const agentCards = computed(() => {
    const routeTrace = latestAssistantMessage.value?.metrics?.route_trace || [];
    const routeSet = new Set(routeTrace);
    const labels: Record<string, string> = {
      profile_agent: '学习画像专员',
      retrieval_agent: '课程检索专员',
      grading_agent: '练习批改专员',
      tutor_agent: '辅导讲解专员',
      web_research_agent: '联网检索专员',
      safety_review_agent: '事实审查专员',
      semantic_cache: '语义缓存',
      demo_mode: '本地兜底回答',
    };
    const descriptions: Record<string, string> = {
      profile_agent: '根据问答与练习更新画像与掌握度',
      retrieval_agent: '从课程资料库和上传文档中检索证据',
      grading_agent: '按批改模式分析作答与后续练习',
      tutor_agent: '负责概念讲解、图像题解和分步辅导',
      web_research_agent: '在启用联网搜索时补充时效信息',
      safety_review_agent: '做事实性与内容安全复核',
      semantic_cache: '命中缓存，快速返回已验证回答',
      demo_mode: '当前使用本地兜底路径',
    };
    const defaultOrder = [
      'profile_agent',
      'retrieval_agent',
      'grading_agent',
      'tutor_agent',
      'web_research_agent',
      'safety_review_agent',
    ];
    const source = routeTrace.length ? routeTrace : defaultOrder;
    return source.map((key: string) => ({
      name: labels[key] || key,
      text: descriptions[key] || '已参与本轮协作',
      active: routeSet.has(key),
    }));
  });

  const quickActions = computed(() => {
    const report = learningReport.value;
    const questions = Array.isArray(report?.follow_up_questions)
      ? report.follow_up_questions.slice(0, 3)
      : [];
    if (questions.length) return questions;
    return [
      '解析这道题并给我提示',
      '按批改模式检查我的答案',
      '根据薄弱点生成 20 分钟练习',
    ];
  });

  const latestFiles = computed(() => files.value.slice(0, 6));

  const masteryRings = computed(() => {
    const map = learningReport.value?.mastery_map || {};
    return Object.entries(map)
      .slice(0, 4)
      .map(([topic, value]) => ({
        topic,
        percent: Math.round(Math.max(0, Math.min(1, Number(value) || 0)) * 100),
      }));
  });

  const avgMastery = computed(() => {
    if (!masteryRings.value.length) return null;
    const sum = masteryRings.value.reduce((acc, item) => acc + item.percent, 0);
    return Math.round(sum / masteryRings.value.length);
  });

  const activeAgentCount = computed(
    () => agentCards.value.filter((item: { active: boolean }) => item.active).length || 4
  );

  const profileDimensionCount = computed(() => {
    if (masteryRings.value.length) return masteryRings.value.length;
    if (profileItems.value.length >= 6) return 6;
    return 6;
  });

  const heroStats = computed(() => [
    {
      key: 'profile' as DrawerKey,
      label: '学习画像',
      value: `${profileDimensionCount.value} 维`,
      sub: avgMastery.value != null ? `均分 ${avgMastery.value}%` : '持续对话更新',
      icon: 'icon-user',
    },
    {
      key: 'resources' as DrawerKey,
      label: '课程资料',
      value: `${files.value.length} 份`,
      sub: 'RAG 检索上下文',
      icon: 'icon-storage',
    },
    {
      key: 'agents' as DrawerKey,
      label: '协作状态',
      value: `${activeAgentCount.value} 个`,
      sub: '多智能体编排',
      icon: 'icon-robot',
    },
  ]);

  const formatBytes = (size: number) => {
    if (!size) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(
      Math.floor(Math.log(size) / Math.log(1024)),
      units.length - 1
    );
    const value = size / 1024 ** index;
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[index]}`;
  };

  const formatDate = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString();
  };

  const getScopeLabel = (scope?: ReferenceFile['scope']) => {
    if (scope === 'system') return '课程库';
    if (scope === 'personal') return '我的资料';
    return '资料';
  };

  async function loadReferenceFiles() {
    loadingFiles.value = true;
    resourceLoadError.value = '';
    try {
      files.value = await fetchReferenceFiles(scopeFilter.value);
      filesLoaded.value = true;
    } catch (error: any) {
      const st = error?.response?.status;
      const msg = String(error?.message || '');
      if (st === 404 || msg.includes('404')) {
        files.value = [];
        filesLoaded.value = true;
        return;
      }
      files.value = [];
      resourceLoadError.value = '课程资料服务暂不可用，可稍后刷新';
    } finally {
      loadingFiles.value = false;
    }
  }

  async function loadLearningReport(refresh = false) {
    loadingReport.value = true;
    try {
      learningReport.value = await fetchLearningReport(refresh);
    } catch {
      learningReport.value = null;
    } finally {
      loadingReport.value = false;
    }
  }

  async function handleDelete(record: ReferenceFile) {
    try {
      await deleteReferenceFile(record.file_id);
      Message.success('资料已删除');
      await loadReferenceFiles();
    } catch (error: any) {
      Message.error(error?.message || '删除失败');
    }
  }

  const columns = [
    { title: '名称', dataIndex: 'name' },
    {
      title: '类型',
      dataIndex: 'scope',
      render: ({ record }: { record: ReferenceFile }) =>
        getScopeLabel(record.scope),
    },
    {
      title: '大小',
      dataIndex: 'size',
      render: ({ record }: { record: ReferenceFile }) =>
        formatBytes(record.size),
    },
    {
      title: '创建时间',
      dataIndex: 'created',
      render: ({ record }: { record: ReferenceFile }) =>
        record.created ? formatDate(record.created) : '-',
    },
    {
      title: '操作',
      dataIndex: 'actions',
      render: ({ record }: { record: ReferenceFile }) => {
        if (!record.can_manage) return '-';
        return h(
          resolveComponent('a-popconfirm'),
          {
            content: `删除 ${record.name}?`,
            onOk: () => handleDelete(record),
          },
          {
            default: () =>
              h(
                resolveComponent('a-button'),
                { type: 'text', status: 'danger' },
                { default: () => '删除' }
              ),
          }
        );
      },
    },
  ];

  function openDrawer(key: DrawerKey) {
    activeDrawer.value = key;
    if (key === 'profile' && !loadingReport.value && !learningReport.value) {
      loadLearningReport(false);
    }
    if (key === 'resources' && !filesLoaded.value && !loadingFiles.value) {
      loadReferenceFiles();
    }
  }

  function openUploadModal() {
    showUploadModal.value = true;
  }

  function handleOpenUploadFromDrawer() {
    activeDrawer.value = 'resources';
    openUploadModal();
  }

  function handleUploadSuccess() {
    filesLoaded.value = false;
    loadReferenceFiles();
  }

  onMounted(() => {
    void loadLearningReport(false);
    void loadReferenceFiles();
  });
</script>

<template>
  <div class="assistant-workbench">
    <div class="workbench-shell zy-stagger-child">
      <section class="workbench-hero">
        <div class="hero-left">
          <span class="eyebrow">AI 伴学工作台</span>
          <h1>专注对话、批改与个性化辅导</h1>
          <p class="hero-desc">
            基于学习画像与课程资料，多智能体协同为你讲解、批改与生成练习。
          </p>
        </div>
        <div class="hero-deco" aria-hidden="true">
          <div class="deco-sphere deco-sphere--1" />
          <div class="deco-sphere deco-sphere--2" />
          <div class="deco-cube" />
        </div>
        <div class="hero-stats">
          <button
            v-for="stat in heroStats"
            :key="stat.label"
            type="button"
            class="stat-card"
            @click="openDrawer(stat.key)"
          >
            <span class="stat-card__icon">
              <component :is="stat.icon" />
            </span>
            <span class="stat-card__label">{{ stat.label }}</span>
            <strong class="stat-card__value">{{ stat.value }}</strong>
            <small class="stat-card__sub">{{ stat.sub }}</small>
          </button>
        </div>
      </section>

      <main class="chat-stage">
        <LegacyAssistantPanel />
      </main>
    </div>

    <a-drawer
      v-model:visible="drawerVisible"
      :title="drawerTitle"
      :width="420"
      :footer="false"
      unmount-on-close
      class="workbench-drawer"
    >
      <section v-if="activeDrawer === 'profile'" class="drawer-section">
        <div class="drawer-toolbar drawer-toolbar--profile">
          <span class="drawer-meta">{{ loadingReport ? '更新中…' : '基于最近对话与练习' }}</span>
          <a-button size="small" :loading="loadingReport" @click="loadLearningReport(true)">
            刷新画像
          </a-button>
        </div>
        <div v-if="masteryRings.length" class="mastery-rings">
          <div v-for="item in masteryRings" :key="item.topic" class="mastery-ring-item">
            <a-progress
              type="circle"
              :percent="item.percent"
              size="small"
              :width="56"
            />
            <span>{{ item.topic }}</span>
          </div>
        </div>
        <div class="profile-grid">
          <article v-for="item in profileItems" :key="item.label">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <small>{{ item.hint }}</small>
          </article>
        </div>
        <div class="drawer-block">
          <h3>下一步学习动作</h3>
          <div class="quick-action-list">
            <article v-for="item in quickActions" :key="item">
              {{ item }}
            </article>
          </div>
        </div>
      </section>

      <section v-if="activeDrawer === 'resources'" class="drawer-section">
        <div class="resource-upload-card">
          <div>
            <strong>课程资料库</strong>
            <span>
              上传课件、讲义、PDF 或 Markdown，作为 AI 回答的检索上下文。
            </span>
          </div>
          <a-button type="primary" @click="handleOpenUploadFromDrawer">
            <template #icon><icon-upload /></template>
            上传资料
          </a-button>
        </div>
        <div class="drawer-toolbar">
          <a-select
            v-model="scopeFilter"
            :options="scopeFilterOptions"
            @change="loadReferenceFiles"
          />
          <a-button :loading="loadingFiles" @click="loadReferenceFiles">
            刷新
          </a-button>
        </div>
        <a-alert
          v-if="resourceLoadError"
          type="warning"
          :content="resourceLoadError"
          show-icon
        />
        <div v-if="latestFiles.length" class="file-list">
          <article v-for="file in latestFiles" :key="file.file_id">
            <div>
              <strong>{{ file.name }}</strong>
              <span>
                {{ getScopeLabel(file.scope) }} · {{ formatBytes(file.size) }}
              </span>
            </div>
            <small>{{ file.created ? formatDate(file.created) : '-' }}</small>
          </article>
        </div>
        <a-empty v-else description="暂无资料，可先上传课程文档">
          <template #extra>
            <a-button type="primary" @click="handleOpenUploadFromDrawer">
              <template #icon><icon-upload /></template>
              上传课程文档
            </a-button>
          </template>
        </a-empty>
        <a-table
          class="resource-table"
          :columns="columns"
          :data="files"
          :loading="loadingFiles"
          :pagination="{ pageSize: 5, simple: true }"
          row-key="file_id"
          size="small"
        />
      </section>

      <section v-if="activeDrawer === 'agents'" class="drawer-section">
        <div class="agent-list">
          <article
            v-for="agent in agentCards"
            :key="agent.name"
            :class="{ active: agent.active }"
          >
            <span class="agent-dot" />
            <div>
              <strong>{{ agent.name }}</strong>
              <small>{{ agent.text }}</small>
            </div>
          </article>
        </div>
      </section>
    </a-drawer>

    <ReferenceFileUploadDialog
      :visible="showUploadModal"
      :is-admin="isAdmin"
      @update:visible="(value) => (showUploadModal = value)"
      @success="handleUploadSuccess"
    />
  </div>
</template>

<style scoped lang="less">
  .assistant-workbench {
    min-height: 100%;
    padding: 16px 20px 24px;
    color: var(--zy-color-text-primary);
  }

  .workbench-shell {
    border-radius: 24px;
    background: #fff;
    border: 1px solid rgba(99, 102, 241, 0.1);
    box-shadow: 0 20px 48px rgba(99, 102, 241, 0.08);
    overflow: hidden;
  }

  .workbench-hero {
    display: grid;
    grid-template-columns: 1fr auto auto;
    align-items: center;
    gap: 20px;
    padding: 24px 28px;
    background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 38%, #ecfeff 100%);
    border-bottom: 1px solid rgba(99, 102, 241, 0.08);
  }

  .hero-left {
    min-width: 0;

    h1 {
      margin: 8px 0 6px;
      font-size: 26px;
      font-weight: 800;
      line-height: 1.25;
      color: var(--zy-color-text-primary);
    }
  }

  .eyebrow {
    display: inline-block;
    padding: 4px 12px;
    border-radius: var(--zy-radius-pill);
    background: rgba(99, 102, 241, 0.12);
    color: var(--zy-color-brand-hover);
    font-size: var(--zy-text-xs);
    font-weight: 700;
  }

  .hero-desc {
    margin: 0;
    max-width: 420px;
    font-size: var(--zy-text-sm);
    line-height: 1.6;
    color: var(--zy-color-text-secondary);
  }

  .hero-deco {
    position: relative;
    width: 120px;
    height: 100px;
    flex-shrink: 0;
  }

  .deco-sphere {
    position: absolute;
    border-radius: 50%;
    background: linear-gradient(145deg, #a5b4fc, #6366f1);
    box-shadow: 0 12px 28px rgba(99, 102, 241, 0.35);

    &--1 {
      width: 52px;
      height: 52px;
      top: 8px;
      left: 12px;
    }

    &--2 {
      width: 28px;
      height: 28px;
      top: 48px;
      right: 8px;
      background: linear-gradient(145deg, #67e8f9, #0ea5e9);
      box-shadow: 0 8px 20px rgba(14, 165, 233, 0.3);
    }
  }

  .deco-cube {
    position: absolute;
    width: 36px;
    height: 36px;
    top: 28px;
    right: 28px;
    border-radius: 10px;
    background: linear-gradient(135deg, #c4b5fd, #8b5cf6);
    transform: rotate(18deg);
    box-shadow: 0 10px 24px rgba(139, 92, 246, 0.35);
  }

  .hero-stats {
    display: flex;
    gap: 10px;
    flex-shrink: 0;
  }

  .stat-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
    width: 108px;
    min-height: 118px;
    padding: 14px 12px;
    border: 1px solid rgba(255, 255, 255, 0.8);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.88);
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.1);
    cursor: pointer;
    text-align: left;
    transition:
      transform var(--zy-duration-fast) ease,
      box-shadow var(--zy-duration-fast) ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: var(--zy-shadow-card-hover);
    }
  }

  .stat-card__icon {
    width: 32px;
    height: 32px;
    border-radius: 10px;
    background: var(--zy-bg-tag);
    color: var(--zy-color-brand);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    margin-bottom: 4px;
  }

  .stat-card__label {
    font-size: 11px;
    color: var(--zy-color-text-secondary);
  }

  .stat-card__value {
    font-size: 18px;
    font-weight: 800;
    color: var(--zy-color-text-primary);
    line-height: 1.2;
  }

  .stat-card__sub {
    font-size: 10px;
    color: var(--zy-color-text-secondary);
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .chat-stage {
    min-width: 0;
    min-height: 520px;
    overflow: hidden;
    background: #fff;
  }

  .drawer-section {
    display: grid;
    gap: 14px;
  }

  .drawer-block h3 {
    margin: 0 0 10px;
    color: var(--zy-color-text-primary);
    font-size: 15px;
  }

  .mastery-rings {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    padding: 12px;
    background: #f8fafc;
    border-radius: 12px;
  }

  .mastery-ring-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--zy-color-text-secondary);
    text-align: center;
    max-width: 72px;
  }

  .profile-grid {
    display: grid;
    gap: 8px;

    article {
      min-height: 76px;
      padding: 10px;
      border: 1px solid rgba(99, 102, 241, 0.12);
      border-radius: var(--zy-radius-sm);
      background: linear-gradient(135deg, #fbfaff, #f5f3ff);
    }

    span,
    small {
      display: block;
      color: var(--zy-color-text-secondary);
      font-size: 12px;
    }

    strong {
      display: block;
      margin: 5px 0;
      color: var(--zy-color-text-primary);
      font-size: 15px;
    }
  }

  .quick-action-list,
  .file-list,
  .agent-list {
    display: grid;
    gap: 8px;
  }

  .quick-action-list article,
  .file-list article,
  .agent-list article {
    padding: 10px;
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: var(--zy-radius-sm);
    background: #fbfaff;
  }

  .resource-upload-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px;
    border: 1px solid rgba(99, 102, 241, 0.14);
    border-radius: var(--zy-radius-sm);
    background: linear-gradient(135deg, #fbfaff, #eef2ff);

    strong,
    span {
      display: block;
    }

    strong {
      margin-bottom: 4px;
      color: var(--zy-color-text-primary);
      font-size: 14px;
      font-weight: 700;
    }

    span {
      color: var(--zy-color-text-secondary);
      font-size: 12px;
      line-height: 1.5;
    }
  }

  .drawer-toolbar {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 8px;
  }

  .drawer-meta {
    color: var(--zy-color-text-secondary);
    font-size: 12px;
  }

  .file-list article {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .file-list strong,
  .agent-list strong {
    display: block;
    max-width: 260px;
    overflow: hidden;
    color: var(--zy-color-text-primary);
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .file-list span,
  .file-list small,
  .agent-list small {
    display: block;
    color: var(--zy-color-text-secondary);
    font-size: 12px;
  }

  .agent-list article {
    display: flex;
    gap: 10px;
    align-items: flex-start;

    &.active {
      border-color: rgba(99, 102, 241, 0.28);
      background: linear-gradient(135deg, #f5f3ff, #eef2ff);

      .agent-dot {
        background: var(--zy-color-brand);
        box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.12);
      }
    }
  }

  .agent-dot {
    flex: 0 0 auto;
    width: 9px;
    height: 9px;
    margin-top: 4px;
    border-radius: 999px;
    background: #b5c3cc;
  }

  :deep(.workbench-drawer .arco-drawer-header) {
    border-bottom-color: rgba(99, 102, 241, 0.12);
    background: #fbfaff;
  }

  @media (max-width: 1100px) {
    .workbench-hero {
      grid-template-columns: 1fr;
    }

    .hero-deco {
      display: none;
    }

    .hero-stats {
      width: 100%;
      justify-content: stretch;
    }

    .stat-card {
      flex: 1;
      width: auto;
    }
  }

  @media (max-width: 640px) {
    .assistant-workbench {
      padding: 10px;
    }

    .workbench-shell {
      border-radius: 18px;
    }

    .workbench-hero {
      padding: 18px 16px;
    }

    .hero-stats {
      flex-direction: column;
    }

    .stat-card {
      width: 100%;
      min-height: auto;
      flex-direction: row;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }

    .resource-upload-card {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>
