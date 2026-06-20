<template>
  <a-layout class="layout">
    <ZyTopNav />
    <div
      v-if="!hideFloatUI && !visible"
      class="float-btn"
      :style="{ left: `${robotPos.x}px`, top: `${robotPos.y}px` }"
      @mousedown="startDragRobot"
    >
      <a-button type="primary" class="float-btn__inner" @click="handleClick">
        <icon-robot :style="{ fontSize: '28px' }" />
        <span class="float-btn__label">AI 小智</span>
      </a-button>
    </div>
    <div
      v-if="!hideFloatUI && visible"
      class="float-ai-panel"
      :style="{
        left: `${panelPos.x}px`,
        top: `${panelPos.y}px`,
        width: `${panelSize.width}px`,
        height: `${panelSize.height}px`,
      }"
      @drop.prevent="handlePanelDrop"
      @dragover.prevent="handlePanelDragOver"
      @dragleave="handlePanelDragLeave"
    >
      <div class="panel-header" @mousedown="startDragPanel">
        <span>课堂 AI 助理</span>
        <a-button size="mini" type="text" @click="handleCancel">关闭</a-button>
      </div>
      <div class="panel-body">
        <ClassroomQuickChat ref="quickChatRef" />
      </div>
      <span class="resize-handle right" @mousedown="startResize($event, 'right')" />
      <span class="resize-handle bottom" @mousedown="startResize($event, 'bottom')" />
      <span class="resize-handle corner" @mousedown="startResize($event, 'bottom-right')" />
    </div>
    <a-layout class="layout-content" :style="{ paddingTop: '64px' }">
      <a-layout-content>
        <PageLayout />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script lang="ts" setup>
  import ClassroomQuickChat from '@/components/float-ai/ClassroomQuickChat.vue';
  import ZyTopNav from '@/components/top-nav/ZyTopNav.vue';
  import usePermission from '@/hooks/permission';
  import useResponsive from '@/hooks/responsive';
  import { useUserStore } from '@/store';
  import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import PageLayout from './page-layout.vue';

  const userStore = useUserStore();
  const router = useRouter();
  const route = useRoute();
  const permission = usePermission();
  useResponsive(true);

  watch(
    () => userStore.role,
    (roleValue) => {
      if (roleValue && !permission.accessRouter(route))
        router.push({ name: 'notFound' });
    }
  );

  const visible = ref(false);
  const quickChatRef = ref<any>(null);
  const PANEL_MIN_WIDTH = 420;
  const PANEL_MIN_HEIGHT = 560;
  const PANEL_MAX_WIDTH = 760;
  const PANEL_MAX_HEIGHT = 900;
  const robotPos = ref({ x: window.innerWidth - 100, y: window.innerHeight - 120 });
  const panelSize = ref({ width: 520, height: 760 });
  const panelPos = ref({
    x: window.innerWidth - panelSize.value.width - 24,
    y: 110,
  });
  const dragState = ref<{ target: 'robot' | 'panel' | null; offsetX: number; offsetY: number }>({
    target: null,
    offsetX: 0,
    offsetY: 0,
  });
  const resizeState = ref({
    active: false,
    mode: null as 'right' | 'bottom' | 'bottom-right' | null,
    startX: 0,
    startY: 0,
    startWidth: 0,
    startHeight: 0,
  });

  const handleClick = () => {
    const onCourse =
      route.name === 'Monitor' ||
      route.name === 'CourseContent' ||
      route.path.startsWith('/course/');
    if (onCourse) {
      visible.value = true;
      return;
    }
    router.push({ name: 'TutorChat' });
  };
  const handleCancel = () => {
    visible.value = false;
  };
  const handlePanelDrop = (event: DragEvent) => {
    quickChatRef.value?.handleDrop(event);
  };
  const handlePanelDragOver = (event: DragEvent) => {
    quickChatRef.value?.handleDragOver(event);
  };
  const handlePanelDragLeave = (event: DragEvent) => {
    quickChatRef.value?.handleDragLeave(event);
  };
  const hideFloatUI = computed(
    () =>
      route.path.startsWith('/assistant') ||
      route.path.startsWith('/tutor') ||
      route.name === 'StudentCourseResources' ||
      route.name === 'StudentCourseAgent'
  );

  const startDragRobot = (e: MouseEvent) => {
    dragState.value = {
      target: 'robot',
      offsetX: e.clientX - robotPos.value.x,
      offsetY: e.clientY - robotPos.value.y,
    };
  };
  const startDragPanel = (e: MouseEvent) => {
    dragState.value = {
      target: 'panel',
      offsetX: e.clientX - panelPos.value.x,
      offsetY: e.clientY - panelPos.value.y,
    };
  };
  const onDragMove = (e: MouseEvent) => {
    if (resizeState.value.active && resizeState.value.mode) {
      const deltaX = e.clientX - resizeState.value.startX;
      const deltaY = e.clientY - resizeState.value.startY;
      let width = resizeState.value.startWidth;
      let height = resizeState.value.startHeight;
      if (resizeState.value.mode === 'right' || resizeState.value.mode === 'bottom-right') {
        width = Math.min(
          Math.max(PANEL_MIN_WIDTH, resizeState.value.startWidth + deltaX),
          Math.min(PANEL_MAX_WIDTH, window.innerWidth - panelPos.value.x - 8)
        );
      }
      if (resizeState.value.mode === 'bottom' || resizeState.value.mode === 'bottom-right') {
        height = Math.min(
          Math.max(PANEL_MIN_HEIGHT, resizeState.value.startHeight + deltaY),
          Math.min(PANEL_MAX_HEIGHT, window.innerHeight - panelPos.value.y - 8)
        );
      }
      panelSize.value = { width, height };
      return;
    }
    if (!dragState.value.target) return;
    if (dragState.value.target === 'robot') {
      robotPos.value = {
        x: Math.max(0, Math.min(window.innerWidth - 80, e.clientX - dragState.value.offsetX)),
        y: Math.max(64, Math.min(window.innerHeight - 80, e.clientY - dragState.value.offsetY)),
      };
      return;
    }
    panelPos.value = {
      x: Math.max(0, Math.min(window.innerWidth - panelSize.value.width, e.clientX - dragState.value.offsetX)),
      y: Math.max(64, Math.min(window.innerHeight - panelSize.value.height, e.clientY - dragState.value.offsetY)),
    };
  };
  const startResize = (e: MouseEvent, mode: 'right' | 'bottom' | 'bottom-right') => {
    e.stopPropagation();
    resizeState.value = {
      active: true,
      mode,
      startX: e.clientX,
      startY: e.clientY,
      startWidth: panelSize.value.width,
      startHeight: panelSize.value.height,
    };
  };
  const onDragEnd = () => {
    dragState.value.target = null;
    resizeState.value.active = false;
    resizeState.value.mode = null;
  };
  onMounted(() => {
    window.addEventListener('mousemove', onDragMove);
    window.addEventListener('mouseup', onDragEnd);
  });
  onUnmounted(() => {
    window.removeEventListener('mousemove', onDragMove);
    window.removeEventListener('mouseup', onDragEnd);
  });
</script>

<style scoped lang="less">
  .layout {
    width: 100%;
    min-height: 100vh;
    background: var(--zy-bg-page, #f5f3ff);
  }

  .layout-content {
    min-height: calc(100vh - 64px);
    background: var(--zy-bg-page, #f5f3ff);

    > :deep(.arco-layout-content) {
      min-height: calc(100vh - 64px);
    }
  }

  .float-btn {
    position: fixed;
    z-index: 10000;
    cursor: move;
  }

  .float-btn__inner {
    height: auto !important;
    min-width: 72px;
    padding: 12px 14px 10px !important;
    border-radius: 20px !important;
    display: flex !important;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    background: var(--zy-gradient-brand, linear-gradient(135deg, #6366f1, #8b5cf6)) !important;
    border: none !important;
    box-shadow: 0 12px 32px rgba(99, 102, 241, 0.42);
  }

  .float-btn__label {
    font-size: 11px;
    line-height: 1;
    color: #fff;
    font-weight: 600;
  }

  .float-ai-panel {
    position: fixed;
    z-index: 10001;
    display: flex;
    flex-direction: column;
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 20px 40px rgba(15, 23, 42, 0.25);
    border: 1px solid rgba(99, 102, 241, 0.18);
    background: linear-gradient(180deg, #eef2ff 0%, #e0e7ff 55%, #f8fafc 100%);
  }

  .panel-header {
    height: 44px;
    padding: 0 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(255, 255, 255, 0.72);
    border-bottom: 1px solid rgba(15, 23, 42, 0.06);
    cursor: move;
    span {
      font-weight: 600;
      color: #1e293b;
    }
  }

  .panel-body {
    flex: 1;
    min-height: 0;
  }

  .resize-handle {
    position: absolute;
    z-index: 2;
  }
  .resize-handle.right {
    top: 0;
    right: -2px;
    width: 6px;
    height: 100%;
    cursor: ew-resize;
  }
  .resize-handle.bottom {
    left: 0;
    bottom: -2px;
    width: 100%;
    height: 6px;
    cursor: ns-resize;
  }
  .resize-handle.corner {
    right: -2px;
    bottom: -2px;
    width: 14px;
    height: 14px;
    cursor: nwse-resize;
  }
</style>
