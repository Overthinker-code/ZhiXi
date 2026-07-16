<script setup lang="ts">
  import { computed, ref } from 'vue';

  const props = defineProps<{
    citations: Array<Record<string, any>>;
    compact?: boolean;
  }>();

  const expanded = ref(false);
  const visibleItems = computed(() =>
    expanded.value ? props.citations : props.citations.slice(0, props.compact ? 2 : 4)
  );

  const sourceType = (item: Record<string, any>) => {
    const scope = String(item.sourceType || item.context_scope || item.scope || '');
    if (scope.includes('uploaded')) return '上传资料';
    if (scope.includes('web')) return '联网来源';
    return '课程资料';
  };

  const titleOf = (item: Record<string, any>, index: number) =>
    String(item.title || item.file_name || item.source || `参考来源 ${index + 1}`);
</script>

<template>
  <section v-if="citations.length" class="citation-list">
    <button type="button" class="citation-list__summary" @click="expanded = !expanded">
      <span>参考来源</span>
      <strong>{{ citations.length }}</strong>
      <span>{{ expanded ? '收起' : '展开' }}</span>
    </button>
    <div v-if="expanded || !compact" class="citation-list__items">
      <article v-for="(item, index) in visibleItems" :key="`${titleOf(item, index)}-${index}`">
        <span>{{ sourceType(item) }}</span>
        <strong>{{ titleOf(item, index) }}</strong>
        <p>{{ item.snippet || item.chunk || item.text || '该来源未返回摘要。' }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped lang="scss">
  .citation-list {
    margin-top: 12px;
  }

  .citation-list__summary {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    height: 32px;
    padding: 0 12px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 999px;
    color: #475467;
    background: #fff;
    cursor: pointer;

    strong {
      color: #4f46e5;
    }
  }

  .citation-list__items {
    display: grid;
    gap: 8px;
    margin-top: 10px;

    article {
      padding: 10px 12px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 14px;
      background: #f8faff;
    }

    span {
      display: inline-flex;
      margin-bottom: 5px;
      color: #6366f1;
      font-size: 12px;
      font-weight: 700;
    }

    strong {
      display: block;
      color: #101828;
      font-size: 13px;
    }

    p {
      margin: 4px 0 0;
      color: #667085;
      font-size: 13px;
      line-height: 1.55;
    }
  }
</style>
