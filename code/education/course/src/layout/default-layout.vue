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
      :style="{ left: `${panelPos.x}px`, top: `${panelPos.y}px` }"
    >
      <div class="panel-header" @mousedown="startDragPanel">
        <span>课堂 AI 助理</span>
        <a-button size="mini" type="text" @click="handleCancel">关闭</a-button>
      </div>
      <ClassroomQuickChat />
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
  const robotPos = ref({
    x: window.innerWidth - 100,
    y: window.innerHeight - 120,
  });
  const panelPos = ref({ x: window.innerWidth - 500, y: 110 });
  const dragState = ref<{
    target: 'robot' | 'panel' | null;
    offsetX: number;
    offsetY: number;
  }>({
    target: null,
    offsetX: 0,
    offsetY: 0,
  });

  const handleClick = () => {
    if (route.name === 'Monitor') {
      visible.value = true;
      panelPos.value = {
        x: Math.min(panelPos.value.x, window.innerWidth - 460),
        y: Math.min(panelPos.value.y, window.innerHeight - 740),
      };
      return;
    }
    router.push({ name: 'Chat' });
  };
  const handleOk = () => {
    visible.value = false;
  };
  const handleCancel = () => {
    visible.value = false;
  };
  const hideFloatUI = computed(() => route.path === '/profile/chat');

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
        Math.min(window.innerWidth - 460, e.clientX - dragState.value.offsetX)
      ),
      y: Math.max(
        60,
        Math.min(window.innerHeight - 740, e.clientY - dragState.value.offsetY)
      ),
    };
  };
  const onDragEnd = () => {
    dragState.value.target = null;
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
    background-color: var(--color-fill-2);
    transition: padding 0.2s cubic-bezier(0.34, 0.69, 0.1, 1);
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
    background-color: #21ccff;
  }
  .arco-drawer-body {
    padding: 5px;
  }

  .float-ai-panel {
    position: fixed;
    width: 440px;
    height: 720px;
    z-index: 10001;
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
</style>
