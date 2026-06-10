<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import axios from 'axios';
  import {
    getTeacherAlertsTrend,
    getTeacherContentDistribution,
    getTeacherStats,
    type TeacherStats,
  } from '@/api/dashboard';
  import ZyMediaHero from '@/components/zy/ZyMediaHero.vue';
  import bannerImg from '@/assets/banners/banner1.png';

  const loading = ref(true);
  const usingFallback = ref(false);
  const stats = ref<TeacherStats | null>(null);
  const alertsTrend = ref<Array<{ date: string; alert_count: number }>>([]);
  const contentDistribution = ref<Array<{ name: string; value: number }>>([]);
  const students = ref<
    Array<{ id: string; name: string; identifier: string }>
  >([]);

  const statCards = computed(() => [
    {
      label: '活跃学生',
      value: stats.value?.active_students ?? '—',
    },
    {
      label: '课程总数',
      value: stats.value?.total_courses ?? '—',
    },
    {
      label: '教学资源',
      value: stats.value?.total_resources ?? '—',
    },
    {
      label: '教学班',
      value: stats.value?.total_teaching_classes ?? '—',
    },
  ]);

  async function loadData() {
    loading.value = true;
    try {
      const [s, trend, dist, studentResp] = await Promise.all([
        getTeacherStats(),
        getTeacherAlertsTrend(14),
        getTeacherContentDistribution(),
        axios.get('/api/education/students', { params: { limit: 20 } }),
      ]);
      stats.value = s;
      alertsTrend.value = trend;
      contentDistribution.value = dist.items || [];
      students.value = studentResp.data?.data || [];
      usingFallback.value =
        !s.active_students && !s.total_resources && students.value.length === 0;
    } catch {
      usingFallback.value = true;
    } finally {
      loading.value = false;
    }
  }

  onMounted(loadData);
</script>

<template>
  <div class="class-insights">
    <ZyMediaHero
      title="班级学情洞察"
      subtitle="汇总你所带班级的学习投入、预警趋势与学生参与情况"
      :image="bannerImg"
    >
      <a-tag v-if="usingFallback" color="orangered" style="margin-top: 12px">
        演示数据
      </a-tag>
    </ZyMediaHero>

    <a-spin :loading="loading" style="width: 100%">
      <div class="stat-grid">
        <div v-for="item in statCards" :key="item.label" class="stat-card">
          <p class="stat-label">{{ item.label }}</p>
          <p class="stat-value">{{ item.value }}</p>
        </div>
      </div>

      <div class="panel-grid">
        <a-card title="近两周预警趋势" class="panel">
          <div v-if="alertsTrend.length" class="trend-list">
            <div
              v-for="row in alertsTrend.slice(-7)"
              :key="row.date"
              class="trend-row"
            >
              <span>{{ row.date }}</span>
              <a-progress
                :percent="Math.min(100, row.alert_count / 10)"
                :show-text="false"
                size="small"
              />
              <span>{{ row.alert_count }}</span>
            </div>
          </div>
          <a-empty v-else description="暂无预警数据" />
        </a-card>

        <a-card title="资源类型分布" class="panel">
          <div v-if="contentDistribution.length" class="dist-list">
            <div
              v-for="item in contentDistribution.slice(0, 6)"
              :key="item.name"
              class="dist-row"
            >
              <span>{{ item.name }}</span>
              <a-progress
                :percent="Math.min(100, item.value / 20)"
                :show-text="false"
                size="small"
              />
              <span>{{ item.value }}</span>
            </div>
          </div>
          <a-empty v-else description="暂无分布数据" />
        </a-card>
      </div>

      <a-card title="学生列表（抽样）" class="student-panel">
        <a-table
          :data="students"
          :pagination="false"
          row-key="id"
          size="small"
        >
          <template #columns>
            <a-table-column title="姓名" data-index="name" />
            <a-table-column title="学号" data-index="identifier" />
            <a-table-column title="操作">
              <template #cell="{ record }">
                <a-link @click="$router.push(`/course/monitor?student=${record.id}`)">
                  查看课堂表现
                </a-link>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-card>
    </a-spin>
  </div>
</template>

<style scoped lang="less">
  .class-insights {
    padding: 4px 0 24px;
  }

  .stat-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }

  .stat-card {
    padding: 16px;
    border-radius: 12px;
    background: var(--color-bg-2, #fff);
    border: 1px solid var(--color-border-2, #e5e6eb);
  }

  .stat-label {
    margin: 0;
    font-size: 12px;
    color: var(--color-text-3, #86909c);
  }

  .stat-value {
    margin: 6px 0 0;
    font-size: 24px;
    font-weight: 700;
    color: var(--color-text-1, #1d2129);
  }

  .panel-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
  }

  .trend-row,
  .dist-row {
    display: grid;
    grid-template-columns: 96px 1fr 40px;
    gap: 8px;
    align-items: center;
    margin-bottom: 8px;
    font-size: 12px;
  }

  @media (max-width: 960px) {
    .stat-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .panel-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
