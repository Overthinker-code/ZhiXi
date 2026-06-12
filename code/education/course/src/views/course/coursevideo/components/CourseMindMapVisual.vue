<template>
  <div class="mm-outer">
    <svg
      class="mm-svg"
      viewBox="0 0 720 300"
      preserveAspectRatio="xMidYMid meet"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="数据库系统原理思维导图"
    >
      <defs>
        <linearGradient id="mm-center-fill" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#5f67f2" />
          <stop offset="100%" stop-color="#8658e8" />
        </linearGradient>
        <filter
          id="mm-center-shadow"
          x="-30%"
          y="-50%"
          width="160%"
          height="200%"
        >
          <feDropShadow
            dx="0"
            dy="7"
            stdDeviation="8"
            flood-color="#6258d9"
            flood-opacity=".24"
          />
        </filter>
        <filter
          id="mm-node-shadow"
          x="-25%"
          y="-50%"
          width="150%"
          height="200%"
        >
          <feDropShadow
            dx="0"
            dy="3"
            stdDeviation="3"
            flood-color="#64748b"
            flood-opacity=".12"
          />
        </filter>
      </defs>

      <g class="mm-edges" fill="none" stroke-linecap="round">
        <g
          v-for="branch in branches"
          :key="`${branch.key}-edges`"
          v-show="step >= branch.step"
          class="edge-reveal"
          :class="{ on: step >= branch.step }"
          :style="{ color: branch.color }"
        >
          <path :d="branch.path" class="branch-line" />
          <path
            v-for="leaf in branch.leaves"
            :key="`${leaf.key}-edge`"
            :d="leaf.path"
            class="leaf-line"
          />
        </g>
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
          y="126"
          width="148"
          height="48"
          rx="12"
          fill="url(#mm-center-fill)"
          filter="url(#mm-center-shadow)"
        />
        <rect
          x="291"
          y="131"
          width="138"
          height="38"
          rx="9"
          fill="none"
          stroke="rgba(255,255,255,.28)"
        />
        <text x="360" y="155" text-anchor="middle">数据库系统原理</text>
      </g>

      <template v-for="branch in branches" :key="branch.key">
        <g
          v-show="step >= branch.step"
          class="node-pop node-hotspot branch-node"
          :class="{ on: step >= branch.step }"
          role="button"
          tabindex="0"
          @pointerdown.stop
          @click.stop="emitNodePrompt(branch.text, $event)"
          @keydown.enter.stop="emitNodePrompt(branch.text, $event)"
        >
          <rect
            :x="branch.x"
            :y="branch.y"
            :width="branch.width"
            :height="branch.height"
            rx="9"
            :fill="branch.fill"
            :stroke="branch.color"
            filter="url(#mm-node-shadow)"
          />
          <circle
            :cx="branch.x + 12"
            :cy="branch.y + branch.height / 2"
            r="3"
            :fill="branch.color"
          />
          <text
            :x="branch.x + branch.width / 2 + 4"
            :y="branch.y + branch.height / 2 + 4"
            text-anchor="middle"
            :fill="branch.textColor"
          >
            {{ branch.text }}
          </text>
        </g>

        <g
          v-for="leaf in branch.leaves"
          :key="leaf.key"
          v-show="step >= branch.step"
          class="node-pop node-hotspot leaf-node"
          :class="{ on: step >= branch.step }"
          role="button"
          tabindex="0"
          @pointerdown.stop
          @click.stop="emitNodePrompt(leaf.text, $event)"
          @keydown.enter.stop="emitNodePrompt(leaf.text, $event)"
        >
          <rect
            :x="leaf.x"
            :y="leaf.y"
            :width="leaf.width"
            :height="leaf.height"
            rx="6"
            fill="#fff"
            :stroke="branch.border"
          />
          <text
            :x="leaf.x + leaf.width / 2"
            :y="leaf.y + leaf.height / 2 + 3.5"
            text-anchor="middle"
            :fill="branch.leafText"
          >
            {{ leaf.text }}
          </text>
        </g>
      </template>
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

  const branches = [
    {
      key: 'model',
      step: 2,
      text: '数据模型',
      x: 110,
      y: 30,
      width: 100,
      height: 32,
      color: '#38b779',
      fill: '#e9f9f0',
      border: '#b9ead0',
      textColor: '#19794b',
      leafText: '#40705a',
      path: 'M 296 136 C 260 90, 230 54, 210 46',
      leaves: [
        {
          key: 'entity',
          text: '实体模型',
          x: 18,
          y: 6,
          width: 76,
          height: 22,
          path: 'M 110 44 C 98 35, 94 20, 94 17',
        },
        {
          key: 'relation',
          text: '关系模型',
          x: 10,
          y: 38,
          width: 84,
          height: 22,
          path: 'M 110 46 C 102 47, 98 49, 94 49',
        },
        {
          key: 'dictionary',
          text: '数据字典',
          x: 18,
          y: 70,
          width: 76,
          height: 22,
          path: 'M 110 49 C 100 60, 98 74, 94 81',
        },
      ],
    },
    {
      key: 'sql',
      step: 3,
      text: 'SQL语言',
      x: 102,
      y: 105,
      width: 100,
      height: 32,
      color: '#35a8e8',
      fill: '#eaf7ff',
      border: '#b9e4f7',
      textColor: '#176f9e',
      leafText: '#3d6f85',
      path: 'M 286 147 C 252 139, 225 124, 202 121',
      leaves: [
        {
          key: 'ddl',
          text: '数据定义',
          x: 12,
          y: 96,
          width: 76,
          height: 22,
          path: 'M 102 117 C 96 111, 92 107, 88 107',
        },
        {
          key: 'dml',
          text: '数据操纵',
          x: 4,
          y: 126,
          width: 84,
          height: 22,
          path: 'M 102 121 C 96 128, 92 137, 88 137',
        },
        {
          key: 'dcl',
          text: '权限控制',
          x: 14,
          y: 156,
          width: 74,
          height: 22,
          path: 'M 102 124 C 97 141, 93 158, 88 167',
        },
      ],
    },
    {
      key: 'transaction',
      step: 4,
      text: '事务处理',
      x: 116,
      y: 207,
      width: 104,
      height: 32,
      color: '#ad70e8',
      fill: '#f5edff',
      border: '#ddc5f5',
      textColor: '#7640aa',
      leafText: '#73558b',
      path: 'M 300 169 C 268 190, 245 219, 220 222',
      leaves: [
        {
          key: 'acid',
          text: 'ACID特性',
          x: 16,
          y: 190,
          width: 82,
          height: 22,
          path: 'M 116 218 C 108 210, 102 202, 98 201',
        },
        {
          key: 'recovery',
          text: '恢复机制',
          x: 6,
          y: 220,
          width: 92,
          height: 22,
          path: 'M 116 223 C 108 227, 104 231, 98 231',
        },
        {
          key: 'log',
          text: '日志管理',
          x: 18,
          y: 250,
          width: 80,
          height: 22,
          path: 'M 116 226 C 108 241, 104 254, 98 261',
        },
      ],
    },
    {
      key: 'query',
      step: 5,
      text: '查询优化',
      x: 310,
      y: 222,
      width: 100,
      height: 32,
      color: '#4d8df5',
      fill: '#edf4ff',
      border: '#c9dcfb',
      textColor: '#2e64ba',
      leafText: '#4f6585',
      path: 'M 360 174 C 360 190, 360 208, 360 222',
      leaves: [
        {
          key: 'plan',
          text: '执行计划',
          x: 220,
          y: 270,
          width: 78,
          height: 22,
          path: 'M 340 254 C 326 265, 310 276, 298 281',
        },
        {
          key: 'cost',
          text: '代价估计',
          x: 321,
          y: 270,
          width: 78,
          height: 22,
          path: 'M 360 254 C 360 262, 360 267, 360 270',
        },
        {
          key: 'strategy',
          text: '优化策略',
          x: 422,
          y: 270,
          width: 78,
          height: 22,
          path: 'M 380 254 C 395 265, 410 276, 422 281',
        },
      ],
    },
    {
      key: 'concurrency',
      step: 6,
      text: '并发控制',
      x: 510,
      y: 30,
      width: 104,
      height: 32,
      color: '#ef6e78',
      fill: '#fff0f1',
      border: '#f5c6ca',
      textColor: '#b33e48',
      leafText: '#8b555a',
      path: 'M 424 136 C 460 90, 486 54, 510 46',
      leaves: [
        {
          key: 'lock',
          text: '并发问题',
          x: 628,
          y: 6,
          width: 78,
          height: 22,
          path: 'M 614 43 C 620 32, 624 22, 628 17',
        },
        {
          key: 'schedule',
          text: '锁机制',
          x: 632,
          y: 38,
          width: 70,
          height: 22,
          path: 'M 614 46 C 621 47, 626 49, 632 49',
        },
        {
          key: 'serial',
          text: '可串行化',
          x: 622,
          y: 70,
          width: 84,
          height: 22,
          path: 'M 614 49 C 620 61, 620 74, 622 81',
        },
      ],
    },
    {
      key: 'normalization',
      step: 7,
      text: '范式优化',
      x: 518,
      y: 105,
      width: 104,
      height: 32,
      color: '#8c66df',
      fill: '#f3efff',
      border: '#d7cbf4',
      textColor: '#6543ac',
      leafText: '#6c5c8a',
      path: 'M 434 147 C 468 139, 494 124, 518 121',
      leaves: [
        {
          key: 'dependency',
          text: '函数依赖',
          x: 634,
          y: 96,
          width: 76,
          height: 22,
          path: 'M 622 117 C 626 111, 630 107, 634 107',
        },
        {
          key: 'normal-form',
          text: '范式理论',
          x: 634,
          y: 126,
          width: 76,
          height: 22,
          path: 'M 622 121 C 627 128, 630 137, 634 137',
        },
        {
          key: 'decompose',
          text: '模式分解',
          x: 630,
          y: 156,
          width: 80,
          height: 22,
          path: 'M 622 124 C 626 141, 628 158, 630 167',
        },
      ],
    },
    {
      key: 'index',
      step: 8,
      text: '索引与存储',
      x: 500,
      y: 207,
      width: 112,
      height: 32,
      color: '#e5a13f',
      fill: '#fff6e8',
      border: '#f2d7ad',
      textColor: '#a96714',
      leafText: '#82643d',
      path: 'M 420 169 C 451 190, 476 219, 500 222',
      leaves: [
        {
          key: 'btree',
          text: '索引结构',
          x: 626,
          y: 190,
          width: 80,
          height: 22,
          path: 'M 612 218 C 618 210, 622 202, 626 201',
        },
        {
          key: 'organization',
          text: '存储组织',
          x: 626,
          y: 220,
          width: 80,
          height: 22,
          path: 'M 612 223 C 618 227, 622 231, 626 231',
        },
        {
          key: 'buffer',
          text: '缓冲管理',
          x: 626,
          y: 250,
          width: 80,
          height: 22,
          path: 'M 612 226 C 619 241, 622 254, 626 261',
        },
      ],
    },
  ];

  const MAX_STEP = 8;

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
      }, 330);
    },
    { immediate: true }
  );

  onUnmounted(stop);
</script>

<style scoped lang="less">
  .mm-outer {
    width: 100%;
    height: 100%;
    min-height: 0;
    max-height: 300px;
    overflow: hidden;
    border-radius: 12px;
    background: radial-gradient(
        circle at 50% 47%,
        rgba(99, 102, 241, 0.055),
        transparent 31%
      ),
      linear-gradient(180deg, #fff 0%, #fdfdff 100%);
  }

  .mm-svg {
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

  .branch-line {
    stroke: currentColor;
    stroke-width: 2.2;
  }

  .leaf-line {
    stroke: currentColor;
    stroke-width: 1.2;
    opacity: 0.62;
  }

  .edge-reveal {
    opacity: 0;

    &.on {
      opacity: 1;
      animation: edge-draw 0.48s ease-out both;
    }
  }

  .node-pop {
    opacity: 0;
    transform: scale(0.84);
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
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.04em;
  }

  .branch-node text {
    font-size: 12px;
    font-weight: 700;
  }

  .leaf-node text {
    font-size: 10px;
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
      stroke-width: 1.8;
      filter: drop-shadow(0 6px 7px rgba(70, 78, 130, 0.18));
      transform: translateY(-1px);
    }
  }

  @keyframes edge-draw {
    from {
      opacity: 0;
      stroke-dasharray: 7 6;
      stroke-dashoffset: 24;
    }
    to {
      opacity: 1;
      stroke-dasharray: 1000 0;
      stroke-dashoffset: 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .edge-reveal,
    .node-pop {
      animation: none;
      transition: none;
    }
  }
</style>
