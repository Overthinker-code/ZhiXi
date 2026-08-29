<template>
  <div class="reasoning-pop">
    <div class="reasoning-pop__header">
      <button
        type="button"
        class="reasoning-pop__label"
        :title="activeHint || activeLabel"
        @click.stop="cycleNext"
      >
        {{ activeLabel }}
        <i class="reasoning-pop__chev" />
      </button>
    </div>

    <div class="reasoning-pop__track">
      <div class="reasoning-pop__fill" :style="{ width: fillWidth }"></div>
      <span
        v-for="(pos, i) in dotPositions"
        :key="i"
        class="reasoning-pop__dot"
        :class="{ on: sliderValue >= dotThresholds[i] }"
        :style="{ left: pos }"
      ></span>
      <input
        type="range"
        min="0"
        max="100"
        :value="sliderValue"
        aria-label="思考强度"
        @input="onInput"
        @change="onRelease"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';

  interface ReasoningSliderOption {
    id: string;
    label: string;
    hint?: string;
  }

  const props = defineProps<{
    options: ReasoningSliderOption[];
    /** 当前档位下标（受控），由父组件同步 */
    index: number;
  }>();

  const emit = defineEmits<{
    (e: 'change', index: number): void;
  }>();

  /* ── 档位与连续值的双向映射 ─────────────────
     拖动时为连续值（顺滑手感），停手后吸附到档位中心。
     档位变化通过 zoneIndex watcher 向父组件发 change。 */
  const step = computed(() => (props.options.length > 1 ? 100 / (props.options.length - 1) : 100));

  const sliderValue = ref(
    Math.round(props.index * (props.options.length > 1 ? 100 / (props.options.length - 1) : 100))
  );

  const zoneIndex = computed(() =>
    Math.max(0, Math.min(props.options.length - 1, Math.round(sliderValue.value / step.value)))
  );

  const activeLabel = computed(() => props.options[zoneIndex.value]?.label ?? '');
  const activeHint = computed(() => props.options[zoneIndex.value]?.hint ?? '');

  let suppressEmit = false;
  watch(zoneIndex, (n) => {
    if (!suppressEmit && n !== props.index) emit('change', n);
  });

  watch(
    () => props.index,
    (n) => {
      if (n === zoneIndex.value) return;
      suppressEmit = true;
      sliderValue.value = Math.round(n * step.value);
      suppressEmit = false;
    }
  );

  function onInput(e: Event) {
    sliderValue.value = parseInt((e.target as HTMLInputElement).value, 10);
  }

  function onRelease() {
    sliderValue.value = Math.round(zoneIndex.value * step.value);
  }

  function selectZone(i: number) {
    sliderValue.value = Math.round(i * step.value);
  }

  /** 点击“档位 ›”循环切换到下一档（到底后回到第一档） */
  function cycleNext() {
    selectZone((zoneIndex.value + 1) % props.options.length);
  }

  /* ── 填充与圆点几何：拇指 22px，行程为 (100% - 22px) ── */
  const THUMB = 22;

  const fillWidth = computed(() => {
    const v = sliderValue.value / 100;
    return `calc(${THUMB / 2}px + (100% - ${THUMB}px) * ${v})`;
  });

  const dotPositions = computed(() => {
    const n = props.options.length;
    if (n < 2) return ['50%'];
    return props.options.map(
      (_, i) => `calc(${THUMB / 2}px + (100% - ${THUMB}px) * ${i / (n - 1)})`
    );
  });

  const dotThresholds = computed(() =>
    props.options.map((_, i) => Math.round(i * step.value))
  );
</script>

<style scoped>
  .reasoning-pop {
    user-select: none;
  }

  .reasoning-pop__header {
    margin-bottom: 10px;
  }

  .reasoning-pop__label {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 4px;
    margin-left: -4px;
    border: 0;
    background: transparent;
    color: #363f4d;
    font-size: 13px;
    font-weight: 650;
    line-height: 1.4;
    cursor: pointer;
    border-radius: 6px;
    transition: color 0.15s ease, background 0.15s ease;
  }

  .reasoning-pop__label:hover {
    color: #1d2433;
    background: #f2f4f7;
  }

  .reasoning-pop__chev {
    width: 6px;
    height: 6px;
    border-right: 1.6px solid #98a2b3;
    border-bottom: 1.6px solid #98a2b3;
    transform: rotate(-45deg);
    transition: border-color 0.15s ease;
  }

  .reasoning-pop__label:hover .reasoning-pop__chev {
    border-color: #4f46e5;
  }

  /* ── 胶囊滑轨 ─────────────────────────────── */
  .reasoning-pop__track {
    position: relative;
    height: 18px;
    border-radius: 999px;
    background: #eef0f4;
    box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.05);
    isolation: isolate;
  }

  .reasoning-pop__fill {
    position: absolute;
    left: 0;
    top: 0;
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #6366f1 0%, #4f46e5 100%);
    transition: width 0.05s linear;
    z-index: 1;
  }

  .reasoning-pop__dot {
    position: absolute;
    top: 50%;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: #cdd3de;
    transform: translate(-50%, -50%);
    transition: background 0.2s ease;
    z-index: 2;
    pointer-events: none;
  }

  .reasoning-pop__dot.on {
    background: #ffffff;
  }

  /* ── range input：白色圆拇指 ───────────────── */
  input[type='range'] {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    background: transparent;
    -webkit-appearance: none;
    appearance: none;
    cursor: pointer;
    z-index: 3;
    outline: none;
    margin: 0;
    padding: 0;
  }

  input[type='range']::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #ffffff;
    border: 1px solid rgba(15, 23, 42, 0.06);
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.18), 0 2px 8px rgba(15, 23, 42, 0.08);
    cursor: grab;
    transition: box-shadow 0.2s ease, transform 0.12s ease;
  }

  input[type='range']::-webkit-slider-thumb:active {
    cursor: grabbing;
    transform: scale(0.94);
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.2), 0 0 0 5px rgba(79, 70, 229, 0.1);
  }

  input[type='range']:hover::-webkit-slider-thumb {
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.18), 0 2px 10px rgba(15, 23, 42, 0.12),
      0 0 0 4px rgba(79, 70, 229, 0.08);
  }

  input[type='range']::-moz-range-thumb {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #ffffff;
    border: 1px solid rgba(15, 23, 42, 0.06);
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.18), 0 2px 8px rgba(15, 23, 42, 0.08);
    cursor: grab;
  }

  input[type='range']::-moz-range-thumb:active {
    cursor: grabbing;
    transform: scale(0.94);
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.2), 0 0 0 5px rgba(79, 70, 229, 0.1);
  }

  input[type='range']::-moz-range-track {
    background: transparent;
    border: none;
    height: 18px;
  }

  @media (prefers-reduced-motion: reduce) {
    .reasoning-pop__fill,
    .reasoning-pop__dot,
    input[type='range']::-webkit-slider-thumb {
      transition: none;
    }
  }
</style>
