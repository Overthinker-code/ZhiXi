<script setup lang="ts">
  import { computed } from 'vue';

  export interface AgentWorkflowItem {
    id: string;
    name: string;
    status: 'waiting' | 'running' | 'completed' | 'failed';
    progress?: number;
    message?: string;
  }

  const props = defineProps<{
    tasks: AgentWorkflowItem[];
    loading?: boolean;
  }>();

  const completedCount = computed(
    () => props.tasks.filter((item) => item.status === 'completed').length
  );

  function statusLabel(status: AgentWorkflowItem['status']) {
    return {
      waiting: '等待',
      running: '运行中',
      completed: '完成',
      failed: '失败',
    }[status];
  }
</script>

<template>
  <aside class="workflow-panel" aria-label="Agent 任务状态">
    <header>
      <div>
        <span>Agent Workflow</span>
        <strong>任务协作状态</strong>
      </div>
      <small v-if="tasks.length">{{ completedCount }}/{{ tasks.length }}</small>
    </header>

    <div v-if="loading && !tasks.length" class="workflow-loading">
      <span v-for="item in 4" :key="item" />
    </div>

    <div v-else-if="tasks.length" class="workflow-list">
      <article v-for="task in tasks" :key="task.id" :class="`is-${task.status}`">
        <span class="workflow-status">
          <i v-if="task.status === 'completed'">✓</i>
          <i v-else-if="task.status === 'failed'">!</i>
        </span>
        <div>
          <strong>{{ task.name }}</strong>
          <p>{{ task.message || statusLabel(task.status) }}</p>
          <div v-if="task.status === 'running'" class="workflow-progress">
            <i :style="{ width: `${task.progress || 36}%` }" />
          </div>
        </div>
        <small>{{ statusLabel(task.status) }}</small>
      </article>
    </div>

    <div v-else class="workflow-empty">
      <span class="workflow-empty__icon">◇</span>
      <strong>等待学习指令</strong>
      <p>发送问题后，这里将实时展示 Agent 的任务分工和执行状态。</p>
    </div>

    <footer>
      <span class="privacy-dot" />
      仅展示任务状态，不展示模型思考过程
    </footer>
  </aside>
</template>

<style scoped lang="scss">
  .workflow-panel {
    grid-area: workflow;
    min-width: 0;
    height: 100%;
    display: flex;
    flex-direction: column;
    padding: 18px 16px 14px;
    overflow: hidden;
    border-left: 1px solid rgba(15, 23, 42, 0.07);
    background: linear-gradient(180deg, #fbfbff, #f8f9fd);
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 3px 16px;

    div { display: grid; gap: 3px; }
    span { color: #6366f1; font-size: 11px; font-weight: 750; letter-spacing: 0.07em; }
    strong { color: #101828; font-size: 15px; }
    small { padding: 4px 8px; border-radius: 999px; background: #eceeff; color: #4f46e5; }
  }

  .workflow-list {
    flex: 1;
    overflow-y: auto;
    padding: 2px 2px 12px;
  }

  article {
    position: relative;
    display: grid;
    grid-template-columns: 24px minmax(0, 1fr) auto;
    gap: 10px;
    padding: 11px 8px;

    &:not(:last-child)::after {
      position: absolute;
      top: 36px;
      bottom: -5px;
      left: 19px;
      width: 1px;
      background: #e4e7ec;
      content: '';
    }

    div { min-width: 0; }
    strong { display: block; color: #344054; font-size: 13px; }
    p { margin: 3px 0 0; overflow: hidden; color: #667085; font-size: 12px; line-height: 1.45; text-overflow: ellipsis; }
    > small { color: #98a2b3; font-size: 11px; white-space: nowrap; }
  }

  .workflow-status {
    position: relative;
    z-index: 1;
    width: 20px;
    height: 20px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #d0d5dd;
    border-radius: 50%;
    background: #fff;

    i { color: #fff; font-size: 11px; font-style: normal; font-weight: 800; }
  }

  .is-running .workflow-status {
    border-color: #6366f1;
    background: #6366f1;
    box-shadow: 0 0 0 5px rgba(99, 102, 241, 0.1);
    animation: workflow-pulse 1.35s ease-in-out infinite;
  }

  .is-completed .workflow-status { border-color: #12b76a; background: #12b76a; }
  .is-failed .workflow-status { border-color: #f04438; background: #f04438; }

  .workflow-progress {
    height: 3px;
    margin-top: 7px;
    overflow: hidden;
    border-radius: 999px;
    background: #e9eafe;

    i { display: block; height: 100%; border-radius: inherit; background: #6366f1; }
  }

  .workflow-empty {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 24px;
    text-align: center;

    strong { margin-top: 12px; color: #344054; font-size: 14px; }
    p { max-width: 210px; margin: 7px 0 0; color: #98a2b3; font-size: 12px; line-height: 1.65; }
  }

  .workflow-empty__icon {
    width: 46px;
    height: 46px;
    display: grid;
    place-items: center;
    border: 1px solid rgba(99, 102, 241, 0.16);
    border-radius: 16px;
    background: #f0f2ff;
    color: #6366f1;
    font-size: 24px;
  }

  .workflow-loading { display: grid; gap: 12px; padding: 8px; }
  .workflow-loading span { height: 62px; border-radius: 14px; background: #eef0f7; }

  footer {
    display: flex;
    align-items: center;
    gap: 7px;
    padding-top: 12px;
    border-top: 1px solid rgba(15, 23, 42, 0.06);
    color: #98a2b3;
    font-size: 10px;
  }

  .privacy-dot { width: 6px; height: 6px; border-radius: 50%; background: #12b76a; }

  @keyframes workflow-pulse {
    50% { box-shadow: 0 0 0 7px rgba(99, 102, 241, 0.05); }
  }
</style>
