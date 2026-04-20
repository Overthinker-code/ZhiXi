<script setup lang="ts">
  import { onMounted, ref, h, resolveComponent, computed } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { useUserStore } from '@/store';
  import {
    fetchReferenceFiles,
    deleteReferenceFile,
    type ReferenceFile,
    type ReferenceScopeFilter,
  } from '@/api/rag';
  import LegacyAssistantPanel from './LegacyAssistantPanel.vue';
  import ReferenceFileUploadDialog from './components/ReferenceFileUploadDialog.vue';

  const activeTab = ref('files');
  const showUploadModal = ref(false);
  const files = ref<ReferenceFile[]>([]);
  const loadingFiles = ref(false);
  const scopeFilter = ref<ReferenceScopeFilter>('all');
  const scopeFilterOptions = [
    { label: '全部文件', value: 'all' },
    { label: '系统文件', value: 'system' },
    { label: '用户文件', value: 'personal' },
  ];
  const userStore = useUserStore();
  const isAdmin = computed(() => userStore.role === 'teacher');

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
    return date.toLocaleString();
  };

  const getScopeLabel = (scope?: ReferenceFile['scope']) => {
    if (scope === 'system') return '系统文件';
    if (scope === 'personal') return '用户文件';
    return '-';
  };

  async function loadReferenceFiles() {
    loadingFiles.value = true;
    try {
      files.value = await fetchReferenceFiles(scopeFilter.value);
    } catch (error: any) {
      const st = error?.response?.status;
      const msg = String(error?.message || '');
      if (st === 404 || msg.includes('404')) {
        files.value = [];
        return;
      }
      Message.error(msg || '加载参考文件失败');
    } finally {
      loadingFiles.value = false;
    }
  }

  async function handleDelete(record: ReferenceFile) {
    try {
      await deleteReferenceFile(record.file_id);
      Message.success('Deleted');
      await loadReferenceFiles();
    } catch (error: any) {
      Message.error(error?.message || 'Delete failed');
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
            content: `Delete ${record.name}?`,
            onOk: () => handleDelete(record),
          },
          {
            default: () =>
              h(
                resolveComponent('a-button'),
                { type: 'text', status: 'danger' },
                { default: () => 'Delete' }
              ),
          }
        );
      },
    },
  ];

  function openUploadModal() {
    showUploadModal.value = true;
  }

  function handleUploadSuccess() {
    loadReferenceFiles();
  }

  onMounted(() => {
    loadReferenceFiles();
  });
</script>

<template>
  <div class="assistant-page">

    <a-tabs v-model:active-key="activeTab" type="rounded">
      <a-tab-pane key="files" title="参考文件">
        <div class="files-toolbar">
          <a-select
            v-model="scopeFilter"
            :options="scopeFilterOptions"
            style="width: 160px"
            @change="loadReferenceFiles"
          />
          <a-button type="primary" @click="openUploadModal">上传资料</a-button>
          <a-button :loading="loadingFiles" @click="loadReferenceFiles">
            刷新
          </a-button>
        </div>
        <a-table
          :columns="columns"
          :data="files"
          :loading="loadingFiles"
          :pagination="false"
          row-key="file_id"
        />
      </a-tab-pane>

      <a-tab-pane key="chat" title="AI对话">
        <LegacyAssistantPanel />
      </a-tab-pane>
    </a-tabs>

    <ReferenceFileUploadDialog
      :visible="showUploadModal"
      :is-admin="isAdmin"
      @update:visible="(v) => (showUploadModal = v)"
      @success="handleUploadSuccess"
    />
  </div>
</template>

<style scoped lang="scss">
  /**
   * 智屿 AI 助手页 - 品牌化样式
   * 文档：designup.md §4
   */
  .assistant-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 14px;
    background-color: var(--zy-bg-page, #f5f3ff);
    border-radius: var(--zy-radius-card, 16px);
    border: 1px solid rgba(99, 102, 241, 0.12);
    box-shadow: var(--zy-shadow-card);
  }

  /* Tabs 顶部分隔线去除 */
  :deep(.arco-tabs-nav::before) {
    background-color: transparent;
  }

  /* Tabs 胶囊风格 */
  :deep(.arco-tabs-nav-type-rounded .arco-tabs-tab) {
    border-radius: 9999px;
    border: 1px solid transparent;
    transition: all 0.2s ease;
    color: var(--zy-color-text-secondary, #64748b);
  }

  :deep(.arco-tabs-nav-type-rounded .arco-tabs-tab:hover) {
    background-color: rgba(99, 102, 241, 0.08);
    color: var(--zy-color-brand, #6366f1);
  }

  /* 激活 Tab：绿色背景白字 */
  :deep(.arco-tabs-nav-type-rounded .arco-tabs-tab-active) {
    background-color: var(--zy-color-brand, #6366f1) !important;
    border-color: var(--zy-color-brand, #6366f1) !important;
    color: #fff !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.30);
  }

  :deep(.arco-tabs-content) {
    height: 100%;
  }

  :deep(.arco-tabs-content .arco-tabs-pane) {
    height: 100%;
  }

  /* 工具栏 */
  .files-toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(99, 102, 241, 0.10);
  }

  /* 主要按钮品牌绿 */
  :deep(.arco-btn-primary) {
    background-color: var(--zy-color-brand, #6366f1) !important;
    border-color: var(--zy-color-brand, #6366f1) !important;
    border-radius: var(--zy-radius-sm, 8px);
    transition: all 0.2s ease;
  }

  :deep(.arco-btn-primary:hover) {
    background-color: var(--zy-color-brand-hover, #4f46e5) !important;
    border-color: var(--zy-color-brand-hover, #4f46e5) !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.30);
  }

  /* 表格行悬停品牌色 */
  :deep(.arco-table-tr:hover .arco-table-td) {
    background-color: rgba(99, 102, 241, 0.04) !important;
  }

  @media (max-width: 760px) {
    .assistant-page {
      padding: 10px;
      border-radius: 12px;
    }
  }
</style>

