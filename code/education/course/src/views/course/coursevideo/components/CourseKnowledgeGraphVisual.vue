<template>
  <div class="kg-outer">
    <svg class="kg-svg" viewBox="0 0 840 480" xmlns="http://www.w3.org/2000/svg">
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
        stroke-width="1.2"
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
          class="e-line"
          :class="{ on: step >= e.s }"
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
          :fill="n.fill || '#ede9fe'"
          :stroke="n.stroke || '#8b5cf6'"
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

  const nodes = [
    { k: 'r', s: 1, x: 370, y: 14, w: 120, h: 32, t: '数据库原理' },
    { k: 'a', s: 2, x: 32, y: 78, w: 112, h: 28, t: '数据库系统结构' },
    { k: 'b', s: 2, x: 158, y: 78, w: 80, h: 28, t: '数据模型' },
    { k: 'c', s: 2, x: 252, y: 78, w: 92, h: 28, t: '数据库语言' },
    { k: 'd', s: 2, x: 358, y: 78, w: 92, h: 28, t: '事务管理' },
    { k: 'e', s: 2, x: 464, y: 78, w: 112, h: 28, t: '存储与索引' },
    { k: 'f', s: 2, x: 590, y: 78, w: 92, h: 28, t: '查询处理' },
    { k: 'g', s: 3, x: 52, y: 148, w: 88, h: 26, t: '关系模型' },
    { k: 'h', s: 3, x: 158, y: 148, w: 72, h: 26, t: 'ER模型' },
    { k: 'i', s: 4, x: 340, y: 148, w: 80, h: 26, t: 'ACID特性' },
    { k: 'j', s: 4, x: 436, y: 148, w: 80, h: 26, t: '故障恢复' },
    { k: 'k', s: 5, x: 448, y: 208, w: 88, h: 26, t: '文件组织' },
    { k: 'l', s: 5, x: 552, y: 208, w: 88, h: 26, t: '索引结构' },
    { k: 'm', s: 6, x: 360, y: 268, w: 96, h: 28, t: '并发控制' },
    { k: 'n', s: 7, x: 520, y: 148, w: 64, h: 26, t: 'B+树' },
    { k: 'o', s: 7, x: 596, y: 148, w: 80, h: 26, t: '哈希索引' },
    { k: 'p', s: 8, x: 100, y: 208, w: 80, h: 26, t: '关系代数' },
    { k: 'q', s: 8, x: 192, y: 208, w: 96, h: 26, t: '规范化理论' },
    { k: 'r2', s: 9, x: 192, y: 268, w: 64, h: 26, t: '范式' },
    { k: 's', s: 9, x: 272, y: 268, w: 80, h: 26, t: '锁机制' },
    { k: 't', s: 10, x: 320, y: 328, w: 104, h: 26, t: '两段锁协议' },
    { k: 'u', s: 10, x: 440, y: 328, w: 88, h: 26, t: '可串行化' },
    { k: 'v', s: 10, x: 648, y: 208, w: 88, h: 26, t: '执行计划' },
  ];

  const edges = [
    { k: 'e1', s: 2, d: 'M 430 46 L 88 78' },
    { k: 'e2', s: 2, d: 'M 430 46 L 198 78' },
    { k: 'e3', s: 2, d: 'M 430 46 L 298 78' },
    { k: 'e4', s: 2, d: 'M 430 46 L 404 78' },
    { k: 'e5', s: 2, d: 'M 430 46 L 520 78' },
    { k: 'e6', s: 2, d: 'M 430 46 L 636 78' },
    { k: 'e7', s: 3, d: 'M 88 106 L 96 148' },
    { k: 'e8', s: 3, d: 'M 198 106 L 194 148' },
    { k: 'e9', s: 4, d: 'M 404 106 L 380 148' },
    { k: 'e10', s: 4, d: 'M 404 106 L 476 148' },
    { k: 'e11', s: 5, d: 'M 520 106 L 492 208' },
    { k: 'e12', s: 5, d: 'M 520 106 L 596 208' },
    {
      k: 'e13',
      s: 6,
      d: 'M 380 174 L 408 268',
      lb: '保证',
      lx: 388,
      ly: 218,
    },
    { k: 'e14', s: 6, d: 'M 476 174 L 408 268' },
    { k: 'e15', s: 7, d: 'M 596 234 L 552 148' },
    { k: 'e16', s: 7, d: 'M 596 234 L 636 148' },
    {
      k: 'e17',
      s: 7,
      d: 'M 636 78 L 692 208',
      lb: '加速',
      lx: 648,
      ly: 138,
    },
    { k: 'e18', s: 8, d: 'M 96 174 L 140 208' },
    { k: 'e19', s: 8, d: 'M 96 174 L 240 208' },
    { k: 'e20', s: 9, d: 'M 240 234 L 224 268' },
    { k: 'e21', s: 9, d: 'M 240 234 L 312 268' },
    { k: 'e22', s: 10, d: 'M 408 296 L 372 328' },
    { k: 'e23', s: 10, d: 'M 408 296 L 484 328' },
    { k: 'e24', s: 10, d: 'M 636 106 L 692 208' },
  ];

  const MAX_STEP = 10;

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
    min-width: 820px;
    width: 100%;
    height: auto;
    min-height: 460px;

    :deep(text) {
      user-select: text;
      pointer-events: auto;
    }
  }

  .e-line {
    opacity: 0;
    transition: opacity 0.4s ease;
  }

  .e-line.on {
    opacity: 1;
  }

  .n-pop {
    opacity: 0;
    transform: scale(0.94);
    transition:
      opacity 0.35s ease,
      transform 0.35s ease;
  }

  .n-pop.on {
    opacity: 1;
    transform: scale(1);
  }
</style>
