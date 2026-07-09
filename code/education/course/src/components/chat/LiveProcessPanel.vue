<script setup lang="ts">
  import { computed, onUnmounted, ref, watch } from 'vue';
  import ProcessPhaseItem from './ProcessPhaseItem.vue';

  type ProcessStatus = 'idle' | 'running' | 'done' | 'error';

  const props = defineProps<{
    state?: Record<string, any> | null;
    loading?: boolean;
  }>();

  const open = ref(true);
  const manuallyToggled = ref(false);
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
  const status = computed<ProcessStatus>(() => String(process.value.status || 'idle') as ProcessStatus);
  const startedAt = computed(() => Number(process.value.startedAt || phases.value[0]?.startedAt || 0));
  const answerChars = computed(() => Number(process.value.answerChars || 0));
  const hasProcess = computed(() =>
    status.value !== 'idle' || phases.value.length > 0 || tools.value.length > 0 || logs.value.length > 0
  );
  const elapsed = computed(() => {
    if (!props.loading || !startedAt.value) return '';
    return `${Math.max(0, Math.floor((now.value - startedAt.value) / 1000))}s`;
  });
  const activePhase = computed(() =>
    [...phases.value].reverse().find((item) => item.status === 'running') ||
    [...phases.value].reverse().find((item) => item.status === 'done') ||
    null
  );
  const runningPhase = computed(() => [...phases.value].reverse().find((item) => item.status === 'running') || null);
  const activeTool = computed(() =>
    [...tools.value].reverse().find((item) => item.status === 'running') ||
    [...tools.value].reverse().find((item) => item.status === 'done') ||
    null
  );
  const runningTool = computed(() => [...tools.value].reverse().find((item) => item.status === 'running') || null);
  const barTitle = computed(() => {
    if (status.value === 'error') return '处理遇到问题';
    if (status.value === 'done') return '已完成处理';
    if (props.loading && answerChars.value > 0) return '正在输出回答';
    if (runningTool.value?.title) return '正在工具调用';
    if (runningPhase.value?.title?.includes('检索')) return '正在检索';
    if (runningPhase.value?.title?.includes('校验')) return '正在校验输出';
    if (runningPhase.value?.title?.includes('组织') || runningPhase.value?.title?.includes('生成')) return '正在组织回答';
    return '正在处理';
  });
  const barDetail = computed(() => {
    if (props.loading && answerChars.value > 0) {
      return '正文正在流式生成，处理记录可展开查看。';
    }
    const raw =
      process.value.currentSummary ||
      activeTool.value?.resultSummary ||
      activeTool.value?.text ||
      activePhase.value?.summary ||
      activePhase.value?.text ||
      '正在从问题、资料和上下文中整理回答依据';
    return String(raw).replace(/\s+/g, ' ').trim();
  });
  const streamItems = computed(() => {
    const phaseItems = phases.value.map((item) => ({
      key: `phase-${item.id}`,
      title: item.title || '处理阶段',
      text: item.summary || item.text || '进行中',
      status: item.status || 'running',
      time: item.startedAt || item.finishedAt || 0,
    }));
    const toolItems = tools.value.map((item) => ({
      key: `tool-${item.tool}`,
      title: item.title || '工具调用',
      text: item.resultSummary || item.text || '工具正在运行',
      status: item.status || 'running',
      time: item.startedAt || item.finishedAt || 0,
    }));
    const logItems = logs.value
      .slice(-6)
      .map((item: Record<string, any>) => ({
        key: `log-${item.id || item.timestamp || item.text}`,
        title: item.title || '处理过程',
        text: item.text,
        status: item.status || 'running',
        time: item.timestamp || Date.now(),
      }));

    const merged = [...phaseItems, ...toolItems, ...logItems]
      .filter((item) => String(item.text || '').trim())
      .sort((a, b) => Number(a.time || 0) - Number(b.time || 0));

    const seen = new Set<string>();
    return merged
      .filter((item) => {
        const signature = `${item.title}-${String(item.text).slice(0, 80)}`;
        if (seen.has(signature)) return false;
        seen.add(signature);
        return true;
      })
      .slice(-12);
  });
  const activeKey = computed(() =>
    [...streamItems.value].reverse().find((item) => item.status === 'running')?.key || ''
  );
  const hasAnswer = computed(() => answerChars.value > 0);

  function toggle() {
    manuallyToggled.value = true;
    open.value = !open.value;
  }

  watch(
    () => props.loading,
    (loading) => {
      if (loading) {
        if (!manuallyToggled.value) open.value = true;
        if (!timer) {
          now.value = Date.now();
          timer = window.setInterval(() => {
            now.value = Date.now();
          }, 1000);
        }
      } else {
        if (!manuallyToggled.value) open.value = false;
        if (timer) {
          window.clearInterval(timer);
          timer = null;
        }
      }
    },
    { immediate: true }
  );

  watch(answerChars, (chars) => {
    if (props.loading && chars > 24 && !manuallyToggled.value) {
      open.value = false;
    }
  });

  watch(status, (next) => {
    if (next === 'done') {
      open.value = false;
      manuallyToggled.value = false;
    }
  });

  onUnmounted(() => {
    if (timer) window.clearInterval(timer);
  });
</script>

<template>
  <section v-if="hasProcess" class="live-process" :class="[`is-${status}`, { 'is-open': open }]">
    <button type="button" class="live-process-bar" @click="toggle">
      <span class="live-process-bar__dot">
        <i v-if="status === 'done'">✓</i>
      </span>
      <span class="live-process-bar__title">{{ barTitle }}</span>
      <span class="live-process-bar__detail">{{ barDetail }}</span>
      <time v-if="elapsed">{{ elapsed }}</time>
      <span class="live-process-bar__toggle">{{ open ? '收起' : '展开' }}</span>
    </button>

    <div v-if="open" class="live-process-stream" aria-live="polite">
      <ProcessPhaseItem
        v-for="item in streamItems"
        :key="item.key"
        :title="item.title"
        :text="item.text"
        :status="item.status"
        :active="item.key === activeKey"
      />
      <div v-if="!streamItems.length" class="live-process-empty">
        <span />
        <p>正在建立流式连接，等待后端处理事件。</p>
      </div>
      <div v-if="loading && hasAnswer" class="live-process-hint">回答已开始输出，处理过程将自动收敛为状态条。</div>
    </div>
  </section>
</template>

<style scoped lang="scss">
  .live-process {
    width: min(820px, 100%);
    margin: 4px auto 14px;
  }

  .live-process-bar {
    display: inline-flex;
    max-width: 100%;
    min-height: 36px;
    align-items: center;
    gap: 8px;
    padding: 6px 11px 6px 9px;
    border: 1px solid rgba(79, 70, 229, 0.16);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.94);
    color: #475467;
    cursor: pointer;
    box-shadow: 0 8px 28px rgba(15, 23, 42, 0.04);
    backdrop-filter: blur(8px);
    transition:
      border-color 0.16s ease,
      box-shadow 0.16s ease,
      background 0.16s ease;

    &:hover {
      border-color: rgba(79, 70, 229, 0.28);
      box-shadow: 0 12px 34px rgba(15, 23, 42, 0.07);
    }

    time {
      color: #98a2b3;
      font-size: 12px;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
  }

  .live-process-bar__dot {
    display: inline-flex;
    width: 9px;
    height: 9px;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    background: #6366f1;
    box-shadow: 0 0 0 6px rgba(99, 102, 241, 0.1);
    animation: process-pulse 1.35s ease-in-out infinite;

    i {
      color: #fff;
      font-size: 7px;
      font-style: normal;
      line-height: 1;
    }
  }

  .is-done .live-process-bar__dot {
    width: 14px;
    height: 14px;
    background: #667085;
    box-shadow: none;
    animation: none;
  }

  .is-error .live-process-bar__dot {
    background: #f04438;
    box-shadow: 0 0 0 6px rgba(240, 68, 56, 0.1);
    animation: none;
  }

  .live-process-bar__title {
    color: #4f46e5;
    font-size: 13px;
    font-weight: 760;
    white-space: nowrap;
  }

  .is-done .live-process-bar__title {
    color: #475467;
  }

  .live-process-bar__detail {
    min-width: 0;
    max-width: min(560px, 52vw);
    overflow: hidden;
    color: #667085;
    font-size: 13px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .live-process-bar__toggle {
    color: #4f46e5;
    font-size: 13px;
    font-weight: 720;
    white-space: nowrap;
  }

  .live-process-stream {
    position: relative;
    max-height: 300px;
    margin-top: 10px;
    overflow: auto;
    padding: 14px 16px 8px;
    border: 1px solid rgba(15, 23, 42, 0.06);
    border-radius: 18px;
    background:
      radial-gradient(circle at 18% 0%, rgba(99, 102, 241, 0.065), transparent 34%),
      linear-gradient(180deg, rgba(248, 250, 255, 0.86), rgba(255, 255, 255, 0.96));
    box-shadow: 0 18px 48px rgba(15, 23, 42, 0.045);
    animation: process-stream-enter 0.18s ease both;
    scrollbar-width: thin;
  }

  .live-process-empty {
    display: flex;
    align-items: center;
    gap: 9px;
    min-height: 42px;
    color: #667085;

    span {
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: #6366f1;
      animation: process-pulse 1.35s ease-in-out infinite;
    }

    p {
      margin: 0;
      font-size: 13px;
    }
  }

  .live-process-hint {
    margin: 3px 0 6px 27px;
    color: #98a2b3;
    font-size: 12px;
  }

  @keyframes process-stream-enter {
    from {
      opacity: 0;
      filter: blur(6px);
      transform: translateY(8px);
    }

    to {
      opacity: 1;
      filter: blur(0);
      transform: translateY(0);
    }
  }

  @keyframes process-pulse {
    0%, 100% {
      opacity: 0.7;
      transform: scale(0.94);
    }

    50% {
      opacity: 1;
      transform: scale(1);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .live-process-bar__dot,
    .live-process-stream,
    .live-process-empty span {
      animation: none !important;
      filter: none;
    }
  }

  @media (max-width: 900px) {
    .live-process-bar__detail {
      max-width: 42vw;
    }

    .live-process-stream {
      max-height: 260px;
    }
  }
</style>
