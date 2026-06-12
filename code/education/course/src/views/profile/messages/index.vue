<script setup lang="ts">
  import { onMounted, ref } from 'vue';
  import { fetchStudentMessages, type StudentMessage } from '@/api/student-hub';
  import ZyPageEnter from '@/components/zy/ZyPageEnter.vue';

  const loading = ref(true);
  const messages = ref<StudentMessage[]>([]);

  onMounted(async () => {
    loading.value = true;
    try {
      messages.value = await fetchStudentMessages(50);
    } finally {
      loading.value = false;
    }
  });
</script>

<template>
  <div class="page-wrap">
    <ZyPageEnter>
      <a-card title="消息中心" class="card-block">
        <a-skeleton v-if="loading" :animation="true" />
        <a-list v-else-if="messages.length" :data="messages" :bordered="false">
          <template #item="{ item }">
            <a-list-item>
              <a-list-item-meta
                :title="item.title"
                :description="`${item.category} · ${item.created_at}`"
              />
              <div class="msg-body">{{ item.body }}</div>
              <a-tag v-if="!item.is_read" color="orangered" size="small">未读</a-tag>
            </a-list-item>
          </template>
        </a-list>
        <a-empty v-else description="暂无消息" />
      </a-card>
    </ZyPageEnter>
  </div>
</template>

<style scoped lang="less">
  .page-wrap { padding: 20px 24px; max-width: 960px; margin: 0 auto; }
  .card-block { border-radius: var(--zy-radius-card); }
  .msg-body { color: #475569; font-size: 13px; max-width: 520px; }
</style>
