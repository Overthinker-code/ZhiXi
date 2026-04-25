<template>
  <a-card class="review-plan-card" :bordered="false">
    <template #title>
      <span>📚 AI 复习计划</span>
    </template>

    <div v-if="state === 'idle'" class="review-plan-empty">
      <p>根据你的学习情况，让 AI 为你生成专属复习计划。</p>
      <a-button type="primary" @click="generate">
        让 AI 帮我生成复习计划
      </a-button>
    </div>

    <div v-else-if="state === 'loading'" class="review-plan-loading">
      <a-spin />
      <span>AI 正在生成复习计划，可能需要 10-30 秒...</span>
    </div>

    <div v-else-if="state === 'error'" class="review-plan-error">
      <span>生成失败，请稍后重试</span>
      <a-button type="primary" size="small" @click="generate">
        重试
      </a-button>
    </div>

    <div v-else class="review-plan-content">
      <div class="review-plan-summary">
        <h4>总览</h4>
        <p>{{ data?.summary }}</p>
      </div>

      <div
        v-if="data?.focus_topics?.length"
        class="review-plan-section"
      >
        <h4>重点主题</h4>
        <a-space wrap>
          <a-tag
            v-for="topic in data.focus_topics"
            :key="topic"
            color="arcoblue"
          >
            {{ topic }}
          </a-tag>
        </a-space>
      </div>

      <div
        v-if="data?.daily_plan?.length"
        class="review-plan-section"
      >
        <h4>每日计划</h4>
        <a-collapse :default-active-key="dailyPlanKeys">
          <a-collapse-item
            v-for="(day, idx) in data.daily_plan"
            :key="idx"
            :header="`${day.day_label} · ${day.focus}`"
          >
            <ul class="review-plan-tasks">
              <li
                v-for="(task, taskIdx) in day.tasks"
                :key="taskIdx"
              >
                {{ task }}
              </li>
            </ul>
          </a-collapse-item>
        </a-collapse>
      </div>

      <div
        v-if="data?.checkpoints?.length"
        class="review-plan-section"
      >
        <h4>检查点</h4>
        <ul class="review-plan-tasks">
          <li
            v-for="(cp, idx) in data.checkpoints"
            :key="idx"
          >
            {{ cp }}
          </li>
        </ul>
      </div>

      <div class="review-plan-footer">
        <a-button size="small" @click="generate">重新生成</a-button>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
  import { ref, computed } from 'vue';
  import { generateReviewPlan, type ReviewPlan } from '@/api/rag';

  type State = 'idle' | 'loading' | 'data' | 'error';

  const state = ref<State>('idle');
  const data = ref<ReviewPlan | null>(null);

  const dailyPlanKeys = computed(
    () => data.value?.daily_plan?.map((_, i) => i) || []
  );

  const generate = async () => {
    state.value = 'loading';
    try {
      data.value = await generateReviewPlan(true);
      state.value = 'data';
    } catch (err) {
      console.error('[ReviewPlanCard] generate failed:', err);
      state.value = 'error';
    }
  };
</script>

<style scoped lang="less">
  .review-plan-card {
    :deep(.arco-card-header) {
      border-bottom: 1px solid var(--color-neutral-3);
    }
  }

  .review-plan-empty,
  .review-plan-loading,
  .review-plan-error {
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

  .review-plan-content {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .review-plan-summary,
  .review-plan-section {
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

  .review-plan-tasks {
    margin: 0;
    padding-left: 20px;

    li {
      font-size: 14px;
      line-height: 1.8;
      color: rgb(var(--gray-8));
    }
  }

  .review-plan-footer {
    display: flex;
    justify-content: flex-end;
    padding-top: 8px;
    border-top: 1px dashed var(--color-neutral-3);
  }
</style>
