<template>
  <Teleport to="body">
    <div
      v-show="modelValue"
      class="monitor-tool-float"
      :style="panelCss"
      @mousedown.stop
    >
      <div class="float-head" @mousedown.prevent="startDrag">
        <span class="float-title">{{ title }}</span>
        <a-button type="text" size="mini" @click="close">关闭</a-button>
      </div>
      <div class="float-body">
        <slot />
      </div>
      <span
        class="rh right monitor-float-resize"
        @mousedown.prevent.stop="startResize($event, 'right')"
      />
      <span
        class="rh bottom monitor-float-resize"
        @mousedown.prevent.stop="startResize($event, 'bottom')"
      />
      <span
        class="rh corner monitor-float-resize"
        @mousedown.prevent.stop="startResize($event, 'bottom-right')"
      />
    </div>
  </Teleport>
</template>

<script setup lang="ts">
  import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

  const props = withDefaults(
    defineProps<{
      modelValue: boolean;
      title: string;
    }>(),
    {
      title: '',
    }
  );

  const emit = defineEmits<{ 'update:modelValue': [boolean] }>();

  const MIN_W = 320;
  const MIN_H = 240;
  const MAX_W = 900;
  const MAX_H = 720;

  const left = ref(0);
  const top = ref(72);
  const width = ref(400);
  const height = ref(480);

  const panelCss = computed(() => ({
    left: `${left.value}px`,
    top: `${top.value}px`,
    width: `${width.value}px`,
    height: `${height.value}px`,
  }));

  function resetPosition() {
    const w = Math.min(440, Math.max(360, window.innerWidth * 0.28));
    const h = Math.min(560, Math.max(360, window.innerHeight * 0.62));
    width.value = w;
    height.value = h;
    left.value = Math.max(12, window.innerWidth - w - 20);
    top.value = Math.max(64, (window.innerHeight - h) * 0.12);
  }

  watch(
    () => props.modelValue,
    (v) => {
      if (v) resetPosition();
    }
  );

  function close() {
    emit('update:modelValue', false);
  }

  const drag = ref({ active: false, ox: 0, oy: 0 });
  const resize = ref({
    active: false,
    mode: null as null | 'right' | 'bottom' | 'bottom-right',
    sx: 0,
    sy: 0,
    sw: 0,
    sh: 0,
  });

  function startDrag(e: MouseEvent) {
    const t = e.target as HTMLElement;
    if (t.closest('.arco-btn')) return;
    drag.value = {
      active: true,
      ox: e.clientX - left.value,
      oy: e.clientY - top.value,
    };
  }

  function startResize(
    e: MouseEvent,
    mode: 'right' | 'bottom' | 'bottom-right'
  ) {
    resize.value = {
      active: true,
      mode,
      sx: e.clientX,
      sy: e.clientY,
      sw: width.value,
      sh: height.value,
    };
  }

  function onMove(e: MouseEvent) {
    if (resize.value.active && resize.value.mode) {
      const dx = e.clientX - resize.value.sx;
      const dy = e.clientY - resize.value.sy;
      let w = resize.value.sw;
      let h = resize.value.sh;
      if (
        resize.value.mode === 'right' ||
        resize.value.mode === 'bottom-right'
      ) {
        w = Math.min(
          MAX_W,
          Math.max(MIN_W, resize.value.sw + dx),
          window.innerWidth - left.value - 8
        );
      }
      if (
        resize.value.mode === 'bottom' ||
        resize.value.mode === 'bottom-right'
      ) {
        h = Math.min(
          MAX_H,
          Math.max(MIN_H, resize.value.sh + dy),
          window.innerHeight - top.value - 8
        );
      }
      width.value = w;
      height.value = h;
      return;
    }
    if (!drag.value.active) return;
    left.value = Math.max(
      0,
      Math.min(window.innerWidth - width.value, e.clientX - drag.value.ox)
    );
    top.value = Math.max(
      56,
      Math.min(window.innerHeight - height.value, e.clientY - drag.value.oy)
    );
  }

  function onUp() {
    drag.value.active = false;
    resize.value.active = false;
    resize.value.mode = null;
  }

  onMounted(() => {
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  });
  onUnmounted(() => {
    window.removeEventListener('mousemove', onMove);
    window.removeEventListener('mouseup', onUp);
  });
</script>

<style scoped lang="less">
  .monitor-tool-float {
    position: fixed;
    z-index: 9990;
    display: flex;
    flex-direction: column;
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 16px 48px rgba(15, 23, 42, 0.22);
    border: 1px solid rgba(99, 102, 241, 0.25);
    background: var(--color-bg-2);
    box-sizing: border-box;
  }

  .float-head {
    flex-shrink: 0;
    height: 42px;
    padding: 0 10px 0 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(90deg, #eef2ff 0%, #fff 100%);
    border-bottom: 1px solid rgba(99, 102, 241, 0.12);
    cursor: grab;
    user-select: none;

    &:active {
      cursor: grabbing;
    }
  }

  .float-title {
    font-weight: 600;
    font-size: 14px;
    color: #312e81;
  }

  .float-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 10px 12px 14px;
  }

  .rh {
    position: absolute;
    z-index: 2;
  }

  .rh.right {
    top: 0;
    right: 0;
    width: 8px;
    height: 100%;
    cursor: ew-resize;
  }

  .rh.bottom {
    left: 0;
    bottom: 0;
    width: 100%;
    height: 8px;
    cursor: ns-resize;
  }

  .rh.corner {
    right: 0;
    bottom: 0;
    width: 14px;
    height: 14px;
    cursor: nwse-resize;
  }
</style>
