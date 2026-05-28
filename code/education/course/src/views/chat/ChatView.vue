<script setup lang="ts">
  import { computed, h, ref, resolveComponent } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { useUserStore } from '@/store';
  import {
    deleteReferenceFile,
    fetchReferenceFiles,
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
  const scopeFilter = ref<ReferenceScopeFilter>('all');
  const scopeFilterOptions = [
    { label: '全部', value: 'all' },
    { label: '课程库', value: 'system' },
    { label: '我的资料', value: 'personal' },
  ];

  const userStore = useUserStore();
  const isAdmin = computed(() => userStore.role === 'teacher');
  const drawerVisible = computed({
    get: () => Boolean(activeDrawer.value),
    set: (value: boolean) => {
      if (!value) activeDrawer.value = null;
    },
  });
  const drawerTitle = computed(() => {
    if (activeDrawer.value === 'profile') return '动态学习画像';
    if (activeDrawer.value === 'agents') return '多智能体协作';
    return '课程资料上下文';
  });

  const profileItems = [
    { label: '知识基础', value: '中等', hint: '关系模型需要迁移训练' },
    { label: '认知风格', value: '例题驱动', hint: '先例题再抽象规则' },
    { label: '易错偏好', value: '完整性约束', hint: '参照完整性最易混淆' },
    { label: '资源偏好', value: '短讲义 + 练习', hint: '适合 20 分钟闭环' },
    { label: '当前目标', value: 'SQL 联结', hint: '下一步进入多表查询' },
    { label: '课堂投入', value: '82%', hint: '可继续提升专注稳定性' },
  ];

  const agentCards = [
    { name: '画像专员', text: '抽取目标、基础、偏好', active: true },
    { name: '检索专员', text: '匹配课程库与个人资料', active: true },
    { name: '批改专员', text: '分析错因并更新掌握度', active: true },
    { name: '资源专员', text: '生成练习、讲义、脚本', active: false },
  ];

  const quickActions = [
    '解析这道题并给我提示',
    '按批改模式检查我的答案',
    '根据薄弱点生成 20 分钟练习',
  ];

  const latestFiles = computed(() => files.value.slice(0, 6));

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
</script>

<template>
  <div class="assistant-workbench">
    <section class="workbench-hero">
      <div>
        <span class="eyebrow">AI 伴学工作台</span>
        <h1>专注对话、批改与个性化辅导</h1>
        <p>
          支持课程资料检索、图片与文档联合提问、练习批改、数字人讲解和学习画像更新。
        </p>
      </div>
      <div class="drawer-actions">
        <button type="button" @click="openDrawer('profile')">
          <span class="drawer-icon"><icon-user /></span>
          <strong>学习画像</strong>
          <span>6维</span>
        </button>
        <button type="button" @click="openDrawer('resources')">
          <span class="drawer-icon"><icon-storage /></span>
          <strong>课程资料</strong>
          <span>{{ files.length }}份</span>
        </button>
        <button type="button" @click="openDrawer('agents')">
          <span class="drawer-icon"><icon-robot /></span>
          <strong>协作状态</strong>
          <span>4个</span>
        </button>
      </div>
    </section>

    <main class="chat-stage">
      <LegacyAssistantPanel />
    </main>

    <a-drawer
      v-model:visible="drawerVisible"
      :title="drawerTitle"
      :width="420"
      :footer="false"
      unmount-on-close
    >
      <section v-if="activeDrawer === 'profile'" class="drawer-section">
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

<style scoped lang="scss">
  .assistant-workbench {
    --assistant-primary: #6366f1;
    --assistant-primary-dark: #4f46e5;
    --assistant-primary-soft: rgba(99, 102, 241, 0.1);
    --assistant-border: rgba(99, 102, 241, 0.16);
    --assistant-surface: rgba(255, 255, 255, 0.86);
    --assistant-text: #0f172a;
    --assistant-sub: #64748b;
    min-height: 100%;
    padding: 16px;
    background:
      radial-gradient(circle at top left, rgba(99, 102, 241, 0.14), transparent 34%),
      linear-gradient(135deg, #f5f3ff 0%, #eef2ff 48%, #f8fafc 100%);
    color: var(--assistant-text);
  }

  .workbench-hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    margin-bottom: 14px;
    padding: 14px 16px;
    border: 1px solid var(--assistant-border);
    border-radius: 8px;
    background: var(--assistant-surface);
    box-shadow: 0 10px 24px rgba(99, 102, 241, 0.08);

    h1 {
      margin: 4px 0 6px;
      color: var(--assistant-text);
      font-size: 23px;
      line-height: 1.25;
      letter-spacing: 0;
    }

    p {
      max-width: 780px;
      margin: 0;
      color: var(--assistant-sub);
      line-height: 1.65;
    }
  }

  .eyebrow {
    color: var(--assistant-primary-dark);
    font-size: 12px;
    font-weight: 800;
  }

  .drawer-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;

    button {
      height: 34px;
      padding: 0 10px;
      border: 1px solid rgba(99, 102, 241, 0.18);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.72);
      color: #334155;
      cursor: pointer;
      text-align: center;
      transition: all 0.18s ease;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      white-space: nowrap;

      &:hover {
        transform: translateY(-1px);
        border-color: rgba(99, 102, 241, 0.34);
        background: linear-gradient(
          135deg,
          rgba(99, 102, 241, 0.12),
          rgba(139, 92, 246, 0.08)
        );
        color: var(--assistant-primary-dark);
        box-shadow: 0 8px 16px rgba(99, 102, 241, 0.12);
      }

      &:active {
        transform: translateY(0);
      }
    }

    strong,
    span {
      display: inline;
    }

    .drawer-icon {
      width: 18px;
      height: 18px;
      border-radius: 6px;
      background: rgba(99, 102, 241, 0.1);
      color: var(--assistant-primary-dark);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
    }

    strong {
      font-size: 13px;
      font-weight: 750;
    }

    span {
      margin-top: 0;
      color: #6d5ee7;
      font-size: 12px;
      font-weight: 700;
    }
  }

  .chat-stage {
    min-width: 0;
    overflow: hidden;
    border: 1px solid var(--assistant-border);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.88);
    box-shadow: 0 12px 28px rgba(99, 102, 241, 0.08);
  }

  .drawer-section {
    display: grid;
    gap: 14px;
  }

  .drawer-block {
    h3 {
      margin: 0 0 10px;
      color: var(--assistant-text);
      font-size: 15px;
    }
  }

  .profile-grid {
    display: grid;
    gap: 8px;

    article {
      min-height: 76px;
      padding: 10px;
      border: 1px solid rgba(99, 102, 241, 0.12);
      border-radius: 8px;
      background: linear-gradient(135deg, #fbfaff, #f5f3ff);
    }

    span,
    small {
      display: block;
      color: var(--assistant-sub);
      font-size: 12px;
    }

    strong {
      display: block;
      margin: 5px 0;
      color: var(--assistant-text);
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
    border-radius: 8px;
    background: #fbfaff;
  }

  .quick-action-list article {
    color: #334155;
    font-size: 13px;
    line-height: 1.35;
  }

  .resource-upload-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px;
    border: 1px solid rgba(99, 102, 241, 0.14);
    border-radius: 8px;
    background: linear-gradient(135deg, #fbfaff, #eef2ff);

    strong,
    span {
      display: block;
    }

    strong {
      margin-bottom: 4px;
      color: var(--assistant-text);
      font-size: 14px;
      font-weight: 750;
    }

    span {
      color: var(--assistant-sub);
      font-size: 12px;
      line-height: 1.5;
    }

    :deep(.arco-btn) {
      flex: 0 0 auto;
    }
  }

  .drawer-toolbar {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 8px;
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
    color: var(--assistant-text);
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .file-list span,
  .file-list small,
  .agent-list small {
    display: block;
    color: var(--assistant-sub);
    font-size: 12px;
  }

  .resource-table {
    margin-top: 6px;

    :deep(.arco-table-th),
    :deep(.arco-table-td) {
      padding: 8px;
      font-size: 12px;
    }
  }

  .agent-list article {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    background: #fbfaff;

    &.active {
      border-color: rgba(99, 102, 241, 0.28);
      background: linear-gradient(135deg, #f5f3ff, #eef2ff);

      .agent-dot {
        background: var(--assistant-primary);
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

  :deep(.arco-btn-primary) {
    background-color: var(--assistant-primary);
    border-color: var(--assistant-primary);
    border-radius: 8px;

    &:hover {
      background-color: var(--assistant-primary-dark);
      border-color: var(--assistant-primary-dark);
    }
  }

  :deep(.arco-drawer) {
    .arco-drawer-header {
      border-bottom-color: rgba(99, 102, 241, 0.12);
      background: #fbfaff;
    }

    .arco-drawer-title {
      color: var(--assistant-text);
      font-weight: 750;
    }

    .arco-drawer-body {
      background: linear-gradient(180deg, #ffffff 0%, #fafaff 100%);
    }
  }

  @media (max-width: 980px) {
    .workbench-hero {
      align-items: flex-start;
      flex-direction: column;
    }

    .drawer-actions {
      width: 100%;
      justify-content: flex-start;
      overflow-x: auto;
    }
  }

  @media (max-width: 640px) {
    .assistant-workbench {
      padding: 10px;
    }

    .drawer-actions button {
      flex: 1 1 120px;
    }

    .resource-upload-card {
      align-items: stretch;
      flex-direction: column;

      :deep(.arco-btn) {
        width: 100%;
      }
    }
  }
</style>
