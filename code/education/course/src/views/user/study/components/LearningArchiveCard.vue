<template>
  <a-card class="learning-archive-card" :bordered="false">
    <template #title>
      <span>🎓 学习档案</span>
    </template>

    <div v-if="state === 'idle'" class="learning-archive-empty">
      <p>让 AI 综合分析你的学习数据，生成完整的学习档案。</p>
      <a-button type="primary" @click="generate">
        让 AI 生成我的学习档案
      </a-button>
    </div>

    <div v-else-if="state === 'loading'" class="learning-archive-loading">
      <a-spin />
      <span>AI 正在生成学习档案，可能需要 10-30 秒...</span>
    </div>

    <div v-else-if="state === 'error'" class="learning-archive-error">
      <span>生成失败，请稍后重试</span>
      <a-button type="primary" size="small" @click="generate">
        重试
      </a-button>
    </div>

    <div v-else class="learning-archive-content">
      <div class="learning-archive-summary">
        <h4>总览</h4>
        <p>{{ data?.summary }}</p>
      </div>

      <div class="learning-archive-meta">
        <div v-if="data?.current_goal" class="learning-archive-meta-item">
          <span class="learning-archive-meta-label">当前目标</span>
          <span class="learning-archive-meta-value">{{ data.current_goal }}</span>
        </div>
        <div v-if="data?.learning_style" class="learning-archive-meta-item">
          <span class="learning-archive-meta-label">学习风格</span>
          <span class="learning-archive-meta-value">{{ data.learning_style }}</span>
        </div>
        <div v-if="data?.risk_level" class="learning-archive-meta-item">
          <span class="learning-archive-meta-label">风险等级</span>
          <a-tag :color="riskColor">{{ data.risk_level }}</a-tag>
        </div>
      </div>

      <div v-if="data?.strengths?.length" class="learning-archive-section">
        <h4>优势</h4>
        <a-space wrap>
          <a-tag v-for="s in data.strengths" :key="s" color="green">{{ s }}</a-tag>
        </a-space>
      </div>

      <div v-if="data?.weak_points?.length" class="learning-archive-section">
        <h4>待提升</h4>
        <a-space wrap>
          <a-tag v-for="w in data.weak_points" :key="w" color="red">{{ w }}</a-tag>
        </a-space>
      </div>

      <div v-if="data?.recommended_actions?.length" class="learning-archive-section">
        <h4>推荐行动</h4>
        <ul class="learning-archive-list">
          <li v-for="(a, i) in data.recommended_actions" :key="i">{{ a }}</li>
        </ul>
      </div>

      <div v-if="data?.recommended_resources?.length" class="learning-archive-section">
        <h4>推荐资源</h4>
        <ul class="learning-archive-list">
          <li v-for="(r, i) in data.recommended_resources" :key="i">{{ r }}</li>
        </ul>
      </div>

      <div v-if="data?.follow_up_questions?.length" class="learning-archive-section">
        <h4>可以继续探索的问题</h4>
        <ul class="learning-archive-list">
          <li v-for="(q, i) in data.follow_up_questions" :key="i">{{ q }}</li>
        </ul>
      </div>

      <div v-if="data?.sections?.length" class="learning-archive-section">
        <h4>详细分析</h4>
        <a-collapse :default-active-key="sectionKeys">
          <a-collapse-item
            v-for="(sec, idx) in data.sections"
            :key="idx"
            :header="sec.title"
          >
            <p class="learning-archive-section-content">{{ sec.content }}</p>
          </a-collapse-item>
        </a-collapse>
      </div>

      <div class="learning-archive-footer">
        <a-button size="small" @click="generate">重新生成</a-button>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
  import { ref, computed } from 'vue';
  import { runLearningDiagnosis, type LearningReport } from '@/api/rag';

  type State = 'idle' | 'loading' | 'data' | 'error';

  const state = ref<State>('idle');
  const data = ref<LearningReport | null>(null);

  const riskColor = computed(() => {
    const lv = data.value?.risk_level;
    if (lv === 'high') return 'red';
    if (lv === 'low') return 'green';
    return 'orange';
  });

  const sectionKeys = computed(
    () => data.value?.sections?.map((_, i) => i) || []
  );

  const generate = async () => {
    state.value = 'loading';
    try {
      data.value = await runLearningDiagnosis(true);
      state.value = 'data';
    } catch (err) {
      console.error('[LearningArchiveCard] generate failed:', err);
      state.value = 'error';
    }
  };
</script>

<style scoped lang="less">
  .learning-archive-card {
    :deep(.arco-card-header) {
      border-bottom: 1px solid var(--color-neutral-3);
    }
  }

  .learning-archive-empty,
  .learning-archive-loading,
  .learning-archive-error {
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

  .learning-archive-content {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .learning-archive-summary,
  .learning-archive-section {
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

  .learning-archive-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    padding: 12px 16px;
    background: var(--color-fill-1);
    border-radius: 6px;
  }

  .learning-archive-meta-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }

  .learning-archive-meta-label {
    font-weight: 600;
    color: rgb(var(--gray-9));
  }

  .learning-archive-meta-value {
    color: rgb(var(--gray-8));
  }

  .learning-archive-list {
    margin: 0;
    padding-left: 20px;

    li {
      font-size: 14px;
      line-height: 1.8;
      color: rgb(var(--gray-8));
    }
  }

  .learning-archive-section-content {
    margin: 0;
    font-size: 14px;
    line-height: 1.7;
    color: rgb(var(--gray-8));
    white-space: pre-wrap;
  }

  .learning-archive-footer {
    display: flex;
    justify-content: flex-end;
    padding-top: 8px;
    border-top: 1px dashed var(--color-neutral-3);
  }
</style>
