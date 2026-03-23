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
  const isAdmin = computed(() => userStore.role === 'admin');

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
      Message.error(error?.message || 'Failed to load reference files');
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
  .assistant-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 14px;
    background-color: #eef1f5;
    border: 1px solid #dce6f4;
    box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
  }

  :deep(.arco-tabs-nav::before) {
    background-color: transparent;
  }

  :deep(.arco-tabs-nav-type-rounded .arco-tabs-tab) {
    border-radius: 999px;
    border: 1px solid transparent;
    transition: all 0.2s ease;
  }

  :deep(.arco-tabs-nav-type-rounded .arco-tabs-tab:hover) {
    background-color: rgba(25, 103, 210, 0.1);
  }

  :deep(.arco-tabs-nav-type-rounded .arco-tabs-tab-active) {
    border-color: rgba(25, 103, 210, 0.24);
    box-shadow: 0 6px 14px rgba(25, 103, 210, 0.18);
  }

  :deep(.arco-tabs-content) {
    height: 100%;
  }

  :deep(.arco-tabs-content .arco-tabs-pane) {
    height: 100%;
  }

  .files-toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 12px;
  }

  @media (max-width: 760px) {
    .assistant-page {
      padding: 10px;
      border-radius: 14px;
    }
  }
</style>
