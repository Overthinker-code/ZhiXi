<script setup lang="ts">
  import { onMounted, ref } from 'vue';
  import { fetchAchievements, type AchievementPayload } from '@/api/student-hub';
  import ZyPageEnter from '@/components/zy/ZyPageEnter.vue';
  import MetricCountUp from '@/components/zy/MetricCountUp.vue';

  const loading = ref(true);
  const payload = ref<AchievementPayload | null>(null);

  onMounted(async () => {
    loading.value = true;
    try {
      payload.value = await fetchAchievements();
    } finally {
      loading.value = false;
    }
  });
</script>

<template>
  <div class="page-wrap">
    <ZyPageEnter>
      <a-card class="summary card-block">
        <div>
          <span>总积分</span>
          <h2><MetricCountUp :value="payload?.total_points ?? 0" /></h2>
        </div>
        <div>
          <span>等级</span>
          <h2>Lv.{{ payload?.level ?? 1 }}</h2>
        </div>
        <div>
          <span>下一级</span>
          <h2>{{ payload?.next_level_points ?? 0 }} 分</h2>
        </div>
      </a-card>
      <a-card title="成就徽章" class="card-block">
        <a-skeleton v-if="loading" :animation="true" />
        <div v-else class="badge-grid">
          <div v-for="item in payload?.data ?? []" :key="item.id" class="badge-item">
            <div class="badge-icon">{{ item.icon || '🏅' }}</div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.description }}</p>
            <small>+{{ item.points_awarded }} 分 · {{ item.earned_at }}</small>
          </div>
        </div>
        <a-empty
          v-if="!loading && !(payload?.data?.length)"
          description="完成课程学习和练习后，这里会记录你的成长"
        />
      </a-card>
    </ZyPageEnter>
  </div>
</template>

<style scoped lang="less">
  .page-wrap { padding: 20px 24px; max-width: 1100px; margin: 0 auto; }
  .card-block { border-radius: var(--zy-radius-card); margin-bottom: 16px; }
  .summary {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    span { color: #64748b; font-size: 13px; }
    h2 { margin: 6px 0 0; font-size: 28px; }
  }
  .badge-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px;
  }
  .badge-item {
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: 14px;
    padding: 14px;
    background: #fff;
  }
  .badge-icon { font-size: 28px; margin-bottom: 8px; }
  p { margin: 6px 0; color: #64748b; font-size: 13px; }
  small { color: #94a3b8; }
</style>
