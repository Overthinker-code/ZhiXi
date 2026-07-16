<script setup lang="ts">
  import { onMounted, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { fetchPracticeSummary, type PracticeSummary } from '@/api/student-hub';

  const router = useRouter();
  const loading = ref(true);
  const summary = ref<PracticeSummary | null>(null);

  onMounted(async () => {
    loading.value = true;
    try {
      summary.value = await fetchPracticeSummary();
    } finally {
      loading.value = false;
    }
  });
</script>

<template>
  <ZyPageShell title="题库练习" subtitle="分层练习、错题复盘与即时反馈">
    <template #actions>
      <a-button type="primary" @click="router.push({ name: 'TutorChat' })">
        批改作业
      </a-button>
    </template>

    <ZyPageEnter>
      <div class="kpi zy-stagger-child">
        <a-card class="kpi-card general-card">
          <icon-edit />
          <div>
            <span>累计题量</span>
            <strong><MetricCountUp :value="summary?.total_questions ?? 0" /></strong>
          </div>
        </a-card>
        <a-card class="kpi-card general-card">
          <icon-check-circle />
          <div>
            <span>正确率</span>
            <strong>{{ Math.round((summary?.correct_rate ?? 0) * 100) }}%</strong>
          </div>
        </a-card>
        <a-card class="kpi-card general-card">
          <icon-calendar />
          <div>
            <span>作业完成</span>
            <strong>{{ summary?.assignment_completed ?? 0 }}/{{ summary?.assignment_total ?? 0 }}</strong>
          </div>
        </a-card>
      </div>

      <a-card title="薄弱主题" class="card-block general-card zy-stagger-child">
        <a-skeleton v-if="loading" :animation="true" />
        <div v-else class="topic-list">
          <div v-for="topic in summary?.topics ?? []" :key="topic.topic" class="topic-item">
            <div>
              <strong>{{ topic.topic }}</strong>
              <p>{{ topic.subject }} · {{ topic.sessions }} 次练习</p>
            </div>
            <a-progress :percent="Math.round(topic.avg_score * 100)" size="small" style="width: 120px" />
          </div>
        </div>
        <a-empty v-if="!loading && !(summary?.topics?.length)" description="完成一次练习后，这里会帮你整理需要加强的主题" />
      </a-card>
    </ZyPageEnter>
  </ZyPageShell>
</template>

<style scoped lang="less">
  .card-block {
    border-radius: var(--zy-radius-card);
  }

  .kpi {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 16px;
  }

  .kpi-card {
    border-radius: var(--zy-radius-card);

    :deep(.arco-card-body) {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 22px;
      color: var(--zy-color-brand);
    }

    span {
      display: block;
      color: var(--zy-color-text-secondary);
      font-size: var(--zy-text-sm);
    }

    strong {
      display: block;
      font-size: 22px;
      color: var(--zy-color-text-primary);
    }
  }

  .topic-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    padding: 12px 0;
    border-bottom: 1px solid #f1f5f9;

    p {
      margin: 4px 0 0;
      color: var(--zy-color-text-secondary);
      font-size: var(--zy-text-xs);
    }
  }

  @media (max-width: 768px) {
    .kpi {
      grid-template-columns: 1fr;
    }
  }
</style>
