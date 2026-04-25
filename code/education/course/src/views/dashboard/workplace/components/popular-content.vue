<template>
  <div class="chart-panel-root">
    <div v-if="loading" class="zy-panel-skeleton" aria-busy="true">
      <div class="zy-skeleton zy-skeleton--radar zy-bar" style="height: 48px" />
      <div class="zy-skeleton zy-skeleton--radar zy-bar" style="height: 300px; margin-top: 12px" />
    </div>
    <div v-else-if="error" class="popular-content-error">
      <span>{{ $t('workplace.loadFailedTip') }}</span>
      <a-button type="primary" size="small" @click="() => fetchData(type)">{{ $t('workplace.retry') }}</a-button>
    </div>
    <a-card
      v-else
      class="general-card"
      :header-style="{ paddingBottom: '0' }"
      :body-style="{ padding: '17px 20px 21px 20px' }"
    >
      <template #title>
        {{ $t('workplace.popularContent') }}
      </template>
      <template #extra>
        <a-link>{{ $t('workplace.viewMore') }}</a-link>
      </template>
      <a-space direction="vertical" :size="10" fill>
        <a-radio-group
          v-model:model-value="type"
          type="button"
          @change="typeChange as any"
        >
          <a-radio value="course">
            {{ $t('workplace.popularContent.text') }}
          </a-radio>
          <a-radio value="resource">
            {{ $t('workplace.popularContent.image') }}
          </a-radio>
        </a-radio-group>
        <a-table
          :data="renderList"
          :pagination="false"
          :bordered="false"
          :scroll="{ x: '100%', y: '264px' }"
        >
          <template #columns>
            <a-table-column
              :title="$t('workplace.popular.table.rank')"
              data-index="key"
            />
            <a-table-column
              :title="$t('workplace.popular.table.title')"
              data-index="title"
            >
              <template #cell="{ record }">
                <a-typography-paragraph
                  :ellipsis="{
                    rows: 1,
                  }"
                >
                  {{ record.title }}
                </a-typography-paragraph>
              </template>
            </a-table-column>
            <a-table-column
              :title="$t('workplace.popular.table.click')"
              data-index="click_number"
            />
            <a-table-column
              :title="$t('workplace.popular.table.increase')"
              data-index="increases"
              :sortable="{
                sortDirections: ['ascend', 'descend'],
              }"
            >
              <template #cell="{ record }">
                <div class="increases-cell">
                  <span>{{ record.increases }}%</span>
                  <icon-caret-up
                    v-if="record.increases !== 0"
                    style="color: #f53f3f; font-size: 8px"
                  />
                </div>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-space>
    </a-card>
  </div>
</template>

<script lang="ts" setup>
  import { ref } from 'vue';
  import { getTeacherPopular, type PopularItem } from '@/api/dashboard';

  const type = ref<'course' | 'resource'>('course');
  const loading = ref(true);
  const error = ref<string | null>(null);
  const renderList = ref<PopularItem[]>([]);
  const fetchData = async (contentType: 'course' | 'resource') => {
    loading.value = true;
    error.value = null;
    try {
      renderList.value = await getTeacherPopular(contentType);
    } catch (err) {
      console.error('[popular-content] fetchData failed:', err);
      error.value = 'failed';
    } finally {
      loading.value = false;
    }
  };
  const typeChange = (contentType: 'course' | 'resource') => {
    fetchData(contentType);
  };
  fetchData('course');
</script>

<style scoped lang="less">
  .general-card {
    min-height: 395px;
  }

  :deep(.arco-radio-group-button .arco-radio-button) {
    border-radius: 8px;
  }

  :deep(.arco-table-tr) {
    height: 44px;

    .arco-typography {
      margin-bottom: 0;
    }
  }

  .chart-panel-root {
    width: 100%;
  }

  .increases-cell {
    display: flex;
    align-items: center;

    span {
      margin-right: 4px;
    }
  }

  .popular-content-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    min-height: 348px;
    color: rgb(var(--gray-6));
    font-size: 14px;
  }
</style>
