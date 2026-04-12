<template>
  <div class="navbar" :class="{ 'navbar--scrolled': isScrolled }">
    <!-- ===== Logo 区（左） ===== -->
    <div class="left-side">
      <!-- 新 Logo -->
      <div class="brand-logo">
        <img :src="logoImg" alt="智屿" style="height: 36px; width: auto;" />

        <!-- 品牌文字 -->
        <div class="brand-text">
          <span class="brand-name">智屿</span>
          <span class="brand-subtitle">智能教育平台</span>
        </div>
      </div>

      <!-- 移动端汉堡菜单 -->
      <icon-menu-fold
        v-if="!topMenu && appStore.device === 'mobile'"
        class="mobile-menu-icon"
        @click="toggleDrawerMenu"
      />
    </div>

    <!-- ===== 顶部导航菜单（桌面端） ===== -->
    <div class="center-side">
      <Menu v-if="topMenu" />
    </div>

    <!-- ===== 右侧工具栏 ===== -->
    <ul class="right-side">
      <li>
        <a-tooltip :content="$t('settings.search')">
          <a-button class="nav-btn" type="outline" :shape="'circle'">
            <template #icon>
              <icon-search />
            </template>
          </a-button>
        </a-tooltip>
      </li>
      <li>
        <a-tooltip :content="$t('settings.language')">
          <a-button
            class="nav-btn"
            type="outline"
            :shape="'circle'"
            @click="setDropDownVisible"
          >
            <template #icon>
              <icon-language />
            </template>
          </a-button>
        </a-tooltip>
        <a-dropdown trigger="click" @select="changeLocale as any">
          <div ref="triggerBtn" class="trigger-btn"></div>
          <template #content>
            <a-doption
              v-for="item in locales"
              :key="item.value"
              :value="item.value"
            >
              <template #icon>
                <icon-check v-show="item.value === currentLocale" />
              </template>
              {{ item.label }}
            </a-doption>
          </template>
        </a-dropdown>
      </li>
      <li>
        <a-tooltip
          :content="
            theme === 'light'
              ? $t('settings.navbar.theme.toDark')
              : $t('settings.navbar.theme.toLight')
          "
        >
          <a-button
            class="nav-btn"
            type="outline"
            :shape="'circle'"
            @click="handleToggleTheme"
          >
            <template #icon>
              <icon-moon-fill v-if="theme === 'dark'" />
              <icon-sun-fill v-else />
            </template>
          </a-button>
        </a-tooltip>
      </li>
      <li>
        <!-- 🔔 通知铃铛：有未读时显示红点 Badge -->
        <a-tooltip :content="$t('settings.navbar.alerts')">
          <div class="message-box-trigger">
            <a-badge :count="9" dot>
              <a-button
                class="nav-btn"
                type="outline"
                :shape="'circle'"
                @click="setPopoverVisible"
              >
                <icon-notification />
              </a-button>
            </a-badge>
          </div>
        </a-tooltip>
        <a-popover
          trigger="click"
          :arrow-style="{ display: 'none' }"
          :content-style="{ padding: 0, minWidth: '400px' }"
          content-class="message-popover"
        >
          <div ref="refBtn" class="ref-btn"></div>
          <template #content>
            <message-box />
          </template>
        </a-popover>
      </li>
      <li>
        <a-tooltip
          :content="
            isFullscreen
              ? $t('settings.navbar.screen.toExit')
              : $t('settings.navbar.screen.toFull')
          "
        >
          <a-button
            class="nav-btn"
            type="outline"
            :shape="'circle'"
            @click="toggleFullScreen"
          >
            <template #icon>
              <icon-fullscreen-exit v-if="isFullscreen" />
              <icon-fullscreen v-else />
            </template>
          </a-button>
        </a-tooltip>
      </li>
      <li>
        <a-tooltip :content="$t('settings.title')">
          <a-button
            class="nav-btn"
            type="outline"
            :shape="'circle'"
            @click="setVisible"
          >
            <template #icon>
              <icon-settings />
            </template>
          </a-button>
        </a-tooltip>
      </li>
      <!-- 用户头像 + 下拉菜单 -->
      <li class="user-avatar-li">
        <a-dropdown trigger="click">
          <div class="user-avatar-wrapper">
            <a-avatar :size="34" class="user-avatar">
              <img alt="avatar" :src="avatar" />
            </a-avatar>
          </div>
          <template #content>
            <a-doption class="dropdown-option">
              <a-space @click="switchRoles">
                <icon-tag />
                <span>{{ $t('messageBox.switchRoles') }}</span>
              </a-space>
            </a-doption>
            <a-doption class="dropdown-option">
              <a-space @click="$router.push({ name: 'Info' })">
                <icon-user />
                <span>{{ $t('messageBox.userCenter') }}</span>
              </a-space>
            </a-doption>
            <a-doption class="dropdown-option">
              <a-space @click="$router.push({ name: 'Setting' })">
                <icon-settings />
                <span>{{ $t('messageBox.userSettings') }}</span>
              </a-space>
            </a-doption>
            <a-doption class="dropdown-option dropdown-option--danger">
              <a-space @click="handleLogout">
                <icon-export />
                <span>{{ $t('messageBox.logout') }}</span>
              </a-space>
            </a-doption>
          </template>
        </a-dropdown>
      </li>
    </ul>
  </div>
</template>

<script lang="ts" setup>
  import logoImg from '@/assets/icons/newlogo.jpg';
  import Menu from '@/components/menu/index.vue';
  import useLocale from '@/hooks/locale';
  import useUser from '@/hooks/user';
  import { LOCALE_OPTIONS } from '@/locale';
  import { useAppStore, useUserStore } from '@/store';
  import { Message } from '@arco-design/web-vue';
  import { useDark, useFullscreen, useToggle } from '@vueuse/core';
  import { computed, inject, onMounted, onUnmounted, ref } from 'vue';
  import MessageBox from '../message-box/index.vue';

  // 滚动检测：滚动后导航栏切换为毛玻璃区
  const isScrolled = ref(false);
  const handleScroll = () => {
    isScrolled.value = window.scrollY > 10;
  };
  onMounted(() => { window.addEventListener('scroll', handleScroll, { passive: true }); });
  onUnmounted(() => { window.removeEventListener('scroll', handleScroll); });

  const appStore = useAppStore();

  const userStore = useUserStore();
  const { logout } = useUser();
  const { changeLocale, currentLocale } = useLocale();
  const { isFullscreen, toggle: toggleFullScreen } = useFullscreen();
  const locales = [...LOCALE_OPTIONS];
  const avatar = computed(() => {
    return userStore.avatar;
  });
  const theme = computed(() => {
    return appStore.theme;
  });
  const topMenu = computed(() => appStore.topMenu && appStore.menu);
  const isDark = useDark({
    selector: 'body',
    attribute: 'arco-theme',
    valueDark: 'dark',
    valueLight: 'light',
    storageKey: 'arco-theme',
    onChanged(dark: boolean) {
      // overridden default behavior
      appStore.toggleTheme(dark);
    },
  });
  const toggleTheme = useToggle(isDark);
  const handleToggleTheme = () => {
    toggleTheme();
  };
  const setVisible = () => {
    appStore.updateSettings({ globalSettings: true });
  };
  const refBtn = ref();
  const triggerBtn = ref();
  const setPopoverVisible = () => {
    const event = new MouseEvent('click', {
      view: window,
      bubbles: true,
      cancelable: true,
    });
    refBtn.value.dispatchEvent(event);
  };
  const handleLogout = () => {
    logout();
  };
  const setDropDownVisible = () => {
    const event = new MouseEvent('click', {
      view: window,
      bubbles: true,
      cancelable: true,
    });
    triggerBtn.value.dispatchEvent(event);
  };
  const switchRoles = async () => {
    const res = await userStore.switchRoles();
    Message.success(res as string);
  };
  const toggleDrawerMenu = inject('toggleDrawerMenu') as () => void;
</script>

<style scoped lang="less">
  /* 智屿平台品牌导航栏
   * 规格：高度 64px，白底，滚动后毛玻璃效果
   * 文档：designup.md §1
   */
  .navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 100%;
    background-color: #FFFFFF;
    border-bottom: 1px solid rgba(99, 102, 241, 0.15);
    transition: background-color 0.3s ease, backdrop-filter 0.3s ease, box-shadow 0.3s ease;
  }

  /* 滚动后：毛玻璃半透明状态 */
  .navbar--scrolled {
    background-color: rgba(255, 255, 255, 0.88);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: 0 2px 16px rgba(99, 102, 241, 0.10);
  }

  /* ===== Logo 区 ===== */
  .left-side {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-left: 24px;
  }

  .brand-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    text-decoration: none;
  }

  .brand-text {
    display: flex;
    flex-direction: column;
    line-height: 1;
  }

  .brand-name {
    font-size: 18px;
    font-weight: 700;
    color: var(--zy-color-text-primary, #0f172a);
    letter-spacing: 0.02em;
    font-family: var(--zy-font-display);
  }

  .brand-subtitle {
    font-size: 11px;
    color: var(--zy-color-text-secondary, #64748b);
    margin-top: 2px;
    letter-spacing: 0.03em;
  }

  .mobile-menu-icon {
    font-size: 22px;
    cursor: pointer;
    color: var(--zy-color-text-primary, #0f172a);
  }

  /* ===== 中部导航 ===== */
  .center-side {
    flex: 1;
  }

  /* ===== 右侧工具栏 ===== */
  .right-side {
    display: flex;
    align-items: center;
    padding-right: 24px;
    list-style: none;
    margin: 0;

    :deep(.locale-select) {
      border-radius: 20px;
    }

    li {
      display: flex;
      align-items: center;
      padding: 0 6px;
    }

    a {
      color: var(--color-text-1);
      text-decoration: none;
    }

    /* 导航按鈕：绝边框，悬停时变绿色 */
    .nav-btn {
      border-color: rgba(99, 102, 241, 0.25);
      color: var(--zy-color-text-secondary, #64748b);
      font-size: 16px;
      transition: all 0.2s ease;

      &:hover {
        border-color: var(--zy-color-brand, #6366f1);
        color: var(--zy-color-brand, #6366f1);
        background-color: rgba(99, 102, 241, 0.06);
      }
    }

    .trigger-btn,
    .ref-btn {
      position: absolute;
      bottom: 14px;
    }

    .trigger-btn {
      margin-left: 14px;
    }
  }

  /* ===== 用户头像 ===== */
  .user-avatar-li {
    padding-left: 8px !important;
  }

  .user-avatar-wrapper {
    cursor: pointer;
    border-radius: 50%;
    padding: 2px;
    border: 2px solid transparent;
    transition: border-color 0.2s ease;

    &:hover {
      border-color: var(--zy-color-brand, #6366f1);
    }
  }

  /* ===== 下拉菜单 ===== */
  :deep(.dropdown-option--danger) {
    color: var(--zy-color-coral, #F97316);
  }
</style>

<style lang="less">
  .message-popover {
    .arco-popover-content {
      margin-top: 0;
    }
  }
</style>
