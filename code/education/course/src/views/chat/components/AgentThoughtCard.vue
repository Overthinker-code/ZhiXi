<script setup lang="ts">
  import { computed, nextTick, ref, watch } from 'vue';

  const props = defineProps<{
    thoughts: string[];
    streaming?: boolean;
    /** 收起时仅显示「流光胶囊」，悬停展开完整终端 */
    collapsed?: boolean;
  }>();

  type Parsed = { id: number; tag: string; detail: string };

  const parsed = computed<Parsed[]>(() =>
    (props.thoughts || []).map((raw, idx) => {
      const m = String(raw).match(/^【([^】]+)】([\s\S]*)$/);
      if (m) {
        return {
          id: idx,
          tag: m[1].trim(),
          detail: (m[2] || '').trim() || '进行中…',
        };
      }
      return { id: idx, tag: '协作', detail: String(raw).trim() };
    })
  );

  const nodes = [
    { key: 'supervisor', label: '主管', sub: '问题拆解' },
    { key: 'tutor', label: '知识讲师', sub: '资料整合' },
    { key: 'final', label: '汇总', sub: '生成答复' },
  ] as const;

  function tagBucket(tag: string): 'supervisor' | 'tutor' | 'final' {
    if (tag.includes('汇总') || tag.includes('合成')) return 'final';
    if (
      tag.includes('主管') ||
      tag.includes('拆解') ||
      tag.includes('流水线') ||
      tag.includes('策略')
    )
      return 'supervisor';
    return 'tutor';
  }

  const activeBucket = computed(() => {
    if (!parsed.value.length) return props.streaming ? 'supervisor' : null;
    const last = parsed.value[parsed.value.length - 1];
    return tagBucket(last.tag);
  });

  function nodeActive(key: (typeof nodes)[number]['key']) {
    const b = activeBucket.value;
    if (!b) return false;
    if (!props.streaming && parsed.value.length) {
      const last = parsed.value[parsed.value.length - 1];
      const lb = tagBucket(last.tag);
      return lb === key;
    }
    return b === key;
  }

  function nodeRipple(key: (typeof nodes)[number]['key']) {
    return props.streaming && activeBucket.value === key;
  }

  function linePrefix(tag: string): string {
    if (tag.includes('知识检索') || tag.includes('工具')) return '[RAG RETRIEVAL]';
    if (tag.includes('主管') || tag.includes('拆解')) return '[SYSTEM INIT]';
    if (tag.includes('汇总')) return '[MERGE]';
    if (tag.includes('代码') || tag.includes('执行')) return '[TOOL EXEC]';
    return '[AGENT]';
  }

  const bootAt = ref(Date.now());
  watch(
    () => props.streaming,
    (v) => {
      if (v) bootAt.value = Date.now();
    },
    { immediate: true }
  );

  function ts(i: number): string {
    const d = new Date(bootAt.value + i * 420);
    return d.toTimeString().slice(0, 8);
  }

  const terminalTarget = computed(() => {
    const lines: string[] = [];
    lines.push(`${ts(0)}  [INIT] 回答流程已启动`);
    parsed.value.forEach((p, i) => {
      lines.push(`${ts(i)}  ${linePrefix(p.tag)} ${p.tag}`);
      const chunks = p.detail.split(/\n+/).filter(Boolean);
      chunks.forEach((c) => {
        lines.push(`           │ ${c}`);
      });
    });
    if (props.streaming && !parsed.value.length) {
      lines.push(`${ts(0)}  [WAIT] 正在连接分析节点…`);
    }
    return lines.join('\n');
  });

  const shownTerminal = ref('');
  const terminalEl = ref<HTMLElement | null>(null);
  const capsuleTerminalEl = ref<HTMLElement | null>(null);

  /** 内容增高前是否贴在终端底部；仅在为 true 时自动滚到底，避免协作日志刷新时强行拽走阅读位置 */
  function captureStickToBottom(): boolean {
    const el = terminalEl.value || capsuleTerminalEl.value;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 48;
  }

  watch(
    () => [terminalTarget.value, props.streaming, props.collapsed] as const,
    () => {
      if (props.collapsed && !props.streaming) {
        shownTerminal.value = terminalTarget.value;
        return;
      }
      const stick = captureStickToBottom();
      shownTerminal.value = terminalTarget.value;
      nextTick(() => {
        const el = terminalEl.value || capsuleTerminalEl.value;
        if (stick && el) el.scrollTop = el.scrollHeight;
      });
    },
    { immediate: true }
  );

  const capsuleHover = ref(false);
</script>

<template>
  <div v-if="parsed.length || streaming" class="atc-root">
    <!-- 收起：流光胶囊 -->
    <div
      v-if="collapsed"
      class="atc-capsule"
      @mouseenter="capsuleHover = true"
      @mouseleave="capsuleHover = false"
    >
      <span class="atc-capsule-shimmer" aria-hidden="true" />
      <span class="atc-capsule-dot" />
      <span class="atc-capsule-text">
        {{ streaming ? '正在整合回答…' : `回答推理已完成 · ${parsed.length} 步` }}
      </span>
      <span class="atc-capsule-hint">
        {{ streaming ? '悬停查看当前进度' : '悬停查看分析过程' }}
      </span>
      <transition name="atc-pop">
        <div v-show="capsuleHover" class="atc-capsule-pop">
          <pre ref="capsuleTerminalEl" class="atc-terminal atc-terminal--pop">{{ shownTerminal }}\n</pre>
        </div>
      </transition>
    </div>

    <!-- 完整：全息条 + 终端 -->
    <div v-else class="atc-card">
      <div class="atc-glow" aria-hidden="true" />
      <div class="atc-inner">
        <div class="atc-head">
          <span class="atc-pulse-dot" />
          <span class="atc-title">多智能体分析过程</span>
          <span v-if="streaming" class="atc-live">处理中</span>
        </div>

        <div class="atc-neuron-row">
          <template v-for="(n, idx) in nodes" :key="n.key">
            <div
              class="atc-node"
              :class="{
                'atc-node--on': nodeActive(n.key),
                'atc-node--ripple': nodeRipple(n.key),
              }"
            >
              <div class="atc-node-ring" aria-hidden="true" />
              <div class="atc-node-ico">{{ idx === 0 ? '🧠' : idx === 1 ? '📡' : '✨' }}</div>
              <div class="atc-node-label">{{ n.label }}</div>
              <div class="atc-node-sub">{{ n.sub }}</div>
            </div>
            <div v-if="idx < nodes.length - 1" class="atc-node-link" aria-hidden="true">
              <span class="atc-node-chev">➜</span>
            </div>
          </template>
        </div>

        <div class="atc-terminal-wrap">
          <div class="atc-terminal-bar">
            <span class="dot r" /><span class="dot y" /><span class="dot g" />
            <span class="atc-terminal-title">ANALYSIS_LOG // 回答生成记录</span>
          </div>
          <pre ref="terminalEl" class="atc-terminal">{{ shownTerminal }}<span v-if="streaming" class="atc-caret">▍</span></pre>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
  .atc-root {
    margin: 0 0 12px 4px;
  }

  .atc-card {
    position: relative;
    border-radius: 16px;
    padding: 1px;
    background: var(--zy-gradient-ocean, linear-gradient(135deg, #0ea5e9, #2563eb));
    box-shadow:
      0 0 0 1px rgba(255, 255, 255, 0.35) inset,
      0 12px 40px rgba(15, 23, 42, 0.18);
    overflow: hidden;
  }

  .atc-glow {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(
      120% 80% at 10% 0%,
      rgba(255, 255, 255, 0.22),
      transparent 55%
    );
  }

  .atc-inner {
    position: relative;
    border-radius: 15px;
    background: linear-gradient(165deg, rgba(15, 23, 42, 0.97) 0%, #0f172a 55%, #020617 100%);
  }

  .atc-head {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 14px 8px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.15);
  }

  .atc-pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #818cf8;
    box-shadow: 0 0 12px rgba(129, 140, 248, 0.9);
    animation: atc-dot-pulse 1.2s ease-in-out infinite;
  }

  .atc-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #e2e8f0;
    text-transform: uppercase;
  }

  .atc-live {
    margin-left: auto;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.12em;
    padding: 3px 10px;
    border-radius: 999px;
    color: #fff;
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    animation: atc-live-blink 1s ease-in-out infinite;
  }

  .atc-neuron-row {
    display: flex;
    align-items: stretch;
    justify-content: space-between;
    gap: 8px;
    padding: 10px 12px 12px;
  }

  .atc-node {
    flex: 1;
    min-width: 0;
    text-align: center;
    padding: 10px 6px 8px;
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: rgba(30, 41, 59, 0.65);
    transition:
      border-color 0.25s,
      box-shadow 0.25s;
    position: relative;
  }

  .atc-node--on {
    border-color: rgba(129, 140, 248, 0.65);
    box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.25);
  }

  .atc-node--ripple .atc-node-ring {
    animation: atc-ripple 1.8s ease-out infinite;
  }

  .atc-node-ring {
    position: absolute;
    inset: -2px;
    border-radius: 14px;
    pointer-events: none;
    box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.45);
    opacity: 0;
  }

  .atc-node-ico {
    font-size: 18px;
    line-height: 1;
    filter: drop-shadow(0 0 6px rgba(129, 140, 248, 0.5));
  }

  .atc-node-label {
    margin-top: 6px;
    font-size: 12px;
    font-weight: 700;
    color: #f8fafc;
  }

  .atc-node-sub {
    margin-top: 2px;
    font-size: 10px;
    color: #94a3b8;
  }

  .atc-node-link {
    display: flex;
    align-items: center;
    color: #64748b;
    font-size: 13px;
    padding: 0 2px;
  }

  .atc-node-chev {
    opacity: 0.85;
  }

  .atc-terminal-wrap {
    margin: 0 10px 10px;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(148, 163, 184, 0.2);
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.06) inset;
  }

  .atc-terminal-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: rgba(15, 23, 42, 0.95);
    border-bottom: 1px solid rgba(51, 65, 85, 0.9);
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }
    .r {
      background: #f87171;
    }
    .y {
      background: #fbbf24;
    }
    .g {
      background: #4ade80;
    }
  }

  .atc-terminal-title {
    margin-left: 8px;
    font-size: 11px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    color: #64748b;
    letter-spacing: 0.06em;
  }

  .atc-terminal {
    margin: 0;
    min-height: 120px;
    max-height: 220px;
    overflow: auto;
    padding: 10px 12px 12px;
    font-size: 12px;
    line-height: 1.5;
    color: #a5f3fc;
    background: #020617;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .atc-terminal--pop {
    max-height: 200px;
    min-height: 80px;
  }

  .atc-caret {
    display: inline-block;
    margin-left: 2px;
    color: #c4b5fd;
    animation: atc-caret-blink 0.9s step-end infinite;
  }

  /* —— 流光胶囊 —— */
  .atc-capsule {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px 10px 12px;
    border-radius: 999px;
    cursor: default;
    overflow: visible;
    border: 1px solid rgba(99, 102, 241, 0.35);
    background: rgba(15, 23, 42, 0.55);
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.2);
  }

  .atc-capsule-shimmer {
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: var(--zy-gradient-brand, linear-gradient(135deg, #6366f1, #8b5cf6));
    opacity: 0.22;
    background-size: 200% 200%;
    animation: atc-shimmer-move 3.5s linear infinite;
    pointer-events: none;
  }

  .atc-capsule-dot {
    position: relative;
    z-index: 1;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #a78bfa;
    box-shadow: 0 0 10px rgba(167, 139, 250, 0.9);
  }

  .atc-capsule-text,
  .atc-capsule-hint {
    position: relative;
    z-index: 1;
    font-size: 13px;
    font-weight: 600;
    color: #e2e8f0;
  }

  .atc-capsule-hint {
    font-size: 11px;
    font-weight: 500;
    color: #94a3b8;
    margin-left: auto;
  }

  .atc-capsule-pop {
    position: absolute;
    left: 0;
    top: calc(100% + 8px);
    z-index: 80;
    min-width: min(420px, 92vw);
    max-width: 96vw;
    border-radius: 14px;
    padding: 1px;
    background: var(--zy-gradient-ocean);
    box-shadow: 0 20px 50px rgba(2, 6, 23, 0.55);
  }

  .atc-capsule-pop .atc-terminal {
    border-radius: 13px;
    max-height: 280px;
  }

  .atc-pop-enter-active,
  .atc-pop-leave-active {
    transition:
      opacity 0.2s ease,
      transform 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  }
  .atc-pop-enter-from,
  .atc-pop-leave-to {
    opacity: 0;
    transform: translateY(6px) scale(0.94);
  }

  @keyframes atc-dot-pulse {
    0%,
    100% {
      transform: scale(1);
      opacity: 1;
    }
    50% {
      transform: scale(1.2);
      opacity: 0.65;
    }
  }

  @keyframes atc-live-blink {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.55;
    }
  }

  @keyframes atc-ripple {
    0% {
      opacity: 0.9;
      box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.55);
    }
    70% {
      opacity: 0;
      box-shadow: 0 0 0 14px rgba(139, 92, 246, 0);
    }
    100% {
      opacity: 0;
      box-shadow: 0 0 0 0 rgba(139, 92, 246, 0);
    }
  }

  @keyframes atc-caret-blink {
    50% {
      opacity: 0;
    }
  }

  @keyframes atc-shimmer-move {
    0% {
      background-position: 0% 50%;
    }
    100% {
      background-position: 100% 50%;
    }
  }
</style>
