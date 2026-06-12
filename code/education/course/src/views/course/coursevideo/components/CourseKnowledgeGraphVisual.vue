<template>
  <div class="kg-outer">
    <svg
      class="kg-svg"
      viewBox="0 0 720 300"
      preserveAspectRatio="xMidYMid meet"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="数据库系统原理课程知识图谱"
    >
      <defs>
        <linearGradient id="kg-center-fill" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#6058ef" />
          <stop offset="100%" stop-color="#8757df" />
        </linearGradient>
        <radialGradient id="kg-halo" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#7768ef" stop-opacity=".14" />
          <stop offset="100%" stop-color="#7768ef" stop-opacity="0" />
        </radialGradient>
        <filter
          id="kg-center-shadow"
          x="-35%"
          y="-60%"
          width="170%"
          height="220%"
        >
          <feDropShadow
            dx="0"
            dy="8"
            stdDeviation="9"
            flood-color="#6d5bdb"
            flood-opacity=".28"
          />
        </filter>
        <filter
          id="kg-node-shadow"
          x="-25%"
          y="-60%"
          width="150%"
          height="220%"
        >
          <feDropShadow
            dx="0"
            dy="3"
            stdDeviation="3"
            flood-color="#596780"
            flood-opacity=".12"
          />
        </filter>
      </defs>

      <ellipse cx="360" cy="148" rx="112" ry="82" fill="url(#kg-halo)" />

      <g class="kg-edges" fill="none" stroke-linecap="round">
        <path
          v-for="edge in edges"
          :key="edge.key"
          v-show="step >= edge.step"
          :d="edge.path"
          class="edge-line"
          :class="{ 'on': step >= edge.step, 'edge-line--leaf': edge.leaf }"
        />
      </g>

      <g
        v-show="step >= 1"
        class="node-pop node-hotspot center-node"
        :class="{ on: step >= 1 }"
        role="button"
        tabindex="0"
        @pointerdown.stop
        @click.stop="emitNodePrompt('数据库系统原理', $event)"
        @keydown.enter.stop="emitNodePrompt('数据库系统原理', $event)"
      >
        <rect
          x="286"
          y="125"
          width="148"
          height="46"
          rx="11"
          fill="url(#kg-center-fill)"
          filter="url(#kg-center-shadow)"
        />
        <circle
          cx="303"
          cy="148"
          r="5"
          fill="none"
          stroke="rgba(255,255,255,.75)"
        />
        <circle cx="303" cy="148" r="1.8" fill="#fff" />
        <text x="365" y="153" text-anchor="middle">数据库系统原理</text>
      </g>

      <g
        v-for="node in nodes"
        :key="node.key"
        v-show="step >= node.step"
        class="node-pop node-hotspot"
        :class="[
          { on: step >= node.step },
          node.kind === 'topic' ? 'topic-node' : 'leaf-node',
        ]"
        role="button"
        tabindex="0"
        @pointerdown.stop
        @click.stop="emitNodePrompt(node.text, $event)"
        @keydown.enter.stop="emitNodePrompt(node.text, $event)"
      >
        <rect
          :x="node.x"
          :y="node.y"
          :width="node.width"
          :height="node.height"
          :rx="node.kind === 'topic' ? 8 : 6"
          :fill="node.fill"
          :stroke="node.stroke"
          :filter="node.kind === 'topic' ? 'url(#kg-node-shadow)' : undefined"
        />
        <circle
          v-if="node.kind === 'topic'"
          :cx="node.x + 11"
          :cy="node.y + node.height / 2"
          r="2.8"
          :fill="node.accent"
        />
        <text
          :x="node.x + node.width / 2 + (node.kind === 'topic' ? 4 : 0)"
          :y="node.y + node.height / 2 + 3.5"
          text-anchor="middle"
          :fill="node.textColor"
        >
          {{ node.text }}
        </text>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
  import { ref, watch, onUnmounted } from 'vue';

  const props = defineProps<{ active: boolean }>();
  const emit = defineEmits<{
    complete: [];
    nodePrompt: [payload: { text: string; rect: DOMRect }];
  }>();

  const step = ref(0);
  let timer: ReturnType<typeof setInterval> | null = null;

  const topicStyle = {
    fill: '#edf3ff',
    stroke: '#b9cafa',
    accent: '#6c72e8',
    textColor: '#405078',
  };
  const leafStyle = {
    fill: '#fbfcff',
    stroke: '#dbe2f3',
    accent: '#9ca9c7',
    textColor: '#68748e',
  };

  const nodes = [
    {
      key: 'model',
      step: 2,
      kind: 'topic',
      text: '数据模型',
      x: 105,
      y: 38,
      width: 94,
      height: 30,
      ...topicStyle,
    },
    {
      key: 'relational',
      step: 2,
      kind: 'leaf',
      text: '关系模型',
      x: 12,
      y: 8,
      width: 72,
      height: 21,
      ...leafStyle,
    },
    {
      key: 'er',
      step: 2,
      kind: 'leaf',
      text: 'ER模型',
      x: 18,
      y: 42,
      width: 66,
      height: 21,
      ...leafStyle,
    },
    {
      key: 'algebra',
      step: 2,
      kind: 'leaf',
      text: '关系代数',
      x: 8,
      y: 76,
      width: 76,
      height: 21,
      ...leafStyle,
    },

    {
      key: 'sql',
      step: 3,
      kind: 'topic',
      text: 'SQL语言',
      x: 84,
      y: 126,
      width: 94,
      height: 30,
      ...topicStyle,
    },
    {
      key: 'select',
      step: 3,
      kind: 'leaf',
      text: '查询',
      x: 8,
      y: 108,
      width: 52,
      height: 21,
      ...leafStyle,
    },
    {
      key: 'update',
      step: 3,
      kind: 'leaf',
      text: '更新',
      x: 4,
      y: 137,
      width: 56,
      height: 21,
      ...leafStyle,
    },
    {
      key: 'view',
      step: 3,
      kind: 'leaf',
      text: '视图',
      x: 8,
      y: 166,
      width: 52,
      height: 21,
      ...leafStyle,
    },

    {
      key: 'concurrency',
      step: 4,
      kind: 'topic',
      text: '并发控制',
      x: 142,
      y: 220,
      width: 102,
      height: 30,
      ...topicStyle,
    },
    {
      key: 'lock',
      step: 4,
      kind: 'leaf',
      text: '锁机制',
      x: 34,
      y: 251,
      width: 64,
      height: 21,
      ...leafStyle,
    },
    {
      key: 'schedule',
      step: 4,
      kind: 'leaf',
      text: '并发调度',
      x: 108,
      y: 270,
      width: 72,
      height: 21,
      ...leafStyle,
    },
    {
      key: 'deadlock',
      step: 4,
      kind: 'leaf',
      text: '死锁处理',
      x: 190,
      y: 270,
      width: 72,
      height: 21,
      ...leafStyle,
    },

    {
      key: 'normalization',
      step: 5,
      kind: 'topic',
      text: '规范化',
      x: 476,
      y: 220,
      width: 102,
      height: 30,
      ...topicStyle,
    },
    {
      key: 'dependency',
      step: 5,
      kind: 'leaf',
      text: '函数依赖',
      x: 458,
      y: 270,
      width: 72,
      height: 21,
      ...leafStyle,
    },
    {
      key: 'normal-form',
      step: 5,
      kind: 'leaf',
      text: '范式',
      x: 540,
      y: 270,
      width: 58,
      height: 21,
      ...leafStyle,
    },
    {
      key: 'decomposition',
      step: 5,
      kind: 'leaf',
      text: '模式分解',
      x: 608,
      y: 251,
      width: 72,
      height: 21,
      ...leafStyle,
    },

    {
      key: 'transaction',
      step: 6,
      kind: 'topic',
      text: '事务处理',
      x: 542,
      y: 126,
      width: 96,
      height: 30,
      ...topicStyle,
    },
    {
      key: 'acid',
      step: 6,
      kind: 'leaf',
      text: 'ACID',
      x: 658,
      y: 108,
      width: 52,
      height: 21,
      ...leafStyle,
    },
    {
      key: 'log',
      step: 6,
      kind: 'leaf',
      text: '日志',
      x: 654,
      y: 137,
      width: 56,
      height: 21,
      ...leafStyle,
    },
    {
      key: 'recovery',
      step: 6,
      kind: 'leaf',
      text: '恢复',
      x: 658,
      y: 166,
      width: 52,
      height: 21,
      ...leafStyle,
    },

    {
      key: 'index',
      step: 7,
      kind: 'topic',
      text: '索引与优化',
      x: 513,
      y: 38,
      width: 108,
      height: 30,
      ...topicStyle,
    },
    {
      key: 'btree',
      step: 7,
      kind: 'leaf',
      text: 'B+树',
      x: 642,
      y: 8,
      width: 58,
      height: 21,
      ...leafStyle,
    },
    {
      key: 'index-structure',
      step: 7,
      kind: 'leaf',
      text: '索引结构',
      x: 636,
      y: 42,
      width: 72,
      height: 21,
      ...leafStyle,
    },
    {
      key: 'query-plan',
      step: 7,
      kind: 'leaf',
      text: '执行计划',
      x: 636,
      y: 76,
      width: 72,
      height: 21,
      ...leafStyle,
    },
  ];

  const edges = [
    {
      key: 'center-model',
      step: 2,
      path: 'M 295 133 C 258 105, 226 73, 199 55',
    },
    {
      key: 'model-relational',
      step: 2,
      leaf: true,
      path: 'M 105 52 C 94 39, 88 24, 84 19',
    },
    {
      key: 'model-er',
      step: 2,
      leaf: true,
      path: 'M 105 53 C 96 53, 90 52, 84 52',
    },
    {
      key: 'model-algebra',
      step: 2,
      leaf: true,
      path: 'M 105 55 C 94 67, 90 80, 84 86',
    },

    {
      key: 'center-sql',
      step: 3,
      path: 'M 286 146 C 245 144, 207 141, 178 141',
    },
    {
      key: 'sql-select',
      step: 3,
      leaf: true,
      path: 'M 84 138 C 74 131, 67 122, 60 119',
    },
    {
      key: 'sql-update',
      step: 3,
      leaf: true,
      path: 'M 84 141 C 75 143, 68 146, 60 147',
    },
    {
      key: 'sql-view',
      step: 3,
      leaf: true,
      path: 'M 84 144 C 74 154, 67 170, 60 176',
    },

    {
      key: 'center-concurrency',
      step: 4,
      path: 'M 306 169 C 273 190, 241 215, 218 225',
    },
    {
      key: 'concurrency-lock',
      step: 4,
      leaf: true,
      path: 'M 159 250 C 137 255, 115 260, 98 261',
    },
    {
      key: 'concurrency-schedule',
      step: 4,
      leaf: true,
      path: 'M 183 250 C 170 260, 158 270, 144 270',
    },
    {
      key: 'concurrency-deadlock',
      step: 4,
      leaf: true,
      path: 'M 209 250 C 219 259, 225 267, 226 270',
    },

    {
      key: 'center-normalization',
      step: 5,
      path: 'M 414 169 C 447 190, 479 215, 502 225',
    },
    {
      key: 'normalization-dependency',
      step: 5,
      leaf: true,
      path: 'M 500 250 C 497 259, 495 266, 494 270',
    },
    {
      key: 'normalization-form',
      step: 5,
      leaf: true,
      path: 'M 526 250 C 540 260, 555 269, 569 270',
    },
    {
      key: 'normalization-decomposition',
      step: 5,
      leaf: true,
      path: 'M 552 250 C 572 256, 592 261, 608 261',
    },

    {
      key: 'center-transaction',
      step: 6,
      path: 'M 434 146 C 475 144, 513 141, 542 141',
    },
    {
      key: 'transaction-acid',
      step: 6,
      leaf: true,
      path: 'M 638 138 C 646 131, 651 122, 658 119',
    },
    {
      key: 'transaction-log',
      step: 6,
      leaf: true,
      path: 'M 638 141 C 644 143, 649 146, 654 147',
    },
    {
      key: 'transaction-recovery',
      step: 6,
      leaf: true,
      path: 'M 638 144 C 646 154, 651 170, 658 176',
    },

    {
      key: 'center-index',
      step: 7,
      path: 'M 425 133 C 462 105, 493 73, 521 55',
    },
    {
      key: 'index-btree',
      step: 7,
      leaf: true,
      path: 'M 621 51 C 630 39, 637 24, 642 19',
    },
    {
      key: 'index-structure-edge',
      step: 7,
      leaf: true,
      path: 'M 621 53 C 627 53, 631 52, 636 52',
    },
    {
      key: 'index-plan',
      step: 7,
      leaf: true,
      path: 'M 621 55 C 629 67, 633 80, 636 86',
    },
  ];

  const MAX_STEP = 7;

  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  function emitNodePrompt(text: string, event: Event) {
    event.preventDefault();
    event.stopPropagation();
    const target = event.currentTarget as SVGGElement | null;
    if (!target) return;
    emit('nodePrompt', { text, rect: target.getBoundingClientRect() });
  }

  watch(
    () => props.active,
    (active) => {
      stop();
      step.value = 0;
      if (!active) return;
      timer = setInterval(() => {
        if (step.value >= MAX_STEP) {
          stop();
          emit('complete');
          return;
        }
        step.value += 1;
      }, 360);
    },
    { immediate: true }
  );

  onUnmounted(stop);
</script>

<style scoped lang="less">
  .kg-outer {
    width: 100%;
    height: 100%;
    min-height: 0;
    max-height: 300px;
    overflow: hidden;
    border-radius: 12px;
    background: radial-gradient(
        circle at 50% 48%,
        rgba(115, 99, 229, 0.06),
        transparent 34%
      ),
      linear-gradient(180deg, #fcfbff 0%, #fff 100%);
  }

  .kg-svg {
    display: block;
    width: 100%;
    height: 100%;
    overflow: visible;

    :deep(text) {
      font-family: inherit;
      user-select: text;
      pointer-events: none;
    }
  }

  .edge-line {
    stroke: #93a4cc;
    stroke-width: 1.35;
    stroke-dasharray: 4 4;
    opacity: 0;

    &.on {
      animation: kg-edge-in 0.48s ease-out both;
    }
  }

  .edge-line--leaf {
    stroke: #b7c2dc;
    stroke-width: 1.05;
    stroke-dasharray: 3 4;
  }

  .node-pop {
    opacity: 0;
    transform: scale(0.82);
    transform-box: fill-box;
    transform-origin: center;
    transition: opacity 0.3s ease,
      transform 0.38s cubic-bezier(0.2, 0.85, 0.3, 1.25);

    &.on {
      opacity: 1;
      transform: scale(1);
    }
  }

  .center-node text {
    fill: #fff;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.035em;
  }

  .topic-node text {
    font-size: 11px;
    font-weight: 700;
  }

  .leaf-node text {
    font-size: 9.5px;
    font-weight: 500;
  }

  .node-hotspot {
    cursor: pointer;
    outline: none;

    rect {
      transition: filter 0.2s ease, stroke-width 0.2s ease, transform 0.2s ease;
      transform-box: fill-box;
      transform-origin: center;
    }

    &:hover rect,
    &:focus-visible rect {
      stroke-width: 1.7;
      filter: drop-shadow(0 6px 7px rgba(84, 76, 160, 0.2));
      transform: translateY(-1px);
    }
  }

  @keyframes kg-edge-in {
    from {
      opacity: 0;
      stroke-dashoffset: 18;
    }
    to {
      opacity: 1;
      stroke-dashoffset: 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .edge-line,
    .node-pop {
      animation: none;
      transition: none;
    }

    .edge-line.on {
      opacity: 1;
    }
  }
</style>
