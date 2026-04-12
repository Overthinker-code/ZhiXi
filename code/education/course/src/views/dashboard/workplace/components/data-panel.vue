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
            :value="displayOverview.total_classes"
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
            :value="displayOverview.total_teachers"
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
            :value="displayOverview.total_resources"
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
  import { reactive, onMounted, ref } from 'vue';
  import useLoading from '@/hooks/loading';
  import { queryDashboardOverview } from '@/api/dashboard';

  const { loading, setLoading } = useLoading(true);
  const overview = reactive({
    total_classes: 3735,
    total_teachers: 768,
    total_resources: 8874,
  });

  const displayOverview = reactive({
    total_classes: 0,
    total_teachers: 0,
    total_resources: 0,
  });

  function easeOutCubic(t: number) {
    return 1 - (1 - t) ** 3;
  }

  function runCountUp(
    key: 'total_classes' | 'total_teachers' | 'total_resources',
    target: number,
    durationMs: number
  ) {
    const from = 0;
    const t0 = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / durationMs);
      displayOverview[key] = Math.round(from + (target - from) * easeOutCubic(p));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  const fetchData = async () => {
    setLoading(true);
    try {
      const { data } = await queryDashboardOverview();
      overview.total_classes = data.total_classes;
      overview.total_teachers = data.total_teachers;
      overview.total_resources = data.total_resources;
    } catch (_err) {
      // keep demo fallback values
    } finally {
      setLoading(false);
    }
  };

  const animatedOnce = ref(false);

  onMounted(async () => {
    await fetchData();
    if (animatedOnce.value) return;
    animatedOnce.value = true;
    const d = 1100;
    runCountUp('total_classes', overview.total_classes, d);
    runCountUp('total_teachers', overview.total_teachers, d);
    runCountUp('total_resources', overview.total_resources, d);
  });
</script>

<style lang="less" scoped>
  /* 智屿 Dashboard 数据卡片 — 品牌绿图标 */
  .arco-grid.panel {
    margin-bottom: 0;
    padding: 16px 20px 0 20px;
  }

  .panel-col {
    padding-left: 43px;
    border-right: 1px solid rgba(99, 102, 241, 0.12);
    margin-bottom: 20px;
  }

  .col-avatar {
    margin-right: 12px;
    color: #6366f1;
    background: linear-gradient(145deg, #eef2ff, #e0e7ff);
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

