<script setup lang="ts">
  import type { MegaMenuItem } from '@/config/top-nav-menu';

  defineProps<{
    items: MegaMenuItem[];
    label: string;
  }>();

  const emit = defineEmits<{
    (e: 'close'): void;
    (e: 'navigate', name: string): void;
  }>();

  const go = (name: string) => {
    emit('navigate', name);
    emit('close');
  };
</script>

<template>
  <div class="mega-panel">
    <div class="mega-panel__head">
      <h3>{{ label }}</h3>
      <span>选择功能模块</span>
    </div>
    <div class="mega-panel__grid">
      <button
        v-for="item in items"
        :key="item.routeName"
        type="button"
        class="mega-item"
        @click="go(item.routeName)"
      >
        <span class="mega-item__icon">
          <icon-apps v-if="item.icon === 'icon-apps'" />
          <icon-message v-else-if="item.icon === 'icon-message'" />
          <icon-book v-else-if="item.icon === 'icon-book'" />
          <icon-play-circle v-else-if="item.icon === 'icon-play-circle'" />
          <icon-file v-else-if="item.icon === 'icon-file'" />
          <icon-camera v-else-if="item.icon === 'icon-camera'" />
          <icon-storage v-else-if="item.icon === 'icon-storage'" />
          <icon-bar-chart v-else-if="item.icon === 'icon-bar-chart'" />
          <icon-folder v-else-if="item.icon === 'icon-folder'" />
          <icon-edit v-else-if="item.icon === 'icon-edit'" />
          <icon-user-group v-else-if="item.icon === 'icon-user-group'" />
          <icon-home v-else-if="item.icon === 'icon-home'" />
          <icon-dashboard v-else-if="item.icon === 'icon-dashboard'" />
          <icon-trophy v-else-if="item.icon === 'icon-trophy'" />
          <icon-notification v-else-if="item.icon === 'icon-notification'" />
          <icon-settings v-else-if="item.icon === 'icon-settings'" />
          <icon-apps v-else />
        </span>
        <span class="mega-item__body">
          <strong>{{ item.title }}</strong>
          <small>{{ item.desc }}</small>
        </span>
        <span class="mega-item__arrow">→</span>
      </button>
    </div>
  </div>
</template>

<style scoped lang="less">
  .mega-panel {
    width: min(760px, 92vw);
    padding: 22px 24px 20px;
    border-radius: 20px;
    background: #fff;
    box-shadow: 0 24px 60px rgba(15, 23, 42, 0.2);
    border: 1px solid rgba(99, 102, 241, 0.12);
  }

  .mega-panel__head {
    margin-bottom: 16px;
    h3 { margin: 0; font-size: 18px; color: #0f172a; }
    span { font-size: 13px; color: #64748b; }
  }

  .mega-panel__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .mega-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px;
    border: 1px solid #e8ecff;
    border-radius: 16px;
    background: #fff;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s ease;
    &:hover {
      border-color: #c7d2fe;
      box-shadow: 0 12px 28px rgba(99, 102, 241, 0.15);
      transform: translateY(-2px);
    }
  }

  .mega-item__icon {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #f0f2ff;
    color: #6366f1;
    font-size: 18px;
    flex-shrink: 0;
  }

  .mega-item__body {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
    strong { font-size: 14px; color: #0f172a; }
    small { font-size: 12px; color: #64748b; line-height: 1.4; }
  }

  .mega-item__arrow { color: #94a3b8; }

  @media (max-width: 640px) {
    .mega-panel__grid { grid-template-columns: 1fr; }
  }
</style>
