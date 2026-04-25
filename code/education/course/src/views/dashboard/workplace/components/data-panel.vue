<template>
  <div class="data-panel-root">
    <div v-if="loading" class="zy-panel-skeleton" aria-busy="true">
      <div class="zy-skeleton zy-skeleton--radar zy-bar" style="height: 72px" />
      <div class="zy-skeleton zy-skeleton--radar zy-bar" style="height: 120px" />
    </div>
    <div v-else-if="error" class="data-panel-error">
      <span>{{ $t('workplace.loadFailedTip') }}</span>
      <a-button type="primary" size="small" @click="fetchData">{{ $t('workplace.retry') }}</a-button>
    </div>
    <a-grid v-else-if="data" :cols="18" :row-gap="16" class="panel">
      <a-grid-item
        class="panel-col"
        :span="{ xs: 12, sm: 12, md: 12, lg: 12, xl: 12, xxl: 6 }"
      >
        <a-space>
          <a-avatar :size="54" class="col-avatar">
            <icon-storage />
          </a-avatar>
          <a-statistic
            :title="$t('workplace.totalCourses')"
            :value="displayOverview.total_courses"
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
            :title="$t('workplace.activeStudents')"
            :value="displayOverview.active_students"
            :precision="0"
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
  </div>
</template>

<script lang="ts" setup>
  import { reactive, onMounted, ref } from 'vue';
  import { getTeacherStats, type TeacherStats } from '@/api/dashboard';

  const loading = ref(true);
  const error = ref<string | null>(null);
  const data = ref<TeacherStats | null>(null);

  const displayOverview = reactive({
    total_courses: 0,
    active_students: 0,
    total_resources: 0,
  });

  function easeOutCubic(t: number) {
    return 1 - (1 - t) ** 3;
  }

  function runCountUp(
    key: 'total_courses' | 'active_students' | 'total_resources',
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
    loading.value = true;
    error.value = null;
    try {
      data.value = await getTeacherStats();
    } catch (err) {
      console.error('[data-panel] fetchData failed:', err);
      error.value = 'failed';
    } finally {
      loading.value = false;
    }
  };

  const animatedOnce = ref(false);

  onMounted(async () => {
    await fetchData();
    if (!data.value || animatedOnce.value) return;
    animatedOnce.value = true;
    const d = 1100;
    runCountUp('total_courses', data.value.total_courses, d);
    runCountUp('active_students', data.value.active_students, d);
    runCountUp('total_resources', data.value.total_resources, d);
  });
</script>

<style lang="less" scoped>
  .data-panel-root {
    width: 100%;
  }

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

  .data-panel-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 48px 20px;
    color: rgb(var(--gray-6));
    font-size: 14px;
  }
</style>
