<script setup lang="ts">
  import { computed, onUnmounted, ref, watch } from 'vue';

  type ProcessStatus = 'idle' | 'running' | 'done' | 'error' | 'pending';

  const props = defineProps<{
    state?: Record<string, any> | null;
    loading?: boolean;
  }>();

  const userTouched = ref(false);
  const open = ref(true);
  const now = ref(Date.now());
  let timer: ReturnType<typeof window.setInterval> | null = null;

  const process = computed(() => props.state || {});
  const phases = computed<Record<string, any>[]>(() =>
    Array.isArray(process.value.phases) ? process.value.phases : []
  );
  const tools = computed<Record<string, any>[]>(() =>
    Array.isArray(process.value.tools) ? process.value.tools : []
  );
  const logs = computed<Record<string, any>[]>(() =>
    Array.isArray(process.value.logs) ? process.value.logs : []
  );
  const reasoningText = computed(() => String(process.value.reasoningText || '').trim());
  const status = computed<ProcessStatus>(() => String(process.value.status || 'idle') as ProcessStatus);
  const hasProcess = computed(() =>
    status.value !== 'idle' ||
    phases.value.length > 0 ||
    tools.value.length > 0 ||
    logs.value.length > 0 ||
    reasoningText.value
  );
  const activePhase = computed(() =>
    [...phases.value].reverse().find((item) => item.status === 'running') ||
    [...phases.value].reverse().find((item) => item.status === 'done') ||
    null
  );
  const activeTool = computed(() =>
    [...tools.value].reverse().find((item) => item.status === 'running') ||
    [...tools.value].reverse().find((item) => item.status === 'done') ||
    null
  );
  const startedAt = computed(() => {
    const value = process.value.startedAt || phases.value[0]?.startedAt || tools.value[0]?.startedAt;
    const time = value ? Number(value) : 0;
    return Number.isFinite(time) ? time : 0;
  });
  const elapsed = computed(() => {
    if (!props.loading || !startedAt.value) return '';
    const seconds = Math.max(0, Math.floor((now.value - startedAt.value) / 1000));
    return `${seconds}s`;
  });
  const summary = computed(() => {
    if (status.value === 'error') return '处理遇到问题';
    if (status.value === 'done') return '已完成处理';
    if (activeTool.value?.title) return `正在${activeTool.value.title}`;
    if (activePhase.value?.title) return `正在${activePhase.value.title}`;
    return '正在思考';
  });
  const detail = computed(() => {
    const raw =
      process.value.currentSummary ||
      activeTool.value?.text ||
      activeTool.value?.resultSummary ||
      activePhase.value?.text ||
      activePhase.value?.summary ||
      '正在根据问题组织处理步骤';
    return String(raw).replace(/\s+/g, ' ').trim();
  });
  const timelineItems = computed(() => {
    const phaseItems = phases.value.map((item) => ({
      id: `phase-${item.id}`,
      kind: 'phase',
      title: item.title || '处理阶段',
      text: item.summary || item.text || '',
      status: item.status || 'running',
      items: [],
      time: item.startedAt || item.finishedAt || 0,
    }));
    const toolItems = tools.value.map((item) => ({
      id: `tool-${item.tool}`,
      kind: 'tool',
      title: item.title || '工具调用',
      text: item.resultSummary || item.text || '',
      status: item.status || 'running',
      items: Array.isArray(item.items) ? item.items.slice(0, 3) : [],
      time: item.startedAt || item.finishedAt || 0,
    }));
    return [...phaseItems, ...toolItems].sort((a, b) => Number(a.time || 0) - Number(b.time || 0));
  });
  const visibleLogs = computed(() => logs.value.slice(-8).reverse());
  const reasoningPreview = computed(() =>
    reasoningText.value
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(-4)
  );

  function toggle() {
    userTouched.value = true;
    open.value = !open.value;
  }

  watch(
    () => props.loading,
    (loading) => {
      if (loading) {
        if (!userTouched.value) open.value = true;
        if (!timer) {
          now.value = Date.now();
          timer = window.setInterval(() => {
            now.value = Date.now();
          }, 1000);
        }
      } else {
        if (!userTouched.value) open.value = false;
        if (timer) {
          window.clearInterval(timer);
          timer = null;
        }
      }
    },
    { immediate: true }
  );

  watch(
    () => logs.value.length,
    (count) => {
      if (props.loading && count > 6 && !userTouched.value) {
        open.value = false;
      }
    }
  );

  onUnmounted(() => {
    if (timer) window.clearInterval(timer);
  });
</script>

<template>
  <section v-if="hasProcess" class="live-process" :class="[`is-${status}`, { 'is-open': open }]">
    <button type="button" class="live-process__bar" @click="toggle">
      <span class="live-process__pulse" />
      <span class="live-process__summary">{{ summary }}</span>
      <span class="live-process__detail">{{ detail }}</span>
      <time v-if="elapsed">{{ elapsed }}</time>
      <span class="live-process__toggle">{{ open ? '收起' : '展开' }}</span>
    </button>

    <div v-if="open" class="live-process__body" aria-live="polite">
      <div class="live-process__timeline">
        <div
          v-for="item in timelineItems"
          :key="item.id"
          class="live-step"
          :class="[`is-${item.status}`, `is-${item.kind}`]"
        >
          <span class="live-step__dot" />
          <div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.text || (item.status === 'running' ? '进行中' : '已完成') }}</p>
            <div v-if="item.items?.length" class="live-step__items">
              <span v-for="entry in item.items" :key="entry.title || entry.chunk || entry">
                {{ entry.title || entry.chunk || entry.summary || entry }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="live-process__stream">
        <div class="live-process__stream-head">
          <span>{{ loading ? '实时动态' : '处理摘要' }}</span>
          <b v-if="loading">LIVE</b>
        </div>
        <div v-if="reasoningPreview.length" class="live-reasoning">
          <span>思考摘要</span>
          <p v-for="line in reasoningPreview" :key="line">{{ line }}</p>
        </div>
        <div class="live-log-list">
          <div v-for="item in visibleLogs" :key="item.id" class="live-log" :class="`is-${item.status || 'running'}`">
            <time>{{ item.time || 'now' }}</time>
            <p>{{ item.text }}</p>
          </div>
          <div v-if="!visibleLogs.length" class="live-log is-running">
            <time>now</time>
            <p>正在建立流式连接，等待后端处理事件。</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped lang="scss">
  .live-process {
    margin: 6px 0 14px;
    color: #344054;
  }

  .live-process__bar {
    display: inline-flex;
    max-width: 100%;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 999px;
    background: #fff;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.03);
    color: #475467;
    cursor: pointer;
    transition: border-color 0.16s ease, box-shadow 0.16s ease;

    &:hover {
      border-color: rgba(99, 102, 241, 0.28);
      box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
    }

    time {
      color: #98a2b3;
      font-size: 12px;
    }
  }

  .live-process__pulse {
    width: 8px;
    height: 8px;
    flex: 0 0 auto;
    border-radius: 999px;
    background: #6366f1;
    box-shadow: 0 0 0 6px rgba(99, 102, 241, 0.1);
    animation: live-pulse 1.25s ease-in-out infinite;
  }

  .is-done .live-process__pulse {
    animation: none;
    background: #12b76a;
    box-shadow: 0 0 0 5px rgba(18, 183, 106, 0.1);
  }

  .is-error .live-process__pulse {
    animation: none;
    background: #f04438;
    box-shadow: 0 0 0 5px rgba(240, 68, 56, 0.12);
  }

  .live-process__summary {
    color: #4f46e5;
    font-size: 13px;
    font-weight: 760;
    white-space: nowrap;
  }

  .live-process__detail {
    min-width: 0;
    max-width: min(520px, 52vw);
    overflow: hidden;
    color: #667085;
    font-size: 13px;
    font-weight: 620;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .live-process__toggle {
    color: #4f46e5;
    font-size: 13px;
    font-weight: 760;
    white-space: nowrap;
  }

  .live-process__body {
    display: grid;
    grid-template-columns: minmax(220px, 0.9fr) minmax(280px, 1.2fr);
    gap: 14px;
    margin-top: 10px;
    padding: 14px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 22px;
    background:
      linear-gradient(90deg, rgba(99, 102, 241, 0.055), rgba(255, 255, 255, 0) 58%),
      #fff;
    box-shadow: 0 14px 40px rgba(15, 23, 42, 0.05);
    animation: process-enter 0.16s ease both;
  }

  .live-process__timeline {
    display: grid;
    gap: 2px;
    padding: 8px 4px;
  }

  .live-step {
    position: relative;
    display: grid;
    grid-template-columns: 20px 1fr;
    gap: 8px;
    padding: 6px 0 10px;

    &::before {
      position: absolute;
      top: 22px;
      bottom: -6px;
      left: 7px;
      width: 1px;
      background: rgba(99, 102, 241, 0.16);
      content: '';
    }

    &:last-child::before {
      display: none;
    }

    strong {
      display: block;
      color: #1d2939;
      font-size: 14px;
      font-weight: 760;
    }

    p {
      margin: 3px 0 0;
      color: #667085;
      font-size: 13px;
      line-height: 1.55;
    }
  }

  .live-step__dot {
    z-index: 1;
    width: 14px;
    height: 14px;
    margin-top: 3px;
    border: 3px solid #fff;
    border-radius: 999px;
    background: #d0d5dd;
    box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.08);
  }

  .live-step.is-running .live-step__dot {
    background: #6366f1;
    box-shadow: 0 0 0 5px rgba(99, 102, 241, 0.1);
    animation: live-pulse 1.25s ease-in-out infinite;
  }

  .live-step.is-done .live-step__dot {
    background: #12b76a;
  }

  .live-step.is-error .live-step__dot {
    background: #f04438;
  }

  .live-step__items {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;

    span {
      max-width: 100%;
      overflow: hidden;
      padding: 4px 8px;
      border-radius: 999px;
      background: #f2f4f7;
      color: #667085;
      font-size: 12px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .live-process__stream {
    min-width: 0;
    padding: 12px;
    border: 1px solid rgba(15, 23, 42, 0.07);
    border-radius: 18px;
    background: rgba(248, 250, 252, 0.72);
  }

  .live-process__stream-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
    color: #4f46e5;
    font-size: 13px;
    font-weight: 760;

    b {
      padding: 2px 7px;
      border-radius: 999px;
      background: rgba(99, 102, 241, 0.1);
      font-size: 10px;
      letter-spacing: 0.08em;
    }
  }

  .live-reasoning {
    margin-bottom: 10px;
    padding: 10px;
    border-radius: 14px;
    background: #fff;

    span {
      color: #667085;
      font-size: 12px;
      font-weight: 760;
    }

    p {
      margin: 6px 0 0;
      color: #344054;
      font-size: 13px;
      line-height: 1.6;
    }
  }

  .live-log-list {
    display: grid;
    gap: 8px;
  }

  .live-log {
    display: grid;
    grid-template-columns: 52px 1fr;
    gap: 8px;
    padding: 9px 10px;
    border-radius: 13px;
    background: #fff;
    color: #475467;
    font-size: 13px;

    time {
      color: #98a2b3;
      font-variant-numeric: tabular-nums;
    }

    p {
      margin: 0;
      line-height: 1.5;
    }
  }

  .live-log.is-running {
    box-shadow: inset 3px 0 0 #6366f1;
  }

  @keyframes live-pulse {
    0%, 100% {
      opacity: 0.72;
      transform: scale(0.94);
    }

    50% {
      opacity: 1;
      transform: scale(1);
    }
  }

  @keyframes process-enter {
    from {
      opacity: 0;
      transform: translateY(6px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .live-process__pulse,
    .live-step.is-running .live-step__dot,
    .live-process__body {
      animation: none;
    }
  }

  @media (max-width: 900px) {
    .live-process__body {
      grid-template-columns: 1fr;
    }

    .live-process__detail {
      max-width: 42vw;
    }
  }
</style>
