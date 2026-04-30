<script setup lang="ts">
  import { computed } from 'vue';
  import { normalizeSuggestionList, normalizeSuggestionText } from '@/utils/llmDisplay';

  const props = defineProps<{
    suggestions?: unknown[];
  }>();

  const emit = defineEmits<{
    (e: 'pick', value: string): void;
  }>();

  const fallbackSuggestions = [
    '先补哪个核心知识点？',
    '能给一道由浅入深的练习题吗？',
    '答错时应该怎么快速纠正？',
  ];

  const displaySuggestions = computed(() => {
    const seen = new Set<string>();
    const normalized = [
      ...normalizeSuggestionList(props.suggestions || []),
      ...fallbackSuggestions.map(normalizeSuggestionText),
    ]
      .filter((item) => {
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
