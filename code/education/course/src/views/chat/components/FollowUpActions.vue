<script setup lang="ts">
  import { computed } from 'vue';

  const props = defineProps<{
    suggestions?: string[];
  }>();

  const emit = defineEmits<{
    (e: 'pick', value: string): void;
  }>();

  const fallbackSuggestions = [
    '我需要先掌握哪个核心知识点？',
    '能给我一道由浅入深的练习题吗？',
    '如果我答错了，应该怎么快速纠正？',
  ];

  const displaySuggestions = computed(() => {
    const seen = new Set<string>();
    const normalized = [...(props.suggestions || []), ...fallbackSuggestions]
      .map((item) => String(item || '').trim())
      .filter((item) => {
        if (/您|你是否|是否需要|请问你|请问您/.test(item)) return false;
        if (!/(我|帮我|给我|带我)/.test(item)) return false;
        if (!item || seen.has(item)) return false;
        seen.add(item);
        return true;
      });
    return normalized.slice(0, 3);
  });
</script>

<template>
  <div v-if="displaySuggestions.length === 3" class="follow-up-row">
    <button
      v-for="item in displaySuggestions"
      :key="item"
      type="button"
      class="follow-up-pill"
      @click="emit('pick', item)"
    >
      {{ item }}
    </button>
  </div>
</template>

<style scoped lang="scss">
  .follow-up-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    margin: 0.7rem 0 0 0.5rem;
  }

  .follow-up-pill {
    padding: 0.52rem 0.78rem;
    border: 1px solid rgba(99, 102, 241, 0.16);
    border-radius: 999px;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(59, 130, 246, 0.08));
    color: #312e81;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.18s ease;

    &:hover {
      transform: translateY(-1px);
      border-color: rgba(99, 102, 241, 0.3);
      box-shadow: 0 10px 18px rgba(99, 102, 241, 0.12);
    }
  }
</style>
