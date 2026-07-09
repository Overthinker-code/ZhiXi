<script setup lang="ts">
  import { computed, onUnmounted, ref, watch } from 'vue';
  import { renderMarkdown } from '@/utils/markdown';
  import ArtifactCards from './ArtifactCards.vue';
  import CitationList from './CitationList.vue';
  import LiveProcessPanel from './LiveProcessPanel.vue';

  const props = defineProps<{
    message: Record<string, any>;
    isLast?: boolean;
  }>();

  const emit = defineEmits<{
    (e: 'send-suggestion', text: string): void;
  }>();

  const processOpen = ref(false);
  const processCollapsed = ref(false);
  const liveNow = ref(Date.now());
  let liveTimer: ReturnType<typeof window.setInterval> | null = null;
  const rendered = computed(() => renderMarkdown(String(props.message.content || ''), {
    streaming: Boolean(props.message.loading),
  }));
  const INTERNAL_REASONING_RE =
    /^(intent_classifier|course_context|deep_research|tutor|homework_review|resource_generation|course_retriever|数据库系统原理|第\s*\d+\s*章.*|.*ER\s*模型.*)$/i;
  const INTERNAL_REASONING_TEXT_RE =
    /(首条系统消息|已根据当前问题检索知识库|上下文注入协作线程|协作线程|系统消息|intent_classifier|course_context|deep_research)/i;
  const reasoning = computed(() =>
    String(props.message.reasoning_content || '')
      .split(/\r?\n/)
      .map((line) =>
        line
          .replace(/^【[^】]+】\s*/, '')
          .replace(/\s*\([^)]*(?:系统消息|agent|context|classifier)[^)]*\)\s*/gi, '')
          .trim()
      )
      .filter((line) => line && !INTERNAL_REASONING_RE.test(line) && !INTERNAL_REASONING_TEXT_RE.test(line))
      .join('\n')
    .trim()
  );
  const suggestions = computed(() =>
    (Array.isArray(props.message.suggestions) ? props.message.suggestions : [])
      .map((item: unknown) => String(item || '').trim())
      .filter(Boolean)
      .slice(0, 3)
  );
  type ProcessStatus = 'pending' | 'running' | 'done' | 'skipped' | 'error';
  type ProcessStage = 'understand' | 'route' | 'retrieve' | 'compose' | 'verify';
  const processEvents = computed<Record<string, any>[]>(() =>
    Array.isArray(props.message.processEvents) ? props.message.processEvents : []
  );
  const processExpanded = computed(() =>
    Boolean((props.message.loading && !processCollapsed.value) || processOpen.value)
  );
  const stageDefs: Array<{ id: ProcessStage; title: string; fallback: string }> = [
    { id: 'understand', title: '理解问题', fallback: '等待接收问题' },
    { id: 'route', title: '选择工具', fallback: '等待选择能力' },
    { id: 'retrieve', title: '检索依据', fallback: '按需检索资料' },
    { id: 'compose', title: '组织回答', fallback: '等待模型生成' },
    { id: 'verify', title: '校验输出', fallback: '等待检查结果' },
  ];
  const statusWeight: Record<ProcessStatus, number> = {
    pending: 0,
    skipped: 1,
    running: 2,
    done: 3,
    error: 4,
  };
  const formatTime = (value: unknown) => {
    if (!value) return '';
    const date = new Date(String(value));
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleTimeString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };
  const eventsForStage = (stage: ProcessStage) =>
    processEvents.value.filter((event) => String(event.stage || '') === stage);
  const latestEventForStage = (stage: ProcessStage) => {
    const list = eventsForStage(stage);
    return list[list.length - 1] || null;
  };
  const statusForStage = (stage: ProcessStage): ProcessStatus => {
    const list = eventsForStage(stage);
    if (!list.length) return 'pending';
    return list
      .map((event) => String(event.status || 'running') as ProcessStatus)
      .filter((status) => status in statusWeight)
      .sort((a, b) => statusWeight[b] - statusWeight[a])[0] || 'running';
  };
  const processSteps = computed(() => {
    const firstPending = stageDefs.findIndex((stage) => statusForStage(stage.id) === 'pending');
    const hasExplicitRunning = processEvents.value.some(
      (event) => String(event.status || 'running') === 'running'
    );
    return stageDefs.map((stage, index) => {
      const latest = latestEventForStage(stage.id);
      let status = statusForStage(stage.id);
      if (status === 'pending' && props.message.loading && !hasExplicitRunning && index === Math.max(firstPending, 0)) {
        status = 'running';
      }
      return {
        id: stage.id,
        title: String(latest?.title || stage.title),
        detail: String(latest?.detail || latest?.log || stage.fallback),
        status,
        items: Array.isArray(latest?.items) ? latest.items : [],
      };
    });
  });
  const activeStepIndex = computed(() => {
    const runningIndex = processSteps.value.findIndex((item) => item.status === 'running');
    if (runningIndex >= 0) return runningIndex + 1;
    const doneCount = processSteps.value.filter((item) => item.status === 'done' || item.status === 'skipped').length;
    return Math.max(1, Math.min(processSteps.value.length, doneCount || 1));
  });
  const activeProcessStep = computed(() =>
    [...processSteps.value].reverse().find((item) => item.status === 'running') ||
    [...processSteps.value].reverse().find((item) => item.status === 'done') ||
    processSteps.value[0]
  );
  const processLogs = computed(() => {
    const eventLogs = processEvents.value
      .map((event) => ({
        id: `${event.stage || 'stage'}-${event.status || 'running'}-${event.timestamp || ''}-${event.log || event.detail || ''}`,
        time: formatTime(event.timestamp),
        status: String(event.status || 'running') as ProcessStatus,
        title: String(event.title || '处理事件'),
        text: String(event.log || event.detail || '').trim(),
        items: Array.isArray(event.items) ? event.items.slice(0, 3) : [],
      }))
      .filter((item) => item.text);
    const lines = reasoning.value
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line, index) => ({
        id: `reasoning-${index}-${line}`,
        time: '',
        status: 'running' as ProcessStatus,
        title: '模型摘要',
        text: line,
        items: [],
      }));
    return [...eventLogs, ...lines].slice(-9).reverse();
  });
  const firstProcessAt = computed(() => {
    const first = processEvents.value.find((event) => event.timestamp);
    const time = first ? new Date(String(first.timestamp)).getTime() : 0;
    return Number.isFinite(time) ? time : 0;
  });
  const liveElapsedLabel = computed(() => {
    if (!props.message.loading || !firstProcessAt.value) return '';
    const seconds = Math.max(0, Math.floor((liveNow.value - firstProcessAt.value) / 1000));
    return `${seconds}s`;
  });
  const waitingForFirstToken = computed(() =>
    Boolean(props.message.loading && processEvents.value.some((event) =>
      String(event.stage || '') === 'compose' && String(event.status || '') === 'running'
    ) && !String(props.message.content || '').trim())
  );
  const liveWaitingText = computed(() => {
    if (!waitingForFirstToken.value) return '';
    return `等待首个输出 ${liveElapsedLabel.value || '0s'}`;
  });
  const processSummary = computed(() => {
    if (props.message.loading) return `正在处理步骤 ${activeStepIndex.value}`;
    if (processEvents.value.length || props.message.content) return '已完成处理';
    return '查看处理过程';
  });
  const processSubtitle = computed(() =>
    props.message.loading
      ? activeProcessStep.value?.title || '实时处理'
      : activeProcessStep.value?.detail || '处理完成'
  );
  function toggleProcess() {
    if (processExpanded.value) {
      processCollapsed.value = true;
      processOpen.value = false;
      return;
    }
    processCollapsed.value = false;
    processOpen.value = true;
  }
  watch(
    () => Boolean(props.message.loading),
    (loading) => {
      if (loading && !liveTimer) {
        liveNow.value = Date.now();
        liveTimer = window.setInterval(() => {
          liveNow.value = Date.now();
        }, 1000);
      } else if (!loading && liveTimer) {
        window.clearInterval(liveTimer);
        liveTimer = null;
      }
    },
    { immediate: true }
  );
  onUnmounted(() => {
    if (liveTimer) window.clearInterval(liveTimer);
  });
</script>

<template>
  <article class="assistant-message">
    <LiveProcessPanel :state="message.liveProcess" :loading="message.loading" />

    <div v-if="message.content" class="assistant-message__body markdown-body" v-html="rendered" />
    <div v-else-if="message.loading" class="assistant-message__loading">
      <span />
      <span />
      <span />
    </div>

    <CitationList :citations="message.citations || []" compact />
    <ArtifactCards
      :artifacts="message.artifacts || []"
      :package-id="message.resourcePackage?.package_id"
    />

    <section v-if="!message.loading && suggestions.length" class="follow-up-capsules">
      <button
        v-for="item in suggestions"
        :key="item"
        type="button"
        @click="emit('send-suggestion', item)"
      >
        {{ item }}
      </button>
    </section>

    <footer v-if="!message.loading && message.content" class="assistant-message__actions">
      <button type="button">生成练习</button>
      <button type="button">加入笔记</button>
      <button type="button">同步图谱</button>
    </footer>
  </article>
</template>

<style scoped lang="scss">
  .assistant-message {
    width: min(820px, 100%);
    margin: 0 auto 28px;
    color: #344054;
  }

  .assistant-message__body {
    color: #344054;
    font-size: 15px;
    line-height: 1.75;

    :deep(h1),
    :deep(h2),
    :deep(h3) {
      margin: 18px 0 8px;
      color: #101828;
      line-height: 1.35;
    }

    :deep(p) {
      margin: 8px 0;
    }

    :deep(table) {
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0;
      overflow: hidden;
      border-radius: 12px;
    }

    :deep(th),
    :deep(td) {
      padding: 9px 10px;
      border: 1px solid rgba(15, 23, 42, 0.08);
    }

    :deep(pre) {
      overflow: auto;
      border-radius: 14px;
    }

    :deep(code:not(pre code)) {
      padding: 2px 6px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 6px;
      background: #f6f8fb;
      color: #344054;
      font-size: 0.92em;
    }

    :deep(.code-block),
    :deep(.markdown-it-code-block) {
      margin: 14px 0;
      overflow: hidden;
      border: 1px solid rgba(15, 23, 42, 0.1);
      border-radius: 14px;
      background: #ffffff !important;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
    }

    :deep(pre.code-block.hljs) {
      position: relative;
      padding: 0;
      background: #ffffff !important;
      color: #344054 !important;
      text-shadow: none !important;
      white-space: normal;
    }

    :deep(pre.code-block.hljs::before) {
      display: flex;
      min-height: 34px;
      align-items: center;
      padding: 0 44px 0 12px;
      border-bottom: 1px solid rgba(15, 23, 42, 0.08);
      background: #f8fafc;
      color: #667085;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      content: attr(data-lang);
    }

    :deep(.code-block > code) {
      display: block;
      padding: 14px 16px;
      overflow-x: auto;
      background: transparent !important;
      color: #344054 !important;
      font-size: 13px;
      line-height: 1.65;
      white-space: pre;
    }

    :deep(.code-header) {
      display: flex;
      min-height: 34px;
      align-items: center;
      justify-content: space-between;
      padding: 0 12px;
      border-bottom: 1px solid rgba(15, 23, 42, 0.08);
      background: #f8fafc;
      color: #667085;
      font-size: 12px;
    }

    :deep(.code-lang) {
      color: #667085;
      font-weight: 700;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }

    :deep(.code-actions) {
      display: inline-flex;
      gap: 4px;
    }

    :deep(.code-action-btn) {
      display: inline-flex;
      width: 24px;
      height: 24px;
      align-items: center;
      justify-content: center;
      border: 0;
      border-radius: 7px;
      background: transparent;
      cursor: pointer;

      &:hover {
        background: #eef2ff;
      }

      img {
        width: 14px;
        height: 14px;
        opacity: 0.72;
      }
    }

    :deep(.code-action-btn--floating) {
      position: absolute;
      top: 5px;
      right: 8px;
      z-index: 1;
    }

    :deep(pre:not(.code-block)),
    :deep(pre.hljs:not(.code-block)) {
      margin: 14px 0;
      padding: 14px 16px;
      border: 1px solid rgba(15, 23, 42, 0.1);
      border-radius: 14px;
      background: #ffffff !important;
      background-color: #ffffff !important;
      color: #344054 !important;
      font-size: 13px;
      line-height: 1.65;
      text-shadow: none !important;
    }

    :deep(pre code),
    :deep(pre.hljs code),
    :deep(.hljs),
    :deep(.hljs-subst) {
      background: transparent !important;
      background-color: transparent !important;
      color: #344054 !important;
      text-shadow: none !important;
    }

    :deep(.hljs-keyword),
    :deep(.hljs-selector-tag),
    :deep(.hljs-title.function_),
    :deep(.hljs-built_in),
    :deep(.hljs-type),
    :deep(.hljs-name),
    :deep(.hljs-operator) {
      color: #4f46e5 !important;
    }

    :deep(.hljs-string),
    :deep(.hljs-attr),
    :deep(.hljs-symbol),
    :deep(.hljs-regexp),
    :deep(.hljs-link) {
      color: #087443 !important;
    }

    :deep(.hljs-number),
    :deep(.hljs-literal),
    :deep(.hljs-variable),
    :deep(.hljs-template-variable) {
      color: #b54708 !important;
    }

    :deep(.hljs-comment),
    :deep(.hljs-quote) {
      color: #98a2b3 !important;
    }

    :deep(.hljs-title),
    :deep(.hljs-section),
    :deep(.hljs-selector-id),
    :deep(.hljs-selector-class) {
      color: #175cd3 !important;
    }

    :deep(.hljs-meta),
    :deep(.hljs-doctag),
    :deep(.hljs-addition),
    :deep(.hljs-deletion) {
      color: #475467 !important;
      background: transparent !important;
      background-color: transparent !important;
    }
  }

  .assistant-message__loading {
    display: inline-flex;
    gap: 5px;
    padding: 12px 0;

    span {
      width: 7px;
      height: 7px;
      border-radius: 999px;
      background: #6366f1;
      animation: loading-dot 1s ease-in-out infinite;

      &:nth-child(2) {
        animation-delay: 0.14s;
      }

      &:nth-child(3) {
        animation-delay: 0.28s;
      }
    }
  }

  .process-toggle {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin: 8px 0 6px;
    max-width: 100%;
    padding: 6px 10px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 999px;
    color: #4f46e5;
    background: #fff;
    font-size: 12px;
    font-weight: 760;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
    transition:
      border-color 0.16s ease,
      box-shadow 0.16s ease,
      transform 0.16s ease;

    &:hover {
      border-color: rgba(99, 102, 241, 0.24);
      box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
      transform: translateY(-1px);
    }
  }

  .process-toggle__main {
    color: #4f46e5;
  }

  .process-toggle__sub {
    max-width: 220px;
    overflow: hidden;
    color: #667085;
    font-weight: 650;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .process-toggle__dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #6366f1;
    box-shadow: 0 0 0 6px rgba(99, 102, 241, 0.1);
    animation: reasoning-pulse 1.35s ease-in-out infinite;
  }

  .streaming-dots {
    display: inline-flex;
    gap: 3px;

    i {
      width: 5px;
      height: 5px;
      border-radius: 999px;
      background: #a4a7ff;
      animation: reasoning-dot 1s ease-in-out infinite;

      &:nth-child(2) {
        animation-delay: 0.14s;
      }

      &:nth-child(3) {
        animation-delay: 0.28s;
      }
    }
  }

  .process-panel {
    margin: 0 0 14px;
    padding: 12px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 20px;
    background:
      radial-gradient(circle at 0 0, rgba(99, 102, 241, 0.08), transparent 34%),
      #fbfcff;
    box-shadow: 0 14px 36px rgba(15, 23, 42, 0.05);
  }

  .process-panel__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
    padding: 2px 2px 0;

    strong {
      display: block;
      color: #101828;
      font-size: 13px;
      line-height: 1.2;
    }

    span {
      display: block;
      margin-top: 3px;
      color: #98a2b3;
      font-size: 12px;
    }

    b {
      max-width: 210px;
      padding: 4px 9px;
      overflow: hidden;
      border: 1px solid rgba(99, 102, 241, 0.13);
      border-radius: 999px;
      background: #fff;
      color: #4f46e5;
      font-size: 12px;
      font-weight: 760;
      text-overflow: ellipsis;
      white-space: nowrap;

      small {
        color: #667085;
        font-size: 11px;
        font-weight: 720;
      }
    }
  }

  .process-monitor {
    display: grid;
    grid-template-columns: minmax(210px, 0.44fr) minmax(0, 1fr);
    gap: 12px;
  }

  .process-steps {
    display: grid;
    align-content: start;
    gap: 10px;
    padding: 10px 10px 10px 8px;
    border: 1px solid rgba(15, 23, 42, 0.06);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.72);
  }

  .process-step {
    position: relative;
    display: grid;
    grid-template-columns: 16px minmax(0, 1fr);
    gap: 10px;
    color: #667085;

    &:not(:last-child)::after {
      content: '';
      position: absolute;
      top: 18px;
      left: 7px;
      width: 1px;
      height: calc(100% + 4px);
      background: rgba(99, 102, 241, 0.16);
    }

    strong {
      display: block;
      color: #344054;
      font-size: 13px;
      line-height: 1.25;
    }

    span:not(.process-step__marker) {
      display: block;
      margin-top: 3px;
      font-size: 12px;
      line-height: 1.45;
    }

    &.is-pending {
      opacity: 0.62;
    }

    &.is-running {
      color: #475467;

      .process-step__marker {
        background: #6366f1;
        box-shadow: 0 0 0 6px rgba(99, 102, 241, 0.12);
        animation: reasoning-pulse 1.2s ease-in-out infinite;
      }
    }

    &.is-done {
      .process-step__marker {
        background: #4f46e5;

        &::after {
          content: '';
          position: absolute;
          top: 3px;
          left: 5px;
          width: 4px;
          height: 7px;
          border: solid #fff;
          border-width: 0 1.5px 1.5px 0;
          transform: rotate(45deg);
        }
      }
    }

    &.is-skipped {
      opacity: 0.72;
    }

    &.is-error {
      .process-step__marker {
        background: #f04438;
      }
    }
  }

  .process-step__items {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 6px;

    em {
      max-width: 100%;
      padding: 2px 6px;
      overflow: hidden;
      border-radius: 999px;
      background: #eef2ff;
      color: #475467;
      font-size: 11px;
      font-style: normal;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .process-step__marker {
    position: relative;
    z-index: 1;
    width: 14px;
    height: 14px;
    margin-top: 2px;
    border-radius: 999px;
    background: #d0d5dd;
    box-shadow: inset 0 0 0 3px #fff;
  }

  .process-stream {
    min-width: 0;
    padding: 10px;
    border: 1px solid rgba(15, 23, 42, 0.06);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.74);
    color: #475467;
    font-size: 13px;
    line-height: 1.65;
  }

  .process-stream__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .process-stream__label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #4f46e5;
    font-weight: 760;

    &::after {
      content: '';
      width: 6px;
      height: 6px;
      border-radius: 999px;
      background: #a4a7ff;
      box-shadow: 10px 0 0 #b9bbff, 20px 0 0 #ced0ff;
      animation: reasoning-dot 1s ease-in-out infinite;
    }
  }

  .process-stream__live {
    padding: 2px 6px;
    border-radius: 999px;
    background: #eef2ff;
    color: #4f46e5;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.05em;
  }

  .process-log-list {
    display: grid;
    gap: 7px;
    max-height: 230px;
    overflow: auto;
    padding-right: 2px;
  }

  .process-log {
    display: grid;
    grid-template-columns: 56px minmax(0, 1fr);
    gap: 9px;
    padding: 8px 9px;
    border-radius: 12px;
    background: #f8faff;
    color: #667085;

    time {
      color: #98a2b3;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 11px;
      line-height: 1.5;
    }

    strong {
      display: block;
      color: #344054;
      font-size: 12px;
      line-height: 1.25;
    }

    p {
      margin: 3px 0 0;
      color: #667085;
      font-size: 12px;
      line-height: 1.5;
    }

    span {
      display: inline-block;
      max-width: 100%;
      margin: 6px 5px 0 0;
      padding: 2px 6px;
      overflow: hidden;
      border-radius: 999px;
      background: #fff;
      color: #667085;
      font-size: 11px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    &.is-running {
      background: #f3f5ff;
      box-shadow: inset 2px 0 0 #6366f1;
    }

    &.is-live-waiting {
      background:
        linear-gradient(90deg, rgba(99, 102, 241, 0.08), transparent 48%),
        #f3f5ff;

      p::after {
        content: '';
        display: inline-block;
        width: 4px;
        height: 4px;
        margin-left: 6px;
        border-radius: 999px;
        background: #6366f1;
        box-shadow: 8px 0 0 #a4a7ff, 16px 0 0 #ced0ff;
        vertical-align: middle;
        animation: reasoning-dot 1s ease-in-out infinite;
      }
    }

    &.is-done {
      background: #f8fafc;
    }

    &.is-error {
      background: #fff7f7;
      box-shadow: inset 2px 0 0 #f04438;
    }
  }

  @media (max-width: 900px) {
    .process-monitor {
      grid-template-columns: 1fr;
    }

    .process-log-list {
      max-height: 180px;
    }
  }

  .follow-up-capsules {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;

    button {
      max-width: 100%;
      min-height: 34px;
      padding: 0 13px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 999px;
      color: #344054;
      background: #f8fafc;
      cursor: pointer;
      font-size: 13px;
      line-height: 1.3;
      transition:
        border-color 0.16s ease,
        color 0.16s ease,
        background 0.16s ease,
        transform 0.16s ease;

      &:hover {
        border-color: rgba(99, 102, 241, 0.28);
        color: #4f46e5;
        background: #eef2ff;
        transform: translateY(-1px);
      }
    }
  }

  .assistant-message__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;

    button {
      height: 32px;
      padding: 0 12px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 999px;
      color: #475467;
      background: #fff;
      cursor: pointer;

      &:hover {
        color: #4f46e5;
        border-color: rgba(99, 102, 241, 0.35);
      }
    }
  }

  @keyframes loading-dot {
    0%, 100% {
      opacity: 0.35;
      transform: translateY(0);
    }
    50% {
      opacity: 1;
      transform: translateY(-3px);
    }
  }

  @keyframes reasoning-dot {
    0%, 100% {
      opacity: 0.35;
    }
    50% {
      opacity: 1;
    }
  }

  @keyframes reasoning-pulse {
    0%,
    100% {
      transform: scale(0.92);
      opacity: 0.72;
    }
    50% {
      transform: scale(1);
      opacity: 1;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .assistant-message__loading span,
    .streaming-dots i,
    .process-toggle__dot,
    .process-step__marker,
    .process-stream__label::after,
    .process-log.is-live-waiting p::after {
      animation: none;
    }
  }
</style>
