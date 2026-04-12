<template>
  <a-layout class="layout" :class="{ mobile: appStore.hideMenu }">
    <div v-if="navbar" class="layout-navbar">
      <NavBar />
    </div>
    <div
      v-if="!hideFloatUI && !visible"
      class="float-btn"
      :style="{ left: `${robotPos.x}px`, top: `${robotPos.y}px` }"
      @mousedown="startDragRobot"
    >
      <a-button type="primary" @click="handleClick"
        ><icon-robot :style="{ fontSize: '30px' }"
      /></a-button>
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
    >
      <div class="panel-header" @mousedown="startDragPanel">
        <span>课堂 AI 助理</span>
        <a-button size="mini" type="text" @click="handleCancel">关闭</a-button>
      </div>
      <div class="panel-body">
        <ClassroomQuickChat />
      </div>
      <span
        class="resize-handle right"
        @mousedown="startResize($event, 'right')"
      />
      <span
        class="resize-handle bottom"
        @mousedown="startResize($event, 'bottom')"
      />
      <span
        class="resize-handle corner"
        @mousedown="startResize($event, 'bottom-right')"
      />
    </div>
    <a-layout>
      <a-layout>
        <a-layout-sider
          v-if="renderMenu"
          v-show="!appStore.hideMenu"
          class="layout-sider"
          breakpoint="xl"
          :collapsed="collapsed"
          :collapsible="true"
          :width="menuWidth"
          :style="{ paddingTop: navbar ? '60px' : '' }"
          :hide-trigger="true"
          @collapse="setCollapsed"
        >
          <div class="menu-wrapper">
            <Menu />
          </div>
        </a-layout-sider>
        <a-drawer
          v-if="appStore.hideMenu"
          :visible="drawerVisible"
          placement="left"
          :footer="false"
          mask-closable
          :closable="false"
          @cancel="drawerCancel"
        >
          <Menu />
        </a-drawer>
        <a-layout class="layout-content" :style="paddingStyle">
          <TabBar v-if="appStore.tabBar" />
          <a-layout-content>
            <PageLayout />
          </a-layout-content>
          <!-- <Footer v-if="footer" /> -->
        </a-layout>
      </a-layout>
    </a-layout>
  </a-layout>
</template>

<script lang="ts" setup>
  import ClassroomQuickChat from '@/components/float-ai/ClassroomQuickChat.vue';
  import Footer from '@/components/footer/index.vue';
  import Menu from '@/components/menu/index.vue';
  import NavBar from '@/components/navbar/index.vue';
  import TabBar from '@/components/tab-bar/index.vue';
  import usePermission from '@/hooks/permission';
  import useResponsive from '@/hooks/responsive';
  import { useAppStore, useUserStore } from '@/store';
  import { computed, onMounted, onUnmounted, provide, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import PageLayout from './page-layout.vue';

  const isInit = ref(false);
  const appStore = useAppStore();
  const userStore = useUserStore();
  const router = useRouter();
  const route = useRoute();
  const permission = usePermission();
  useResponsive(true);
  const navbarHeight = `60px`;
  const navbar = computed(() => appStore.navbar);
  const renderMenu = computed(() => appStore.menu && !appStore.topMenu);
  // const hideMenu = computed(() => appStore.hideMenu);
  const footer = computed(() => appStore.footer);
  const menuWidth = computed(() => {
    return appStore.menuCollapse ? 48 : appStore.menuWidth;
  });
  const collapsed = computed(() => {
    return appStore.menuCollapse;
  });
  const paddingStyle = computed(() => {
    const paddingLeft =
      renderMenu.value && !appStore.hideMenu
        ? { paddingLeft: `${menuWidth.value}px` }
        : {};
    const paddingTop = navbar.value ? { paddingTop: navbarHeight } : {};
    return { ...paddingLeft, ...paddingTop };
  });
  const setCollapsed = (val: boolean) => {
    if (!isInit.value) return; // for page initialization menu state problem
    appStore.updateSettings({ menuCollapse: val });
  };
  watch(
    () => userStore.role,
    (roleValue) => {
      if (roleValue && !permission.accessRouter(route))
        router.push({ name: 'notFound' });
    }
  );
  const drawerVisible = ref(false);
  const drawerCancel = () => {
    drawerVisible.value = false;
  };
  provide('toggleDrawerMenu', () => {
    drawerVisible.value = !drawerVisible.value;
  });
  onMounted(() => {
    isInit.value = true;
  });
  const visible = ref(false);
  const PANEL_MIN_WIDTH = 420;
  const PANEL_MIN_HEIGHT = 560;
  const PANEL_MAX_WIDTH = 760;
  const PANEL_MAX_HEIGHT = 900;
  const robotPos = ref({
    x: window.innerWidth - 100,
    y: window.innerHeight - 120,
  });
  const panelSize = ref({ width: 520, height: 760 });
  const panelPos = ref({
    x: window.innerWidth - panelSize.value.width - 24,
    y: 110,
  });
  const dragState = ref<{
    target: 'robot' | 'panel' | null;
    offsetX: number;
    offsetY: number;
  }>({
    target: null,
    offsetX: 0,
    offsetY: 0,
  });
  const resizeState = ref<{
    active: boolean;
    mode: 'right' | 'bottom' | 'bottom-right' | null;
    startX: number;
    startY: number;
    startWidth: number;
    startHeight: number;
  }>({
    active: false,
    mode: null,
    startX: 0,
    startY: 0,
    startWidth: 0,
    startHeight: 0,
  });

  const handleClick = () => {
    const onCourseMonitor =
      route.name === 'Monitor' || route.path === '/course/monitor';
    const onCourseContent =
      route.name === 'CourseContent' || route.path === '/course/course-content';
    if (onCourseMonitor || onCourseContent) {
      visible.value = true;
      panelPos.value = {
        x: Math.min(
          panelPos.value.x,
          window.innerWidth - panelSize.value.width
        ),
        y: Math.min(
          panelPos.value.y,
          window.innerHeight - panelSize.value.height
        ),
      };
      return;
    }
    router.push({ name: 'AssistantChat' });
  };
  const handleOk = () => {
    visible.value = false;
  };
  const handleCancel = () => {
    visible.value = false;
  };
  const hideFloatUI = computed(() => route.path.startsWith('/assistant'));

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
      if (
        resizeState.value.mode === 'right' ||
        resizeState.value.mode === 'bottom-right'
      ) {
        width = Math.min(
          Math.max(PANEL_MIN_WIDTH, resizeState.value.startWidth + deltaX),
          Math.min(PANEL_MAX_WIDTH, window.innerWidth - panelPos.value.x - 8)
        );
      }
      if (
        resizeState.value.mode === 'bottom' ||
        resizeState.value.mode === 'bottom-right'
      ) {
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
        x: Math.max(
          0,
          Math.min(window.innerWidth - 80, e.clientX - dragState.value.offsetX)
        ),
        y: Math.max(
          60,
          Math.min(window.innerHeight - 80, e.clientY - dragState.value.offsetY)
        ),
      };
      return;
    }
    panelPos.value = {
      x: Math.max(
        0,
        Math.min(
          window.innerWidth - panelSize.value.width,
          e.clientX - dragState.value.offsetX
        )
      ),
      y: Math.max(
        60,
        Math.min(
          window.innerHeight - panelSize.value.height,
          e.clientY - dragState.value.offsetY
        )
      ),
    };
  };
  const startResize = (
    e: MouseEvent,
    mode: 'right' | 'bottom' | 'bottom-right'
  ) => {
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
  @nav-size-height: 60px;
  @layout-max-width: 1100px;

  .layout {
    width: 100%;
    height: 100%;
  }

  .layout-navbar {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 100;
    width: 100%;
    height: @nav-size-height;
  }

  .layout-sider {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 99;
    height: 100%;
    transition: all 0.2s cubic-bezier(0.34, 0.69, 0.1, 1);

    &::after {
      position: absolute;
      top: 0;
      right: -1px;
      display: block;
      width: 1px;
      height: 100%;
      background-color: var(--color-border);
      content: '';
    }

    > :deep(.arco-layout-sider-children) {
      overflow-y: hidden;
    }
  }

  .menu-wrapper {
    height: 100%;
    overflow: auto;
    overflow-x: hidden;

    :deep(.arco-menu) {
      ::-webkit-scrollbar {
        width: 12px;
        height: 4px;
      }

      ::-webkit-scrollbar-thumb {
        border: 4px solid transparent;
        background-clip: padding-box;
        border-radius: 7px;
        background-color: var(--color-text-4);
      }

      ::-webkit-scrollbar-thumb:hover {
        background-color: var(--color-text-3);
      }
    }
  }

  .layout-content {
    min-height: 100vh;
    overflow-y: hidden;
    display: flex;
    flex-direction: column;
    background-color: var(--color-fill-2);
    transition: padding 0.2s cubic-bezier(0.34, 0.69, 0.1, 1);

    > :deep(.arco-layout-content) {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
    }
  }

  .float-ai {
    position: fixed;
    bottom: 0px;
    right: 0px;
    z-index: 1;
  }

  .float-btn {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 10000;
    cursor: move;
  }

  .float-btn .arco-btn-primary,
  .arco-btn-primary[type='button'] {
    height: 70px;
    width: 70px;
    border-radius: 50%;
    background: var(--zy-gradient-brand, linear-gradient(135deg, #6366f1, #8b5cf6)) !important;
    border: none !important;
    box-shadow: 0 8px 28px rgba(99, 102, 241, 0.45);
    transition: all 0.2s ease;
  }
  .float-btn .arco-btn-primary:hover {
    filter: brightness(1.08);
    transform: scale(1.05);
    box-shadow: 0 12px 36px rgba(139, 92, 246, 0.4);
  }
  .arco-drawer-body {
    padding: 5px;
  }

  .float-ai-panel {
    position: fixed;
    z-index: 10001;
    display: flex;
    flex-direction: column;
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 20px 40px rgba(15, 23, 42, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.9);
    background: #e9fbf4;
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
      color: #2a4b43;
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
