<script setup lang="ts">
  import { onMounted, ref } from 'vue';
  import { fetchStudyGroups, type StudyGroupItem } from '@/api/student-hub';

  const loading = ref(true);
  const groups = ref<StudyGroupItem[]>([]);

  onMounted(async () => {
    loading.value = true;
    try {
      groups.value = await fetchStudyGroups();
    } finally {
      loading.value = false;
    }
  });
</script>

<template>
  <ZyPageShell title="小组协作" subtitle="与同学组队讨论、共享学习进度">
    <ZyPageEnter>
      <a-card class="card-block general-card zy-stagger-child">
        <template #title>我的学习小组</template>
        <template #extra>
          <a-tag color="arcoblue">{{ groups.length }} 个小组</a-tag>
        </template>
        <a-skeleton v-if="loading" :animation="true" />
        <div v-else class="group-grid">
          <a-card v-for="g in groups" :key="g.id" class="group-card" hoverable>
            <div class="group-card__head">
              <span class="group-icon"><icon-user-group /></span>
              <h3>{{ g.name }}</h3>
            </div>
            <p>{{ g.description }}</p>
            <div class="meta">
              <span><icon-user /> {{ g.member_count }} 人</span>
              <span>{{ g.course_name || '综合小组' }}</span>
              <a-tag size="small">{{ g.my_role }}</a-tag>
            </div>
          </a-card>
        </div>
        <a-empty v-if="!loading && !groups.length" description="还没有加入学习小组" />
      </a-card>
    </ZyPageEnter>
  </ZyPageShell>
</template>

<style scoped lang="less">
  .card-block {
    border-radius: var(--zy-radius-card);
  }

  .group-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
  }

  .group-card {
    border-radius: var(--zy-radius-card);
    border: 1px solid rgba(99, 102, 241, 0.1);

    h3 {
      margin: 0;
      font-size: var(--zy-text-base);
      color: var(--zy-color-text-primary);
    }

    p {
      color: var(--zy-color-text-secondary);
      font-size: var(--zy-text-sm);
      min-height: 40px;
      line-height: 1.6;
    }
  }

  .group-card__head {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }

  .group-icon {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: var(--zy-bg-tag);
    color: var(--zy-color-brand);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
  }

  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    color: var(--zy-color-text-secondary);
    font-size: var(--zy-text-xs);
    margin-top: 10px;
  }
</style>
