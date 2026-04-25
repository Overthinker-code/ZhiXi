<template>
  <a-card class="wrong-question-card" :bordered="false">
    <template #title>
      <span>📝 错题诊断</span>
    </template>

    <div v-if="state === 'idle'" class="wrong-question-empty">
      <p>让 AI 分析你最近的错题，生成针对性的诊断报告。</p>
      <a-button type="primary" @click="generate">
        让 AI 诊断我的错题
      </a-button>
    </div>

    <div v-else-if="state === 'loading'" class="wrong-question-loading">
      <a-spin />
      <span>AI 正在分析错题，可能需要 10-30 秒...</span>
    </div>

    <div v-else-if="state === 'error'" class="wrong-question-error">
      <span>诊断失败，请稍后重试</span>
      <a-button type="primary" size="small" @click="generate">
        重试
      </a-button>
    </div>

    <div v-else class="wrong-question-content">
      <div class="wrong-question-summary">
        <h4>诊断总览</h4>
        <p>{{ data?.summary }}</p>
      </div>

      <div
        v-if="data?.mistakes?.length"
        class="wrong-question-section"
      >
        <h4>错题诊断（{{ data.mistakes.length }} 条）</h4>
        <div
          v-for="(item, idx) in data.mistakes"
          :key="idx"
          class="wrong-question-item"
        >
          <div class="wrong-question-item-title">
            <span class="wrong-question-item-index">{{ idx + 1 }}</span>
            {{ item.title }}
          </div>
          <div class="wrong-question-item-row">
            <span class="wrong-question-item-label">症状:</span>
            <span>{{ item.symptom }}</span>
          </div>
          <div class="wrong-question-item-row">
            <span class="wrong-question-item-label">证据:</span>
            <span>{{ item.evidence }}</span>
          </div>
          <div class="wrong-question-item-row">
            <span class="wrong-question-item-label">改进策略:</span>
            <span>{{ item.fix_strategy }}</span>
          </div>
        </div>
      </div>

      <div
        v-if="data?.flashcards?.length"
        class="wrong-question-section"
      >
        <h4>知识卡片</h4>
        <a-space wrap>
          <a-tag
            v-for="card in data.flashcards"
            :key="card"
            color="orange"
          >
            {{ card }}
          </a-tag>
        </a-space>
      </div>

      <div class="wrong-question-footer">
        <a-button size="small" @click="generate">重新诊断</a-button>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
  import { ref } from 'vue';
  import { generateMistakeDigest, type MistakeDigest } from '@/api/rag';

  type State = 'idle' | 'loading' | 'data' | 'error';

  const state = ref<State>('idle');
  const data = ref<MistakeDigest | null>(null);

  const generate = async () => {
    state.value = 'loading';
    try {
      data.value = await generateMistakeDigest(true);
      state.value = 'data';
    } catch (err) {
      console.error('[WrongQuestionList] generate failed:', err);
      state.value = 'error';
    }
  };
</script>

<style scoped lang="less">
  .wrong-question-card {
    :deep(.arco-card-header) {
      border-bottom: 1px solid var(--color-neutral-3);
    }
  }

  .wrong-question-empty,
  .wrong-question-loading,
  .wrong-question-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    min-height: 180px;
    padding: 32px 16px;
    color: rgb(var(--gray-7));
    font-size: 14px;
    text-align: center;
  }

  .wrong-question-content {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .wrong-question-summary,
  .wrong-question-section {
    h4 {
      margin: 0 0 8px 0;
      font-size: 14px;
      font-weight: 600;
      color: rgb(var(--gray-9));
    }

    p {
      margin: 0;
      font-size: 14px;
      line-height: 1.6;
      color: rgb(var(--gray-8));
    }
  }

  .wrong-question-item {
    padding: 12px 16px;
    margin-bottom: 12px;
    background: var(--color-fill-1);
    border-radius: 6px;
    border-left: 3px solid rgb(var(--red-6));

    &:last-child {
      margin-bottom: 0;
    }
  }

  .wrong-question-item-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 600;
    color: rgb(var(--gray-9));
    margin-bottom: 8px;
  }

  .wrong-question-item-index {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 22px;
    height: 22px;
    padding: 0 6px;
    background: rgb(var(--red-6));
    color: white;
    font-size: 12px;
    border-radius: 11px;
  }

  .wrong-question-item-row {
    display: flex;
    gap: 8px;
    font-size: 13px;
    line-height: 1.7;
    color: rgb(var(--gray-8));
    margin-top: 4px;
  }

  .wrong-question-item-label {
    flex-shrink: 0;
    font-weight: 600;
    color: rgb(var(--gray-9));
  }

  .wrong-question-footer {
    display: flex;
    justify-content: flex-end;
    padding-top: 8px;
    border-top: 1px dashed var(--color-neutral-3);
  }
</style>
