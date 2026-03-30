<template>
  <a-spin :loading="loading" style="width: 100%">
    <a-grid :cols="18" :row-gap="16" class="panel">
      <a-grid-item
        class="panel-col"
        :span="{ xs: 12, sm: 12, md: 12, lg: 12, xl: 12, xxl: 6 }"
      >
        <a-space>
          <a-avatar :size="54" class="col-avatar">
            <icon-storage />
          </a-avatar>
          <a-statistic
            :title="$t('workplace.onlineContent')"
            :value="overview.onlineContent"
            :precision="0"
            :value-from="0"
            animation
            show-group-separator
          >
            <template #suffix>
              <span class="unit">{{ $t('workplace.pecs') }}</span>
            </template>
          </a-statistic>
        </a-space>
      </a-grid-item>
      <a-grid-item
        class="panel-col"
        :span="{ xs: 12, sm: 12, md: 12, lg: 12, xl: 12, xxl: 6 }"
      >
        <a-space>
          <a-avatar :size="54" class="col-avatar">
            <icon-user />
          </a-avatar>
          <a-statistic
            :title="$t('workplace.putIn')"
            :value="overview.putIn"
            :value-from="0"
            animation
            show-group-separator
          >
            <template #suffix>
              <span class="unit">{{ $t('workplace.personpecs') }}</span>
            </template>
          </a-statistic>
        </a-space>
      </a-grid-item>
      <a-grid-item
        class="panel-col"
        :span="{ xs: 12, sm: 12, md: 12, lg: 12, xl: 12, xxl: 6 }"
      >
        <a-space>
          <a-avatar :size="54" class="col-avatar">
            <icon-file />
          </a-avatar>
          <a-statistic
            :title="$t('workplace.newDay')"
            :value="overview.newDay"
            :value-from="0"
            animation
            show-group-separator
          >
            <template #suffix>
              <span class="unit">{{ $t('workplace.pecs') }}</span>
            </template>
          </a-statistic>
        </a-space>
      </a-grid-item>

      <a-grid-item :span="24">
        <a-divider class="panel-border" />
      </a-grid-item>
    </a-grid>
  </a-spin>
</template>

<script lang="ts" setup>
  import { reactive, onMounted } from 'vue';
  import useLoading from '@/hooks/loading';
  import { queryDashboardOverview, DashboardOverview } from '@/api/dashboard';

  const { loading, setLoading } = useLoading(true);
  const overview = reactive<DashboardOverview>({
    onlineContent: 0,
    putIn: 0,
    newDay: 0,
    growthRate: 0,
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const { data } = await queryDashboardOverview();
      Object.assign(overview, data);
    } catch (err) {
      console.error('Failed to fetch dashboard overview:', err);
    } finally {
      setLoading(false);
    }
  };

  onMounted(() => {
    fetchData();
  });
</script>

<style lang="less" scoped>
  .arco-grid.panel {
    margin-bottom: 0;
    padding: 16px 20px 0 20px;
  }

  .panel-col {
    padding-left: 43px;
    border-right: 1px solid rgb(var(--gray-2));
    margin-bottom: 20px;
  }

  .col-avatar {
    margin-right: 12px;
    color: #0b5ca8;
    background: linear-gradient(160deg, #d4ecff, #e6faf8);
  }

  .up-icon {
    color: rgb(var(--red-6));
  }

  .unit {
    margin-left: 8px;
    color: rgb(var(--gray-8));
    font-size: 12px;
  }

  :deep(.panel-border) {
    margin: 4px 0 0 0;
  }
</style>
