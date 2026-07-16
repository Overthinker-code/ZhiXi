<script setup lang="ts">
  import { computed, onUnmounted, ref, watch } from 'vue';
  import {
    ChevronDown,
    CircleCheck,
    CircleStop,
    LoaderCircle,
    Square,
    TriangleAlert,
  } from 'lucide-vue-next';
  import ProcessPhaseItem from './ProcessPhaseItem.vue';

  type ProcessStatus =
    | 'idle'
    | 'running'
    | 'stopping'
    | 'stopped'
    | 'done'
    | 'error';

  const props = defineProps<{
    state?: Record<string, any> | null;
    loading?: boolean;
  }>();

  const emit = defineEmits<{
    (e: 'stop'): void;
  }>();

  const open = ref(false);
  const now = ref(Date.now());
  let timer: ReturnType<typeof window.setInterval> | null = null;

  const process = computed(() => props.state || {});
  const status = computed<ProcessStatus>(
    () => String(process.value.status || 'idle') as ProcessStatus
  );
  const phases = computed<Record<string, any>[]>(() =>
    Array.isArray(process.value.phases) ? process.value.phases : []
  );
  const tools = computed<Record<string, any>[]>(() =>
    Array.isArray(process.value.tools) ? process.value.tools : []
  );
  const answerChars = computed(() => Number(process.value.answerChars || 0));
  const panelId = computed(() => {
    const runId = String(process.value.runId || 'current').replace(/[^a-zA-Z0-9_-]/g, '');
    return `execution-trace-${runId}`;
  });

  function timestamp(value: unknown) {
    if (typeof value === 'number') return value;
    const parsed = Date.parse(String(value || ''));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function inferCategory(item: Record<string, any>, isTool = false) {
    if (item.category) return String(item.category);
    if (isTool) return String(item.tool || '').includes('retriev') ? 'retrieval' : 'tool';
    const key = `${item.id || ''} ${item.title || ''}`.toLowerCase();
    if (/retriev|检索|资料|引用/.test(key)) return 'retrieval';
    if (/verify|safe|校验|检查/.test(key)) return 'safety';
    if (/plan|规划|选择能力/.test(key)) return 'plan';
    if (/understand|route|理解|识别/.test(key)) return 'route';
    if (/compose|answer|model|组织回答|生成/.test(key)) return 'model';
    return 'output';
  }

  const streamItems = computed(() => {
    const phaseItems = phases.value.map((item, index) => ({
      key: `phase-${item.traceKey || item.stepId || item.id || index}`,
      title: item.title || '处理任务',
      text: item.summary || item.text || (item.status === 'done' ? '已完成' : '正在处理'),
      status: item.status || 'running',
      category: inferCategory(item),
      durationMs: Number(item.durationMs || 0),
      itemCount: 0,
      sequence: Number.isFinite(Number(item.sequence))
        ? Number(item.sequence)
        : Number.MAX_SAFE_INTEGER,
      time: timestamp(item.startedAt || item.finishedAt),
    }));
    const toolItems = tools.value.map((item, index) => ({
      key: `tool-${item.traceKey || item.callId || item.stepId || item.tool || index}`,
      title: item.title || '调用学习工具',
      text:
        item.resultSummary ||
        item.summary ||
        item.text ||
        (item.status === 'done' ? '调用完成' : '正在执行'),
      status: item.status || 'running',
      category: inferCategory(item, true),
      durationMs: Number(item.durationMs || 0),
      itemCount: Array.isArray(item.items) ? item.items.length : Number(item.itemCount || 0),
      sequence: Number.isFinite(Number(item.sequence))
        ? Number(item.sequence)
        : Number.MAX_SAFE_INTEGER,
      time: timestamp(item.startedAt || item.finishedAt),
    }));

    return [...phaseItems, ...toolItems]
      .sort((a, b) => a.sequence - b.sequence || a.time - b.time)
      .slice(-16);
  });

  const runningItem = computed(() =>
    [...streamItems.value]
      .reverse()
      .find((item) => ['running', 'stopping'].includes(String(item.status)))
  );
  const activeKey = computed(() => runningItem.value?.key || '');
  const completedCount = computed(
    () => streamItems.value.filter((item) => item.status === 'done').length
  );
  const hasProcess = computed(
    () => status.value !== 'idle' || phases.value.length > 0 || tools.value.length > 0
  );
  const startedAt = computed(() =>
    timestamp(process.value.startedAt || phases.value[0]?.startedAt || tools.value[0]?.startedAt)
  );
  const finishedAt = computed(() => timestamp(process.value.finishedAt));
  const elapsedSeconds = computed(() => {
    if (!startedAt.value) return 0;
    return Math.max(0, Math.floor(((finishedAt.value || now.value) - startedAt.value) / 1000));
  });
  const elapsed = computed(() => (elapsedSeconds.value ? `${elapsedSeconds.value} 秒` : ''));

  const heading = computed(() => {
    if (status.value === 'error') return '执行出现问题';
    if (status.value === 'stopping') return '正在停止';
    if (status.value === 'stopped') return '已停止';
    if (status.value === 'done') return '已完成';
    if (answerChars.value > 0) return '正在回答';
    return '正在分析';
  });
  const summary = computed(() => {
    if (status.value === 'stopping') return '正在结束模型输出和本轮工具连接';
    if (status.value === 'stopped') return '已保留停止前生成的内容';
    if (status.value === 'done') return process.value.currentSummary || '本轮处理完成';
    if (status.value === 'error') return process.value.currentSummary || '部分步骤未完成';
    return runningItem.value?.text || process.value.currentSummary || '正在准备本轮回答';
  });
  const statusLabel = computed(() => {
    if (status.value === 'done') return '完成';
    if (status.value === 'stopped') return '已停止';
    if (status.value === 'error') return '异常';
    return '实时';
  });
  const statusIcon = computed(() => {
    if (status.value === 'done') return CircleCheck;
    if (status.value === 'stopped') return CircleStop;
    if (status.value === 'error') return TriangleAlert;
    return LoaderCircle;
  });
  const canStop = computed(
    () => Boolean(props.loading) && status.value === 'running'
  );

  watch(
    () => process.value.runId,
    () => {
      open.value = false;
    }
  );

  watch(
    () => props.loading,
    (loading) => {
      if (loading && !timer) {
        now.value = Date.now();
        timer = window.setInterval(() => {
          now.value = Date.now();
        }, 1000);
      } else if (!loading && timer) {
        window.clearInterval(timer);
        timer = null;
      }
    },
    { immediate: true }
  );

  onUnmounted(() => {
    if (timer) window.clearInterval(timer);
  });
</script>

<template>
  <section
    v-if="hasProcess"
    class="execution-trace"
    :class="[`is-${status}`, { 'is-open': open }]"
  >
    <div class="execution-trace__bar">
      <button
        type="button"
        class="execution-trace__summary"
        :aria-expanded="open"
        :aria-controls="panelId"
        @click="open = !open"
      >
        <component :is="statusIcon" class="execution-trace__status-icon" :size="16" />
        <span class="execution-trace__copy">
          <span class="execution-trace__title-row">
            <strong>{{ heading }}</strong>
            <time v-if="elapsed">{{ elapsed }}</time>
          </span>
          <span class="execution-trace__detail">{{ summary }}</span>
        </span>
        <ChevronDown class="execution-trace__chevron" :size="16" aria-hidden="true" />
      </button>
      <button
        v-if="loading && ['running', 'stopping'].includes(status)"
        type="button"
        class="execution-trace__stop"
        :disabled="!canStop"
        :aria-label="status === 'stopping' ? '正在停止生成' : '停止生成'"
        :title="status === 'stopping' ? '正在停止' : '停止生成'"
        data-testid="trace-stop-generation"
        @click="emit('stop')"
      >
        <Square :size="11" fill="currentColor" />
      </button>
    </div>

    <div
      v-if="open"
      :id="panelId"
      class="execution-trace__panel"
      role="status"
      aria-live="polite"
      aria-atomic="false"
    >
      <header>
        <div>
          <strong>活动</strong>
          <span>{{ statusLabel }}</span>
        </div>
        <p>展示任务和工具摘要，不展示模型内部推理</p>
      </header>

      <div v-if="streamItems.length" class="execution-trace__steps">
        <ProcessPhaseItem
          v-for="item in streamItems"
          :key="item.key"
          :title="item.title"
          :text="item.text"
          :status="item.status"
          :active="item.key === activeKey"
          :category="item.category"
          :duration-ms="item.durationMs"
          :item-count="item.itemCount"
        />
      </div>
      <div v-else class="execution-trace__connecting">
        <LoaderCircle :size="15" />
        <span>正在连接执行服务…</span>
      </div>

      <footer>
        <span>{{ completedCount }}/{{ streamItems.length || 1 }} 项已完成</span>
        <time v-if="elapsed">用时 {{ elapsed }}</time>
      </footer>
    </div>
  </section>
</template>

<style scoped lang="scss">
  .execution-trace {
    width: min(820px, 100%);
    margin: 0 auto 12px;
    color: #475467;
  }

  .execution-trace__bar {
    display: flex;
    align-items: center;
    gap: 5px;
    width: fit-content;
    max-width: 100%;
  }

  .execution-trace__summary {
    display: grid;
    min-width: 0;
    max-width: min(720px, calc(100vw - 410px));
    min-height: 42px;
    grid-template-columns: 20px minmax(0, 1fr) 18px;
    align-items: center;
    gap: 8px;
    padding: 5px 9px 5px 7px;
    border: 0;
    border-radius: 10px;
    color: #475467;
    background: transparent;
    text-align: left;
    cursor: pointer;
    transition: background 160ms ease;

    &:hover,
    &:focus-visible {
      background: #f5f5f5;
      outline: none;
    }
  }

  .execution-trace__status-icon {
    color: #667085;
  }

  .is-running .execution-trace__status-icon,
  .is-stopping .execution-trace__status-icon {
    animation: trace-rotate 1.4s linear infinite;
  }

  .is-done .execution-trace__status-icon { color: #067647; }
  .is-stopped .execution-trace__status-icon { color: #667085; }
  .is-error .execution-trace__status-icon { color: #d92d20; }

  .execution-trace__copy { min-width: 0; }

  .execution-trace__title-row {
    display: flex;
    align-items: center;
    gap: 7px;

    strong {
      color: #344054;
      font-size: 13px;
      font-weight: 650;
    }

    time {
      color: #98a2b3;
      font-size: 11px;
      font-variant-numeric: tabular-nums;
    }
  }

  .execution-trace__detail {
    display: block;
    margin-top: 1px;
    overflow: hidden;
    color: #7a8494;
    font-size: 12px;
    line-height: 1.35;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .execution-trace__chevron {
    color: #98a2b3;
    transition: transform 180ms ease;
  }

  .is-open .execution-trace__chevron { transform: rotate(180deg); }

  .execution-trace__stop {
    display: inline-flex;
    flex: 0 0 auto;
    width: 30px;
    height: 30px;
    align-items: center;
    justify-content: center;
    border: 1px solid #e4e7ec;
    border-radius: 999px;
    color: #475467;
    background: #fff;
    cursor: pointer;
    transition: border-color 160ms ease, background 160ms ease, transform 120ms ease;

    &:hover:not(:disabled) {
      border-color: #cfd4dc;
      background: #f7f7f8;
    }

    &:active:not(:disabled) { transform: scale(0.96); }
    &:disabled { cursor: wait; opacity: 0.55; }
  }

  .execution-trace__panel {
    width: min(760px, 100%);
    margin: 3px 0 0 27px;
    padding: 12px 14px 9px;
    border-radius: 14px;
    background: #f7f7f8;
    animation: trace-enter 160ms ease both;

    > header,
    > footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    > header {
      padding: 0 1px 8px;
      border-bottom: 1px solid #e8e9eb;

      div { display: flex; align-items: center; gap: 7px; }
      strong { color: #344054; font-size: 12px; font-weight: 680; }
      span {
        padding: 1px 6px;
        border-radius: 999px;
        color: #667085;
        background: #e9eaed;
        font-size: 10px;
      }
      p { margin: 0; color: #98a2b3; font-size: 11px; }
    }

    > footer {
      padding: 8px 1px 0 38px;
      border-top: 1px solid #e8e9eb;
      color: #98a2b3;
      font-size: 11px;
      font-variant-numeric: tabular-nums;
    }
  }

  .execution-trace__steps {
    max-height: 300px;
    overflow-y: auto;
    padding: 5px 1px;
    scrollbar-width: thin;
  }

  .execution-trace__connecting {
    display: flex;
    min-height: 44px;
    align-items: center;
    gap: 8px;
    padding: 7px 4px;
    color: #667085;
    font-size: 12px;

    svg { animation: trace-rotate 1.4s linear infinite; }
  }

  @keyframes trace-rotate { to { transform: rotate(360deg); } }
  @keyframes trace-enter {
    from { opacity: 0; transform: translateY(-3px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @media (max-width: 1280px) {
    .execution-trace__summary { max-width: calc(100vw - 380px); }
  }

  @media (max-width: 720px) {
    .execution-trace__summary { max-width: calc(100vw - 92px); }
    .execution-trace__panel { margin-left: 0; }
    .execution-trace__panel > header p { display: none; }
  }

  @media (prefers-reduced-motion: reduce) {
    .execution-trace__status-icon,
    .execution-trace__connecting svg,
    .execution-trace__panel { animation: none !important; }
  }
</style>
