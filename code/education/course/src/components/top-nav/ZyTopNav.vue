<script setup lang="ts">
  import { computed, onMounted, onUnmounted, ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useUserStore } from '@/store';
  import { fetchStudentMessages } from '@/api/student-hub';
  import { getTopNavGroups, type TopNavGroup } from '@/config/top-nav-menu';
  import { SCENARIO_COURSE_IDS } from '@/data/teachingScenario';
  import ZyMegaMenuPanel from './ZyMegaMenuPanel.vue';
  import logoImg from '@/assets/logo.svg?url';

  const userStore = useUserStore();
  const router = useRouter();
  const route = useRoute();

  const activeGroup = ref<string | null>(null);
  const mobileOpen = ref(false);
  const isScrolled = ref(false);
  const unreadCount = ref(0);

  const navGroups = computed(() =>
    getTopNavGroups(userStore.role || 'student')
  );

  const activePanel = computed<TopNavGroup | null>(() => {
    if (!activeGroup.value) return null;
    return navGroups.value.find((g) => g.key === activeGroup.value) || null;
  });

  const displayName = computed(
    () => userStore.name || userStore.email || '同学'
  );

  const navigateByName = async (name: string) => {
    closeMenu();
    mobileOpen.value = false;
    if (name === 'CourseOne') {
      await router.push({
        name: 'CourseOne',
        params: { id: SCENARIO_COURSE_IDS[0] },
      });
      return;
    }
    await router.push({ name });
  };

  const handleNavClick = async (group: TopNavGroup) => {
    const hasMenu = Boolean(group.items?.length);
    if (!hasMenu && group.routeName) {
      await navigateByName(group.routeName);
      return;
    }
    if (activeGroup.value === group.key) {
      if (group.routeName) {
        await navigateByName(group.routeName);
      } else {
        closeMenu();
      }
      return;
    }
    activeGroup.value = group.key;
  };

  const closeMenu = () => {
    activeGroup.value = null;
  };

  const isActive = (group: TopNavGroup) => {
    if (group.routeName && route.name === group.routeName) return true;
    return Boolean(group.items?.some((item) => item.routeName === route.name));
  };

  const onDocClick = (e: MouseEvent) => {
    const target = e.target as HTMLElement | null;
    if (!target?.closest('.zy-topnav') && !target?.closest('.zy-mega-overlay')) {
      closeMenu();
    }
  };

  const onKeydown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') closeMenu();
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      router.push({ name: 'AssistantHome', query: { search: '1' } });
    }
  };

  const onScroll = () => {
    isScrolled.value = window.scrollY > 12;
  };

  onMounted(async () => {
    document.addEventListener('click', onDocClick);
    window.addEventListener('keydown', onKeydown);
    window.addEventListener('scroll', onScroll, { passive: true });
    try {
      const msgs = await fetchStudentMessages(30);
      unreadCount.value = msgs.filter((m) => !m.is_read).length;
    } catch {
      unreadCount.value = 0;
    }
  });

  onUnmounted(() => {
    document.removeEventListener('click', onDocClick);
    window.removeEventListener('keydown', onKeydown);
    window.removeEventListener('scroll', onScroll);
  });
</script>

<template>
  <header class="zy-topnav" :class="{ 'zy-topnav--scrolled': isScrolled }">
    <div class="zy-topnav__inner">
      <router-link
        :to="{ name: userStore.role === 'teacher' ? 'Workplace' : 'AssistantHome' }"
        class="zy-topnav__brand"
        @click="closeMenu"
      >
        <img :src="logoImg" alt="智屿" class="zy-topnav__logo" />
        <div>
          <strong>智屿</strong>
          <small>智能教育平台</small>
        </div>
      </router-link>

      <button type="button" class="zy-topnav__mobile" @click="mobileOpen = true">
        <icon-menu />
      </button>

      <nav class="zy-topnav__menu">
        <button
          v-for="group in navGroups"
          :key="group.key"
          type="button"
          class="zy-topnav__link"
          :class="{ 'is-active': isActive(group) || activeGroup === group.key }"
          @click.stop="handleNavClick(group)"
        >
          {{ group.label }}
          <icon-down v-if="group.items?.length" class="zy-topnav__caret" />
        </button>
      </nav>

      <a-drawer
        v-model:visible="mobileOpen"
        placement="left"
        :width="300"
        :footer="false"
        title="智屿导航"
      >
        <div class="zy-mobile-nav">
          <template v-for="group in navGroups" :key="group.key">
            <button
              type="button"
              class="zy-mobile-nav__group"
              @click="handleNavClick(group)"
            >
              {{ group.label }}
            </button>
            <div v-if="group.items?.length" class="zy-mobile-nav__items">
              <button
                v-for="item in group.items"
                :key="item.routeName"
                type="button"
                @click="navigateByName(item.routeName)"
              >
                {{ item.title }}
              </button>
            </div>
          </template>
        </div>
      </a-drawer>

      <div class="zy-topnav__actions">
        <button
          type="button"
          class="zy-topnav__search"
          @click="router.push({ name: 'AssistantHome', query: { search: '1' } })"
        >
          <icon-search />
          <span>搜索课程、资源、知识点…</span>
          <kbd>⌘K</kbd>
        </button>
        <a-badge :count="unreadCount" :dot="unreadCount > 0">
          <a-button shape="circle" type="outline" @click="navigateByName('ProfileMessages')">
            <icon-notification />
          </a-button>
        </a-badge>
        <a-dropdown trigger="click">
          <button type="button" class="zy-topnav__user">
            <a-avatar :size="32">{{ displayName.slice(0, 1) }}</a-avatar>
            <span>{{ displayName }}</span>
            <icon-down />
          </button>
          <template #content>
            <a-doption @click="navigateByName('ProfileUserInfo')">用户设置</a-doption>
            <a-doption @click="userStore.logout()">退出登录</a-doption>
          </template>
        </a-dropdown>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="activePanel?.items?.length" class="zy-mega-overlay" @click="closeMenu">
        <div class="zy-mega-overlay__panel" @click.stop>
          <ZyMegaMenuPanel
            :label="activePanel.label"
            :items="activePanel.items"
            @close="closeMenu"
            @navigate="navigateByName"
          />
        </div>
      </div>
    </Teleport>
  </header>
</template>

<style scoped lang="less">
  .zy-topnav {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 300;
    height: 64px;
    background: rgba(255, 255, 255, 0.92);
    backdrop-filter: blur(14px);
    border-bottom: 1px solid transparent;
    transition: all 0.25s ease;
  }

  .zy-topnav--scrolled {
    border-bottom-color: rgba(99, 102, 241, 0.12);
    box-shadow: var(--zy-shadow-nav);
  }

  .zy-topnav__inner {
    max-width: 1440px;
    margin: 0 auto;
    height: 64px;
    padding: 0 24px;
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .zy-topnav__brand {
    display: flex;
    align-items: center;
    gap: 10px;
    text-decoration: none;
    color: inherit;
    flex-shrink: 0;
    strong { display: block; font-size: 16px; color: #0f172a; }
    small { display: block; font-size: 11px; color: #64748b; }
  }

  .zy-topnav__logo { width: 34px; height: 34px; }

  .zy-topnav__menu {
    display: flex;
    align-items: center;
    gap: 2px;
    flex: 1;
    min-width: 0;
    overflow-x: auto;
    scrollbar-width: none;

    &::-webkit-scrollbar {
      display: none;
    }
  }

  .zy-topnav__link {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    border: none;
    background: transparent;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    color: #4b5563;
    cursor: pointer;
    transition: color 0.2s ease;
    letter-spacing: 0.02em;
    white-space: nowrap;

    &:hover {
      color: #6366f1;
    }

    &.is-active {
      color: #6366f1;
      font-weight: 600;

      &::after {
        content: '';
        position: absolute;
        left: 10px;
        right: 10px;
        bottom: 2px;
        height: 2px;
        border-radius: 2px;
        background: linear-gradient(90deg, #6366f1, #4f46e5);
      }
    }
  }

  .zy-topnav__caret { font-size: 12px; opacity: 0.6; }

  .zy-topnav__actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }

  .zy-topnav__search {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    height: 36px;
    padding: 0 12px;
    border-radius: 999px;
    border: 1px solid rgba(99, 102, 241, 0.15);
    background: #fff;
    color: #64748b;
    cursor: pointer;
    font-size: 13px;
    span { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    kbd { font-size: 11px; padding: 2px 6px; border-radius: 6px; background: #f1f5f9; color: #94a3b8; }
  }

  .zy-topnav__user {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: none;
    background: transparent;
    cursor: pointer;
    color: #334155;
    font-size: 13px;
  }

  .zy-topnav__mobile {
    display: none;
    border: none;
    background: transparent;
    font-size: 20px;
    color: #475569;
    cursor: pointer;
  }

  .zy-mobile-nav__group {
    width: 100%;
    text-align: left;
    border: none;
    background: #f8fafc;
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 8px;
    font-weight: 600;
    cursor: pointer;
  }

  .zy-mobile-nav__items {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin: 0 0 12px 8px;
    button {
      border: none;
      background: transparent;
      text-align: left;
      padding: 8px 10px;
      border-radius: 8px;
      cursor: pointer;
      color: #475569;
      &:hover { background: #f0f2ff; color: #6366f1; }
    }
  }

  @media (max-width: 960px) {
    .zy-topnav__search span { display: none; }
    .zy-topnav__menu { display: none; }
    .zy-topnav__mobile { display: inline-flex; }
  }
</style>

<style lang="less">
  .zy-mega-overlay {
    position: fixed;
    inset: 0;
    z-index: 250;
    background: rgba(15, 23, 42, 0.45);
    backdrop-filter: blur(2px);
    display: flex;
    justify-content: center;
    padding-top: 72px;
    animation: zyMegaFade 0.18s ease;
  }

  .zy-mega-overlay__panel {
    position: relative;
    z-index: 251;
    pointer-events: auto;
  }

  @keyframes zyMegaFade {
    from { opacity: 0; }
    to { opacity: 1; }
  }
</style>
