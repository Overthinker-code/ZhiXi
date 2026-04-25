<template>
  <div class="mm-outer">
    <svg
      class="mm-svg"
      viewBox="0 0 660 410"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <marker
          id="mm-arrow"
          markerWidth="9"
          markerHeight="9"
          refX="7"
          refY="4.5"
          orient="auto"
        >
          <path d="M0,0 L9,4.5 L0,9 Z" fill="#94a3b8" />
        </marker>
      </defs>

      <!-- 连线：随 step 逐步显示 -->
      <g
        class="edges"
        fill="none"
        stroke="#94a3b8"
        stroke-width="1.55"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path
          v-show="step >= 2"
          d="M 330 60 Q 286 90 136 102"
          marker-end="url(#mm-arrow)"
          class="edge-fade"
          :class="{ on: step >= 2 }"
        />
        <path
          v-show="step >= 3"
          d="M 330 60 L 330 102"
          marker-end="url(#mm-arrow)"
          class="edge-fade"
          :class="{ on: step >= 3 }"
        />
        <path
          v-show="step >= 4"
          d="M 330 60 Q 374 90 526 102"
          marker-end="url(#mm-arrow)"
          class="edge-fade"
          :class="{ on: step >= 4 }"
        />
        <path
          v-show="step >= 5"
          d="M 330 136 Q 294 164 248 188"
          marker-end="url(#mm-arrow)"
          class="edge-fade"
          :class="{ on: step >= 5 }"
        />
        <path
          v-show="step >= 6"
          d="M 330 136 L 330 188"
          marker-end="url(#mm-arrow)"
          class="edge-fade"
          :class="{ on: step >= 6 }"
        />
        <path
          v-show="step >= 7"
          d="M 330 136 Q 366 164 392 188"
          marker-end="url(#mm-arrow)"
          class="edge-fade"
          :class="{ on: step >= 7 }"
        />
        <path
          v-show="step >= 8"
          d="M 330 220 Q 306 248 268 278"
          marker-end="url(#mm-arrow)"
          class="edge-fade"
          :class="{ on: step >= 8 }"
        />
        <path
          v-show="step >= 9"
          d="M 330 220 L 330 278"
          marker-end="url(#mm-arrow)"
          class="edge-fade"
          :class="{ on: step >= 9 }"
        />
        <path
          v-show="step >= 10"
          d="M 330 220 Q 354 248 392 278"
          marker-end="url(#mm-arrow)"
          class="edge-fade"
          :class="{ on: step >= 10 }"
        />
        <path
          v-show="step >= 11"
          d="M 526 136 L 526 170"
          marker-end="url(#mm-arrow)"
          class="edge-fade"
          :class="{ on: step >= 11 }"
        />
        <path
          v-show="step >= 12"
          d="M 526 136 L 526 210"
          marker-end="url(#mm-arrow)"
          class="edge-fade"
          :class="{ on: step >= 12 }"
        />
        <path
          v-show="step >= 13"
          d="M 526 136 L 526 250"
          marker-end="url(#mm-arrow)"
          class="edge-fade"
          :class="{ on: step >= 13 }"
        />
      </g>

      <!-- 节点 -->
      <g class="nodes" style="font-size: 12px">
        <g v-show="step >= 1" class="node-pop" :class="{ on: step >= 1 }">
          <rect
            x="270"
            y="22"
            width="120"
            height="38"
            rx="8"
            fill="#6366f1"
            stroke="#4f46e5"
          />
          <text
            x="330"
            y="46"
            text-anchor="middle"
            fill="#fff"
            font-weight="700"
          >
            并发控制
          </text>
        </g>

        <g v-show="step >= 2" class="node-pop" :class="{ on: step >= 2 }">
          <rect
            x="44"
            y="102"
            width="184"
            height="34"
            rx="6"
            fill="#e8e0ff"
            stroke="#b8a9e8"
          />
          <text x="136" y="123" text-anchor="middle" fill="#1a1a1a">
            目标：高吞吐·强一致
          </text>
        </g>

        <g v-show="step >= 3" class="node-pop" :class="{ on: step >= 3 }">
          <rect
            x="275"
            y="102"
            width="110"
            height="34"
            rx="6"
            fill="#e8e0ff"
            stroke="#b8a9e8"
          />
          <text x="330" y="123" text-anchor="middle" fill="#1a1a1a">
            执行方式
          </text>
        </g>

        <g v-show="step >= 4" class="node-pop" :class="{ on: step >= 4 }">
          <rect
            x="432"
            y="102"
            width="188"
            height="34"
            rx="6"
            fill="#e8e0ff"
            stroke="#b8a9e8"
          />
          <text x="526" y="123" text-anchor="middle" fill="#1a1a1a">
            应用场景
          </text>
        </g>

        <g v-show="step >= 5" class="node-pop" :class="{ on: step >= 5 }">
          <rect
            x="188"
            y="188"
            width="88"
            height="30"
            rx="6"
            fill="#f1f5f9"
            stroke="#cbd5e1"
          />
          <text x="232" y="207" text-anchor="middle" fill="#334155">
            串行执行
          </text>
        </g>

        <g v-show="step >= 6" class="node-pop" :class="{ on: step >= 6 }">
          <rect
            x="268"
            y="188"
            width="104"
            height="30"
            rx="6"
            fill="#bae0ff"
            stroke="#1677ff"
          />
          <text x="320" y="207" text-anchor="middle" fill="#0958d9" font-weight="600">
            交叉并发
          </text>
        </g>

        <g v-show="step >= 7" class="node-pop" :class="{ on: step >= 7 }">
          <rect
            x="364"
            y="188"
            width="88"
            height="30"
            rx="6"
            fill="#f1f5f9"
            stroke="#cbd5e1"
          />
          <text x="408" y="207" text-anchor="middle" fill="#334155">
            同时并发
          </text>
        </g>

        <g v-show="step >= 8" class="node-pop" :class="{ on: step >= 8 }">
          <rect
            x="188"
            y="268"
            width="92"
            height="28"
            rx="4"
            fill="#f8fafc"
            stroke="#e2e8f0"
          />
          <text x="234" y="286" text-anchor="middle" fill="#475569" font-size="11px">
            单核优化
          </text>
        </g>
        <g v-show="step >= 9" class="node-pop" :class="{ on: step >= 9 }">
          <rect
            x="288"
            y="268"
            width="92"
            height="28"
            rx="4"
            fill="#f8fafc"
            stroke="#e2e8f0"
          />
          <text x="334" y="286" text-anchor="middle" fill="#475569" font-size="11px">
            时间片轮转
          </text>
        </g>
        <g v-show="step >= 10" class="node-pop" :class="{ on: step >= 10 }">
          <rect
            x="388"
            y="268"
            width="92"
            height="28"
            rx="4"
            fill="#f8fafc"
            stroke="#e2e8f0"
          />
          <text x="434" y="286" text-anchor="middle" fill="#475569" font-size="11px">
            本章重点
          </text>
        </g>

        <g v-show="step >= 11" class="node-pop" :class="{ on: step >= 11 }">
          <rect
            x="466"
            y="170"
            width="120"
            height="28"
            rx="4"
            fill="#f8fafc"
            stroke="#e2e8f0"
          />
          <text x="526" y="188" text-anchor="middle" fill="#475569" font-size="11px">
            机房系统
          </text>
        </g>
        <g v-show="step >= 12" class="node-pop" :class="{ on: step >= 12 }">
          <rect
            x="466"
            y="210"
            width="120"
            height="28"
            rx="4"
            fill="#f8fafc"
            stroke="#e2e8f0"
          />
          <text x="526" y="228" text-anchor="middle" fill="#475569" font-size="11px">
            银行交易
          </text>
        </g>
        <g v-show="step >= 13" class="node-pop" :class="{ on: step >= 13 }">
          <rect
            x="466"
            y="250"
            width="120"
            height="28"
            rx="4"
            fill="#f8fafc"
            stroke="#e2e8f0"
          />
          <text x="526" y="268" text-anchor="middle" fill="#475569" font-size="11px">
            电商平台
          </text>
        </g>
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

  const MAX_STEP = 13;

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
      }, 420);
    },
    { immediate: true }
  );

  onUnmounted(stop);
</script>

<style scoped lang="less">
  .mm-outer {
    width: 100%;
    overflow-x: auto;
    background: #fff;
    border-radius: 8px;
    border: 2px solid #1677ff;
  }

  .mm-svg {
    display: block;
    width: 100%;
    min-width: 580px;
    height: auto;
    min-height: 380px;

    :deep(text) {
      user-select: text;
      pointer-events: auto;
    }
  }

  .edge-fade {
    opacity: 0;
    transition: opacity 0.35s ease;
  }

  .edge-fade.on {
    opacity: 1;
  }

  .node-pop {
    opacity: 0;
    transform: scale(0.92);
    transform-origin: center;
    transition:
      opacity 0.35s ease,
      transform 0.35s ease;
  }

  .node-pop.on {
    opacity: 1;
    transform: scale(1);
  }
</style>
