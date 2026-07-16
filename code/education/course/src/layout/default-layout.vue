<template>
  <a-layout class="layout">
    <a href="#main-content" class="zy-skip-link">跳到主要内容</a>
    <ZyTopNav />
    <div
      v-if="!hideFloatUI && !visible"
      class="float-btn"
      aria-label="打开课堂 AI 助理"
      :style="{ left: `${robotPos.x}px`, top: `${robotPos.y}px` }"
      @mousedown="startDragRobot"
    >
      <a-button type="primary" class="float-btn__inner" @click="handleClick">
        <icon-robot :style="{ fontSize: '24px' }" />
        <span class="float-btn__label">小智</span>
      </a-button>
    </div>
    <div
      v-if="!hideFloatUI && visible"
      class="float-ai-panel"
      role="dialog"
      aria-label="课堂 AI 助理"
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
      <a-layout-content id="main-content" tabindex="-1">
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
  const PANEL_MIN_WIDTH = 340;
  const PANEL_MIN_HEIGHT = 480;
  const PANEL_MAX_WIDTH = 760;
  const PANEL_MAX_HEIGHT = 900;
  const panelViewportMaxWidth = () =>
    Math.max(PANEL_MIN_WIDTH, Math.min(PANEL_MAX_WIDTH, window.innerWidth - 20));
  const panelViewportMaxHeight = () =>
    Math.max(PANEL_MIN_HEIGHT, Math.min(PANEL_MAX_HEIGHT, window.innerHeight - 76));
  const robotPos = ref({ x: window.innerWidth - 100, y: window.innerHeight - 120 });
  const panelSize = ref({
    width: Math.min(468, panelViewportMaxWidth()),
    height: Math.min(700, panelViewportMaxHeight()),
  });
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

  const fitFloatingUiToViewport = () => {
    const maxWidth = panelViewportMaxWidth();
    const maxHeight = panelViewportMaxHeight();
    panelSize.value = {
      width:
        window.innerWidth < 720
          ? maxWidth
          : Math.min(Math.max(panelSize.value.width, PANEL_MIN_WIDTH), maxWidth),
      height: Math.min(Math.max(panelSize.value.height, PANEL_MIN_HEIGHT), maxHeight),
    };
    panelPos.value = {
      x: Math.max(8, Math.min(window.innerWidth - panelSize.value.width - 8, panelPos.value.x)),
      y: Math.max(72, Math.min(window.innerHeight - panelSize.value.height - 8, panelPos.value.y)),
    };
    robotPos.value = {
      x: Math.max(8, Math.min(window.innerWidth - 88, robotPos.value.x)),
      y: Math.max(72, Math.min(window.innerHeight - 88, robotPos.value.y)),
    };
  };
  const preparePanelForOpen = () => {
    panelSize.value = {
      width:
        window.innerWidth >= 720
          ? Math.min(468, panelViewportMaxWidth())
          : panelViewportMaxWidth(),
      height:
        window.innerHeight >= 760
          ? Math.min(700, panelViewportMaxHeight())
          : panelViewportMaxHeight(),
    };
    panelPos.value = {
      x: window.innerWidth >= 720 ? window.innerWidth - panelSize.value.width - 24 : 8,
      y: window.innerHeight >= 760 ? 110 : 72,
    };
    fitFloatingUiToViewport();
  };

  const handleClick = () => {
    const onCourse =
      route.name === 'Monitor' ||
      route.name === 'CourseContent' ||
      route.path.startsWith('/course/');
    if (onCourse) {
      preparePanelForOpen();
      visible.value = true;
      return;
    }
    router.push({ name: 'TutorChat' });
  };
  const openClassroomAi = (event?: Event) => {
    preparePanelForOpen();
    visible.value = true;
    const detail = (event as CustomEvent<{ prompt?: string }> | undefined)?.detail;
    if (detail?.prompt) {
      setTimeout(() => quickChatRef.value?.prefillPrompt?.(detail.prompt), 0);
    }
  };
  const handleCancel = () => {
    visible.value = false;
  };
  const handleKeydown = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && visible.value) handleCancel();
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
      route.name === 'CourseResourceGeneration' ||
      route.name === 'ResourceHub' ||
      route.name === 'StudentCourseResourceGenerator' ||
      route.name === 'StudentCourseResources' ||
      route.name === 'StudentCourseKnowledge' ||
      route.name === 'StudentCourseAnalytics' ||
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
          Math.min(panelViewportMaxWidth(), window.innerWidth - panelPos.value.x - 8)
        );
      }
      if (resizeState.value.mode === 'bottom' || resizeState.value.mode === 'bottom-right') {
        height = Math.min(
          Math.max(PANEL_MIN_HEIGHT, resizeState.value.startHeight + deltaY),
          Math.min(panelViewportMaxHeight(), window.innerHeight - panelPos.value.y - 8)
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
    fitFloatingUiToViewport();
    window.addEventListener('mousemove', onDragMove);
    window.addEventListener('mouseup', onDragEnd);
    window.addEventListener('resize', fitFloatingUiToViewport);
    window.addEventListener('keydown', handleKeydown);
    window.addEventListener('open-classroom-ai', openClassroomAi as EventListener);
  });
  onUnmounted(() => {
    window.removeEventListener('mousemove', onDragMove);
    window.removeEventListener('mouseup', onDragEnd);
    window.removeEventListener('resize', fitFloatingUiToViewport);
    window.removeEventListener('keydown', handleKeydown);
    window.removeEventListener('open-classroom-ai', openClassroomAi as EventListener);
  });
</script>

<style scoped lang="less">
  .layout {
    width: 100%;
    min-height: 100vh;
    background: var(--zy-bg-page, #f5f3ff);
  }

  .zy-skip-link {
    position: fixed;
    top: 8px;
    left: 16px;
    z-index: 100000;
    padding: 10px 14px;
    border-radius: 8px;
    color: #fff;
    background: #3730a3;
    font-weight: 700;
    text-decoration: none;
    transform: translateY(-160%);
    transition: transform 120ms ease;
  }

  .zy-skip-link:focus-visible {
    transform: translateY(0);
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
    position: relative;
    width: 58px !important;
    height: 58px !important;
    min-width: 58px !important;
    padding: 0 !important;
    border-radius: 50% !important;
    display: flex !important;
    align-items: center;
    justify-content: center;
    overflow: visible;
    background:
      radial-gradient(circle at 30% 24%, rgba(255, 255, 255, 0.95), transparent 18%),
      linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    border: 1px solid rgba(255, 255, 255, 0.72) !important;
    box-shadow: 0 16px 34px rgba(79, 70, 229, 0.32);
    transition:
      transform 0.16s ease,
      box-shadow 0.16s ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 20px 40px rgba(79, 70, 229, 0.38);
    }

    &::after {
      content: '';
      position: absolute;
      inset: -5px;
      border: 1px solid rgba(99, 102, 241, 0.18);
      border-radius: inherit;
      pointer-events: none;
    }
  }

  .float-btn__label {
    position: absolute;
    right: 50px;
    top: 50%;
    transform: translateY(-50%);
    padding: 5px 9px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.94);
    color: #4f46e5;
    font-size: 12px;
    line-height: 1.1;
    font-weight: 760;
    white-space: nowrap;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
  }

  .float-ai-panel {
    position: fixed;
    z-index: 10001;
    display: flex;
    flex-direction: column;
    border-radius: 22px;
    overflow: hidden;
    box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
    border: 1px solid rgba(15, 23, 42, 0.08);
    background: #fff;
  }

  @media (min-width: 720px) {
    .float-ai-panel {
      min-width: 420px;
    }
  }

  @media (max-width: 719px) {
    .float-ai-panel {
      max-width: calc(100vw - 20px);
      min-width: min(320px, calc(100vw - 20px));
    }
  }

  .panel-header {
    height: 48px;
    padding: 0 14px 0 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(255, 255, 255, 0.94);
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
    background: #fbfcff;
  }

  @media (prefers-reduced-motion: reduce) {
    .float-btn__inner {
      transition: none;

      &:hover {
        transform: none;
      }
    }
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
