<template>
  <div class="chart-panel-root">
    <div v-if="loading" class="zy-panel-skeleton" aria-busy="true">
      <div class="zy-skeleton zy-skeleton--radar zy-bar" style="height: 48px" />
      <div class="zy-skeleton zy-skeleton--radar zy-bar" style="height: 300px; margin-top: 12px" />
    </div>
    <a-card
      v-show="!loading"
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
          <a-radio value="discussion">
            {{ $t('workplace.popularContent.video') }}
          </a-radio>
          <a-radio value="homework">
            {{ $t('workplace.popularContent.homework') }}
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
  import useLoading from '@/hooks/loading';
  import { queryPopularList, type PopularRecord } from '@/api/dashboard';
  import type { TableData } from '@arco-design/web-vue/es/table/interface';

  const type = ref('course');
  const { loading, setLoading } = useLoading();
  const renderList = ref<TableData[]>();
  const popularDemoMap: Record<string, PopularRecord[]> = {
    course: [
      { key: 1, title: '数据库系统原理', click_number: 1820, increases: 14 },
      { key: 2, title: '人工智能导论', click_number: 1684, increases: 12 },
      { key: 3, title: '数据结构与算法', click_number: 1546, increases: 10 },
    ],
    resource: [
      { key: 1, title: 'SQL 实验指导书', click_number: 926, increases: 11 },
      { key: 2, title: '机器学习案例集', click_number: 874, increases: 9 },
      { key: 3, title: '知识图谱课堂讲义', click_number: 816, increases: 8 },
    ],
    discussion: [
      { key: 1, title: '事务隔离级别课堂讨论', click_number: 268, increases: 16 },
      { key: 2, title: '大模型落地应用交流', click_number: 231, increases: 12 },
      { key: 3, title: '树与图算法答疑串', click_number: 198, increases: 9 },
    ],
    homework: [
      { key: 1, title: '数据库范式设计作业', click_number: 642, increases: 18 },
      { key: 2, title: '数据结构周测练习', click_number: 588, increases: 13 },
      { key: 3, title: 'AI 应用场景分析报告', click_number: 521, increases: 11 },
    ],
  };

  function normalizeRow(item: Partial<PopularRecord>, index: number) {
    return {
      key: item.key ?? index + 1,
      title: item.title || '示例内容',
      click_number: Number(item.click_number ?? 0),
      increases: Number(item.increases ?? 0),
    };
  }

  function useDemoList(contentType: string) {
    renderList.value = (popularDemoMap[contentType] || popularDemoMap.course).map(
      normalizeRow
    );
  }

  const fetchData = async (contentType: string) => {
    if (contentType === 'discussion' || contentType === 'homework') {
      useDemoList(contentType);
      return;
    }
    try {
      setLoading(true);
      const { data } = await queryPopularList({ type: contentType });
      const normalized = (data || []).map(normalizeRow);
      const hasUsableData =
        normalized.length > 0 &&
        normalized.some((item) => item.click_number > 0 || item.increases > 0);
      renderList.value = hasUsableData
        ? normalized
        : (popularDemoMap[contentType] || popularDemoMap.course).map(normalizeRow);
    } catch (err) {
      useDemoList(contentType);
    } finally {
      setLoading(false);
    }
  };
  const typeChange = (contentType: string) => {
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
</style>
