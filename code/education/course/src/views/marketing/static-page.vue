<script setup lang="ts">
  import { computed } from 'vue';
  import { useRoute } from 'vue-router';
  import ZyPageEnter from '@/components/zy/ZyPageEnter.vue';

  const route = useRoute();
  const title = computed(() => String(route.meta.pageTitle || route.meta.locale || '智屿'));
  const desc = computed(() => String(route.meta.pageDesc || ''));
</script>

<template>
  <div class="static-page">
    <ZyPageEnter>
      <a-card class="card-block">
        <h1>{{ title }}</h1>
        <p>{{ desc }}</p>
        <p class="muted">
          智屿面向高校提供 AI 多智能体伴学、个性化资源生成、学情诊断与课堂行为分析能力。
          如需试点部署或赛题演示环境，请通过院校信息化部门联系我们。
        </p>
      </a-card>
    </ZyPageEnter>
  </div>
</template>

<style scoped lang="less">
  .static-page {
    padding: 32px 24px;
    max-width: 880px;
    margin: 0 auto;
  }
  .card-block {
    border-radius: var(--zy-radius-card);
    h1 { margin: 0 0 12px; font-size: 28px; }
    p { color: #334155; line-height: 1.8; }
    .muted { color: #64748b; font-size: 14px; margin-top: 16px; }
  }
</style>
