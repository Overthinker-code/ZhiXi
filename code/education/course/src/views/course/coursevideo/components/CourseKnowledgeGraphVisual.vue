<template>
  <div class="kg-outer">
    <svg class="kg-svg" viewBox="0 0 940 360" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker
          id="kg-ar"
          markerWidth="7"
          markerHeight="7"
          refX="5"
          refY="3.5"
          orient="auto"
        >
          <path d="M0,0 L7,3.5 L0,7 Z" fill="#64748b" />
        </marker>
      </defs>

      <g
        v-for="e in edges"
        :key="e.k"
        fill="none"
        stroke="#475569"
        stroke-width="1.15"
        marker-end="url(#kg-ar)"
      >
        <path
          v-show="step >= e.s"
          :d="e.d"
          class="e-line"
          :class="{ on: step >= e.s }"
        />
        <text
          v-if="e.lb"
          v-show="step >= e.s"
          :x="e.lx"
          :y="e.ly"
          font-size="10"
          fill="#64748b"
          class="e-lbl"
          :class="{ on: step >= e.s }"
          :text-anchor="e.ta || 'start'"
        >
          {{ e.lb }}
        </text>
      </g>

      <g
        v-for="n in nodes"
        :key="n.k"
        class="n-pop"
        :class="{ on: step >= n.s }"
      >
        <rect
          v-show="step >= n.s"
          :x="n.x"
          :y="n.y"
          :width="n.w"
          :height="n.h"
          rx="5"
          fill="#ede9fe"
          stroke="#8b5cf6"
        />
        <text
          v-show="step >= n.s"
          :x="n.x + n.w / 2"
          :y="n.y + n.h / 2 + 4"
          text-anchor="middle"
          font-size="11"
          fill="#1e293b"
        >
          {{ n.t }}
        </text>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
  import { ref, watch, onUnmounted } from 'vue';

  const props = defineProps<{ active: boolean }>();
  const emit = defineEmits<{ complete: [] }>();

  const step = ref(0);
  let timer: ReturnType<typeof setInterval> | null = null;

  /** 分层排布，折线连接，边标签偏离线段中点以减少遮挡 */
  const nodes = [
    { k: 'r', s: 1, x: 408, y: 12, w: 124, h: 28, t: '数据库原理' },
    { k: 'a', s: 2, x: 16, y: 68, w: 118, h: 26, t: '数据库系统结构' },
    { k: 'b', s: 2, x: 146, y: 68, w: 82, h: 26, t: '数据模型' },
    { k: 'c', s: 2, x: 238, y: 68, w: 90, h: 26, t: '数据库语言' },
    { k: 'd', s: 2, x: 340, y: 68, w: 86, h: 26, t: '事务管理' },
    { k: 'e', s: 2, x: 438, y: 68, w: 114, h: 26, t: '存储与索引' },
    { k: 'f', s: 2, x: 564, y: 68, w: 90, h: 26, t: '查询处理' },
    { k: 'g', s: 3, x: 36, y: 128, w: 84, h: 24, t: '关系模型' },
    { k: 'h', s: 3, x: 132, y: 128, w: 70, h: 24, t: 'ER模型' },
    { k: 'i', s: 3, x: 322, y: 128, w: 78, h: 24, t: 'ACID特性' },
    { k: 'j', s: 3, x: 412, y: 128, w: 82, h: 24, t: '故障恢复' },
    { k: 'n', s: 3, x: 510, y: 128, w: 58, h: 24, t: 'B+树' },
    { k: 'o', s: 3, x: 584, y: 128, w: 82, h: 24, t: '哈希索引' },
    { k: 'p', s: 4, x: 16, y: 188, w: 76, h: 24, t: '关系代数' },
    { k: 'q', s: 4, x: 102, y: 188, w: 96, h: 24, t: '规范化理论' },
    { k: 'k', s: 4, x: 406, y: 188, w: 82, h: 24, t: '文件组织' },
    { k: 'l', s: 4, x: 502, y: 188, w: 82, h: 24, t: '索引结构' },
    { k: 'v', s: 4, x: 688, y: 188, w: 86, h: 24, t: '执行计划' },
    { k: 'm', s: 5, x: 332, y: 248, w: 94, h: 24, t: '并发控制' },
    { k: 'r2', s: 5, x: 108, y: 248, w: 58, h: 24, t: '范式' },
    { k: 's', s: 5, x: 176, y: 248, w: 72, h: 24, t: '锁机制' },
    { k: 't', s: 6, x: 292, y: 308, w: 108, h: 24, t: '两段锁协议' },
    { k: 'u', s: 6, x: 412, y: 308, w: 90, h: 24, t: '可串行化' },
  ];

  const edges = [
    { k: 'e1', s: 2, d: 'M 470 40 L 75 68' },
    { k: 'e2', s: 2, d: 'M 470 40 L 187 68' },
    { k: 'e3', s: 2, d: 'M 470 40 L 283 68' },
    { k: 'e4', s: 2, d: 'M 470 40 L 383 68' },
    { k: 'e5', s: 2, d: 'M 470 40 L 495 68' },
    { k: 'e6', s: 2, d: 'M 470 40 L 609 68' },
    { k: 'e7', s: 3, d: 'M 78 94 L 78 128' },
    { k: 'e8', s: 3, d: 'M 167 94 L 167 128' },
    { k: 'e9', s: 4, d: 'M 78 152 L 54 188' },
    { k: 'e10', s: 4, d: 'M 78 152 L 150 188' },
    { k: 'e11', s: 4, d: 'M 167 152 L 54 188' },
    { k: 'e12', s: 4, d: 'M 167 152 L 150 188' },
    { k: 'e13', s: 5, d: 'M 150 212 L 137 248' },
    { k: 'e14', s: 5, d: 'M 150 212 L 212 248' },
    { k: 'e15', s: 3, d: 'M 383 94 L 361 128' },
    {
      k: 'e16',
      s: 5,
      d: 'M 361 152 L 361 206 L 379 206 L 379 248',
      lb: '保证',
      lx: 368,
      ly: 198,
      ta: 'start' as const,
    },
    { k: 'e17', s: 6, d: 'M 379 272 L 346 308' },
    { k: 'e18', s: 6, d: 'M 379 272 L 457 308' },
    { k: 'e19', s: 3, d: 'M 495 94 L 453 128' },
    { k: 'e20', s: 3, d: 'M 495 94 L 539 128' },
    { k: 'e21', s: 4, d: 'M 453 152 L 447 188' },
    { k: 'e22', s: 4, d: 'M 539 152 L 543 188' },
    {
      k: 'e23',
      s: 3,
      d: 'M 609 94 L 609 112 L 625 112 L 625 128',
      lb: '加速',
      lx: 632,
      ly: 106,
      ta: 'start' as const,
    },
    { k: 'e24', s: 4, d: 'M 625 152 L 625 182 L 543 182 L 543 188' },
    { k: 'e25', s: 4, d: 'M 625 152 L 625 174 L 731 174 L 731 188' },
  ];

  const MAX_STEP = 6;

  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  watch(
    () => props.active,
    (a) => {
      stop();
      step.value = 0;
      if (!a) return;
      timer = setInterval(() => {
        if (step.value >= MAX_STEP) {
          stop();
          emit('complete');
          return;
        }
        step.value += 1;
      }, 460);
    },
    { immediate: true }
  );

  onUnmounted(stop);
</script>

<style scoped lang="less">
  .kg-outer {
    width: 100%;
    overflow-x: auto;
    background: linear-gradient(180deg, #faf5ff 0%, #fff 100%);
    border-radius: 10px;
    border: 1px solid #722ed1;
  }

  .kg-svg {
    display: block;
    min-width: 920px;
    width: 100%;
    height: auto;
    min-height: 340px;

    :deep(text) {
      user-select: text;
      pointer-events: auto;
    }
  }

  .e-line {
    opacity: 0.35;
    transition: opacity 0.35s ease;

    &.on {
      opacity: 1;
    }
  }

  .e-lbl {
    opacity: 0.45;
    pointer-events: none;

    &.on {
      opacity: 1;
    }
  }

  .n-pop {
    opacity: 0.4;
    transition: opacity 0.35s ease;

    &.on {
      opacity: 1;
    }
  }
</style>
