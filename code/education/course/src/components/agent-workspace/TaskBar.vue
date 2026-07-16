<script setup lang="ts">
  export interface LearningTaskSummary {
    title: string;
    goal?: string;
    currentStage?: string;
    progress?: number;
    deadline?: string | null;
  }

  defineProps<{
    task?: LearningTaskSummary | null;
    loading?: boolean;
  }>();

  const emit = defineEmits<{
    (event: 'edit'): void;
  }>();
</script>

<template>
  <section class="task-bar" aria-label="当前学习任务">
    <div class="task-bar__identity">
      <span class="task-bar__eyebrow">当前学习任务</span>
      <template v-if="loading">
        <div class="task-bar__skeleton" />
      </template>
      <template v-else-if="task">
        <strong>{{ task.title }}</strong>
        <small v-if="task.goal">{{ task.goal }}</small>
      </template>
      <template v-else>
        <strong>暂未设置学习任务</strong>
        <small>开始一次学习会话后，任务进度将在这里同步。</small>
      </template>
    </div>

    <button v-if="task && !loading" type="button" class="task-bar__edit" @click="emit('edit')">
      编辑任务
    </button>

    <div v-if="task" class="task-bar__status">
      <div class="task-bar__stage">
        <span>当前阶段</span>
        <strong>{{ task.currentStage || '待规划' }}</strong>
      </div>
      <div v-if="task.deadline" class="task-bar__deadline">
        <span>截止日期</span>
        <strong>{{ new Date(task.deadline).toLocaleDateString('zh-CN') }}</strong>
      </div>
      <div class="task-bar__progress">
        <span>{{ Math.min(100, Math.max(0, task.progress || 0)) }}%</span>
        <div>
          <i :style="{ width: `${Math.min(100, Math.max(0, task.progress || 0))}%` }" />
        </div>
      </div>
    </div>
    <span v-else-if="!loading" class="task-bar__empty-badge">等待任务</span>
  </section>
</template>

<style scoped lang="scss">
  .task-bar {
    grid-area: task;
    min-height: 76px;
    display: flex;
    align-items: center;
    gap: 28px;
    padding: 12px 22px;
    border-bottom: 1px solid rgba(79, 70, 229, 0.1);
    background:
      radial-gradient(circle at 12% 0%, rgba(99, 102, 241, 0.11), transparent 36%),
      rgba(255, 255, 255, 0.94);
  }

  .task-bar__identity {
    min-width: 0;
    flex: 1;
    display: grid;
    gap: 2px;

    strong {
      overflow: hidden;
      color: #101828;
      font-size: 15px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    small {
      overflow: hidden;
      color: #667085;
      font-size: 12px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .task-bar__eyebrow {
    color: #6366f1;
    font-size: 11px;
    font-weight: 750;
    letter-spacing: 0.08em;
  }

  .task-bar__status {
    width: min(410px, 42vw);
    display: grid;
    grid-template-columns: minmax(100px, 0.9fr) minmax(100px, 0.9fr) minmax(150px, 1.35fr);
    align-items: center;
    gap: 24px;
  }

  .task-bar__edit {
    flex: 0 0 auto;
    padding: 6px 11px;
    border: 1px solid rgba(99, 102, 241, 0.22);
    border-radius: 8px;
    color: #4f46e5;
    background: #fff;
    font-size: 12px;
    cursor: pointer;

    &:hover {
      border-color: #6366f1;
      background: #f7f7ff;
    }
  }

  .task-bar__stage {
    display: grid;
    gap: 3px;

    span { color: #98a2b3; font-size: 11px; }
    strong { color: #344054; font-size: 13px; }
  }

  .task-bar__deadline {
    display: grid;
    gap: 3px;

    span { color: #98a2b3; font-size: 11px; }
    strong { color: #344054; font-size: 13px; }
  }

  .task-bar__progress {
    display: grid;
    grid-template-columns: auto 1fr;
    align-items: center;
    gap: 10px;

    span { color: #4f46e5; font-size: 13px; font-weight: 750; }

    div {
      height: 7px;
      overflow: hidden;
      border-radius: 999px;
      background: #e9eafe;
    }

    i {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #6366f1, #8b5cf6);
    }
  }

  .task-bar__empty-badge {
    padding: 7px 11px;
    border: 1px solid rgba(99, 102, 241, 0.14);
    border-radius: 999px;
    background: #f7f7ff;
    color: #667085;
    font-size: 12px;
  }

  .task-bar__skeleton {
    width: min(340px, 75%);
    height: 18px;
    border-radius: 8px;
    background: linear-gradient(90deg, #eef0f7, #f8f9fc, #eef0f7);
    background-size: 200% 100%;
    animation: task-loading 1.4s linear infinite;
  }

  @keyframes task-loading {
    to { background-position: -200% 0; }
  }

  @media (max-width: 760px) {
    .task-bar { min-height: 66px; padding: 10px 14px; }
    .task-bar__identity small { display: none; }
    .task-bar__status { width: auto; grid-template-columns: minmax(110px, 1fr); }
    .task-bar__stage, .task-bar__deadline { display: none; }
  }
</style>
